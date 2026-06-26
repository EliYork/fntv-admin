from __future__ import annotations

from app.db.admin_db import init_admin_db


def run_migrations() -> None:
    init_admin_db()

