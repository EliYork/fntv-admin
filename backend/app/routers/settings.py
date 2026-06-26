from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.response import ok
from app.db.admin_db import get_session
from app.services.system_service import default_settings

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


@router.get("/theme")
def theme_settings():
    return ok({"theme": "system"})

