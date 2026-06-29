from __future__ import annotations

import csv
import io
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.fntv_readonly import open_fntv_connection
from app.db.schema_check import TableInfo, find_column, inspect_schema, quote_identifier
from app.models import MediaProfile, UserProfile
from app.utils.pagination import normalize_page

USER_TABLES = ("user", "users")
ITEM_TABLES = ("item", "items", "media")
PLAY_TABLES = ("item_user_play", "user_play", "play_history", "playback_history")

USER_DISPLAY_FIELDS = ("username", "nickname", "name", "display_name", "guid")
ITEM_TITLE_FIELDS = ("title", "original_title", "filename", "name", "guid")
PLAY_TIME_FIELDS = ("update_time", "create_time", "last_play_time", "timestamp", "played_at", "time")

USER_FIELD_PRIORITIES = {
    "guid": ("guid", "user_guid", "uuid", "id"),
    "username": USER_DISPLAY_FIELDS,
    "last_login_at": ("last_login_time", "last_login_at", "login_time", "last_login"),
    "is_admin": ("is_admin", "admin", "role"),
    "status": ("status", "state"),
}

ITEM_FIELD_PRIORITIES = {
    "guid": ("guid", "item_guid", "uuid", "id"),
    "title": ITEM_TITLE_FIELDS,
    "original_title": ("original_title", "original_name", "title", "filename", "name"),
    "overview": ("overview", "summary", "description"),
    "media_type": ("type", "media_type", "kind", "category"),
    "parent_guid": ("parent_guid", "parent_id", "parent", "series_guid", "season_guid"),
    "runtime": ("runtime", "duration", "length", "run_time"),
    "release_date": ("release_date", "premiere_date", "year", "date"),
    "season_number": ("season_number", "season_index", "season"),
    "episode_number": ("episode_number", "episode_index", "episode"),
}

HASH_LIKE_RE = re.compile(r"^[0-9a-f]{24,64}$", re.IGNORECASE)
UUID_LIKE_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
LONG_NUMERIC_ID_RE = re.compile(r"^\d{12,}$")

PLAY_FIELD_PRIORITIES = {
    "id": ("id", "guid", "uuid"),
    "user_guid": ("user_guid", "user_id", "uid"),
    "item_guid": ("item_guid", "item_id", "media_guid", "media_id"),
    "played_at": PLAY_TIME_FIELDS,
    "position": ("ts", "position", "playback_position", "progress"),
    "watched": ("watched", "is_watched", "completed", "finished"),
    "resolution": ("resolution", "video_resolution", "quality"),
    "visible": ("visible", "is_visible"),
    "type": ("type", "media_type"),
}


@dataclass(frozen=True)
class FntvTableInfo:
    name: str | None
    columns: list[str]


@dataclass(frozen=True)
class FntvFieldMap:
    table: str | None
    fields: dict[str, str | None]


@dataclass(frozen=True)
class FntvSchemaInfo:
    tables: dict[str, TableInfo]
    users: FntvFieldMap
    items: FntvFieldMap
    plays: FntvFieldMap
    capabilities: dict[str, bool]


def detect_schema(conn: sqlite3.Connection | None = None) -> FntvSchemaInfo:
    tables = inspect_schema(conn=conn)
    user_table = _choose_table(tables, USER_TABLES, ("user", "account", "member"))
    item_table = _choose_table(tables, ITEM_TABLES, ("item", "media", "video", "movie", "episode"))
    play_table = _choose_table(tables, PLAY_TABLES, ("item_user_play", "play", "history", "watch", "progress"))
    users = FntvFieldMap(user_table, _map_fields(tables.get(user_table), USER_FIELD_PRIORITIES))
    items = FntvFieldMap(item_table, _map_fields(tables.get(item_table), ITEM_FIELD_PRIORITIES))
    plays = FntvFieldMap(play_table, _map_fields(tables.get(play_table), PLAY_FIELD_PRIORITIES))
    capabilities = {
        "has_users": bool(users.table),
        "has_items": bool(items.table),
        "has_plays": bool(plays.table),
        "can_join_users": bool(users.table and users.fields.get("guid") and plays.fields.get("user_guid")),
        "can_join_items": bool(items.table and items.fields.get("guid") and plays.fields.get("item_guid")),
        "has_play_time": bool(plays.fields.get("played_at")),
        "has_progress": bool(plays.fields.get("position")),
        "has_runtime": bool(items.fields.get("runtime")),
        "has_resolution": bool(plays.fields.get("resolution")),
        "has_watched": bool(plays.fields.get("watched")),
    }
    return FntvSchemaInfo(tables=tables, users=users, items=items, plays=plays, capabilities=capabilities)


def get_capabilities() -> dict[str, bool]:
    return detect_schema().capabilities


def has_table(schema: FntvSchemaInfo, table_name: str | None) -> bool:
    return bool(table_name and table_name in schema.tables)


def has_column(schema: FntvSchemaInfo, table_name: str | None, column: str | None) -> bool:
    return bool(table_name and column and table_name in schema.tables and column in schema.tables[table_name].columns)


def get_user_display_columns(schema: FntvSchemaInfo) -> list[str]:
    table = schema.tables.get(schema.users.table or "")
    return [column for column in USER_DISPLAY_FIELDS if table and column in table.columns]


def get_item_display_columns(schema: FntvSchemaInfo) -> list[str]:
    table = schema.tables.get(schema.items.table or "")
    return [column for column in ITEM_TITLE_FIELDS if table and column in table.columns]


def get_play_record_columns(schema: FntvSchemaInfo) -> dict[str, str | None]:
    return schema.plays.fields


