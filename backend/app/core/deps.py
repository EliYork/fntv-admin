from __future__ import annotations

import logging

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
logger = logging.getLogger(__name__)


def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_session),
) -> AuthPrincipal:
    policy = auth_policy_service.get_auth_policy(db)
    is_local, client_ip = auth_policy_service.enforce_remote_access(policy, request)
    if is_local and not policy.local_auth_required:
        return auth_policy_service.local_principal(policy, client_ip)
    path = request_path(request)
    if credentials is None or credentials.scheme.lower() != "bearer":
        logger.info("auth rejected: path=%s status=401 code=AUTH_REQUIRED client=%s", path, client_ip)
        raise AppError("AUTH_REQUIRED", "请先登录", 401)
    try:
        user_id = decode_access_token(credentials.credentials)
    except AppError as exc:
        logger.info("auth rejected: path=%s status=%s code=%s client=%s", path, exc.status_code, exc.code, client_ip)
        raise
    user = db.get(AdminUser, int(user_id)) if user_id.isdigit() else None
    if user is None:
        logger.info("auth rejected: path=%s status=401 code=AUTH_REQUIRED client=%s reason=user_not_found", path, client_ip)
        raise AppError("AUTH_REQUIRED", "请先登录", 401)
    return auth_policy_service.admin_principal(user, policy, is_local_request=is_local, client_ip=client_ip)


def request_path(request: Request) -> str:
    url = getattr(request, "url", None)
    return str(getattr(url, "path", "-"))
