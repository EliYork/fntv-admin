from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from app.core.errors import AppError
from app.db.fntv_readonly import open_fntv_connection


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


def find_table(tables: dict[str, TableInfo], hints: tuple[str, ...]) -> str | None:
    for table in tables.values():
        lower = table.name.lower()
        if any(hint in lower for hint in hints):
            return table.name
    return None


def find_column(table: TableInfo, hints: tuple[str, ...]) -> str | None:
    for column in table.columns:
        lower = column.lower()
        if any(hint in lower for hint in hints):
            return column
    return None