def normalize_timestamp(value: Any) -> str | None:
    number = _to_float(value)
    if number is None or number <= 0:
        return None
    if number > 1_000_000_000_000:
        number = number / 1000
    elif number < 1_000_000_000:
        return None
    try:
        return datetime.fromtimestamp(number).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return None


def normalize_duration_seconds(value: Any) -> int | None:
    number = _to_float(value)
    if number is None or number < 0:
        return None
    if number > 1_000_000:
        number = number / 1000
    return int(number)


def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "-"
    total = max(0, int(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_play_progress(position_value: Any, runtime_value: Any, watched: bool) -> dict[str, Any]:
    position_seconds = normalize_duration_seconds(position_value)
    runtime_seconds = normalize_duration_seconds(runtime_value)
    if watched and position_seconds is None and runtime_seconds is None:
        return {"position_seconds": None, "runtime_seconds": None, "progress_percent": 100, "progress": "已完成"}
    if position_seconds is not None and runtime_seconds and runtime_seconds > 0:
        percent = min(100.0, round((position_seconds / runtime_seconds) * 100, 1))
        return {
            "position_seconds": position_seconds,
            "runtime_seconds": runtime_seconds,
            "progress_percent": percent,
            "progress": f"{format_duration(position_seconds)} / {format_duration(runtime_seconds)}",
        }
    if position_seconds is not None:
        return {"position_seconds": position_seconds, "runtime_seconds": runtime_seconds, "progress_percent": None, "progress": format_duration(position_seconds)}
    return {"position_seconds": None, "runtime_seconds": runtime_seconds, "progress_percent": None, "progress": "已完成" if watched else "-"}


def overview_data() -> dict[str, Any]:
    try:
        schema = detect_schema()
        with open_fntv_connection() as conn:
            users = _count_table(conn, schema.users.table)
            media = _count_table(conn, schema.items.table)
            plays = _count_play_records(conn, schema)
            today_plays = _count_today_plays(conn, schema)
            latest_play_time = _latest_play_time(conn, schema)
        return {
            "database_ok": True,
            "total_users": users,
            "total_media": media,
            "total_play_records": plays,
            "today_plays": today_plays,
            "latest_play_time": latest_play_time,
            "capabilities": schema.capabilities,
            "candidates": {"users": schema.users.table, "media": schema.items.table, "plays": schema.plays.table},
            "table_count": len(schema.tables),
        }
    except AppError as exc:
        return _empty_overview(exc.message)
    except sqlite3.Error:
        return _empty_overview("飞牛影视数据库查询失败")


def recent_activities(limit: int = 20) -> list[dict[str, Any]]:
    try:
        schema = detect_schema()
        if not schema.plays.table:
            return []
        with open_fntv_connection() as conn:
            rows, _ = _play_rows(conn, schema, 1, limit, {})
            return _hydrate_play_rows(conn, schema, rows)
    except (AppError, sqlite3.Error):
        return []


def play_trend() -> list[dict[str, Any]]:
    return []


def top_media() -> list[dict[str, Any]]:
    return []


def top_users() -> list[dict[str, Any]]:
    return []


def history_page(page: int, page_size: int, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    try:
        schema = detect_schema()
        if not schema.plays.table:
            return _empty_page(page, page_size, capabilities=schema.capabilities)
        page_num, clean_page_size, _ = normalize_page(page, page_size)
        with open_fntv_connection() as conn:
            rows, total = _play_rows(conn, schema, page_num, clean_page_size, filters)
            items = _hydrate_play_rows(conn, schema, rows)
        pages = 0 if total == 0 else (total + clean_page_size - 1) // clean_page_size
        return {"items": items, "page": page_num, "page_size": clean_page_size, "total": total, "pages": pages, "capabilities": schema.capabilities}
    except AppError as exc:
        return _empty_page(page, page_size, error=exc.message)
    except sqlite3.Error:
        return _empty_page(page, page_size, error="飞牛影视数据库查询失败")


def history_detail(record_id: str) -> dict[str, Any] | None:
    try:
        schema = detect_schema()
        if not schema.plays.table:
            return None
        id_col = schema.plays.fields.get("id")
        where = "p.rowid = ?"
        params: list[Any] = [record_id]
        if id_col:
            where = f"(p.rowid = ? OR p.{quote_identifier(id_col)} = ?)"
            params = [record_id, record_id]
        with open_fntv_connection() as conn:
            row = conn.execute(f"SELECT p.*, p.rowid AS __rowid FROM {quote_identifier(schema.plays.table)} p WHERE {where} LIMIT 1", params).fetchone()
            if not row:
                return None
            items = _hydrate_play_rows(conn, schema, [dict(row)])
            return items[0] if items else None
    except (AppError, sqlite3.Error):
        return None


def history_csv(filters: dict[str, Any] | None = None) -> str:
    page_data = history_page(1, 1000, filters)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "username", "display_title", "played_at", "progress", "watched", "resolution"])
    writer.writeheader()
    for item in page_data["items"]:
        writer.writerow(
            {
                "id": item.get("id", ""),
                "username": item.get("username", ""),
                "display_title": item.get("display_title", ""),
                "played_at": item.get("played_at", ""),
                "progress": item.get("progress", ""),
                "watched": item.get("watched_text", ""),
                "resolution": item.get("resolution", ""),
            }
        )
    return output.getvalue()


def users_page(page: int, page_size: int, db: Session | None = None, keyword: str | None = None, show_hidden: bool = False) -> dict[str, Any]:
    try:
        schema = detect_schema()
        if not schema.users.table:
            return _empty_page(page, page_size, capabilities=schema.capabilities)
        page_num, clean_page_size, _ = normalize_page(page, page_size)
        profiles = _user_profiles(db)
        hidden_guids = set() if show_hidden else {guid for guid, profile in profiles.items() if profile.hidden}
        with open_fntv_connection() as conn:
            rows, total = _entity_rows(conn, schema.users, schema, keyword, page_num, clean_page_size, "user", exclude_guids=hidden_guids)
            stats = _user_stats_for(conn, schema, [_row_value(row, schema.users.fields.get("guid")) for row in rows])
            items = [_user_row(row, schema, profiles, stats) for row in rows]
        pages = 0 if total == 0 else (total + clean_page_size - 1) // clean_page_size
        return {"items": items, "page": page_num, "page_size": clean_page_size, "total": total, "pages": pages, "capabilities": schema.capabilities}
    except AppError as exc:
        return _empty_page(page, page_size, error=exc.message)
    except sqlite3.Error:
        return _empty_page(page, page_size, error="飞牛影视数据库查询失败")


def user_detail(guid: str, db: Session | None = None) -> dict[str, Any]:
    page_data = users_page(1, 1, db=db, keyword=guid, show_hidden=True)
    item = page_data["items"][0] if page_data["items"] else {"guid": guid, "username": guid}
    item["recent_history"] = history_page(1, 10, {"user_guid": guid})["items"]
    return item


def user_history(guid: str, page: int, page_size: int) -> dict[str, Any]:
    return history_page(page, page_size, {"user_guid": guid})


def user_stats(guid: str) -> dict[str, Any]:
    try:
        schema = detect_schema()
        with open_fntv_connection() as conn:
            return _user_stats_for(conn, schema, [guid]).get(guid, _empty_user_stats(guid))
    except (AppError, sqlite3.Error):
        return _empty_user_stats(guid)


def media_page(page: int, page_size: int, db: Session | None = None, keyword: str | None = None, media_type: str | None = None, show_hidden: bool = False) -> dict[str, Any]:
    try:
        schema = detect_schema()
        if not schema.items.table:
            return _empty_page(page, page_size, capabilities=schema.capabilities)
        page_num, clean_page_size, _ = normalize_page(page, page_size)
        profiles = _media_profiles(db)
        hidden_guids = set() if show_hidden else {guid for guid, profile in profiles.items() if profile.hidden}
        with open_fntv_connection() as conn:
            rows, total = _entity_rows(conn, schema.items, schema, keyword, page_num, clean_page_size, "media", media_type, hidden_guids)
            stats = _media_stats_for(conn, schema, [_row_value(row, schema.items.fields.get("guid")) for row in rows])
            parent_titles = _parent_titles(conn, schema, rows)
            children_counts = _children_counts(conn, schema, [_row_value(row, schema.items.fields.get("guid")) for row in rows])
            items = [_media_row(row, schema, profiles, stats, parent_titles, children_counts) for row in rows]
        pages = 0 if total == 0 else (total + clean_page_size - 1) // clean_page_size
        return {"items": items, "page": page_num, "page_size": clean_page_size, "total": total, "pages": pages, "capabilities": schema.capabilities}
    except AppError as exc:
        return _empty_page(page, page_size, error=exc.message)
    except sqlite3.Error:
        return _empty_page(page, page_size, error="飞牛影视数据库查询失败")


def media_tree() -> list[dict[str, Any]]:
    return []


def media_detail(guid: str, db: Session | None = None) -> dict[str, Any]:
    page_data = media_page(1, 1, db=db, keyword=guid, show_hidden=True)
    item = page_data["items"][0] if page_data["items"] else {"guid": guid, "title": guid}
    item["children"] = media_children(guid)
    item["history"] = media_history(guid, 1, 10)["items"]
    item["stats"] = media_stats(guid)
    return item


def media_children(guid: str) -> list[dict[str, Any]]:
    try:
        schema = detect_schema()
        parent_col = schema.items.fields.get("parent_guid")
        if not schema.items.table or not parent_col:
            return []
        guid_col = schema.items.fields.get("guid")
        with open_fntv_connection() as conn:
            rows = conn.execute(f"SELECT *, rowid AS __rowid FROM {quote_identifier(schema.items.table)} WHERE {quote_identifier(parent_col)} = ? LIMIT 200", (guid,)).fetchall()
            children_counts = _children_counts(conn, schema, [_row_value(dict(row), guid_col) for row in rows])
            return [_media_row(dict(row), schema, {}, {}, {}, children_counts) for row in rows]
    except (AppError, sqlite3.Error):
        return []


def media_history(guid: str, page: int, page_size: int) -> dict[str, Any]:
    return history_page(page, page_size, {"item_guid": guid})


def media_stats(guid: str) -> dict[str, Any]:
    try:
        schema = detect_schema()
        with open_fntv_connection() as conn:
            return _media_stats_for(conn, schema, [guid]).get(guid, _empty_media_stats(guid))
    except (AppError, sqlite3.Error):
        return _empty_media_stats(guid)


def _find_column(schema: FntvSchemaInfo, table_name: str | None, hints: tuple[str, ...]) -> str | None:
    table = schema.tables.get(table_name or "")
    return find_column(table, hints) if table else None


def _play_time_columns(schema: FntvSchemaInfo) -> list[str]:
    table = schema.tables.get(schema.plays.table or "")
    if not table:
        return []
    by_lower = {column.lower(): column for column in table.columns}
    return [by_lower[name] for name in PLAY_TIME_FIELDS if name in by_lower]


def _qualified_column(column: str, alias: str | None = None) -> str:
    prefix = f"{alias}." if alias else ""
    return f"{prefix}{quote_identifier(column)}"


def _play_time_expr(schema: FntvSchemaInfo, alias: str | None = None) -> str | None:
    columns = _play_time_columns(schema)
    if not columns:
        return None
    expressions = [f"NULLIF(NULLIF({_qualified_column(column, alias)}, 0), '')" for column in columns]
    return expressions[0] if len(expressions) == 1 else f"COALESCE({', '.join(expressions)})"


def _timestamp_seconds_expr(expr: str) -> str:
    return f"(CASE WHEN {expr} IS NULL THEN NULL WHEN CAST({expr} AS REAL) > 1000000000000 THEN CAST({expr} AS REAL) / 1000 ELSE CAST({expr} AS REAL) END)"


def _app_timezone() -> ZoneInfo | None:
    tz_name = os.getenv("TZ") or "Asia/Shanghai"
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return None


def _local_day_bounds(now: datetime | None = None) -> tuple[int, int]:
    timezone = _app_timezone()
    current = now or (datetime.now(timezone) if timezone else datetime.now().astimezone())
    if timezone and current.tzinfo is None:
        current = current.replace(tzinfo=timezone)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp())


