from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Iterator

from app.db.fntv_readonly import open_fntv_connection
from app.db.schema_check import find_column, quote_identifier
from app.services import fntv_schema_adapter as adapter

ALLOWED_DAYS = {7, 30, 90}
MAX_DAYS = 180
MAX_TREND_DAYS = 365
MAX_LIMIT = 50
MEDIA_TYPE_LABELS = {
    "episode": "单集",
    "season": "季",
    "movie": "电影",
    "tv": "剧集",
    "series": "剧集",
    "video": "视频",
    "directory": "目录",
    "mediadb": "媒体库",
}


@contextmanager
def _readonly_connection(conn: sqlite3.Connection | None = None) -> Iterator[sqlite3.Connection]:
    if conn is not None:
        yield conn
        return
    with open_fntv_connection() as active_conn:
        yield active_conn


def normalize_days(days: int | str | None, *, allow_all: bool = False) -> int | str:
    if allow_all and days == "all":
        return "all"
    try:
        clean = int(days) if days is not None else 30
    except (TypeError, ValueError):
        clean = 30
    return max(1, min(MAX_DAYS, clean))


def normalize_limit(limit: int | None) -> int:
    try:
        clean = int(limit) if limit is not None else 10
    except (TypeError, ValueError):
        clean = 10
    return max(1, min(MAX_LIMIT, clean))


