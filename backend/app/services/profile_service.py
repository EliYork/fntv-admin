from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, MediaProfile, UserProfile
from app.schemas.common import ProfileUpdate
from app.utils.time import now_ts


def upsert_user_profile(db: Session, guid: str, payload: ProfileUpdate, hidden: int | None = None, admin_user_id: int | None = None) -> dict[str, object]:
    now = now_ts()
    profile = db.scalar(select(UserProfile).where(UserProfile.fntv_user_guid == guid))
    if profile is None:
        profile = UserProfile(fntv_user_guid=guid, created_at=now, updated_at=now)
        db.add(profile)
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.note is not None:
        profile.note = payload.note
    if hidden is not None:
        profile.hidden = hidden
    profile.updated_at = now
    _audit(db, admin_user_id, "update_user_profile", "fntv_user", guid)
    db.commit()
    db.refresh(profile)
    return {"guid": guid, "display_name": profile.display_name, "note": profile.note, "hidden": bool(profile.hidden)}


def upsert_media_profile(db: Session, guid: str, payload: ProfileUpdate, hidden: int | None = None, admin_user_id: int | None = None) -> dict[str, object]:
    now = now_ts()
    profile = db.scalar(select(MediaProfile).where(MediaProfile.fntv_item_guid == guid))
    if profile is None:
        profile = MediaProfile(fntv_item_guid=guid, created_at=now, updated_at=now)
        db.add(profile)
    if payload.display_title is not None:
        profile.display_title = payload.display_title
    if payload.note is not None:
        profile.note = payload.note
    if hidden is not None:
        profile.hidden = hidden
    profile.updated_at = now
    _audit(db, admin_user_id, "update_media_profile", "fntv_media", guid)
    db.commit()
    db.refresh(profile)
    return {"guid": guid, "display_title": profile.display_title, "note": profile.note, "hidden": bool(profile.hidden)}


def _audit(db: Session, admin_user_id: int | None, action: str, target_type: str, target_id: str) -> None:
    db.add(
        AuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=None,
            ip_address=None,
            user_agent=None,
            created_at=now_ts(),
        )
    )

