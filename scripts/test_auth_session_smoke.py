from __future__ import annotations

import sys
from pathlib import Path

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core import deps  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.models import Base  # noqa: E402
from app.routers import auth, dashboard, history, media, reports, settings, system, users  # noqa: E402
from app.services import auth_policy_service, auth_service, fntv_adapter, report_service, system_service  # noqa: E402


def _session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class FakeUrl:
    path = "/api/test"


class FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class FakeRequest:
    def __init__(self, host: str = "192.168.1.20") -> None:
        self.client = FakeClient(host)
        self.headers: dict[str, str] = {}
        self.url = FakeUrl()


def _patch_read_services() -> dict[str, object]:
    originals = {
        "overview_data": fntv_adapter.overview_data,
        "history_page": fntv_adapter.history_page,
        "users_page": fntv_adapter.users_page,
        "media_page": fntv_adapter.media_page,
        "report_overview": report_service.overview,
        "database_status": system_service.database_status,
    }
    fntv_adapter.overview_data = lambda: {"total_users": 0, "total_media": 0, "total_plays": 0}
    fntv_adapter.history_page = lambda *args, **kwargs: {"items": [], "page": 1, "page_size": 20, "total": 0, "pages": 0}
    fntv_adapter.users_page = lambda *args, **kwargs: {"items": [], "page": 1, "page_size": 20, "total": 0, "pages": 0}
    fntv_adapter.media_page = lambda *args, **kwargs: {"items": [], "page": 1, "page_size": 20, "total": 0, "pages": 0}
    report_service.overview = lambda: {
        "total_users": 0,
        "total_media": 0,
        "total_play_records": 0,
        "watched_records": 0,
        "active_users_7d": 0,
        "active_users_30d": 0,
        "plays_7d": 0,
        "plays_30d": 0,
        "total_watch_seconds": 0,
        "avg_progress_percent": None,
        "generated_at": "1970-01-01T00:00:00Z",
    }
    system_service.database_status = lambda detail=False: {
        "fntv": {"ok": True, "availability": "available"},
        "admin": {"exists": True, "ok": True},
    }
    return originals


def _restore_read_services(originals: dict[str, object]) -> None:
    fntv_adapter.overview_data = originals["overview_data"]
    fntv_adapter.history_page = originals["history_page"]
    fntv_adapter.users_page = originals["users_page"]
    fntv_adapter.media_page = originals["media_page"]
    report_service.overview = originals["report_overview"]
    system_service.database_status = originals["database_status"]


def _deny_code(func) -> str:
    try:
        func()
    except AppError as exc:
        return f"{exc.status_code}:{exc.code}"
    raise AssertionError("expected AppError")


def _token(db: Session) -> str:
    payload = auth_service.login(db, "admin", "password123", "192.168.1.20", "smoke")
    token = payload.token
    assert token
    return token


def _principal(db: Session, token: str):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return deps.get_current_admin(request=FakeRequest(), credentials=credentials, db=db)


def test_valid_token_is_stable_across_protected_api() -> None:
    session_factory = _session_factory()
    db: Session = session_factory()
    try:
        auth_service.create_initial_admin(db, "admin", "password123")
        token = _token(db)
        first_principal = _principal(db, token)
        second_principal = _principal(db, token)
        assert first_principal.username == second_principal.username == "admin"
        assert first_principal.auth_mode == second_principal.auth_mode == "jwt"
        assert first_principal.local_auth_required is True
        assert first_principal.remote_access_policy == "login"
    finally:
        db.close()

    originals = _patch_read_services()
    try:
        db = session_factory()
        try:
            principal = _principal(db, token)
            responses = [
                auth.me(current_user=principal),
                dashboard.overview(),
                history.list_history(),
                users.list_users(db=db),
                media.list_media(db=db),
                reports.overview(),
                system.database_status(detail=True, _=principal),
                settings.get_settings(db=db),
            ]
            for response in responses:
                assert response["success"] is True
        finally:
            db.close()
    finally:
        _restore_read_services(originals)


def test_missing_token_returns_401_for_protected_api() -> None:
    session_factory = _session_factory()
    db: Session = session_factory()
    try:
        for path in ("/api/reports/overview", "/api/system/database-status?detail=true", "/api/settings"):
            request = FakeRequest()
            request.url.path = path
            code = _deny_code(lambda: deps.get_current_admin(request=request, credentials=None, db=db))
            assert code == "401:AUTH_REQUIRED"
    finally:
        db.close()


def test_remote_deny_returns_403_not_401() -> None:
    session_factory = _session_factory()
    db: Session = session_factory()
    try:
        auth_policy_service.save_auth_policy(db, local_auth_required=True, remote_access_policy="deny")
        request = FakeRequest("8.8.8.8")
        request.url.path = "/api/settings"
        code = _deny_code(lambda: deps.get_current_admin(request=request, credentials=None, db=db))
        assert code == "403:REMOTE_ACCESS_DENIED"
    finally:
        db.close()


def main() -> None:
    test_valid_token_is_stable_across_protected_api()
    test_missing_token_returns_401_for_protected_api()
    test_remote_deny_returns_403_not_401()
    print("auth session smoke passed")


if __name__ == "__main__":
    main()
