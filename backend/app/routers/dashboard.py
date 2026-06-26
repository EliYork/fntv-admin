from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.core.response import ok
from app.services import fntv_adapter, system_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_admin)])


@router.get("/overview")
def overview():
    return ok(fntv_adapter.overview_data())


@router.get("/recent-activities")
def recent_activities():
    return ok(fntv_adapter.recent_activities())


@router.get("/play-trend")
def play_trend():
    return ok(fntv_adapter.play_trend())


@router.get("/top-media")
def top_media():
    return ok(fntv_adapter.top_media())


@router.get("/top-users")
def top_users():
    return ok(fntv_adapter.top_users())


@router.get("/system-status")
def dashboard_system_status():
    return ok({"database": system_service.database_status(), "storage": system_service.storage_status()})

