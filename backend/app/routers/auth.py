from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.errors import AppError
from app.core.response import ok
from app.db.admin_db import get_session
from app.schemas.auth import ChangePasswordRequest, InitAdminRequest, LoginRequest
from app.services import auth_policy_service, auth_service, initialization_service
from app.services.auth_policy_service import AuthPrincipal
from app.services.login_rate_limiter import login_rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def auth_status(request: Request, db: Session = Depends(get_session)):
    auth_policy_service.enforce_auth_endpoint_allowed(db, request)
    initialized = auth_service.admin_exists(db)
    return ok({"admin_initialized": initialized})


@router.post("/init-admin")
def init_admin(payload: InitAdminRequest, db: Session = Depends(get_session)):
    db.rollback()
    user = initialization_service.create_initial_admin(payload.username, payload.password)
    return ok({"user": user.model_dump()})


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_session)):
    policy = auth_policy_service.enforce_auth_endpoint_allowed(db, request)
    is_local, client_ip = auth_policy_service.request_is_local(request)
    if is_local and not policy.local_auth_required:
        return ok(auth_policy_service.local_login_payload(policy, request))
    login_rate_limiter.check(client_ip, payload.username)
    try:
        token = auth_service.login(db, payload.username, payload.password, client_ip, request.headers.get("user-agent"))
    except AppError as exc:
        if exc.code != "INVALID_CREDENTIALS":
            raise
        retry_after = login_rate_limiter.record_failure(client_ip, payload.username)
        if retry_after > 0:
            auth_service.add_audit_log(
                db,
                None,
                "login_rate_limited",
                "admin_user",
                auth_service.safe_username(payload.username),
                "rate limited",
                client_ip,
            )
            db.commit()
            raise AppError("LOGIN_RATE_LIMITED", "登录尝试过于频繁，请稍后重试", 429, headers={"Retry-After": str(retry_after)}) from exc
        raise
    login_rate_limiter.record_success(client_ip, payload.username)
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
    token = auth_service.change_password(db, current_user.admin_user, payload.old_password, payload.new_password)
    return ok(token.model_dump())
