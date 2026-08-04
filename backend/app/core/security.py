from __future__ import annotations

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


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expires}
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError("INVALID_TOKEN", "登录已失效，请重新登录", 401) from exc
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AppError("INVALID_TOKEN", "登录已失效，请重新登录", 401)
    return subject

