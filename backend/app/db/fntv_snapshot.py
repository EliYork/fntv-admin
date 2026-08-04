from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import AppError

_active_database: str = "none"
_last_status: dict[str, Any] = {}

SNAPSHOT_META_NAME = "trimmedia.snapshot.json"


def snapshot_path() -> Path:
    return settings.cache_dir / "trimmedia.snapshot.db"


def snapshot_meta_path() -> Path:
    return settings.cache_dir / SNAPSHOT_META_NAME


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
    meta = _read_meta()
    last_error = _last_status.get("snapshot_error")
    return {
        "snapshot_enabled": snapshot_enabled(),
        "snapshot_refresh_interval_seconds": snapshot_refresh_interval_seconds(),
        "snapshot_stale": _snapshot_stale(),
        "source_path_container": str(src),
        "source_exists": src.exists(),
        "source_readable": src.exists() and os.access(src, os.R_OK),
        "source_readonly_configured": True,
        "snapshot_path_container": str(snap),
        "snapshot_exists": snap.exists(),
        "snapshot_dir_exists": settings.cache_dir.exists() and settings.cache_dir.is_dir(),
        "snapshot_dir_writable": settings.cache_dir.exists() and settings.cache_dir.is_dir() and os.access(settings.cache_dir, os.W_OK),
        "snapshot_tmp_path": str(tmp_path),
        "snapshot_last_refresh_at": meta.get("snapshot_last_refresh_at"),
        "snapshot_last_attempt_at": meta.get("snapshot_last_attempt_at"),
        "snapshot_ok": _last_status.get("snapshot_ok", _can_read_sqlite_schema(snap) if snap.exists() else None),
        "snapshot_error": last_error,
        "snapshot_error_type": _last_status.get("snapshot_error_type"),
        "snapshot_error_message": _last_status.get("snapshot_error_message"),
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


def snapshot_enabled() -> bool:
    if _setting_bool_from_admin_db("snapshot_enabled") is not None:
        return bool(_setting_bool_from_admin_db("snapshot_enabled"))
    return bool(settings.snapshot_enabled)


def snapshot_refresh_interval_seconds() -> int:
    """生效的自动刷新间隔（秒）。0 表示禁用自动刷新，仅手动刷新。"""
    raw = _setting_str_from_admin_db("snapshot_refresh_interval_seconds")
    if raw is not None:
        try:
            return max(0, int(float(raw)))
        except (TypeError, ValueError):
            pass
    return int(settings.snapshot_refresh_interval_seconds or 0)


def _snapshot_stale() -> bool:
    """快照是否已过期（按距上次成功刷新的时间判断）。

    刷新失败后记录 snapshot_last_attempt_at，在间隔内不重复重试，
    避免每次请求都触发一次失败的整库备份。
    """
    interval = snapshot_refresh_interval_seconds()
    if interval <= 0:
        return False
    meta = _read_meta()
    now = int(time.time())
    last_attempt = meta.get("snapshot_last_attempt_at")
    if last_attempt is not None and now - int(last_attempt) < interval:
        return False
    last_refresh = meta.get("snapshot_last_refresh_at")
    if last_refresh is None:
        return True
    return now - int(last_refresh) >= interval


def resolve_active_fntv_database() -> dict[str, Any]:
    global _active_database

    snap_info = snapshot_status()
    if snap_info["snapshot_enabled"]:
        snap = snapshot_path()
        if not snap.exists() or _snapshot_stale():
            refresh_fntv_snapshot()
            snap_info = snapshot_status()
        snap_usable = snap.exists() and _can_read_sqlite_schema(snap)
        # 快照刷新成功（或未过期）时优先使用快照
        if snap_usable and snap_info.get("snapshot_ok") is not False:
            _active_database = "snapshot"
            return {
                "active_database": "snapshot",
                "active_db_path": str(snap),
                "availability": "available",
                "degraded": False,
                "fallback_to_source": False,
                "source_direct_ok": source_direct_ok(),
                "snapshot_enabled": True,
                "snapshot_ok": snap_info.get("snapshot_ok"),
                "snapshot_path_container": str(snap),
                "snapshot_error": snap_info.get("snapshot_error"),
                "snapshot_error_type": snap_info.get("snapshot_error_type"),
                "snapshot_error_message": snap_info.get("snapshot_error_message"),
            }
        # 快照刷新失败 → 自动回退源库只读直连，保证数据新鲜
        src_ok = source_direct_ok()
        if src_ok:
            _active_database = "source"
            return {
                "active_database": "source",
                "active_db_path": str(source_path()),
                "availability": "available",
                "degraded": True,
                "fallback_to_source": True,
                "source_direct_ok": True,
                "snapshot_enabled": True,
                "snapshot_ok": snap_info.get("snapshot_ok"),
                "snapshot_path_container": str(snapshot_path()),
                "snapshot_error": snap_info.get("snapshot_error"),
                "snapshot_error_type": snap_info.get("snapshot_error_type"),
                "snapshot_error_message": snap_info.get("snapshot_error_message"),
            }
        # 源库也不可用 → 用旧快照兜底，避免页面白屏
        if snap_usable:
            _active_database = "snapshot"
            return {
                "active_database": "snapshot",
                "active_db_path": str(snap),
                "availability": "available",
                "degraded": True,
                "fallback_to_source": False,
                "source_direct_ok": False,
                "snapshot_enabled": True,
                "snapshot_ok": snap_info.get("snapshot_ok"),
                "snapshot_path_container": str(snap),
                "snapshot_error": snap_info.get("snapshot_error"),
                "snapshot_error_type": snap_info.get("snapshot_error_type"),
                "snapshot_error_message": snap_info.get("snapshot_error_message"),
            }

    src_ok = source_direct_ok()
    if src_ok:
        _active_database = "source"
        return {
            "active_database": "source",
            "active_db_path": str(source_path()),
            "availability": "available",
            "degraded": bool(snap_info["snapshot_enabled"] and snap_info.get("snapshot_ok") is False),
            "fallback_to_source": bool(snap_info["snapshot_enabled"]),
            "source_direct_ok": True,
            "snapshot_enabled": snap_info["snapshot_enabled"],
            "snapshot_ok": snap_info.get("snapshot_ok"),
            "snapshot_path_container": str(snapshot_path()),
            "snapshot_error": snap_info.get("snapshot_error"),
            "snapshot_error_type": snap_info.get("snapshot_error_type"),
            "snapshot_error_message": snap_info.get("snapshot_error_message"),
        }

    _active_database = "none"
    return {
        "active_database": "none",
        "active_db_path": None,
        "availability": "unavailable",
        "degraded": False,
        "fallback_to_source": False,
        "source_direct_ok": False,
        "snapshot_enabled": snap_info["snapshot_enabled"],
        "snapshot_ok": snap_info.get("snapshot_ok"),
    }


def copy_fntv_snapshot() -> dict[str, Any]:
    global _last_status
    if not snapshot_enabled():
        _last_status = {"snapshot_ok": None, "snapshot_error": None, "snapshot_error_type": None, "snapshot_error_message": None}
        return {"ok": False, "disabled": True, "message": "FNTV snapshot is disabled; using readonly source database"}
    snap = snapshot_path()
    tmp = snap.with_name(snap.stem + ".tmp" + snap.suffix)
    try:
        if settings.cache_dir.exists() and not settings.cache_dir.is_dir():
            raise OSError("snapshot cache path is not a directory")
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        if tmp.exists():
            tmp.unlink()
        with open_fntv_source_connection() as source_conn:
            with sqlite3.connect(tmp) as target_conn:
                source_conn.backup(target_conn)
                check = target_conn.execute("PRAGMA quick_check").fetchone()
                if not check or str(check[0]).lower() != "ok":
                    raise sqlite3.DatabaseError("snapshot quick_check failed")
        os.replace(tmp, snap)
        refreshed_at = int(time.time())
        _write_meta({"snapshot_last_refresh_at": refreshed_at})
        _last_status = {"snapshot_ok": True, "snapshot_error": None, "snapshot_error_type": None, "snapshot_error_message": None}
        return {
            "ok": True,
            "snapshot_path": str(snap),
            "snapshot_last_refresh_at": refreshed_at,
            "active_database": "snapshot",
        }
    except Exception as exc:  # noqa: BLE001
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        _record_refresh_failure()
        _last_status = {
            "snapshot_ok": False,
            "snapshot_error": "SNAPSHOT_REFRESH_FAILED",
            "snapshot_error_type": type(exc).__name__,
            "snapshot_error_message": _sanitize_error(str(exc)),
        }
        return {
            "ok": False,
            "snapshot_error": "SNAPSHOT_REFRESH_FAILED",
            "snapshot_error_type": type(exc).__name__,
            "snapshot_error_message": _sanitize_error(str(exc)),
            "fallback_to_source": source_direct_ok(),
        }


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
    if active == "snapshot":
        try:
            conn = sqlite3.connect(_readonly_uri(snapshot_path()), uri=True)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only = ON")
            return conn
        except sqlite3.Error as exc:
            raise AppError("FNTV_SNAPSHOT_OPEN_FAILED", "飞牛影视快照只读打开失败", 503) from exc
    if active == "source":
        return open_fntv_source_connection()
    raise AppError("FNTV_DATABASE_UNAVAILABLE", "飞牛影视数据库不可用，请检查源库只读挂载", 503)


def _setting_bool_from_admin_db(key: str) -> bool | None:
    value = _setting_str_from_admin_db(key)
    if value is None:
        return None
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _setting_str_from_admin_db(key: str) -> str | None:
    path = settings.admin_db_path
    if not path.exists():
        return None
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(path)
        row = conn.execute("SELECT value FROM settings WHERE key = ? LIMIT 1", (key,)).fetchone()
    except sqlite3.Error:
        return None
    finally:
        if conn is not None:
            conn.close()
    if row is None or row[0] in (None, ""):
        return None
    return str(row[0])


def _record_refresh_failure() -> None:
    """记录一次刷新尝试时间，用于在间隔内抑制重复失败重试。"""
    try:
        meta = _read_meta()
        meta["snapshot_last_attempt_at"] = int(time.time())
        _write_meta(meta)
    except OSError:
        pass


def _read_meta() -> dict[str, Any]:
    path = snapshot_meta_path()
    if not path.exists():
        return {}
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_meta(data: dict[str, Any]) -> None:
    import json

    path = snapshot_meta_path()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _sanitize_error(message: str) -> str:
    result = message or "snapshot refresh failed"
    for path in (settings.fntv_db_path, settings.cache_dir, snapshot_path()):
        for text in {str(path), path.as_posix()}:
            if text:
                result = result.replace(text, "<path>")
    return result
