from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.errors import AppError
from app.core.response import ok
from app.db.admin_db import get_session
from app.schemas.auth import ChangePasswordRequest, InitAdminRequest, LoginRequest
from app.services import auth_policy_service, auth_service
from app.services.auth_policy_service import AuthPrincipal

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def auth_status(request: Request, db: Session = Depends(get_session)):
    auth_policy_service.enforce_auth_endpoint_allowed(db, request)
    return ok({"admin_initialized": auth_service.admin_exists(db)})


@router.post("/init-admin")
def init_admin(payload: InitAdminRequest, request: Request, db: Session = Depends(get_session)):
    auth_policy_service.enforce_auth_endpoint_allowed(db, request)
    user = auth_service.create_initial_admin(db, payload.username, payload.password)
    return ok({"user": user.model_dump()})


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_session)):
    policy = auth_policy_service.enforce_auth_endpoint_allowed(db, request)
    is_local, _ = auth_policy_service.request_is_local(request)
    if is_local and not policy.local_auth_required:
        return ok(auth_policy_service.local_login_payload(policy, request))
    token = auth_service.login(
        db,
        payload.username,
        payload.password,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )
    return ok(token.model_dump())


@router.post("/logout")
def logout(current_user: AuthPrincipal = Depends(get_current_admin), db: Session = Depends(get_session)):
    if current_user.auth_mode != "local_no_auth":
        auth_service.add_audit_log(db, current_user.id, "logout", "admin_user", str(current_user.id), "admin logout")
        db.commit()
    return ok({})


@router.get("/me")
def me(current_user: AuthPrincipal = Depends(get_current_admin)):
    return ok(auth_policy_service.principal_to_out(current_user).model_dump())


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: AuthPrincipal = Depends(get_current_admin),
    db: Session = Depends(get_session),
):
    if current_user.admin_user is None:
        raise AppError("LOCAL_AUTH_PASSWORD_UNAVAILABLE", "本地免登录模式下不能修改密码", 400)
    auth_service.change_password(db, current_user.admin_user, payload.old_password, payload.new_password)
    return ok({})
