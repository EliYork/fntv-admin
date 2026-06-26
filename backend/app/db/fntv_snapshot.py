from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

_snapshot_last_refresh_at: float | None = None
_snapshot_last_error: str | None = None
_snapshot_ok: bool = False
_active_database: str = "none"


def snapshot_path() -> Path:
    return settings.fntv_snapshot_path


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
    return {
        "source_path_container": str(src),
        "source_exists": src.exists(),
        "source_readable": src.exists() and os.access(src, os.R_OK),
        "source_readonly_configured": True,
        "snapshot_path_container": str(snap),
        "snapshot_exists": snap.exists(),
        "snapshot_last_refresh_at": _snapshot_last_refresh_at,
        "snapshot_ok": _snapshot_ok,
        "snapshot_error": _snapshot_last_error,
        "active_database": _active_database,
    }


def _remove_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _source_readonly_uri() -> str:
    src = source_path().resolve().as_posix()
    return f"file:{src}?mode=ro&cache=private"


def _validate_snapshot(db_path: Path) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON")
        row = conn.execute("PRAGMA quick_check").fetchone()
        result = str(row[0]) if row else ""
        if result != "ok":
            conn.close()
            return False, f"quick_check failed: {result}"
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        conn.close()
        return True, ""
    except sqlite3.Error as exc:
        return False, f"validation error: {exc}"


def copy_fntv_snapshot() -> dict[str, Any]:
    global _snapshot_last_refresh_at, _snapshot_last_error, _snapshot_ok

    src = source_path()
    snap = snapshot_path()

    if not src.exists():
        _snapshot_ok = False
        _snapshot_last_error = "源数据库不存在"
        return {"ok": False, "error": "源数据库不存在"}

    if not os.access(src, os.R_OK):
        _snapshot_ok = False
        _snapshot_last_error = "源数据库不可读"
        return {"ok": False, "error": "源数据库不可读"}

    snap.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = snap.with_name(snap.stem + ".tmp" + snap.suffix)
    _remove_if_exists(tmp_path)
    _remove_if_exists(Path(str(tmp_path) + "-wal"))
    _remove_if_exists(Path(str(tmp_path) + "-shm"))

    source_conn = None
    dest_conn = None
    try:
        source_conn = sqlite3.connect(_source_readonly_uri(), uri=True)
        source_conn.execute("PRAGMA query_only = ON")

        dest_conn = sqlite3.connect(str(tmp_path))
        source_conn.backup(dest_conn)
        dest_conn.close()
        dest_conn = None
        source_conn.close()
        source_conn = None
    except sqlite3.Error as exc:
        _snapshot_ok = False
        _snapshot_last_error = f"SQLite backup 失败: {exc}"
        logger.error("sqlite backup failed: %s", exc)
        if source_conn:
            source_conn.close()
        if dest_conn:
            dest_conn.close()
        _remove_if_exists(tmp_path)
        _remove_if_exists(Path(str(tmp_path) + "-wal"))
        _remove_if_exists(Path(str(tmp_path) + "-shm"))
        return {"ok": False, "error": f"SQLite backup 失败: {exc}"}

    ok, err = _validate_snapshot(tmp_path)
    if not ok:
        _snapshot_ok = False
        _snapshot_last_error = f"快照校验失败: {err}"
        logger.error("snapshot validation failed: %s", err)
        _remove_if_exists(tmp_path)
        _remove_if_exists(Path(str(tmp_path) + "-wal"))
        _remove_if_exists(Path(str(tmp_path) + "-shm"))
        return {"ok": False, "error": f"快照校验失败: {err}"}

    try:
        os.replace(str(tmp_path), str(snap))
    except OSError as exc:
        _snapshot_ok = False
        _snapshot_last_error = f"原子替换失败: {exc}"
        logger.error("snapshot atomic replace failed: %s", exc)
        _remove_if_exists(tmp_path)
        _remove_if_exists(Path(str(tmp_path) + "-wal"))
        _remove_if_exists(Path(str(tmp_path) + "-shm"))
        return {"ok": False, "error": f"原子替换失败: {exc}"}

    _remove_if_exists(Path(str(tmp_path) + "-wal"))
    _remove_if_exists(Path(str(tmp_path) + "-shm"))
    _remove_if_exists(Path(str(snap) + "-wal"))
    _remove_if_exists(Path(str(snap) + "-shm"))

    _snapshot_last_refresh_at = time.time()
    _snapshot_ok = True
    _snapshot_last_error = None
    logger.info("fntv snapshot refreshed via sqlite backup: %s", snap)
    return {"ok": True, "snapshot_path": str(snap)}


def refresh_fntv_snapshot() -> dict[str, Any]:
    return copy_fntv_snapshot()


def open_snapshot_connection() -> sqlite3.Connection:
    snap = snapshot_path()
    if not snap.exists():
        raise AppError("FNTV_SNAPSHOT_NOT_FOUND", "飞牛数据库快照不存在，请先刷新快照", 503)
    try:
        conn = sqlite3.connect(f"file:{snap.resolve().as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error as exc:
        raise AppError("FNTV_SNAPSHOT_OPEN_FAILED", "飞牛数据库快照打开失败", 503) from exc


def open_fntv_source_connection() -> sqlite3.Connection:
    src = source_path()
    if not src.exists():
        raise AppError("FNTV_DATABASE_NOT_FOUND", "飞牛影视数据库不存在，请检查 Docker Compose 只读挂载路径", 503)
    try:
        conn = sqlite3.connect(_source_readonly_uri(), uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error as exc:
        raise AppError("FNTV_DATABASE_OPEN_FAILED", "飞牛影视数据库只读打开失败", 503) from exc
