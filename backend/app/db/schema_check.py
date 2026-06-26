from __future__ import annotations

import logging
import sqlite3
import traceback
from dataclasses import dataclass
from typing import Any

from app.core.errors import AppError
from app.db.fntv_readonly import open_fntv_connection

logger = logging.getLogger(__name__)

CORE_TABLE_HINTS: dict[str, tuple[str, ...]] = {
    "user": ("user", "users", "account", "member"),
    "item": ("item", "items", "media", "video", "movie", "episode"),
    "item_user_play": ("item_user_play", "play_history", "playback_history", "play", "history", "watch", "progress"),
}

USER_FIELD_HINTS = ("username", "nickname", "name", "display_name", "guid")
ITEM_FIELD_HINTS = ("title", "original_title", "filename", "name", "guid")
PLAY_USER_GUID_HINTS = ("user_guid", "user_id", "uid")
PLAY_ITEM_GUID_HINTS = ("item_guid", "item_id", "media_guid", "media_id")
PLAY_POSITION_HINTS = ("ts", "position", "playback_position", "progress")
PLAY_RUNTIME_HINTS = ("runtime", "duration", "length", "run_time")


@dataclass(frozen=True)
class TableInfo:
    name: str
    columns: list[str]


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def inspect_schema() -> dict[str, TableInfo]:
    try:
        with open_fntv_connection() as conn:
            table_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            tables: dict[str, TableInfo] = {}
            for row in table_rows:
                name = str(row["name"])
                escaped = quote_identifier(name)
                columns = [str(col["name"]) for col in conn.execute(f"PRAGMA table_info({escaped})").fetchall()]
                tables[name] = TableInfo(name=name, columns=columns)
            return tables
    except AppError:
        raise
    except sqlite3.Error as exc:
        raise AppError("FNTV_SCHEMA_FAILED", "飞牛影视数据库结构读取失败", 503) from exc


def schema_status() -> dict[str, Any]:
    tables = inspect_schema()
    candidates = {
        "users": find_table(tables, ("user", "account", "member")),
        "media": find_table(tables, ("item", "media", "video", "movie", "episode")),
        "plays": find_table(tables, ("play", "history", "watch", "progress")),
    }
    return {
        "table_count": len(tables),
        "tables": [{"name": table.name, "columns": table.columns} for table in tables.values()],
        "candidates": candidates,
    }


def schema_diagnostics() -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "error": None,
        "error_type": None,
        "error_message": None,
        "detected_table_count": 0,
        "detected_tables": [],
        "detected_columns_by_table": {},
        "core_candidates": {"user_table": None, "item_table": None, "play_table": None},
        "required_tables_status": {"user": False, "item": False, "item_user_play": False},
        "capabilities": {
            "can_read_users": False,
            "can_read_items": False,
            "can_read_play_history": False,
            "can_join_user_names": False,
            "can_join_item_titles": False,
            "can_calculate_progress": False,
        },
    }
    try:
        with open_fntv_connection() as conn:
            table_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        table_names = [str(r["name"]) for r in table_rows]
        result["detected_table_count"] = len(table_names)
        result["detected_tables"] = table_names

        columns_by_table: dict[str, list[str]] = {}
        tables: dict[str, TableInfo] = {}
        for tname in table_names:
            escaped = quote_identifier(tname)
            try:
                with open_fntv_connection() as conn:
                    cols = [str(c["name"]) for c in conn.execute(f"PRAGMA table_info({escaped})").fetchall()]
                columns_by_table[tname] = cols
                tables[tname] = TableInfo(name=tname, columns=cols)
            except (AppError, sqlite3.Error) as col_exc:
                logger.warning("PRAGMA table_info failed for table %s: %s", tname, col_exc)
                columns_by_table[tname] = [f"<error: {type(col_exc).__name__}>"]

        result["detected_columns_by_table"] = columns_by_table

        user_table = find_table(tables, CORE_TABLE_HINTS["user"])
        item_table = find_table(tables, CORE_TABLE_HINTS["item"])
        play_table = find_table(tables, CORE_TABLE_HINTS["item_user_play"])

        result["core_candidates"] = {
            "user_table": user_table,
            "item_table": item_table,
            "play_table": play_table,
        }
        result["required_tables_status"] = {
            "user": user_table is not None,
            "item": item_table is not None,
            "item_user_play": play_table is not None,
        }

        user_has_guid = bool(user_table and _find_col_in(tables, user_table, ("guid", "uuid", "id")))
        user_has_display = bool(user_table and _find_col_in(tables, user_table, USER_FIELD_HINTS))
        item_has_guid = bool(item_table and _find_col_in(tables, item_table, ("guid", "uuid", "id")))
        item_has_title = bool(item_table and _find_col_in(tables, item_table, ITEM_FIELD_HINTS))
        play_has_user_guid = bool(play_table and _find_col_in(tables, play_table, PLAY_USER_GUID_HINTS))
        play_has_item_guid = bool(play_table and _find_col_in(tables, play_table, PLAY_ITEM_GUID_HINTS))
        play_has_position = bool(play_table and _find_col_in(tables, play_table, PLAY_POSITION_HINTS))
        item_has_runtime = bool(item_table and _find_col_in(tables, item_table, PLAY_RUNTIME_HINTS))

        result["capabilities"] = {
            "can_read_users": user_has_display,
            "can_read_items": item_has_title,
            "can_read_play_history": bool(play_table),
            "can_join_user_names": bool(user_has_guid and play_has_user_guid),
            "can_join_item_titles": bool(item_has_guid and play_has_item_guid),
            "can_calculate_progress": bool(play_has_position and item_has_runtime),
        }

        result["ok"] = True
    except AppError as exc:
        logger.error("schema_diagnostics AppError: %s\n%s", exc, traceback.format_exc())
        result["error"] = exc.code
        result["error_type"] = "AppError"
        result["error_message"] = exc.message
    except sqlite3.Error as exc:
        logger.error("schema_diagnostics sqlite3.Error: %s\n%s", exc, traceback.format_exc())
        result["error"] = "SQLITE_ERROR"
        result["error_type"] = type(exc).__name__
        result["error_message"] = f"SQLite 错误: {exc}"
    except Exception as exc:
        logger.error("schema_diagnostics unexpected error: %s\n%s", exc, traceback.format_exc())
        result["error"] = "UNEXPECTED_ERROR"
        result["error_type"] = type(exc).__name__
        result["error_message"] = f"未预期错误: {exc}"

    return result


def _find_col_in(tables: dict[str, TableInfo], table_name: str, hints: tuple[str, ...]) -> str | None:
    table = tables.get(table_name)
    if table is None:
        return None
    return find_column(table, hints)


def find_table(tables: dict[str, TableInfo], hints: tuple[str, ...]) -> str | None:
    by_lower = {name.lower(): name for name in tables}
    for hint in hints:
        if hint in by_lower:
            return by_lower[hint]
    for table in tables.values():
        lower = table.name.lower()
        for hint in hints:
            if hint in {"user", "users", "item", "items", "item_user_play"}:
                continue
            if hint in lower:
                return table.name
    return None


def find_column(table: TableInfo, hints: tuple[str, ...]) -> str | None:
    by_lower = {column.lower(): column for column in table.columns}
    for hint in hints:
        if hint in by_lower:
            return by_lower[hint]
    for column in table.columns:
        lower = column.lower()
        if any(hint in lower for hint in hints):
            return column
    return None
