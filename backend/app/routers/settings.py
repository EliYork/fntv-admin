from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.response import ok
from app.db.admin_db import get_session
from app.schemas.settings import AuthPolicyUpdate, SnapshotSettingUpdate
from app.services import auth_policy_service
from app.services.system_service import default_settings, save_snapshot_setting

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_admin)])


@router.get("")
def get_settings(db: Session = Depends(get_session)):
    return ok(default_settings(db))


@router.put("")
def update_settings():
    return ok({})


@router.get("/database")
def database_settings():
    return ok({})


@router.put("/database")
def update_database_settings(payload: SnapshotSettingUpdate, db: Session = Depends(get_session)):
    return ok(save_snapshot_setting(db, payload.snapshot_enabled))


@router.get("/theme")
def theme_settings():
    return ok({"theme": "system"})


@router.get("/auth-policy")
def get_auth_policy(request: Request, db: Session = Depends(get_session)):
    policy = auth_policy_service.get_auth_policy(db)
    return ok(auth_policy_service.auth_policy_payload(policy, request))


@router.put("/auth-policy")
def update_auth_policy(payload: AuthPolicyUpdate, request: Request, db: Session = Depends(get_session)):
    policy = auth_policy_service.save_auth_policy(
        db,
        local_auth_required=payload.local_auth_required,
        remote_access_policy=payload.remote_access_policy,
    )
    return ok(auth_policy_service.auth_policy_payload(policy, request))
