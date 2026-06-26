from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.response import ok
from app.db.admin_db import get_session
from app.models import AdminUser
from app.schemas.common import ProfileUpdate
from app.services import fntv_adapter, profile_service

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_users(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=200), keyword: str | None = None):
    _ = keyword
    return ok(fntv_adapter.users_page(page, page_size))


@router.get("/{guid}")
def user_detail(guid: str):
    return ok({"guid": guid, "stats": {"play_count": 0, "watch_seconds": 0}, "recent_history": []})


@router.get("/{guid}/history")
def user_history(guid: str, page: int = 1, page_size: int = 20):
    _ = guid
    return ok(fntv_adapter.history_page(page, page_size))


@router.get("/{guid}/stats")
def user_stats(guid: str):
    return ok({"guid": guid, "play_count": 0, "watch_seconds": 0, "recent_play_at": None})


@router.put("/{guid}/profile")
def update_user_profile(
    guid: str,
    payload: ProfileUpdate,
    db: Session = Depends(get_session),
    current_user: AdminUser = Depends(get_current_admin),
):
    return ok(profile_service.upsert_user_profile(db, guid, payload, admin_user_id=current_user.id))


@router.post("/{guid}/hide")
def hide_user(guid: str, db: Session = Depends(get_session), current_user: AdminUser = Depends(get_current_admin)):
    return ok(profile_service.upsert_user_profile(db, guid, ProfileUpdate(), hidden=1, admin_user_id=current_user.id))


@router.post("/{guid}/unhide")
def unhide_user(guid: str, db: Session = Depends(get_session), current_user: AdminUser = Depends(get_current_admin)):
    return ok(profile_service.upsert_user_profile(db, guid, ProfileUpdate(), hidden=0, admin_user_id=current_user.id))

