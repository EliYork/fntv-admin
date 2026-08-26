from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import AppError

_active_database: str = "none"
_last_status: dict[str, Any] = {}
_refresh_lock = threading.Lock()

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
    tmp_path = snap.with_name("trimmedia.snapshot.*.tmp.db")
    meta = _read_meta()
    schedule = _snapshot_schedule(meta)
    last_error = _last_status.get("snapshot_error")
    return {
        "snapshot_enabled": snapshot_enabled(),
        "snapshot_refresh_interval_seconds": snapshot_refresh_interval_seconds(),
        "snapshot_stale": schedule["due"],
        "snapshot_refreshing": _refresh_lock.locked(),
        "snapshot_retry_suppressed": schedule["state"] == "retry_wait",
        "snapshot_next_refresh_at": schedule["next_refresh_at"],
        "snapshot_schedule_state": "refreshing" if _refresh_lock.locked() else schedule["state"],
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
    return bool(_snapshot_schedule(_read_meta())["due"])


def _snapshot_schedule(meta: dict[str, Any] | None = None, now: int | None = None) -> dict[str, Any]:
    """返回自动刷新真实调度状态，失败重试以最近一次尝试为基准。"""
    interval = snapshot_refresh_interval_seconds()
    if interval <= 0:
        return {"state": "manual_only", "due": False, "next_refresh_at": None}
    values = meta if meta is not None else _read_meta()
    current = int(time.time()) if now is None else int(now)
    last_refresh = _meta_timestamp(values.get("snapshot_last_refresh_at"))
    last_attempt = _meta_timestamp(values.get("snapshot_last_attempt_at"))
    failed_attempt = last_attempt is not None and (last_refresh is None or last_attempt > last_refresh)
    base = last_attempt if failed_attempt else last_refresh
    if base is None:
        return {"state": "due", "due": True, "next_refresh_at": current}
    next_refresh = base + interval
    if current >= next_refresh:
        return {"state": "due", "due": True, "next_refresh_at": current}
    return {
        "state": "retry_wait" if failed_attempt else "scheduled",
        "due": False,
        "next_refresh_at": next_refresh,
    }


def resolve_active_fntv_database() -> dict[str, Any]:
    global _active_database

    snap_info = snapshot_status()
    if snap_info["snapshot_enabled"]:
        snap = snapshot_path()
        if not snap.exists() or _snapshot_stale():
            trigger_fntv_snapshot_refresh()
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
    """同步请求刷新；若已有任务在执行则立即返回，不等待也不重复刷新。"""
    return refresh_fntv_snapshot()


def refresh_fntv_snapshot() -> dict[str, Any]:
    if not snapshot_enabled():
        return _snapshot_disabled_result()
    process_lock, acquired = _acquire_refresh_guards()
    if not acquired:
        return _snapshot_busy_result()
    try:
        return _copy_fntv_snapshot_locked()
    finally:
        _release_process_refresh_lock(process_lock)
        _refresh_lock.release()


def trigger_fntv_snapshot_refresh() -> dict[str, Any]:
    """非阻塞触发自动刷新，页面读取继续使用旧快照或只读源库。"""
    if not snapshot_enabled():
        return _snapshot_disabled_result()
    process_lock, acquired = _acquire_refresh_guards()
    if not acquired:
        return _snapshot_busy_result()

    def run() -> None:
        try:
            _copy_fntv_snapshot_locked()
        finally:
            _release_process_refresh_lock(process_lock)
            _refresh_lock.release()

    threading.Thread(target=run, name="fntv-snapshot-refresh", daemon=True).start()
    return {
        "ok": True,
        "started": True,
        "refresh_in_progress": True,
        "message": "快照刷新已开始",
    }


def _copy_fntv_snapshot_locked() -> dict[str, Any]:
    global _last_status
    snap = snapshot_path()
    tmp: Path | None = None
    attempt_at = int(time.time())
    try:
        if settings.cache_dir.exists() and not settings.cache_dir.is_dir():
            raise OSError("snapshot cache path is not a directory")
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        _record_refresh_attempt(attempt_at)
        handle, tmp_name = tempfile.mkstemp(prefix="trimmedia.snapshot.", suffix=".tmp.db", dir=settings.cache_dir)
        os.close(handle)
        tmp = Path(tmp_name)
        with open_fntv_source_connection() as source_conn:
            with sqlite3.connect(tmp) as target_conn:
                source_conn.backup(target_conn)
                check = target_conn.execute("PRAGMA quick_check").fetchone()
                if not check or str(check[0]).lower() != "ok":
                    raise sqlite3.DatabaseError("snapshot quick_check failed")
        os.replace(tmp, snap)
        refreshed_at = int(time.time())
        _write_meta({"snapshot_last_refresh_at": refreshed_at, "snapshot_last_attempt_at": attempt_at})
        _last_status = {"snapshot_ok": True, "snapshot_error": None, "snapshot_error_type": None, "snapshot_error_message": None}
        return {
            "ok": True,
            "snapshot_path": str(snap),
            "snapshot_last_refresh_at": refreshed_at,
            "active_database": "snapshot",
        }
    except Exception as exc:  # noqa: BLE001
        try:
            if tmp is not None and tmp.exists():
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


def _snapshot_disabled_result() -> dict[str, Any]:
    global _last_status
    _last_status = {"snapshot_ok": None, "snapshot_error": None, "snapshot_error_type": None, "snapshot_error_message": None}
    return {"ok": False, "disabled": True, "message": "快照未启用，继续使用源库只读直连"}


def _snapshot_busy_result() -> dict[str, Any]:
    return {
        "ok": False,
        "skipped": True,
        "refresh_in_progress": True,
        "message": "快照正在刷新，本次未重复启动",
        "fallback_to_source": source_direct_ok(),
    }


def _acquire_refresh_guards() -> tuple[Any | None, bool]:
    """同时取得进程内和跨进程非阻塞门控；官方单进程部署与未来多 worker 均安全。"""
    if not _refresh_lock.acquire(blocking=False):
        return None, False
    try:
        process_lock = _try_acquire_process_refresh_lock()
    except OSError:
        # 目录不可用时仍进入正式刷新路径，让统一错误与 fallback 逻辑记录失败。
        return None, True
    if process_lock is None:
        _refresh_lock.release()
        return None, False
    return process_lock, True


def _try_acquire_process_refresh_lock() -> Any | None:
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    stream = (settings.cache_dir / "trimmedia.snapshot.lock").open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return stream
    except (BlockingIOError, OSError):
        stream.close()
        return None


def _release_process_refresh_lock(stream: Any | None) -> None:
    if stream is None:
        return
    try:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()


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


def _record_refresh_attempt(attempt_at: int | None = None) -> None:
    try:
        meta = _read_meta()
        meta["snapshot_last_attempt_at"] = int(time.time()) if attempt_at is None else int(attempt_at)
        _write_meta(meta)
    except OSError:
        pass


def _record_refresh_failure(attempt_at: int | None = None) -> None:
    """记录一次刷新尝试时间，用于在间隔内抑制重复失败重试。"""
    try:
        meta = _read_meta()
        meta["snapshot_last_attempt_at"] = int(time.time()) if attempt_at is None else int(attempt_at)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _meta_timestamp(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _sanitize_error(message: str) -> str:
    result = message or "snapshot refresh failed"
    for path in (settings.fntv_db_path, settings.cache_dir, snapshot_path()):
        for text in {str(path), path.as_posix()}:
            if text:
                result = result.replace(text, "<path>")
    return result
