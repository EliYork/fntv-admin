from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.response import ok
from app.db.admin_db import get_session
from app.models import AdminUser
from app.schemas.auth import ChangePasswordRequest, InitAdminRequest, LoginRequest
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def auth_status(db: Session = Depends(get_session)):
    return ok({"admin_initialized": auth_service.admin_exists(db)})


@router.post("/init-admin")
def init_admin(payload: InitAdminRequest, db: Session = Depends(get_session)):
    user = auth_service.create_initial_admin(db, payload.username, payload.password)
    return ok({"user": user.model_dump()})


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_session)):
    token = auth_service.login(
        db,
        payload.username,
        payload.password,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )
    return ok(token.model_dump())


@router.post("/logout")
def logout(current_user: AdminUser = Depends(get_current_admin), db: Session = Depends(get_session)):
    auth_service.add_audit_log(db, current_user.id, "logout", "admin_user", str(current_user.id), "admin logout")
    db.commit()
    return ok({})


@router.get("/me")
def me(current_user: AdminUser = Depends(get_current_admin)):
    return ok(auth_service.admin_to_out(current_user).model_dump())


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_session),
):
    auth_service.change_password(db, current_user, payload.old_password, payload.new_password)
    return ok({})

