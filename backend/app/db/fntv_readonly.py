from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import AppError

WRITE_KEYWORDS = ("insert", "update", "delete", "drop", "alter", "vacuum", "reindex", "create")


def _readonly_uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro"


def open_fntv_connection() -> sqlite3.Connection:
    path = settings.fntv_db_path
    if not path.exists():
        raise AppError("FNTV_DATABASE_NOT_FOUND", "飞牛影视数据库不存在，请检查 Docker Compose 只读挂载路径", 503)
    try:
        conn = sqlite3.connect(_readonly_uri(path), uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error as exc:
        raise AppError("FNTV_DATABASE_OPEN_FAILED", "飞牛影视数据库只读打开失败", 503) from exc


def reject_write_sql(sql: str) -> None:
    normalized = sql.strip().lower()
    if any(normalized.startswith(keyword) for keyword in WRITE_KEYWORDS):
        raise AppError("FNTV_WRITE_FORBIDDEN", "禁止写入飞牛影视数据库", 400)


def fetch_all(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    reject_write_sql(sql)
    try:
        with open_fntv_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]
    except AppError:
        raise
    except sqlite3.Error as exc:
        raise AppError("FNTV_QUERY_FAILED", "飞牛影视数据库查询失败", 503) from exc


def fetch_one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    reject_write_sql(sql)
    rows = fetch_all(sql, params)
    return rows[0] if rows else None
