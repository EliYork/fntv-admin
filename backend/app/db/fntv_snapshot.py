from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

_snapshot_last_refresh_at: float | None = None
_snapshot_last_error: str | None = None
_snapshot_last_error_type: str | None = None
_snapshot_last_error_message: str | None = None
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
    snap_dir = snap.parent
    tmp_path = snap.with_name(snap.stem + ".tmp" + snap.suffix)
    return {
        "source_path_container": str(src),
        "source_exists": src.exists(),
        "source_readable": src.exists() and os.access(src, os.R_OK),
        "source_readonly_configured": True,
        "snapshot_path_container": str(snap),
        "snapshot_exists": snap.exists(),
        "snapshot_dir_exists": snap_dir.exists(),
        "snapshot_dir_writable": snap_dir.exists() and os.access(snap_dir, os.W_OK),
        "snapshot_tmp_path": str(tmp_path),
        "snapshot_last_refresh_at": _snapshot_last_refresh_at,
        "snapshot_ok": _snapshot_ok,
        "snapshot_error": _snapshot_last_error,
        "snapshot_error_type": _snapshot_last_error_type,
        "snapshot_error_message": _snapshot_last_error_message,
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
    return f"file:{src}?mode=ro"


def _readonly_uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro"


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


def snapshot_readable_ok() -> bool:
    return _snapshot_ok and _can_read_sqlite_schema(snapshot_path())


def resolve_active_fntv_database() -> dict[str, Any]:
    global _active_database

    snap_ok = snapshot_readable_ok()
    src_ok = source_direct_ok()
    if snap_ok:
        _active_database = "snapshot"
        return {
            "active_database": "snapshot",
            "active_db_path": str(snapshot_path()),
            "availability": "available",
            "degraded": False,
            "source_direct_ok": src_ok,
            "snapshot_ok": True,
        }

    if src_ok:
        _active_database = "source"
        return {
            "active_database": "source",
            "active_db_path": str(source_path()),
            "availability": "degraded",
            "degraded": True,
            "source_direct_ok": True,
            "snapshot_ok": False,
        }

    _active_database = "none"
    return {
        "active_database": "none",
        "active_db_path": None,
        "availability": "unavailable",
        "degraded": False,
        "source_direct_ok": False,
        "snapshot_ok": False,
    }


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


def _test_dir_writable(d: Path) -> tuple[bool, str]:
    try:
        fd, path = tempfile.mkstemp(dir=str(d), prefix=".fntv_snap_test_")
        os.close(fd)
        os.unlink(path)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _set_error(error: str, error_type: str, error_message: str) -> None:
    global _snapshot_last_error, _snapshot_last_error_type, _snapshot_last_error_message, _snapshot_ok
    _snapshot_ok = False
    _snapshot_last_error = error
    _snapshot_last_error_type = error_type
    _snapshot_last_error_message = error_message


def copy_fntv_snapshot() -> dict[str, Any]:
    global _snapshot_last_refresh_at, _snapshot_last_error, _snapshot_last_error_type
    global _snapshot_last_error_message, _snapshot_ok

    src = source_path()
    snap = snapshot_path()

    if not src.exists():
        _set_error("FNTV_SOURCE_NOT_FOUND", "FileNotFoundError", "源数据库不存在")
        return {"ok": False, "error": "源数据库不存在"}

    if not os.access(src, os.R_OK):
        _set_error("FNTV_SOURCE_NOT_READABLE", "PermissionError", "源数据库不可读")
        return {"ok": False, "error": "源数据库不可读"}

    snap_dir = snap.parent
    snap_dir.mkdir(parents=True, exist_ok=True)

    dir_ok, dir_err = _test_dir_writable(snap_dir)
    if not dir_ok:
        _set_error("SNAPSHOT_DIR_NOT_WRITABLE", "PermissionError", f"快照目录不可写: {dir_err}")
        return {"ok": False, "error": f"快照目录不可写: {dir_err}"}

    tmp_path = snap.with_name(snap.stem + ".tmp" + snap.suffix)
    _remove_if_exists(tmp_path)
    _remove_if_exists(Path(str(tmp_path) + "-wal"))
    _remove_if_exists(Path(str(tmp_path) + "-shm"))

    source_conn = None
    dest_conn = None
    try:
        source_uri = _source_readonly_uri()
        logger.info("opening source for backup: %s", source_uri)
        source_conn = sqlite3.connect(source_uri, uri=True)
        source_conn.execute("PRAGMA query_only = ON")
        source_conn.execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:
        _set_error("SOURCE_OPEN_FAILED", type(exc).__name__, f"打开源数据库失败: {exc}")
        logger.error("failed to open source for backup: %s", exc)
        if source_conn:
            source_conn.close()
        return {"ok": False, "error": f"打开源数据库失败: {exc}"}

    try:
        dest_path_str = str(tmp_path.resolve())
        logger.info("opening snapshot dest: %s", dest_path_str)
        dest_conn = sqlite3.connect(dest_path_str)
        dest_conn.execute("CREATE TABLE _fntv_writetest(id INTEGER)")
        dest_conn.execute("DROP TABLE _fntv_writetest")
    except sqlite3.Error as exc:
        _set_error("DEST_OPEN_FAILED", type(exc).__name__, f"打开快照目标失败: {exc}")
        logger.error("failed to open snapshot dest: %s", exc)
        source_conn.close()
        if dest_conn:
            dest_conn.close()
        _remove_if_exists(tmp_path)
        _remove_if_exists(Path(str(tmp_path) + "-wal"))
        _remove_if_exists(Path(str(tmp_path) + "-shm"))
        return {"ok": False, "error": f"打开快照目标失败: {exc}"}

    try:
        logger.info("starting sqlite backup")
        source_conn.backup(dest_conn)
        dest_conn.close()
        dest_conn = None
        source_conn.close()
        source_conn = None
        logger.info("sqlite backup completed")
    except sqlite3.Error as exc:
        _set_error("BACKUP_FAILED", type(exc).__name__, f"SQLite backup 执行失败: {exc}")
        logger.error("sqlite backup failed: %s", exc)
        if source_conn:
            source_conn.close()
        if dest_conn:
            dest_conn.close()
        _remove_if_exists(tmp_path)
        _remove_if_exists(Path(str(tmp_path) + "-wal"))
        _remove_if_exists(Path(str(tmp_path) + "-shm"))
        return {"ok": False, "error": f"SQLite backup 执行失败: {exc}"}

    ok, err = _validate_snapshot(tmp_path)
    if not ok:
        _set_error("VALIDATION_FAILED", "ValidationError", f"快照校验失败: {err}")
        logger.error("snapshot validation failed: %s", err)
        _remove_if_exists(tmp_path)
        _remove_if_exists(Path(str(tmp_path) + "-wal"))
        _remove_if_exists(Path(str(tmp_path) + "-shm"))
        return {"ok": False, "error": f"快照校验失败: {err}"}

    try:
        os.replace(str(tmp_path), str(snap))
    except OSError as exc:
        _set_error("REPLACE_FAILED", type(exc).__name__, f"原子替换失败: {exc}")
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
    _snapshot_last_error_type = None
    _snapshot_last_error_message = None
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


def open_active_fntv_connection() -> sqlite3.Connection:
    resolved = resolve_active_fntv_database()
    active = resolved["active_database"]
    if active == "snapshot":
        return open_snapshot_connection()
    if active == "source":
        return open_fntv_source_connection()
    raise AppError("FNTV_DATABASE_UNAVAILABLE", "飞牛影视数据库不可用，请检查快照或源库只读挂载", 503)
