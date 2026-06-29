from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import AppError

_active_database: str = "none"


def snapshot_path() -> Path:
    return settings.cache_dir / "trimmedia.snapshot.db"


def source_path() -> Path:
    return settings.fntv_db_path


def active_database() -> str:
    return _active_database


def set_active_database(value: str) -> None:
    global _active_database
    _active_database = value


def snapshot_status() -> dict[str, Any]:
    snap = snapshot_path()
    src = source_path()
    tmp_path = snap.with_name(snap.stem + ".tmp" + snap.suffix)
    return {
        "snapshot_enabled": False,
        "source_path_container": str(src),
        "source_exists": src.exists(),
        "source_readable": src.exists() and os.access(src, os.R_OK),
        "source_readonly_configured": True,
        "snapshot_path_container": str(snap),
        "snapshot_exists": False,
        "snapshot_dir_exists": False,
        "snapshot_dir_writable": False,
        "snapshot_tmp_path": str(tmp_path),
        "snapshot_last_refresh_at": None,
        "snapshot_ok": None,
        "snapshot_error": None,
        "snapshot_error_type": None,
        "snapshot_error_message": None,
        "active_database": _active_database,
    }


def _readonly_uri(path: Path) -> str:
    return f"file:{path.as_posix()}?mode=ro"


def _can_read_sqlite_schema(path: Path) -> bool:
    if not path.exists() or not os.access(path, os.R_OK):
        return False
    try:
        with sqlite3.connect(_readonly_uri(path), uri=True) as conn:
            conn.execute("PRAGMA query_only = ON")
            conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
        return True
    except sqlite3.Error:
        return False


def source_direct_ok() -> bool:
    return _can_read_sqlite_schema(source_path())


def resolve_active_fntv_database() -> dict[str, Any]:
    global _active_database

    src_ok = source_direct_ok()
    if src_ok:
        _active_database = "source"
        return {
            "active_database": "source",
            "active_db_path": str(source_path()),
            "availability": "available",
            "degraded": False,
            "source_direct_ok": True,
            "snapshot_enabled": False,
            "snapshot_ok": None,
        }

    _active_database = "none"
    return {
        "active_database": "none",
        "active_db_path": None,
        "availability": "unavailable",
        "degraded": False,
        "source_direct_ok": False,
        "snapshot_enabled": False,
        "snapshot_ok": None,
    }


def copy_fntv_snapshot() -> dict[str, Any]:
    return {"ok": False, "disabled": True, "message": "FNTV snapshot is disabled in V1; using readonly source database"}


def refresh_fntv_snapshot() -> dict[str, Any]:
    return copy_fntv_snapshot()


def open_fntv_source_connection() -> sqlite3.Connection:
    src = source_path()
    if not src.exists():
        raise AppError("FNTV_DATABASE_NOT_FOUND", "飞牛影视数据库不存在，请检查 Docker Compose 只读挂载路径", 503)
    try:
        conn = sqlite3.connect(_readonly_uri(src), uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error as exc:
        raise AppError("FNTV_DATABASE_OPEN_FAILED", "飞牛影视数据库只读打开失败", 503) from exc


def open_active_fntv_connection() -> sqlite3.Connection:
    resolved = resolve_active_fntv_database()
    active = resolved["active_database"]
    if active == "source":
        return open_fntv_source_connection()
    raise AppError("FNTV_DATABASE_UNAVAILABLE", "飞牛影视数据库不可用，请检查源库只读挂载", 503)
