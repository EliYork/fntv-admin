from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.security import HTTPAuthorizationCredentials  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.errors import AppError  # noqa: E402
from app.core import deps  # noqa: E402
from app.models import Base  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402
from app.services import auth_policy_service  # noqa: E402


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _request(host: str, headers: dict[str, str] | None = None):
    return SimpleNamespace(client=SimpleNamespace(host=host), headers=headers or {})


def _deny_code(func) -> str:
    try:
        func()
    except AppError as exc:
        return f"{exc.status_code}:{exc.code}"
    raise AssertionError("expected AppError")


def test_default_policy_requires_login_for_local(db: Session) -> None:
    request = _request("192.168.1.20")
    code = _deny_code(lambda: deps.get_current_admin(request=request, credentials=None, db=db))
    assert code == "401:AUTH_REQUIRED"


def test_local_no_auth_allows_local_me_and_protected_dependency(db: Session) -> None:
    auth_policy_service.save_auth_policy(db, local_auth_required=False, remote_access_policy="login")
    request = _request("192.168.1.20")
    principal = deps.get_current_admin(request=request, credentials=None, db=db)
    assert principal.username == "local"
    assert principal.auth_mode == "local_no_auth"
    response = auth_router.me(current_user=principal)
    data = response["data"]
    assert data["username"] == "local"
    assert data["is_admin"] is True
    assert data["auth_mode"] == "local_no_auth"
    assert data["is_local_request"] is True
    assert data["local_auth_required"] is False
    assert data["remote_access_policy"] == "login"


def test_remote_login_policy_still_requires_jwt(db: Session) -> None:
    auth_policy_service.save_auth_policy(db, local_auth_required=False, remote_access_policy="login")
    request = _request("8.8.8.8")
    code = _deny_code(lambda: deps.get_current_admin(request=request, credentials=None, db=db))
    assert code == "401:AUTH_REQUIRED"


def test_remote_deny_policy_blocks_remote_before_login(db: Session) -> None:
    auth_policy_service.save_auth_policy(db, local_auth_required=False, remote_access_policy="deny")
    request = _request("8.8.8.8")
    code = _deny_code(lambda: deps.get_current_admin(request=request, credentials=None, db=db))
    assert code == "403:REMOTE_ACCESS_DENIED"


def test_proxy_headers_are_not_trusted_by_default(db: Session) -> None:
    auth_policy_service.save_auth_policy(db, local_auth_required=False, remote_access_policy="deny")
    request = _request("192.168.1.20", {"x-forwarded-for": "8.8.8.8"})
    principal = deps.get_current_admin(request=request, credentials=None, db=db)
    assert principal.auth_mode == "local_no_auth"
    assert principal.client_ip == "192.168.1.20"


def test_proxy_headers_are_used_when_enabled(db: Session) -> None:
    original = auth_policy_service.settings.trust_proxy_headers
    auth_policy_service.settings.trust_proxy_headers = True
    try:
        auth_policy_service.save_auth_policy(db, local_auth_required=False, remote_access_policy="deny")
        request = _request("192.168.1.20", {"x-forwarded-for": "8.8.8.8"})
        code = _deny_code(lambda: deps.get_current_admin(request=request, credentials=None, db=db))
        assert code == "403:REMOTE_ACCESS_DENIED"
    finally:
        auth_policy_service.settings.trust_proxy_headers = original


def test_invalid_token_still_rejected_under_login_policy(db: Session) -> None:
    auth_policy_service.save_auth_policy(db, local_auth_required=True, remote_access_policy="login")
    request = _request("192.168.1.20")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
    code = _deny_code(lambda: deps.get_current_admin(request=request, credentials=credentials, db=db))
    assert code == "401:INVALID_TOKEN"


def main() -> None:
    tests = [
        test_default_policy_requires_login_for_local,
        test_local_no_auth_allows_local_me_and_protected_dependency,
        test_remote_login_policy_still_requires_jwt,
        test_remote_deny_policy_blocks_remote_before_login,
        test_proxy_headers_are_not_trusted_by_default,
        test_proxy_headers_are_used_when_enabled,
        test_invalid_token_still_rejected_under_login_policy,
    ]
    for test in tests:
        db = _session()
        try:
            test(db)
        finally:
            db.close()
    print("auth policy smoke passed")


if __name__ == "__main__":
    main()
