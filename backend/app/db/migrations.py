from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import settings
from app.db.admin_db import init_admin_db


def run_migrations() -> None:
    init_admin_db()
    migrate_admin_schema(settings.admin_db_path)


def migrate_admin_schema(database_path: Path) -> None:
    with sqlite3.connect(database_path) as conn:
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(admin_users)")}
        if "token_version" not in columns:
            conn.execute("ALTER TABLE admin_users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1")