def _play_time_value(row: dict[str, Any], schema: FntvSchemaInfo) -> Any:
    for column in _play_time_columns(schema):
        value = row.get(column)
        if value not in (None, "", 0, "0"):
            return value
    return None


def _visible_clause(schema: FntvSchemaInfo, alias: str | None = None) -> str | None:
    visible_col = schema.plays.fields.get("visible")
    if not visible_col:
        return None
    return f"{_qualified_column(visible_col, alias)} = 1"


def _choose_table(tables: dict[str, TableInfo], preferred: tuple[str, ...], hints: tuple[str, ...]) -> str | None:
    by_lower = {name.lower(): name for name in tables}
    for name in preferred:
        if name in by_lower:
            return by_lower[name]
    for name in tables:
        lower = name.lower()
        for hint in hints:
            if hint in {"user", "users", "item", "items", "item_user_play"}:
                continue
            if hint in lower:
                return name
    return None


def _map_fields(table: TableInfo | None, priorities: dict[str, tuple[str, ...]]) -> dict[str, str | None]:
    if table is None:
        return {key: None for key in priorities}
    return {key: find_column(table, hints) for key, hints in priorities.items()}


def _count_table(conn: sqlite3.Connection, table_name: str | None) -> int:
    if not table_name:
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS total FROM {quote_identifier(table_name)}").fetchone()
    return int(row["total"]) if row else 0