def overview(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _readonly_connection(conn) as active_conn:
        schema = adapter.detect_schema(conn=active_conn)
        users = _count_table(active_conn, schema.users.table, _visible_column(schema, schema.users.table))
        media = _count_table(active_conn, schema.items.table, _visible_column(schema, schema.items.table))
        play_stats = _overview_play_stats(active_conn, schema)
        return {
            "total_users": users,
            "total_media": media,
            "total_play_records": play_stats["total_play_records"],
            "watched_records": play_stats["watched_records"],
            "active_users_7d": play_stats["active_users_7d"],
            "active_users_30d": play_stats["active_users_30d"],
            "plays_7d": play_stats["plays_7d"],
            "plays_30d": play_stats["plays_30d"],
            "total_watch_seconds": play_stats["total_watch_seconds"],
            "avg_progress_percent": play_stats["avg_progress_percent"],
            "generated_at": generated_at,
        }


def play_trend(days: int | str | None = 30, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    clean_days = MAX_TREND_DAYS if days == "all" else normalize_days(days)
    assert isinstance(clean_days, int)
    with _readonly_connection(conn) as active_conn:
        schema = adapter.detect_schema(conn=active_conn)
        table = schema.plays.table
        user_col = schema.plays.fields.get("user_guid")
        time_expr = adapter._play_time_expr(schema, "p")
        if not table or not time_expr:
            return _empty_trend(clean_days)
        seconds_expr = _timestamp_seconds_sql(time_expr)
        watched_expr = _watched_sql(schema.plays.fields.get("watched"), "p")
        joins, where = _play_scope(schema, include_user=True, include_item=True)
        cutoff = _days_cutoff(clean_days)
        where.append(f"{seconds_expr} >= ?")
        params: list[Any] = [cutoff]
        active_user_sql = f"COUNT(DISTINCT p.{quote_identifier(user_col)})" if user_col else "0"
        rows = active_conn.execute(
            f"""
            SELECT
                date({seconds_expr}, 'unixepoch') AS play_date,
                COUNT(*) AS play_count,
                SUM({watched_expr}) AS watched_count,
                {active_user_sql} AS active_user_count
            FROM {quote_identifier(table)} p
            {joins}
            WHERE {' AND '.join(where)}
            GROUP BY play_date
            ORDER BY play_date ASC
            """,
            params,
        ).fetchall()
        by_date = {
            str(row["play_date"]): {
                "date": str(row["play_date"]),
                "play_count": int(row["play_count"] or 0),
                "watched_count": int(row["watched_count"] or 0),
                "active_user_count": int(row["active_user_count"] or 0),
            }
            for row in rows
            if row["play_date"]
        }
        return [by_date.get(day, {"date": day, "play_count": 0, "watched_count": 0, "active_user_count": 0}) for day in _date_range(clean_days)]


def hourly_distribution(days: int | str | None = 30, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    clean_days = normalize_days(days, allow_all=True)
    buckets = [{"hour": hour, "label": f"{hour:02d}:00", "play_count": 0} for hour in range(24)]
    with _readonly_connection(conn) as active_conn:
        schema = adapter.detect_schema(conn=active_conn)
        table = schema.plays.table
        if not table:
            return buckets
        time_expr = _hourly_time_expr(schema)
        if not time_expr:
            return buckets
        seconds_expr = _timestamp_seconds_sql(time_expr)
        joins, where = _play_scope(schema, include_user=True, include_item=True)
        params: list[Any] = []
        if clean_days != "all":
            where.append(f"{seconds_expr} >= ?")
            params.append(_days_cutoff(clean_days))
        rows = active_conn.execute(
            f"""
            SELECT {seconds_expr} AS played_seconds, COUNT(*) AS play_count
            FROM {quote_identifier(table)} p
            {joins}
            WHERE {' AND '.join(where)}
            GROUP BY played_seconds
            """,
            params,
        ).fetchall()
        timezone = adapter._app_timezone()
        for row in rows:
            seconds = row["played_seconds"]
            if seconds is None:
                continue
            try:
                hour = datetime.fromtimestamp(float(seconds), timezone).hour if timezone else datetime.fromtimestamp(float(seconds)).hour
            except (OSError, OverflowError, ValueError, TypeError):
                continue
            buckets[hour]["play_count"] += int(row["play_count"] or 0)
        return buckets


def top_users(days: int | str | None = 30, limit: int | None = 10, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    clean_days = normalize_days(days, allow_all=True)
    clean_limit = normalize_limit(limit)
    with _readonly_connection(conn) as active_conn:
        schema = adapter.detect_schema(conn=active_conn)
        table = schema.plays.table
        play_user_col = schema.plays.fields.get("user_guid")
        user_table = schema.users.table
        user_guid_col = schema.users.fields.get("guid")
        time_expr = adapter._play_time_expr(schema, "p")
        if not table or not play_user_col or not user_table or not user_guid_col:
            return []
        seconds_expr = _timestamp_seconds_sql(time_expr) if time_expr else None
        watched_expr = _watched_sql(schema.plays.fields.get("watched"), "p")
        watch_seconds_expr = _duration_seconds_sql(_qualified(schema.plays.fields.get("position"), "p"))
        username_expr = _display_expr(schema, schema.users.table, "u", ("username", "nickname", "name", "display_name", "guid"))
        joins, where = _play_scope(schema, include_user=True, include_item=True)
        if clean_days != "all" and seconds_expr:
            where.append(f"{seconds_expr} >= ?")
            params: list[Any] = [_days_cutoff(clean_days)]
        else:
            params = []
        last_play_expr = f"MAX({seconds_expr})" if seconds_expr else "NULL"
        rows = active_conn.execute(
            f"""
            SELECT
                p.{quote_identifier(play_user_col)} AS user_guid,
                {username_expr} AS username,
                COUNT(*) AS play_count,
                SUM({watched_expr}) AS watched_count,
                SUM({watch_seconds_expr}) AS watch_seconds,
                {last_play_expr} AS last_played
            FROM {quote_identifier(table)} p
            {joins}
            WHERE {' AND '.join(where)}
            GROUP BY p.{quote_identifier(play_user_col)}
            ORDER BY play_count DESC, last_played DESC
            LIMIT ?
            """,
            (*params, clean_limit),
        ).fetchall()
        return [
            {
                "user_guid": str(row["user_guid"] or ""),
                "username": str(row["username"] or row["user_guid"] or ""),
                "play_count": int(row["play_count"] or 0),
                "watched_count": int(row["watched_count"] or 0),
                "watch_seconds": int(row["watch_seconds"] or 0),
                "last_played_at": adapter.normalize_timestamp(row["last_played"]),
            }
            for row in rows
        ]


def top_media(days: int | str | None = 30, limit: int | None = 10, mode: str = "episode", conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    clean_days = normalize_days(days, allow_all=True)
    clean_limit = normalize_limit(limit)
    clean_mode = mode if mode in {"episode", "series"} else "episode"
    with _readonly_connection(conn) as active_conn:
        schema = adapter.detect_schema(conn=active_conn)
        table = schema.plays.table
        play_item_col = schema.plays.fields.get("item_guid")
        item_table = schema.items.table
        item_guid_col = schema.items.fields.get("guid")
        time_expr = adapter._play_time_expr(schema, "p")
        if not table or not play_item_col or not item_table or not item_guid_col:
            return []
        seconds_expr = _timestamp_seconds_sql(time_expr) if time_expr else None
        watched_expr = _watched_sql(schema.plays.fields.get("watched"), "p")
        type_col = schema.items.fields.get("media_type")
        parent_col = schema.items.fields.get("parent_guid")
        title_expr = _display_expr(schema, schema.items.table, "i", ("title", "original_title", "filename", "name", "guid"))
        type_expr = f"i.{quote_identifier(type_col)}" if type_col else "''"
        parent_title_expr = "''"
        parent_join = _top_media_parent_join(item_table, item_guid_col, parent_col)
        if parent_col:
            parent_title_expr = _display_expr(schema, schema.items.table, "parent", ("title", "original_title", "filename", "name", "guid"), fallback="''")
        group_guid_expr = f"p.{quote_identifier(play_item_col)}"
        group_title_expr = title_expr
        group_type_expr = type_expr
        if clean_mode == "series" and parent_col:
            parent_type_expr = f"parent.{quote_identifier(type_col)}" if type_col else "''"
            grandparent_type_expr = f"grandparent.{quote_identifier(type_col)}" if type_col else "''"
            parent_title_for_group = _display_expr(schema, schema.items.table, "parent", ("title", "original_title", "filename", "name", "guid"), fallback=title_expr)
            grandparent_title_for_group = _display_expr(schema, schema.items.table, "grandparent", ("title", "original_title", "filename", "name", "guid"), fallback=parent_title_for_group)
            parent_guid_expr = f"parent.{quote_identifier(item_guid_col)}"
            grandparent_guid_expr = f"grandparent.{quote_identifier(item_guid_col)}"
            type_lower = f"LOWER(COALESCE({type_expr}, ''))"
            parent_type_lower = f"LOWER(COALESCE({parent_type_expr}, ''))"
            group_guid_expr = (
                f"CASE "
                f"WHEN {type_lower} = 'episode' AND {grandparent_guid_expr} IS NOT NULL THEN {grandparent_guid_expr} "
                f"WHEN {type_lower} = 'episode' AND {parent_guid_expr} IS NOT NULL THEN {parent_guid_expr} "
                f"WHEN {type_lower} = 'season' AND {parent_guid_expr} IS NOT NULL THEN {parent_guid_expr} "
                f"ELSE i.{quote_identifier(item_guid_col)} END"
            )
            group_title_expr = (
                f"CASE "
                f"WHEN {type_lower} = 'episode' AND {grandparent_guid_expr} IS NOT NULL THEN {grandparent_title_for_group} "
                f"WHEN {type_lower} = 'episode' AND {parent_guid_expr} IS NOT NULL THEN {parent_title_for_group} "
                f"WHEN {type_lower} = 'season' AND {parent_guid_expr} IS NOT NULL THEN {parent_title_for_group} "
                f"ELSE {title_expr} END"
            )
            group_type_expr = (
                f"CASE "
                f"WHEN {type_lower} = 'episode' AND {grandparent_guid_expr} IS NOT NULL THEN {grandparent_type_expr} "
                f"WHEN {type_lower} = 'episode' AND {parent_guid_expr} IS NOT NULL THEN "
                f"CASE WHEN {parent_type_lower} = 'season' THEN 'TV' ELSE {parent_type_expr} END "
                f"WHEN {type_lower} = 'season' AND {parent_guid_expr} IS NOT NULL THEN {parent_type_expr} "
                f"ELSE {type_expr} END"
            )
        joins, where = _play_scope(schema, include_user=True, include_item=True)
        if clean_days != "all" and seconds_expr:
            where.append(f"{seconds_expr} >= ?")
            params: list[Any] = [_days_cutoff(clean_days)]
        else:
            params = []
        last_play_expr = f"MAX({seconds_expr})" if seconds_expr else "NULL"
        rows = active_conn.execute(
            f"""
            SELECT
                {group_guid_expr} AS item_guid,
                {group_title_expr} AS title,
                {group_type_expr} AS media_type,
                {parent_title_expr} AS parent_title,
                COUNT(*) AS play_count,
                SUM({watched_expr}) AS watched_count,
                {last_play_expr} AS last_played
            FROM {quote_identifier(table)} p
            {joins}
            {parent_join}
            WHERE {' AND '.join(where)}
            GROUP BY 1, 2, 3, 4
            ORDER BY play_count DESC, last_played DESC
            LIMIT ?
            """,
            (*params, clean_limit),
        ).fetchall()
        return [
            {
                "item_guid": str(row["item_guid"] or ""),
                "title": str(row["title"] or row["item_guid"] or ""),
                "type": _top_media_type_label(row["media_type"], clean_mode),
                "play_count": int(row["play_count"] or 0),
                "watched_count": int(row["watched_count"] or 0),
                "last_played_at": adapter.normalize_timestamp(row["last_played"]),
                "parent_title": str(row["parent_title"] or ""),
            }
            for row in rows
        ]


def media_type_distribution(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    with _readonly_connection(conn) as active_conn:
        schema = adapter.detect_schema(conn=active_conn)
        table = schema.items.table
        type_col = schema.items.fields.get("media_type")
        if not table or not type_col:
            return []
        where = []
        visible_col = _visible_column(schema, table)
        if visible_col:
            where.append(f"{quote_identifier(visible_col)} = 1")
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = active_conn.execute(
            f"""
            SELECT COALESCE(NULLIF({quote_identifier(type_col)}, ''), '未知') AS media_type, COUNT(*) AS total
            FROM {quote_identifier(table)}
            {where_sql}
            GROUP BY media_type
            ORDER BY total DESC, media_type ASC
            LIMIT 100
            """
        ).fetchall()
        return [{"type": media_type_label(row["media_type"]), "count": int(row["total"] or 0)} for row in rows]


def resolution_distribution(days: int | str | None = 30, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    clean_days = normalize_days(days, allow_all=True)
    with _readonly_connection(conn) as active_conn:
        schema = adapter.detect_schema(conn=active_conn)
        table = schema.plays.table
        resolution_col = schema.plays.fields.get("resolution")
        time_expr = adapter._play_time_expr(schema, "p")
        if not table or not resolution_col:
            return []
        joins, where = _play_scope(schema, include_user=True, include_item=True)
        params: list[Any] = []
        if clean_days != "all" and time_expr:
            seconds_expr = _timestamp_seconds_sql(time_expr)
            where.append(f"{seconds_expr} >= ?")
            params.append(_days_cutoff(clean_days))
        rows = active_conn.execute(
            f"""
            SELECT COALESCE(NULLIF(TRIM(p.{quote_identifier(resolution_col)}), ''), '未记录') AS resolution, COUNT(*) AS play_count
            FROM {quote_identifier(table)} p
            {joins}
            WHERE {' AND '.join(where)}
            GROUP BY resolution
            ORDER BY play_count DESC, resolution ASC
            LIMIT 100
            """,
            params,
        ).fetchall()
        items = [{"resolution": str(row["resolution"] or "未记录"), "play_count": int(row["play_count"] or 0)} for row in rows]
        return sorted(items, key=lambda item: (item["resolution"] == "未记录", -item["play_count"], item["resolution"]))


def media_type_label(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw or raw == "未知":
        return "未知"
    return MEDIA_TYPE_LABELS.get(raw.lower(), raw)


def _top_media_type_label(value: Any, mode: str) -> str:
    raw = str(value or "").strip()
    if mode == "series" and raw.lower() in {"series", "tv"}:
        return "TV"
    return raw


def _top_media_parent_join(item_table: str, item_guid_col: str, parent_col: str | None) -> str:
    if not parent_col:
        return ""
    quoted_table = quote_identifier(item_table)
    quoted_parent = quote_identifier(parent_col)
    quoted_guid = quote_identifier(item_guid_col)
    return (
        f" LEFT JOIN {quoted_table} parent ON i.{quoted_parent} = parent.{quoted_guid}"
        f" LEFT JOIN {quoted_table} grandparent ON parent.{quoted_parent} = grandparent.{quoted_guid}"
    )


def _hourly_time_expr(schema: adapter.FntvSchemaInfo) -> str | None:
    table = schema.tables.get(schema.plays.table or "")
    if not table:
        return None
    by_lower = {column.lower(): column for column in table.columns}
    for name in ("create_time", "start_time", "update_time", "last_play_time", "played_at", "time", "timestamp"):
        column = by_lower.get(name)
        if column:
            return f"p.{quote_identifier(column)}"
    return None


def _overview_play_stats(conn: sqlite3.Connection, schema: adapter.FntvSchemaInfo) -> dict[str, Any]:
    table = schema.plays.table
    time_expr = adapter._play_time_expr(schema, "p")
    user_col = schema.plays.fields.get("user_guid")
    if not table:
        return _empty_play_stats()
    joins, where = _play_scope(schema, include_user=True, include_item=True)
    seconds_expr = _timestamp_seconds_sql(time_expr) if time_expr else None
    watched_expr = _watched_sql(schema.plays.fields.get("watched"), "p")
    watch_seconds_expr = _duration_seconds_sql(_qualified(schema.plays.fields.get("position"), "p"))
    active_7d_expr = _count_distinct_recent(user_col, seconds_expr, 7)
    active_30d_expr = _count_distinct_recent(user_col, seconds_expr, 30)
    plays_7d_expr = _count_recent(seconds_expr, 7)
    plays_30d_expr = _count_recent(seconds_expr, 30)
    avg_progress_expr = _avg_progress_expr(schema)
    rows = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total_play_records,
            SUM({watched_expr}) AS watched_records,
            {active_7d_expr} AS active_users_7d,
            {active_30d_expr} AS active_users_30d,
            {plays_7d_expr} AS plays_7d,
            {plays_30d_expr} AS plays_30d,
            SUM({watch_seconds_expr}) AS total_watch_seconds,
            {avg_progress_expr} AS avg_progress_percent
        FROM {quote_identifier(table)} p
        {joins}
        WHERE {' AND '.join(where)}
        """
    ).fetchone()
    if not rows:
        return _empty_play_stats()
    avg_progress = rows["avg_progress_percent"]
    return {
        "total_play_records": int(rows["total_play_records"] or 0),
        "watched_records": int(rows["watched_records"] or 0),
        "active_users_7d": int(rows["active_users_7d"] or 0),
        "active_users_30d": int(rows["active_users_30d"] or 0),
        "plays_7d": int(rows["plays_7d"] or 0),
        "plays_30d": int(rows["plays_30d"] or 0),
        "total_watch_seconds": int(rows["total_watch_seconds"] or 0),
        "avg_progress_percent": round(float(avg_progress), 1) if avg_progress is not None else None,
    }


def _play_scope(schema: adapter.FntvSchemaInfo, *, include_user: bool, include_item: bool) -> tuple[str, list[str]]:
    table = schema.plays.table
    if not table:
        return "", ["1 = 0"]
    joins: list[str] = []
    where: list[str] = []
    play_visible = schema.plays.fields.get("visible")
    if play_visible:
        where.append(f"p.{quote_identifier(play_visible)} = 1")
    user_visible = _visible_column(schema, schema.users.table)
    play_user_col = schema.plays.fields.get("user_guid")
    user_guid_col = schema.users.fields.get("guid")
    if include_user and schema.users.table and play_user_col and user_guid_col:
        joins.append(f"JOIN {quote_identifier(schema.users.table)} u ON p.{quote_identifier(play_user_col)} = u.{quote_identifier(user_guid_col)}")
        if user_visible:
            where.append(f"u.{quote_identifier(user_visible)} = 1")
    item_visible = _visible_column(schema, schema.items.table)
    play_item_col = schema.plays.fields.get("item_guid")
    item_guid_col = schema.items.fields.get("guid")
    if include_item and schema.items.table and play_item_col and item_guid_col:
        joins.append(f"JOIN {quote_identifier(schema.items.table)} i ON p.{quote_identifier(play_item_col)} = i.{quote_identifier(item_guid_col)}")
        if item_visible:
            where.append(f"i.{quote_identifier(item_visible)} = 1")
    if not where:
        where.append("1 = 1")
    return "\n".join(joins), where


def _visible_column(schema: adapter.FntvSchemaInfo, table_name: str | None) -> str | None:
    table = schema.tables.get(table_name or "")
    return find_column(table, ("visible", "is_visible")) if table else None


def _count_table(conn: sqlite3.Connection, table_name: str | None, visible_col: str | None) -> int:
    if not table_name:
        return 0
    where_sql = f" WHERE {quote_identifier(visible_col)} = 1" if visible_col else ""
    row = conn.execute(f"SELECT COUNT(*) AS total FROM {quote_identifier(table_name)}{where_sql}").fetchone()
    return int(row["total"] or 0) if row else 0


def _qualified(column: str | None, alias: str) -> str | None:
    return f"{alias}.{quote_identifier(column)}" if column else None


def _timestamp_seconds_sql(expr: str) -> str:
    return f"(CASE WHEN {expr} IS NULL THEN NULL WHEN CAST({expr} AS REAL) > 1000000000000 THEN CAST({expr} AS REAL) / 1000 ELSE CAST({expr} AS REAL) END)"


def _duration_seconds_sql(expr: str | None, *, runtime: bool = False) -> str:
    if not expr:
        return "0"
    if runtime:
        return (
            f"(CASE WHEN {expr} IS NULL OR {expr} = '' THEN 0 "
            f"WHEN CAST({expr} AS REAL) > 1000000 THEN CAST({expr} AS REAL) / 1000 "
            f"WHEN CAST({expr} AS REAL) BETWEEN 1 AND 600 AND CAST({expr} AS REAL) = CAST(CAST({expr} AS REAL) AS INTEGER) "
            f"THEN CAST({expr} AS REAL) * 60 "
            f"ELSE CAST({expr} AS REAL) END)"
        )
    return f"(CASE WHEN {expr} IS NULL OR {expr} = '' THEN 0 WHEN CAST({expr} AS REAL) > 1000000 THEN CAST({expr} AS REAL) / 1000 ELSE CAST({expr} AS REAL) END)"


def _watched_sql(column: str | None, alias: str) -> str:
    if not column:
        return "0"
    expr = f"{alias}.{quote_identifier(column)}"
    return (
        f"(CASE WHEN {expr} IS NULL THEN 0 "
        f"WHEN LOWER(CAST({expr} AS TEXT)) IN ('1','true','yes','y','watched','completed','finished') THEN 1 "
        f"WHEN CAST({expr} AS REAL) > 0 THEN 1 ELSE 0 END)"
    )


def _display_expr(schema: adapter.FntvSchemaInfo, table_name: str | None, alias: str, columns: tuple[str, ...], fallback: str = "''") -> str:
    table = schema.tables.get(table_name or "")
    if not table:
        return fallback
    expressions = [f"NULLIF({alias}.{quote_identifier(column)}, '')" for column in columns if column in table.columns]
    if not expressions:
        return fallback
    return f"COALESCE({', '.join(expressions)}, {fallback})"


def _count_recent(seconds_expr: str | None, days: int) -> str:
    if not seconds_expr:
        return "0"
    return f"SUM(CASE WHEN {seconds_expr} >= {_days_cutoff(days)} THEN 1 ELSE 0 END)"


def _count_distinct_recent(user_col: str | None, seconds_expr: str | None, days: int) -> str:
    if not user_col or not seconds_expr:
        return "0"
    return f"COUNT(DISTINCT CASE WHEN {seconds_expr} >= {_days_cutoff(days)} THEN p.{quote_identifier(user_col)} END)"


def _avg_progress_expr(schema: adapter.FntvSchemaInfo) -> str:
    position_expr = _duration_seconds_sql(_qualified(schema.plays.fields.get("position"), "p"))
    runtime_expr = _duration_seconds_sql(_qualified(schema.items.fields.get("runtime"), "i"), runtime=True)
    watched_expr = _watched_sql(schema.plays.fields.get("watched"), "p")
    if not schema.items.table or not schema.plays.fields.get("position") or not schema.items.fields.get("runtime"):
        return "NULL"
    return f"AVG(CASE WHEN {runtime_expr} > 0 THEN MIN(100.0, ({position_expr} / {runtime_expr}) * 100.0) WHEN {watched_expr} = 1 THEN 100.0 ELSE NULL END)"


def _days_cutoff(days: int | str) -> int:
    clean_days = int(days)
    return int(time.time()) - ((clean_days - 1) * 86_400)


def _date_range(days: int) -> list[str]:
    today = datetime.now().date()
    start = today - timedelta(days=days - 1)
    return [(start + timedelta(days=index)).isoformat() for index in range(days)]


def _empty_trend(days: int) -> list[dict[str, Any]]:
    return [{"date": day, "play_count": 0, "watched_count": 0, "active_user_count": 0} for day in _date_range(days)]


def _empty_play_stats() -> dict[str, Any]:
    return {
        "total_play_records": 0,
        "watched_records": 0,
        "active_users_7d": 0,
        "active_users_30d": 0,
        "plays_7d": 0,
        "plays_30d": 0,
        "total_watch_seconds": 0,
        "avg_progress_percent": None,
    }
