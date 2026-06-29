from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.fntv_readonly import open_fntv_connection
from app.db.fntv_snapshot import (
    set_active_database,
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
        logger.info("fntv source database configured for readonly direct access")
    else:
        logger.info("fntv source database not found; app will report database unavailable")


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


def database_status(detail: bool = False) -> dict[str, Any]:
    snap_info = snapshot_status()
    fntv: dict[str, Any] = {
        "path": snap_info["source_path_container"],
        "exists": snap_info["source_exists"],
        "readonly": True,
        "source_path_container": snap_info["source_path_container"],
        "source_exists": snap_info["source_exists"],
        "source_readable": snap_info["source_readable"],
        "source_readonly_configured": snap_info["source_readonly_configured"],
        "snapshot_enabled": False,
        "snapshot_path_container": snap_info["snapshot_path_container"],
        "snapshot_exists": snap_info["snapshot_exists"],
        "snapshot_dir_exists": snap_info["snapshot_dir_exists"],
        "snapshot_dir_writable": snap_info["snapshot_dir_writable"],
        "snapshot_tmp_path": snap_info["snapshot_tmp_path"],
        "snapshot_last_refresh_at": snap_info["snapshot_last_refresh_at"],
        "snapshot_ok": None,
        "snapshot_error": snap_info["snapshot_error"],
        "snapshot_error_type": snap_info["snapshot_error_type"],
        "snapshot_error_message": snap_info["snapshot_error_message"],
        "ok": False,
        "error": None,
        "error_type": None,
        "error_message": None,
        "warnings": [],
        "source_direct_ok": False,
        "source_direct_error_type": None,
        "source_direct_error_message": None,
        "source_test_query": "sqlite_master",
        "active_database": "none",
        "active_db_path": None,
        "availability": "unavailable",
        "degraded": False,
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

    try:
        with open_fntv_connection() as conn:
            conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
            set_active_database("source")
            fntv.update(
                {
                    "source_direct_ok": True,
                    "source_direct_error_type": None,
                    "source_direct_error_message": None,
                    "active_database": "source",
                    "active_db_path": snap_info["source_path_container"],
                    "availability": "available",
                }
            )
            diag = schema_diagnostics(conn=conn, detail=detail)
        fntv.update(diag)
        fntv["ok"] = bool(diag.get("ok"))
        if fntv["ok"]:
            fntv["error"] = None
            fntv["error_type"] = None
            fntv["error_message"] = None
    except Exception as exc:  # noqa: BLE001
        set_active_database("none")
        source_error_type, source_error_message = _source_direct_error(exc)
        fntv.update(
            {
                "ok": False,
                "source_direct_ok": False,
                "source_direct_error_type": source_error_type,
                "source_direct_error_message": source_error_message,
                "active_database": "none",
                "active_db_path": None,
                "availability": "unavailable",
                "error": "FNTV_DATABASE_UNAVAILABLE",
                "error_type": "DatabaseUnavailable",
                "error_message": "飞牛影视数据库不可用，请检查源库只读挂载",
            }
        )

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


def _source_direct_error(exc: Exception) -> tuple[str, str]:
    if hasattr(exc, "code"):
        error_type = str(getattr(exc, "code"))
    elif isinstance(exc, sqlite3.Error):
        error_type = type(exc).__name__
    else:
        error_type = type(exc).__name__
    message = str(getattr(exc, "message", None) or exc or "源库只读打开失败")
    return error_type, _sanitize_source_error(message)


def _sanitize_source_error(message: str) -> str:
    replacements = {
        str(settings.fntv_db_path): "<fntv_db>",
        settings.fntv_db_path.as_posix(): "<fntv_db>",
    }
    result = message
    for needle, replacement in replacements.items():
        if needle:
            result = result.replace(needle, replacement)
    return result


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
