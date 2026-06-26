from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.admin_db import get_session
from app.models import AdminUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_session),
) -> AdminUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("AUTH_REQUIRED", "请先登录", 401)
    user_id = decode_access_token(credentials.credentials)
    user = db.get(AdminUser, int(user_id)) if user_id.isdigit() else None
    if user is None:
        raise AppError("AUTH_REQUIRED", "请先登录", 401)
    return user

