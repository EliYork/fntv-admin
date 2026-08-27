from __future__ import annotations

import hmac
import os
import secrets
import sqlite3
import threading
from pathlib import Path

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import hash_password
from app.schemas.auth import AdminUserOut
from app.utils.time import now_ts

INITIALIZATION_TOKEN_NAME = "init-admin.token"
_initialization_lock = threading.Lock()


def initialization_token_path() -> Path:
    return settings.data_dir / INITIALIZATION_TOKEN_NAME


def ensure_initialization_token() -> bool:
    path = initialization_token_path()
    if _admin_exists():
        path.unlink(missing_ok=True)
        return False
    if path.exists():
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(48)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return True
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(token)
        stream.write("\n")
    return True


def create_initial_admin(username: str, password: str, initialization_token: str) -> AdminUserOut:
    clean_username = username.strip()
    with _initialization_lock, sqlite3.connect(settings.admin_db_path, timeout=10) as conn:
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM admin_users LIMIT 1").fetchone() is not None:
            raise AppError("ADMIN_ALREADY_EXISTS", "管理员已初始化", 409)
        expected = _read_initialization_token()
        if not expected or not hmac.compare_digest(initialization_token.strip(), expected):
            raise AppError("INVALID_INITIALIZATION_TOKEN", "初始化凭据无效", 403)
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
    initialization_token_path().unlink(missing_ok=True)
    return AdminUserOut(id=user_id, username=clean_username, role="admin", created_at=now)


def _read_initialization_token() -> str:
    try:
        return initialization_token_path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _admin_exists() -> bool:
    if not settings.admin_db_path.exists():
        return False
    try:
        with sqlite3.connect(settings.admin_db_path) as conn:
            return conn.execute("SELECT 1 FROM admin_users LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        return False
