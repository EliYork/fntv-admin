from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.fntv_readonly import assert_readonly_write_fails
from app.db.fntv_snapshot import (
    active_database,
    copy_fntv_snapshot,
    open_fntv_source_connection,
    refresh_fntv_snapshot,
    snapshot_status,
)
from app.db.migrations import run_migrations
from app.db.schema_check import schema_diagnostics
from app.models import Setting
from app.utils.time import now_ts

logger = logging.getLogger(__name__)


def startup_check() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    run_migrations()
    if settings.fntv_db_path.exists():
        result = copy_fntv_snapshot()
        if result.get("ok"):
            logger.info("initial fntv snapshot created")
        else:
            logger.warning("initial fntv snapshot failed: %s", result.get("error"))
    else:
        logger.info("fntv source database not found, skipping initial snapshot")


def storage_status() -> dict[str, Any]:
    paths = {
        "data": settings.data_dir,
        "logs": settings.log_dir,
        "cache": settings.cache_dir,
        "backup": settings.backup_dir,
    }
    items = []
    for key, path in paths.items():
        exists = path.exists()
        writable = exists and os.access(path, os.W_OK)
        items.append({"key": key, "path": str(path), "exists": exists, "writable": writable})
    return {"ok": all(item["exists"] and item["writable"] for item in items), "items": items}


def database_status() -> dict[str, Any]:
    snap_info = snapshot_status()
    fntv: dict[str, Any] = {
        "source_path_container": snap_info["source_path_container"],
        "source_exists": snap_info["source_exists"],
        "source_readable": snap_info["source_readable"],
        "source_readonly_configured": snap_info["source_readonly_configured"],
        "snapshot_path_container": snap_info["snapshot_path_container"],
        "snapshot_exists": snap_info["snapshot_exists"],
        "snapshot_dir_exists": snap_info["snapshot_dir_exists"],
        "snapshot_dir_writable": snap_info["snapshot_dir_writable"],
        "snapshot_tmp_path": snap_info["snapshot_tmp_path"],
        "snapshot_last_refresh_at": snap_info["snapshot_last_refresh_at"],
        "snapshot_ok": snap_info["snapshot_ok"],
        "snapshot_error": snap_info["snapshot_error"],
        "snapshot_error_type": snap_info["snapshot_error_type"],
        "snapshot_error_message": snap_info["snapshot_error_message"],
        "ok": False,
        "error": None,
        "error_type": None,
        "error_message": None,
        "source_direct_ok": None,
        "active_database": "none",
        "fallback_to_source": False,
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

    source_direct_ok = None
    try:
        with open_fntv_source_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        source_direct_ok = True
    except Exception:
        source_direct_ok = False
    fntv["source_direct_ok"] = source_direct_ok

    try:
        diag = schema_diagnostics()
        fntv.update(diag)
        fntv["write_probe_failed"] = assert_readonly_write_fails()
    except Exception as exc:  # noqa: BLE001
        fntv.update({
            "ok": False,
            "error": "FNTV_DIAG_FAILED",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        })

    current_active = active_database()
    fntv["active_database"] = current_active
    fntv["fallback_to_source"] = current_active == "source"
    fntv["degraded"] = bool(fntv.get("ok") and not snap_info["snapshot_ok"] and source_direct_ok)
    if fntv.get("ok") and snap_info["snapshot_ok"]:
        fntv["availability"] = "normal"
    elif fntv.get("ok") and source_direct_ok:
        fntv["availability"] = "degraded"
    else:
        fntv["availability"] = "unavailable"

    if not snap_info["source_exists"]:
        fntv["error"] = fntv.get("error") or "FNTV_DATABASE_NOT_FOUND"
        fntv["error_type"] = fntv.get("error_type") or "ConfigError"
        fntv["error_message"] = fntv.get("error_message") or "飞牛影视数据库不存在，请检查 Docker Compose 只读挂载路径"

    admin = {
        "path": str(settings.admin_db_path),
        "exists": settings.admin_db_path.exists(),
        "ok": settings.admin_db_path.exists(),
    }
    return {"fntv": fntv, "admin": admin}


def health() -> dict[str, Any]:
    return {"name": settings.app_name, "env": settings.app_env, "status": "ok"}


def default_settings(db: Session) -> dict[str, Any]:
    rows = db.scalars(select(Setting)).all()
    result = {row.key: row.value for row in rows}
    if not result:
        now = now_ts()
        defaults = {
            "default_page_size": str(settings.default_page_size),
            "log_retention_days": str(settings.log_retention_days),
            "theme": "system",
        }
        for key, value in defaults.items():
            db.merge(Setting(key=key, value=value, value_type="string", updated_at=now))
        db.commit()
        return defaults
    return result


def ensure_path_is_under_data(path: Path) -> bool:
    try:
        path.resolve().relative_to(settings.data_dir.resolve())
    except ValueError:
        return False
    return True