def _count_play_records(conn: sqlite3.Connection, schema: FntvSchemaInfo) -> int:
    table = schema.plays.table
    if not table:
        return 0
    where = _visible_clause(schema)
    where_sql = f" WHERE {where}" if where else ""
    row = conn.execute(f"SELECT COUNT(*) AS total FROM {quote_identifier(table)}{where_sql}").fetchone()
    return int(row["total"]) if row else 0


def _count_today_plays(conn: sqlite3.Connection, schema: FntvSchemaInfo) -> int:
    table = schema.plays.table
    time_expr = _play_time_expr(schema)
    if not table or not time_expr:
        return 0
    seconds_expr = _timestamp_seconds_expr(time_expr)
    # Use TZ when configured, otherwise Asia/Shanghai, so "today" matches common FNOS deployments.
    start, end = _local_day_bounds()
    where = [f"{seconds_expr} >= ?", f"{seconds_expr} < ?"]
    params: list[Any] = [start, end]
    visible = _visible_clause(schema)
    if visible:
        where.append(visible)
    row = conn.execute(f"SELECT COUNT(*) AS total FROM {quote_identifier(table)} WHERE {' AND '.join(where)}", params).fetchone()
    return int(row["total"]) if row else 0


def _latest_play_time(conn: sqlite3.Connection, schema: FntvSchemaInfo) -> str | None:
    table = schema.plays.table
    time_expr = _play_time_expr(schema)
    if not table or not time_expr:
        return None
    where = _visible_clause(schema)
    where_sql = f" WHERE {where}" if where else ""
    row = conn.execute(f"SELECT {time_expr} AS played_at FROM {quote_identifier(table)}{where_sql} ORDER BY {time_expr} DESC LIMIT 1").fetchone()
    return normalize_timestamp(row["played_at"]) if row else None


