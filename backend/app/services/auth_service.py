from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import AdminUser, AuditLog
from app.schemas.auth import AdminUserOut, TokenOut
from app.utils.time import now_ts

_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def admin_exists(db: Session) -> bool:
    return bool(db.scalar(select(func.count()).select_from(AdminUser)))


def admin_to_out(user: AdminUser) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def login(db: Session, username: str, password: str, ip_address: str | None, user_agent: str | None) -> TokenOut:
    user = db.scalar(select(AdminUser).where(AdminUser.username == username.strip()))
    password_valid = verify_password(password, user.password_hash if user is not None else _DUMMY_PASSWORD_HASH)
    if user is None or not password_valid:
        add_audit_log(db, None, "login_failed", "admin_user", safe_username(username), "invalid credentials", ip_address, user_agent)
        db.commit()
        raise AppError("INVALID_CREDENTIALS", "用户名或密码错误", 401)
    user.last_login_at = now_ts()
    user.updated_at = user.last_login_at
    add_audit_log(db, user.id, "login", "admin_user", str(user.id), "admin login", ip_address, user_agent)
    db.commit()
    db.refresh(user)
    return TokenOut(token=create_access_token(str(user.id), user.token_version), user=admin_to_out(user))


def change_password(db: Session, user: AdminUser, old_password: str, new_password: str) -> TokenOut:
    if not verify_password(old_password, user.password_hash):
        raise AppError("INVALID_PASSWORD", "原密码错误", 400)
    user.password_hash = hash_password(new_password)
    user.token_version += 1
    user.updated_at = now_ts()
    add_audit_log(db, user.id, "change_password", "admin_user", str(user.id), "password changed")
    db.commit()
    db.refresh(user)
    return TokenOut(token=create_access_token(str(user.id), user.token_version), user=admin_to_out(user))


def add_audit_log(
    db: Session,
    admin_user_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now_ts(),
        )
    )


def safe_username(username: str) -> str:
    return "".join(character for character in username.strip() if character.isprintable())[:64]
