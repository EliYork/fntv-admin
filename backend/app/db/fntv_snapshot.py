from __future__ import annotations

import logging
import os
import shutil
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


def snapshot_path() -> Path:
    return settings.fntv_snapshot_path


def source_path() -> Path:
    return settings.fntv_db_path


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
    }


def _copy_file_safe(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    try:
        shutil.copy2(src, dst)
        return True
    except OSError as exc:
        logger.warning("failed to copy %s -> %s: %s", src, dst, exc)
        return False


def _remove_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def copy_fntv_snapshot() -> dict[str, Any]:
    global _snapshot_last_refresh_at, _snapshot_last_error, _snapshot_ok

    src = source_path()
    snap = snapshot_path()

    if not src.exists():
        _snapshot_ok = False
        _snapshot_last_error = "源数据库不存在"
        return {"ok": False, "error": "源数据库不存在"}

    snap.parent.mkdir(parents=True, exist_ok=True)

    tmp_base = snap.with_suffix(".tmp.db")
    tmp_wal = Path(str(snap) + ".tmp.db-wal")
    tmp_shm = Path(str(snap) + ".tmp.db-shm")
    snap_wal = Path(str(snap) + "-wal")
    snap_shm = Path(str(snap) + "-shm")

    _remove_if_exists(tmp_base)
    _remove_if_exists(tmp_wal)
    _remove_if_exists(tmp_shm)

    src_wal = Path(str(src) + "-wal")
    src_shm = Path(str(src) + "-shm")

    if not _copy_file_safe(src, tmp_base):
        _snapshot_ok = False
        _snapshot_last_error = "复制源数据库失败"
        _remove_if_exists(tmp_base)
        return {"ok": False, "error": "复制源数据库失败"}

    _copy_file_safe(src_wal, tmp_wal)
    _copy_file_safe(src_shm, tmp_shm)

    _remove_if_exists(snap)
    _remove_if_exists(snap_wal)
    _remove_if_exists(snap_shm)

    try:
        tmp_base.rename(snap)
    except OSError as exc:
        _snapshot_ok = False
        _snapshot_last_error = f"原子替换失败: {exc}"
        logger.error("snapshot atomic rename failed: %s", exc)
        _remove_if_exists(tmp_base)
        _remove_if_exists(tmp_wal)
        _remove_if_exists(tmp_shm)
        return {"ok": False, "error": f"原子替换失败: {exc}"}

    if tmp_wal.exists():
        try:
            tmp_wal.rename(snap_wal)
        except OSError:
            _remove_if_exists(tmp_wal)

    if tmp_shm.exists():
        try:
            tmp_shm.rename(snap_shm)
        except OSError:
            _remove_if_exists(tmp_shm)

    _snapshot_last_refresh_at = time.time()
    _snapshot_ok = True
    _snapshot_last_error = None
    logger.info("fntv snapshot refreshed: %s", snap)
    return {"ok": True, "snapshot_path": str(snap)}


def refresh_fntv_snapshot() -> dict[str, Any]:
    return copy_fntv_snapshot()


def open_snapshot_connection() -> sqlite3.Connection:
    snap = snapshot_path()
    if not snap.exists():
        raise AppError("FNTV_SNAPSHOT_NOT_FOUND", "飞牛数据库快照不存在，请先刷新快照", 503)
    try:
        conn = sqlite3.connect(f"file:{snap.as_posix()}?mode=ro", uri=True)
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
        conn = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error as exc:
        raise AppError("FNTV_DATABASE_OPEN_FAILED", "飞牛影视数据库只读打开失败", 503) from exc