def _play_rows(conn: sqlite3.Connection, schema: FntvSchemaInfo, page: int, page_size: int, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    table = schema.plays.table
    if not table:
        return [], 0
    _, clean_page_size, offset = normalize_page(page, page_size)
    where, params, joins = _play_where(schema, filters)
    order = _play_time_expr(schema, "p")
    order_sql = f" ORDER BY {order} DESC" if order else " ORDER BY p.rowid DESC"
    from_sql = f"FROM {quote_identifier(table)} p {joins}"
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    count = conn.execute(f"SELECT COUNT(*) AS total {from_sql}{where_sql}", params).fetchone()
    rows = conn.execute(f"SELECT p.*, p.rowid AS __rowid {from_sql}{where_sql}{order_sql} LIMIT ? OFFSET ?", (*params, clean_page_size, offset)).fetchall()
    return [dict(row) for row in rows], int(count["total"]) if count else 0


def _play_where(schema: FntvSchemaInfo, filters: dict[str, Any]) -> tuple[list[str], list[Any], str]:
    where: list[str] = []
    params: list[Any] = []
    joins: list[str] = []
    fields = schema.plays.fields
    joined_items = False
    joined_users = False

    def ensure_item_join() -> None:
        nonlocal joined_items
        if joined_items or not schema.items.table or not fields.get("item_guid") or not schema.items.fields.get("guid"):
            return
        joins.append(f"LEFT JOIN {quote_identifier(schema.items.table)} i ON p.{quote_identifier(fields['item_guid'])} = i.{quote_identifier(schema.items.fields['guid'])}")
        joined_items = True

    def ensure_user_join() -> None:
        nonlocal joined_users
        if joined_users or not schema.users.table or not fields.get("user_guid") or not schema.users.fields.get("guid"):
            return
        joins.append(f"LEFT JOIN {quote_identifier(schema.users.table)} u ON p.{quote_identifier(fields['user_guid'])} = u.{quote_identifier(schema.users.fields['guid'])}")
        joined_users = True

    visible = _visible_clause(schema, "p")
    if visible:
        where.append(visible)
    if filters.get("user_guid") and fields.get("user_guid"):
        where.append(f"p.{quote_identifier(fields['user_guid'])} = ?")
        params.append(filters["user_guid"])
    if filters.get("item_guid") and fields.get("item_guid"):
        where.append(f"p.{quote_identifier(fields['item_guid'])} = ?")
        params.append(filters["item_guid"])
    if filters.get("watched") is not None and fields.get("watched"):
        where.append(f"p.{quote_identifier(fields['watched'])} = ?")
        params.append(1 if filters["watched"] else 0)
    if filters.get("resolution") and fields.get("resolution"):
        where.append(f"p.{quote_identifier(fields['resolution'])} = ?")
        params.append(filters["resolution"])
    if filters.get("progress_min") is not None and fields.get("position"):
        where.append(f"p.{quote_identifier(fields['position'])} >= ?")
        params.append(filters["progress_min"])
    if filters.get("progress_max") is not None and fields.get("position"):
        where.append(f"p.{quote_identifier(fields['position'])} <= ?")
        params.append(filters["progress_max"])
    if filters.get("media_type"):
        if fields.get("type"):
            where.append(f"LOWER(p.{quote_identifier(fields['type'])}) = LOWER(?)")
            params.append(filters["media_type"])
        elif schema.items.fields.get("media_type"):
            ensure_item_join()
            if joined_items:
                where.append(f"LOWER(i.{quote_identifier(schema.items.fields['media_type'])}) = LOWER(?)")
                params.append(filters["media_type"])
    time_expr = _play_time_expr(schema, "p")
    if filters.get("start_time") and time_expr:
        start = _parse_datetime_to_seconds(filters["start_time"])
        if start:
            where.append(f"{time_expr} >= ?")
            params.append(start)
    if filters.get("end_time") and time_expr:
        end = _parse_datetime_to_seconds(filters["end_time"])
        if end:
            where.append(f"{time_expr} <= ?")
            params.append(end)
    keyword = (filters.get("keyword") or "").strip()
    if keyword:
        keyword_where: list[str] = []
        title_columns = [
            schema.items.fields.get("title"),
            schema.items.fields.get("original_title"),
            _find_column(schema, schema.items.table, ("filename",)),
        ]
        title_columns = [col for col in dict.fromkeys(title_columns) if col]
        if title_columns:
            ensure_item_join()
            if joined_items:
                keyword_where.extend(f"i.{quote_identifier(col)} LIKE ?" for col in title_columns)
                params.extend([f"%{keyword}%"] * len(title_columns))
        user_columns = [
            schema.users.fields.get("username"),
            _find_column(schema, schema.users.table, ("nickname", "name", "display_name")),
        ]
        user_columns = [col for col in dict.fromkeys(user_columns) if col]
        if user_columns:
            ensure_user_join()
            if joined_users:
                keyword_where.extend(f"u.{quote_identifier(col)} LIKE ?" for col in user_columns)
                params.extend([f"%{keyword}%"] * len(user_columns))
        if keyword_where:
            where.append("(" + " OR ".join(keyword_where) + ")")
    return where, params, " ".join(joins)


def _hydrate_play_rows(conn: sqlite3.Connection, schema: FntvSchemaInfo, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    user_col = schema.plays.fields.get("user_guid")
    item_col = schema.plays.fields.get("item_guid")
    users = _lookup_users(conn, schema, [_row_value(row, user_col) for row in rows])
    items = _lookup_items(conn, schema, [_row_value(row, item_col) for row in rows])
    return [_play_row(row, schema, users, items) for row in rows]


def _lookup_users(conn: sqlite3.Connection, schema: FntvSchemaInfo, guids: list[Any]) -> dict[str, dict[str, Any]]:
    table = schema.users.table
    guid_col = schema.users.fields.get("guid")
    keys = [str(value) for value in guids if value not in (None, "")]
    if not table or not guid_col or not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    rows = conn.execute(f"SELECT * FROM {quote_identifier(table)} WHERE {quote_identifier(guid_col)} IN ({placeholders})", keys).fetchall()
    return {str(row[guid_col]): dict(row) for row in rows}


def _lookup_items(conn: sqlite3.Connection, schema: FntvSchemaInfo, guids: list[Any]) -> dict[str, dict[str, Any]]:
    table = schema.items.table
    guid_col = schema.items.fields.get("guid")
    keys = [str(value) for value in guids if value not in (None, "")]
    if not table or not guid_col or not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    rows = conn.execute(f"SELECT * FROM {quote_identifier(table)} WHERE {quote_identifier(guid_col)} IN ({placeholders})", keys).fetchall()
    result = {str(row[guid_col]): dict(row) for row in rows}
    for key in list(result):
        result[key]["__hierarchy_title"] = _hierarchy_title(conn, schema, result[key], max_depth=4)
    return result


def _play_row(row: dict[str, Any], schema: FntvSchemaInfo, users: dict[str, dict[str, Any]], items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fields = schema.plays.fields
    user_guid = str(_row_value(row, fields.get("user_guid")) or "")
    item_guid = str(_row_value(row, fields.get("item_guid")) or "")
    user = users.get(user_guid, {})
    item = items.get(item_guid, {})
    username = _display_user(user, schema) or user_guid
    title = item.get("__hierarchy_title") or _display_item(item, schema) or item_guid
    watched = _truthy(_row_value(row, fields.get("watched")))
    progress = format_play_progress(_row_value(row, fields.get("position")), _row_value(item, schema.items.fields.get("runtime")), watched)
    return {
        "id": str(_row_value(row, fields.get("id")) or row.get("__rowid") or ""),
        "user_guid": user_guid,
        "username": username,
        "user": username,
        "item_guid": item_guid,
        "title": title,
        "display_title": title,
        "played_at": normalize_timestamp(_play_time_value(row, schema)) or "",
        "position_seconds": progress["position_seconds"],
        "runtime_seconds": progress["runtime_seconds"],
        "progress_percent": progress["progress_percent"],
        "progress": progress["progress"],
        "watched": watched,
        "watched_text": "是" if watched else "否",
        "resolution": _row_value(row, fields.get("resolution")) or "",
    }


def _entity_rows(
    conn: sqlite3.Connection,
    fmap: FntvFieldMap,
    schema: FntvSchemaInfo,
    keyword: str | None,
    page: int,
    page_size: int,
    kind: str,
    media_type: str | None = None,
    exclude_guids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    if not fmap.table:
        return [], 0
    _, clean_page_size, offset = normalize_page(page, page_size)
    where: list[str] = []
    params: list[Any] = []
    display_cols = get_user_display_columns(schema) if kind == "user" else get_item_display_columns(schema)
    if keyword:
        cols = [col for col in (display_cols or [fmap.fields.get("guid")]) if col]
        if cols:
            where.append("(" + " OR ".join(f"{quote_identifier(col)} LIKE ?" for col in cols) + ")")
            params.extend([f"%{keyword}%"] * len(cols))
    type_col = fmap.fields.get("media_type")
    if kind == "media" and media_type and type_col:
        where.append(f"LOWER({quote_identifier(type_col)}) = LOWER(?)")
        params.append(media_type)
    guid_col = fmap.fields.get("guid")
    if exclude_guids and guid_col:
        keys = sorted(str(guid) for guid in exclude_guids if guid)
        if keys:
            placeholders = ",".join("?" for _ in keys)
            where.append(f"{quote_identifier(guid_col)} NOT IN ({placeholders})")
            params.extend(keys)
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    order_col = display_cols[0] if display_cols else fmap.fields.get("guid")
    order_sql = f" ORDER BY {quote_identifier(order_col)} ASC" if order_col else ""
    count = conn.execute(f"SELECT COUNT(*) AS total FROM {quote_identifier(fmap.table)}{where_sql}", params).fetchone()
    rows = conn.execute(f"SELECT *, rowid AS __rowid FROM {quote_identifier(fmap.table)}{where_sql}{order_sql} LIMIT ? OFFSET ?", (*params, clean_page_size, offset)).fetchall()
    return [dict(row) for row in rows], int(count["total"]) if count else 0


def _user_row(row: dict[str, Any], schema: FntvSchemaInfo, profiles: dict[str, UserProfile], stats: dict[str, dict[str, Any]]) -> dict[str, Any]:
    guid = str(_row_value(row, schema.users.fields.get("guid")) or "")
    profile = profiles.get(guid)
    row_stats = stats.get(guid, {})
    display_name = profile.display_name if profile else None
    username = display_name or _display_user(row, schema) or guid
    return {
        "guid": guid,
        "username": username,
        "raw_username": _display_user(row, schema) or guid,
        "is_admin": _truthy(_row_value(row, schema.users.fields.get("is_admin"))),
        "status": str(_row_value(row, schema.users.fields.get("status")) or "active"),
        "last_login_at": normalize_timestamp(_row_value(row, schema.users.fields.get("last_login_at"))) or "",
        "last_play_at": row_stats.get("recent_play_at") or "",
        "play_count": row_stats.get("play_count", 0),
        "watch_seconds": row_stats.get("watch_seconds", 0),
        "watch_duration": row_stats.get("watch_duration", "00:00:00"),
        "hidden": bool(profile.hidden) if profile else False,
        "display_name": display_name,
        "note": profile.note if profile else None,
    }


def _media_row(row: dict[str, Any], schema: FntvSchemaInfo, profiles: dict[str, MediaProfile], stats: dict[str, dict[str, Any]], parent_titles: dict[str, str], children_counts: dict[str, int]) -> dict[str, Any]:
    guid = str(_row_value(row, schema.items.fields.get("guid")) or "")
    profile = profiles.get(guid)
    raw_title = _display_item(row, schema) or guid
    fallback_title = _media_hierarchy_fallback_title(row, schema, parent_titles) or raw_title
    title = profile.display_title if profile and profile.display_title else fallback_title
    row_stats = stats.get(guid, {})
    runtime_seconds = normalize_duration_seconds(_row_value(row, schema.items.fields.get("runtime")))
    parent_guid = str(_row_value(row, schema.items.fields.get("parent_guid")) or "")
    return {
        "guid": guid,
        "title": title,
        "original_title": _row_value(row, schema.items.fields.get("original_title")) or raw_title,
        "media_type": str(_row_value(row, schema.items.fields.get("media_type")) or ""),
        "runtime": format_duration(runtime_seconds) if runtime_seconds is not None else "-",
        "runtime_seconds": runtime_seconds,
        "release_time": normalize_timestamp(_row_value(row, schema.items.fields.get("release_date"))) or "",
        "parent": parent_titles.get(parent_guid) or parent_guid,
        "parent_guid": parent_guid,
        "children_count": children_counts.get(guid, 0),
        "play_count": row_stats.get("play_count", 0),
        "last_play_at": row_stats.get("recent_play_at") or "",
        "hidden": bool(profile.hidden) if profile else False,
        "favorite": bool(profile.favorite) if profile else False,
        "note": profile.note if profile else None,
    }


def _media_hierarchy_fallback_title(row: dict[str, Any], schema: FntvSchemaInfo, parent_titles: dict[str, str]) -> str | None:
    base_title = _display_item(row, schema)
    media_type = str(_row_value(row, schema.items.fields.get("media_type")) or "").lower()
    parent_guid = str(_row_value(row, schema.items.fields.get("parent_guid")) or "")
    parent_title = parent_titles.get(parent_guid) or ""
    season = _row_value(row, schema.items.fields.get("season_number"))
    episode = _row_value(row, schema.items.fields.get("episode_number"))
    marker = _season_episode_marker(season, episode)
    if media_type == "season" and marker and parent_title:
        return f"{parent_title} - {marker}"
    if media_type == "episode":
        if parent_title and marker:
            return " - ".join(part for part in (_strip_trailing_season_marker(parent_title, marker), marker, base_title) if part)
        if parent_title and base_title:
            return f"{parent_title} - {base_title}"
    return base_title


def _strip_trailing_season_marker(title: str, episode_marker: str) -> str:
    season_marker = episode_marker.split("E", 1)[0]
    return re.sub(rf"\s+-\s+{re.escape(season_marker)}$", "", title).strip()


def _user_stats_for(conn: sqlite3.Connection, schema: FntvSchemaInfo, guids: list[Any]) -> dict[str, dict[str, Any]]:
    table = schema.plays.table
    user_col = schema.plays.fields.get("user_guid")
    if not table or not user_col:
        return {}
    keys = [str(value) for value in guids if value not in (None, "")]
    if not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    time_expr = _play_time_expr(schema)
    position_col = schema.plays.fields.get("position")
    select_parts = [f"{quote_identifier(user_col)} AS guid", "COUNT(*) AS play_count"]
    if position_col:
        select_parts.append(f"SUM(COALESCE({quote_identifier(position_col)}, 0)) AS watch_seconds")
    if time_expr:
        select_parts.append(f"MAX({time_expr}) AS recent_play")
    where = [f"{quote_identifier(user_col)} IN ({placeholders})"]
    visible = _visible_clause(schema)
    if visible:
        where.append(visible)
    rows = conn.execute(f"SELECT {', '.join(select_parts)} FROM {quote_identifier(table)} WHERE {' AND '.join(where)} GROUP BY {quote_identifier(user_col)}", keys).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        watch_seconds = normalize_duration_seconds(row["watch_seconds"]) if position_col else 0
        result[str(row["guid"])] = {
            "guid": str(row["guid"]),
            "play_count": int(row["play_count"] or 0),
            "watch_seconds": watch_seconds or 0,
            "watch_duration": format_duration(watch_seconds or 0),
            "recent_play_at": normalize_timestamp(row["recent_play"]) if time_expr else None,
        }
    return result


def _media_stats_for(conn: sqlite3.Connection, schema: FntvSchemaInfo, guids: list[Any]) -> dict[str, dict[str, Any]]:
    table = schema.plays.table
    item_col = schema.plays.fields.get("item_guid")
    if not table or not item_col:
        return {}
    keys = [str(value) for value in guids if value not in (None, "")]
    if not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    time_expr = _play_time_expr(schema)
    watched_col = schema.plays.fields.get("watched")
    select_parts = [f"{quote_identifier(item_col)} AS guid", "COUNT(*) AS play_count"]
    if time_expr:
        select_parts.append(f"MAX({time_expr}) AS recent_play")
    if watched_col:
        select_parts.append(f"SUM(CASE WHEN {quote_identifier(watched_col)} THEN 1 ELSE 0 END) AS watched_count")
    where = [f"{quote_identifier(item_col)} IN ({placeholders})"]
    visible = _visible_clause(schema)
    if visible:
        where.append(visible)
    rows = conn.execute(f"SELECT {', '.join(select_parts)} FROM {quote_identifier(table)} WHERE {' AND '.join(where)} GROUP BY {quote_identifier(item_col)}", keys).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        play_count = int(row["play_count"] or 0)
        watched_count = int(row["watched_count"] or 0) if watched_col else 0
        result[str(row["guid"])] = {
            "guid": str(row["guid"]),
            "play_count": play_count,
            "recent_play_at": normalize_timestamp(row["recent_play"]) if time_expr else None,
            "completion_rate": round((watched_count / play_count) * 100, 1) if play_count else 0,
        }
    return result


def _children_counts(conn: sqlite3.Connection, schema: FntvSchemaInfo, guids: list[Any]) -> dict[str, int]:
    table = schema.items.table
    parent_col = schema.items.fields.get("parent_guid")
    keys = [str(value) for value in guids if value not in (None, "")]
    if not table or not parent_col or not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    rows = conn.execute(f"SELECT {quote_identifier(parent_col)} AS parent_guid, COUNT(*) AS total FROM {quote_identifier(table)} WHERE {quote_identifier(parent_col)} IN ({placeholders}) GROUP BY {quote_identifier(parent_col)}", keys).fetchall()
    return {str(row["parent_guid"]): int(row["total"]) for row in rows}


def _parent_titles(conn: sqlite3.Connection, schema: FntvSchemaInfo, rows: list[dict[str, Any]]) -> dict[str, str]:
    parent_col = schema.items.fields.get("parent_guid")
    parent_guids = [str(_row_value(row, parent_col)) for row in rows if _row_value(row, parent_col)]
    looked_up = _lookup_items(conn, schema, parent_guids)
    return {guid: item.get("__hierarchy_title") or _display_item(item, schema) or guid for guid, item in looked_up.items()}


def _hierarchy_title(conn: sqlite3.Connection, schema: FntvSchemaInfo, row: dict[str, Any], max_depth: int) -> str:
    title = _display_item(row, schema) or ""
    parent_col = schema.items.fields.get("parent_guid")
    guid_col = schema.items.fields.get("guid")
    if not parent_col or not guid_col or not schema.items.table:
        return title
    parts = [title] if title else []
    current = row
    seen: set[str] = set()
    for _ in range(max_depth):
        parent_guid = str(_row_value(current, parent_col) or "")
        if not parent_guid or parent_guid in seen:
            break
        seen.add(parent_guid)
        parent = conn.execute(f"SELECT * FROM {quote_identifier(schema.items.table)} WHERE {quote_identifier(guid_col)} = ? LIMIT 1", (parent_guid,)).fetchone()
        if not parent:
            break
        current = dict(parent)
        parent_title = _display_item(current, schema)
        if parent_title:
            parts.insert(0, parent_title)
    season = _row_value(row, schema.items.fields.get("season_number"))
    episode = _row_value(row, schema.items.fields.get("episode_number"))
    marker = _season_episode_marker(season, episode)
    if marker and marker not in parts:
        parts.insert(max(1, len(parts) - 1), marker)
    return " - ".join(str(part) for part in parts if part) or title


def _season_episode_marker(season: Any, episode: Any) -> str | None:
    if season in (None, ""):
        return None
    try:
        season_text = f"S{int(float(season)):02d}"
        if episode in (None, ""):
            return season_text
        return f"{season_text}E{int(float(episode)):02d}"
    except (TypeError, ValueError):
        return None


def _user_profiles(db: Session | None) -> dict[str, UserProfile]:
    if db is None:
        return {}
    rows = db.scalars(select(UserProfile)).all()
    return {row.fntv_user_guid: row for row in rows}


def _media_profiles(db: Session | None) -> dict[str, MediaProfile]:
    if db is None:
        return {}
    rows = db.scalars(select(MediaProfile)).all()
    return {row.fntv_item_guid: row for row in rows}


def _display_user(row: dict[str, Any], schema: FntvSchemaInfo) -> str | None:
    for key in ("username", "nickname", "name", "display_name", "guid"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    mapped = _row_value(row, schema.users.fields.get("username"))
    return str(mapped) if mapped not in (None, "") else None


def _display_item(row: dict[str, Any], schema: FntvSchemaInfo) -> str | None:
    candidates = [
        row.get("title"),
        _row_value(row, schema.items.fields.get("title")),
        row.get("original_title"),
        _row_value(row, schema.items.fields.get("original_title")),
        row.get("filename"),
        _basename_from_path(row.get("filename")),
        _basename_from_path(row.get("path")),
        _basename_from_path(row.get("file_path")),
        _basename_from_path(row.get("filepath")),
        row.get("name"),
    ]
    media_type = str(_row_value(row, schema.items.fields.get("media_type")) or row.get("type") or "").lower()
    for value in candidates:
        text = _clean_display_text(value)
        if text and not _is_generic_media_title(text, media_type):
            return text
    return None


def _clean_display_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text or _is_meaningless_identifier(text):
        return None
    return text


def _basename_from_path(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("\\", "/").rstrip("/")
    if not text:
        return None
    return text.rsplit("/", 1)[-1]


def _is_meaningless_identifier(value: str) -> bool:
    text = value.strip()
    if UUID_LIKE_RE.fullmatch(text):
        return True
    compact = text.replace("-", "")
    if HASH_LIKE_RE.fullmatch(compact):
        return True
    return bool(LONG_NUMERIC_ID_RE.fullmatch(text))


def _is_generic_media_title(value: str, media_type: str) -> bool:
    if media_type not in {"season", "episode"}:
        return False
    text = value.strip().lower()
    if text.isdigit():
        return True
    return bool(re.fullmatch(r"(season|s)\s*0*\d+", text))


def _row_value(row: dict[str, Any], column: str | None) -> Any:
    return row.get(column) if column else None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "y", "watched", "completed", "finished"}
    return False


def _parse_datetime_to_seconds(value: Any) -> int | None:
    if value in (None, ""):
        return None
    number = _to_float(value)
    if number is not None:
        return int(number / 1000 if number > 1_000_000_000_000 else number)
    text = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(text[: len(fmt)], fmt).timestamp())
        except ValueError:
            continue
    return None


def _empty_overview(error: str) -> dict[str, Any]:
    return {
        "database_ok": False,
        "error": error,
        "total_users": 0,
        "total_media": 0,
        "total_play_records": 0,
        "today_plays": 0,
        "latest_play_time": None,
        "capabilities": {},
    }


def _empty_page(page: int, page_size: int, error: str | None = None, capabilities: dict[str, bool] | None = None) -> dict[str, Any]:
    page_num, clean_page_size, _ = normalize_page(page, page_size)
    data: dict[str, Any] = {"items": [], "page": page_num, "page_size": clean_page_size, "total": 0, "pages": 0, "capabilities": capabilities or {}}
    if error:
        data["error"] = error
    return data


def _empty_user_stats(guid: str) -> dict[str, Any]:
    return {"guid": guid, "play_count": 0, "watch_seconds": 0, "watch_duration": "00:00:00", "recent_play_at": None}


def _empty_media_stats(guid: str) -> dict[str, Any]:
    return {"guid": guid, "play_count": 0, "completion_rate": 0, "recent_play_at": None}
