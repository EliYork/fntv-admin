from __future__ import annotations

import csv
import io
import sqlite3
from typing import Any

from app.core.errors import AppError
from app.db.fntv_readonly import open_fntv_connection
from app.db.schema_check import TableInfo, find_column, find_table, inspect_schema, quote_identifier
from app.utils.pagination import normalize_page


def _snapshot() -> tuple[dict[str, TableInfo], dict[str, str | None]]:
    tables = inspect_schema()
    return tables, {
        "users": find_table(tables, ("user", "account", "member")),
        "media": find_table(tables, ("item", "media", "video", "movie", "episode")),
        "plays": find_table(tables, ("play", "history", "watch", "progress")),
    }


def _count_table(conn: sqlite3.Connection, table_name: str | None) -> int:
    if not table_name:
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS total FROM {quote_identifier(table_name)}").fetchone()
    return int(row["total"]) if row else 0


def _first_existing(table: TableInfo, hints: tuple[str, ...], fallback: str | None = None) -> str | None:
    return find_column(table, hints) or fallback


def _order_column(table: TableInfo) -> str | None:
    return find_column(table, ("time", "date", "created", "updated", "played", "last"))


def _guid_column(table: TableInfo) -> str | None:
    return find_column(table, ("guid", "uuid", "id"))


def _title_column(table: TableInfo) -> str | None:
    return find_column(table, ("title", "name", "filename"))


def _limit_rows(conn: sqlite3.Connection, table: TableInfo, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    page_num, clean_page_size, offset = normalize_page(page, page_size)
    order = _order_column(table)
    order_sql = f" ORDER BY {quote_identifier(order)} DESC" if order else ""
    rows = conn.execute(
        f"SELECT * FROM {quote_identifier(table.name)}{order_sql} LIMIT ? OFFSET ?",
        (clean_page_size, offset),
    ).fetchall()
    total = _count_table(conn, table.name)
    return [dict(row) for row in rows], total


def overview_data() -> dict[str, Any]:
    try:
        tables, candidates = _snapshot()
        with open_fntv_connection() as conn:
            users = _count_table(conn, candidates["users"])
            media = _count_table(conn, candidates["media"])
            plays = _count_table(conn, candidates["plays"])
        return {
            "database_ok": True,
            "total_users": users,
            "total_media": media,
            "total_play_records": plays,
            "today_plays": 0,
            "latest_play_time": None,
            "candidates": candidates,
            "table_count": len(tables),
        }
    except AppError as exc:
        return {
            "database_ok": False,
            "error": exc.message,
            "total_users": 0,
            "total_media": 0,
            "total_play_records": 0,
            "today_plays": 0,
            "latest_play_time": None,
        }


def recent_activities(limit: int = 20) -> list[dict[str, Any]]:
    try:
        tables, candidates = _snapshot()
        table_name = candidates["plays"]
        if not table_name:
            return []
        table = tables[table_name]
        with open_fntv_connection() as conn:
            rows, _ = _limit_rows(conn, table, 1, limit)
        return [_play_row(row, table) for row in rows]
    except AppError:
        return []


def play_trend() -> list[dict[str, Any]]:
    return []


def top_media() -> list[dict[str, Any]]:
    return []


def top_users() -> list[dict[str, Any]]:
    return []


def history_page(page: int, page_size: int) -> dict[str, Any]:
    try:
        tables, candidates = _snapshot()
        table_name = candidates["plays"]
        if not table_name:
            return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
        table = tables[table_name]
        page_num, clean_page_size, _ = normalize_page(page, page_size)
        with open_fntv_connection() as conn:
            rows, total = _limit_rows(conn, table, page_num, clean_page_size)
        pages = 0 if total == 0 else (total + clean_page_size - 1) // clean_page_size
        return {"items": [_play_row(row, table) for row in rows], "page": page_num, "page_size": clean_page_size, "total": total, "pages": pages}
    except AppError as exc:
        return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0, "error": exc.message}


def history_detail(record_id: str) -> dict[str, Any] | None:
    try:
        tables, candidates = _snapshot()
        table_name = candidates["plays"]
        if not table_name:
            return None
        table = tables[table_name]
        id_col = _guid_column(table)
        if not id_col:
            return None
        with open_fntv_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {quote_identifier(table.name)} WHERE {quote_identifier(id_col)} = ? LIMIT 1",
                (record_id,),
            ).fetchone()
        return dict(row) if row else None
    except AppError:
        return None


