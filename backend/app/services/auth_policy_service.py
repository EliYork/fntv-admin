from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import AdminUser, Setting
from app.schemas.auth import AdminUserOut
from app.utils.time import now_ts

LOCAL_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "127.0.0.0/8",
        "::1/128",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "fc00::/7",
        "fe80::/10",
    )
)

REMOTE_ACCESS_POLICIES = {"login", "deny"}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthPolicy:
    local_auth_required: bool = True
    remote_access_policy: str = "login"


@dataclass
class AuthPrincipal:
    id: int | None
    username: str
    role: str
    created_at: int
    last_login_at: int | None
    auth_mode: str
    is_local_request: bool
    local_auth_required: bool
    remote_access_policy: str
    client_ip: str | None
    admin_user: AdminUser | None = None

    @property
    def is_admin(self) -> bool:
        return True


def get_auth_policy(db: Session) -> AuthPolicy:
    local_required = _setting_bool(db, "local_auth_required", True)
    remote_policy = _setting_text(db, "remote_access_policy", "login")
    if remote_policy not in REMOTE_ACCESS_POLICIES:
        remote_policy = "login"
    return AuthPolicy(local_auth_required=local_required, remote_access_policy=remote_policy)


def save_auth_policy(db: Session, *, local_auth_required: bool, remote_access_policy: str) -> AuthPolicy:
    if remote_access_policy not in REMOTE_ACCESS_POLICIES:
        raise AppError("INVALID_AUTH_POLICY", "外部访问策略不合法", 422)
    now = now_ts()
    db.merge(Setting(key="local_auth_required", value="true" if local_auth_required else "false", value_type="bool", updated_at=now))
    db.merge(Setting(key="remote_access_policy", value=remote_access_policy, value_type="string", updated_at=now))
    db.commit()
    return AuthPolicy(local_auth_required=local_auth_required, remote_access_policy=remote_access_policy)


def auth_policy_payload(policy: AuthPolicy, request: Request | Any | None = None) -> dict[str, Any]:
    is_local, client_ip = request_is_local(request) if request is not None else (None, None)
    return {
        "local_auth_required": policy.local_auth_required,
        "remote_access_policy": policy.remote_access_policy,
        "trust_proxy_headers": settings.trust_proxy_headers,
        "is_local_request": is_local,
        "client_ip": client_ip,
    }


def request_is_local(request: Request | Any) -> tuple[bool, str | None]:
    client_ip = client_ip_from_request(request)
    if not client_ip:
        return False, None
    try:
        address = ipaddress.ip_address(client_ip)
    except ValueError:
        return False, client_ip
    return any(address in network for network in LOCAL_NETWORKS), client_ip


def client_ip_from_request(request: Request | Any) -> str | None:
    if settings.trust_proxy_headers:
        forwarded = _header(request, "x-forwarded-for")
        if forwarded:
            first = forwarded.split(",", 1)[0].strip()
            if first:
                return first
        real_ip = _header(request, "x-real-ip")
        if real_ip:
            return real_ip.strip()
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return str(host) if host else None


def enforce_remote_access(policy: AuthPolicy, request: Request | Any) -> tuple[bool, str | None]:
    is_local, client_ip = request_is_local(request)
    if not is_local and policy.remote_access_policy == "deny":
        logger.info("auth rejected: path=%s status=403 code=REMOTE_ACCESS_DENIED client=%s", _request_path(request), client_ip)
        raise AppError("REMOTE_ACCESS_DENIED", "外部访问已被禁止", 403)
    return is_local, client_ip


def local_principal(policy: AuthPolicy, client_ip: str | None) -> AuthPrincipal:
    return AuthPrincipal(
        id=None,
        username="local",
        role="admin",
        created_at=0,
        last_login_at=None,
        auth_mode="local_no_auth",
        is_local_request=True,
        local_auth_required=policy.local_auth_required,
        remote_access_policy=policy.remote_access_policy,
        client_ip=client_ip,
        admin_user=None,
    )


def admin_principal(user: AdminUser, policy: AuthPolicy, *, is_local_request: bool, client_ip: str | None) -> AuthPrincipal:
    return AuthPrincipal(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        auth_mode="jwt",
        is_local_request=is_local_request,
        local_auth_required=policy.local_auth_required,
        remote_access_policy=policy.remote_access_policy,
        client_ip=client_ip,
        admin_user=user,
    )


def principal_to_out(principal: AuthPrincipal) -> AdminUserOut:
    return AdminUserOut(
        id=principal.id,
        username=principal.username,
        role=principal.role,
        created_at=principal.created_at,
        last_login_at=principal.last_login_at,
        is_admin=principal.is_admin,
        auth_mode=principal.auth_mode,
        is_local_request=principal.is_local_request,
        local_auth_required=principal.local_auth_required,
        remote_access_policy=principal.remote_access_policy,
    )


def local_login_payload(policy: AuthPolicy, request: Request | Any) -> dict[str, Any]:
    _, client_ip = request_is_local(request)
    principal = local_principal(policy, client_ip)
    return {"token": "", "token_type": "local", "user": principal_to_out(principal)}


def enforce_auth_endpoint_allowed(db: Session, request: Request | Any) -> AuthPolicy:
    policy = get_auth_policy(db)
    enforce_remote_access(policy, request)
    return policy


def _setting_text(db: Session, key: str, default: str) -> str:
    row = db.get(Setting, key)
    if row is None or row.value in (None, ""):
        return default
    return str(row.value)


def _setting_bool(db: Session, key: str, default: bool) -> bool:
    row = db.get(Setting, key)
    if row is None or row.value in (None, ""):
        return default
    return str(row.value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _header(request: Request | Any, name: str) -> str | None:
    headers = getattr(request, "headers", None)
    if headers is None:
        return None
    value = headers.get(name)
    if value is None:
        value = headers.get(name.title())
    return str(value) if value is not None else None


def _request_path(request: Request | Any) -> str:
    url = getattr(request, "url", None)
    return str(getattr(url, "path", "-"))
