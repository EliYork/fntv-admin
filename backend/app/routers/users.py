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
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
    keyword: str | None = None,
    show_hidden: bool = False,
    sort_by: str | None = None,
    sort_order: str | None = None,
    db: Session = Depends(get_session),
):
    return ok(
        fntv_adapter.users_page(
            page,
            page_size,
            db=db,
            keyword=keyword,
            show_hidden=show_hidden,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )


@router.get("/{guid}")
def user_detail(guid: str, db: Session = Depends(get_session)):
    return ok(fntv_adapter.user_detail(guid, db=db))


@router.get("/{guid}/history")
def user_history(guid: str, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1)):
    return ok(fntv_adapter.user_history(guid, page, page_size))


@router.get("/{guid}/stats")
def user_stats(guid: str):
    return ok(fntv_adapter.user_stats(guid))


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
