from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.response import ok
from app.db.admin_db import get_session
from app.db.fntv_snapshot import refresh_fntv_snapshot
from app.services import system_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
def health():
    return ok(system_service.health())


@router.get("/database-status")
def database_status(_: object = Depends(get_current_admin)):
    return ok(system_service.database_status())


@router.get("/storage-status")
def storage_status(_: object = Depends(get_current_admin)):
    return ok(system_service.storage_status())


@router.get("/settings")
def settings(db: Session = Depends(get_session), _: object = Depends(get_current_admin)):
    return ok(system_service.default_settings(db))


@router.post("/refresh-snapshot")
def refresh_snapshot(_: object = Depends(get_current_admin)):
    return ok(refresh_fntv_snapshot())