def history_csv() -> str:
    page_data = history_page(1, 1000)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "user", "title", "played_at", "progress", "watched"])
    writer.writeheader()
    for item in page_data["items"]:
        writer.writerow(item)
    return output.getvalue()


def users_page(page: int, page_size: int) -> dict[str, Any]:
    try:
        tables, candidates = _snapshot()
        table_name = candidates["users"]
        if not table_name:
            return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
        table = tables[table_name]
        page_num, clean_page_size, _ = normalize_page(page, page_size)
        with open_fntv_connection() as conn:
            rows, total = _limit_rows(conn, table, page_num, clean_page_size)
        pages = 0 if total == 0 else (total + clean_page_size - 1) // clean_page_size
        return {"items": [_user_row(row, table) for row in rows], "page": page_num, "page_size": clean_page_size, "total": total, "pages": pages}
    except AppError as exc:
        return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0, "error": exc.message}


def media_page(page: int, page_size: int) -> dict[str, Any]:
    try:
        tables, candidates = _snapshot()
        table_name = candidates["media"]
        if not table_name:
            return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
        table = tables[table_name]
        page_num, clean_page_size, _ = normalize_page(page, page_size)
        with open_fntv_connection() as conn:
            rows, total = _limit_rows(conn, table, page_num, clean_page_size)
        pages = 0 if total == 0 else (total + clean_page_size - 1) // clean_page_size
        return {"items": [_media_row(row, table) for row in rows], "page": page_num, "page_size": clean_page_size, "total": total, "pages": pages}
    except AppError as exc:
        return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0, "error": exc.message}


def media_children(guid: str) -> list[dict[str, Any]]:
    _ = guid
    return []


def _play_row(row: dict[str, Any], table: TableInfo) -> dict[str, Any]:
    id_col = _guid_column(table)
    user_col = _first_existing(table, ("user", "account", "member"))
    title_col = _first_existing(table, ("title", "name", "item", "media"))
    time_col = _order_column(table)
    progress_col = _first_existing(table, ("progress", "percent", "position"))
    watched_col = _first_existing(table, ("watched", "finished", "complete"))
    return {
        "id": str(row.get(id_col) if id_col else ""),
        "user": str(row.get(user_col) if user_col else ""),
        "title": str(row.get(title_col) if title_col else ""),
        "played_at": row.get(time_col) if time_col else None,
        "progress": row.get(progress_col) if progress_col else None,
        "watched": bool(row.get(watched_col)) if watched_col else False,
    }


def _user_row(row: dict[str, Any], table: TableInfo) -> dict[str, Any]:
    guid_col = _guid_column(table)
    name_col = _first_existing(table, ("username", "user_name", "name", "nick"))
    admin_col = _first_existing(table, ("admin", "role"))
    login_col = _first_existing(table, ("login", "last"))
    guid = str(row.get(guid_col) if guid_col else "")
    return {
        "guid": guid,
        "username": str(row.get(name_col) if name_col else guid),
        "is_admin": bool(row.get(admin_col)) if admin_col else False,
        "status": "active",
        "last_login_at": row.get(login_col) if login_col else None,
        "last_play_at": None,
        "play_count": 0,
        "watch_seconds": 0,
        "hidden": False,
        "display_name": None,
        "note": None,
    }


def _media_row(row: dict[str, Any], table: TableInfo) -> dict[str, Any]:
    guid_col = _guid_column(table)
    title_col = _title_column(table)
    type_col = _first_existing(table, ("type", "kind", "category"))
    runtime_col = _first_existing(table, ("runtime", "duration", "length"))
    parent_col = _first_existing(table, ("parent", "series", "season"))
    guid = str(row.get(guid_col) if guid_col else "")
    return {
        "guid": guid,
        "title": str(row.get(title_col) if title_col else guid),
        "original_title": str(row.get(title_col) if title_col else guid),
        "media_type": str(row.get(type_col) if type_col else ""),
        "runtime": row.get(runtime_col) if runtime_col else None,
        "release_time": None,
        "parent": row.get(parent_col) if parent_col else None,
        "children_count": 0,
        "play_count": 0,
        "last_play_at": None,
        "hidden": False,
        "note": None,
    }


# Keep the original import path stable while using the Phase 6.5 schema adapter.
from app.services.fntv_schema_adapter import *  # noqa: E402,F403
