from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.fntv_readonly import assert_readonly_write_fails, open_fntv_connection
from app.db.migrations import run_migrations
from app.db.schema_check import schema_diagnostics
from app.models import Setting
from app.utils.time import now_ts


def startup_check() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    run_migrations()


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
    fntv_path = settings.fntv_db_path
    fntv: dict[str, Any] = {
        "path": str(fntv_path),
        "exists": fntv_path.exists(),
        "readonly": True,
        "ok": False,
        "error": None,
        "error_type": None,
        "error_message": None,
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
    if fntv_path.exists():
        try:
            with open_fntv_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            diag = schema_diagnostics()
            fntv.update(diag)
            fntv["write_probe_failed"] = assert_readonly_write_fails()
        except Exception as exc:  # noqa: BLE001
            fntv.update({
                "ok": False,
                "error": "FNTV_OPEN_FAILED",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            })
    else:
        fntv.update({
            "error": "FNTV_DATABASE_NOT_FOUND",
            "error_type": "ConfigError",
            "error_message": "飞牛影视数据库不存在，请检查 Docker Compose 挂载路径",
        })

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

