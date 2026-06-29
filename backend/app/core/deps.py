from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.admin_db import get_session
from app.models import AdminUser
from app.services import auth_policy_service
from app.services.auth_policy_service import AuthPrincipal

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_session),
) -> AuthPrincipal:
    policy = auth_policy_service.get_auth_policy(db)
    is_local, client_ip = auth_policy_service.enforce_remote_access(policy, request)
    if is_local and not policy.local_auth_required:
        return auth_policy_service.local_principal(policy, client_ip)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("AUTH_REQUIRED", "请先登录", 401)
    user_id = decode_access_token(credentials.credentials)
    user = db.get(AdminUser, int(user_id)) if user_id.isdigit() else None
    if user is None:
        raise AppError("AUTH_REQUIRED", "请先登录", 401)
    return auth_policy_service.admin_principal(user, policy, is_local_request=is_local, client_ip=client_ip)
