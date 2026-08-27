from __future__ import annotations

import sqlite3
import threading
from contextlib import closing

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import hash_password
from app.schemas.auth import AdminUserOut
from app.utils.time import now_ts

_initialization_lock = threading.Lock()


def create_initial_admin(username: str, password: str) -> AdminUserOut:
    clean_username = username.strip()
    with _initialization_lock, closing(sqlite3.connect(settings.admin_db_path, timeout=10)) as conn:
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM admin_users LIMIT 1").fetchone() is not None:
            raise AppError("ADMIN_ALREADY_EXISTS", "管理员已初始化", 409)
        now = now_ts()
        password_hash = hash_password(password)
        cursor = conn.execute(
            "INSERT INTO admin_users (username, password_hash, role, created_at, updated_at, last_login_at, token_version) "
            "VALUES (?, ?, 'admin', ?, ?, NULL, 1)",
            (clean_username, password_hash, now, now),
        )
        user_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO audit_logs (admin_user_id, action, target_type, target_id, detail, created_at) "
            "VALUES (?, 'init_admin', 'admin_user', ?, 'initial admin created', ?)",
            (user_id, str(user_id), now),
        )
        conn.commit()
    return AdminUserOut(id=user_id, username=clean_username, role="admin", created_at=now)
