from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.response import ok
from app.db.admin_db import get_session
from app.models import AdminUser
from app.schemas.common import ProfileUpdate
from app.services import fntv_adapter, profile_service

router = APIRouter(prefix="/api/media", tags=["media"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_media(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    keyword: str | None = None,
    media_type: str | None = None,
    show_hidden: bool = False,
    db: Session = Depends(get_session),
):
    return ok(fntv_adapter.media_page(page, page_size, db=db, keyword=keyword, media_type=media_type, show_hidden=show_hidden))


@router.get("/tree")
def media_tree():
    return ok(fntv_adapter.media_tree())


@router.get("/{guid}")
def media_detail(guid: str, db: Session = Depends(get_session)):
    return ok(fntv_adapter.media_detail(guid, db=db))


@router.get("/{guid}/children")
def children(guid: str):
    return ok(fntv_adapter.media_children(guid))


@router.get("/{guid}/history")
def media_history(guid: str, page: int = 1, page_size: int = 20):
    return ok(fntv_adapter.media_history(guid, page, page_size))


@router.get("/{guid}/stats")
def media_stats(guid: str):
    return ok(fntv_adapter.media_stats(guid))


@router.put("/{guid}/profile")
def update_media_profile(
    guid: str,
    payload: ProfileUpdate,
    db: Session = Depends(get_session),
    current_user: AdminUser = Depends(get_current_admin),
):
    return ok(profile_service.upsert_media_profile(db, guid, payload, admin_user_id=current_user.id))


@router.post("/{guid}/hide")
def hide_media(guid: str, db: Session = Depends(get_session), current_user: AdminUser = Depends(get_current_admin)):
    return ok(profile_service.upsert_media_profile(db, guid, ProfileUpdate(), hidden=1, admin_user_id=current_user.id))


@router.post("/{guid}/unhide")
def unhide_media(guid: str, db: Session = Depends(get_session), current_user: AdminUser = Depends(get_current_admin)):
    return ok(profile_service.upsert_media_profile(db, guid, ProfileUpdate(), hidden=0, admin_user_id=current_user.id))
