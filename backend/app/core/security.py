from __future__ import annotations

import secrets
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.errors import AppError


class _BcryptAbout:
    __version__ = getattr(bcrypt, "__version__", "")


if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = _BcryptAbout()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
MIN_SIGNING_KEY_LENGTH = 32
INSECURE_PLACEHOLDER_KEYS = {"", "change-me", "change-this-to-a-long-random-string"}
_signing_key_lock = threading.Lock()
_managed_signing_key: str | None = None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expires}
    return jwt.encode(payload, signing_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, signing_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError("INVALID_TOKEN", "登录已失效，请重新登录", 401) from exc
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AppError("INVALID_TOKEN", "登录已失效，请重新登录", 401)
    return subject


def ensure_signing_key() -> None:
    signing_key()


def signing_key() -> str:
    configured = settings.app_secret_key.strip()
    if configured not in INSECURE_PLACEHOLDER_KEYS and len(configured) >= MIN_SIGNING_KEY_LENGTH:
        return configured
    return _managed_key()


def _managed_key() -> str:
    global _managed_signing_key
    if _managed_signing_key is not None:
        return _managed_signing_key
    with _signing_key_lock:
        if _managed_signing_key is not None:
            return _managed_signing_key
        generated = secrets.token_urlsafe(48)
        with sqlite3.connect(settings.admin_db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO system_secrets (key, value) VALUES (?, ?)",
                ("jwt_signing_secret", generated),
            )
            row = conn.execute(
                "SELECT value FROM system_secrets WHERE key = ? LIMIT 1",
                ("jwt_signing_secret",),
            ).fetchone()
        stored = str(row[0]).strip() if row else ""
        if len(stored) < MIN_SIGNING_KEY_LENGTH:
            raise RuntimeError("managed JWT signing key is missing or invalid")
        _managed_signing_key = stored
        return stored

