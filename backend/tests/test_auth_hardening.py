from __future__ import annotations

import csv
import io
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.deps import get_current_admin
from app.core.errors import AppError
from app.db.migrations import migrate_admin_schema
from app.models import AdminUser, Base
from app.schemas.auth import InitAdminRequest
from app.services import auth_policy_service, auth_service, fntv_schema_adapter, initialization_service
from app.services.login_rate_limiter import LoginRateLimiter
from app.utils.csv import sanitize_csv_text


class FakeRequest:
    def __init__(self, peer: str, headers: dict[str, str] | None = None) -> None:
        self.client = SimpleNamespace(host=peer)
        self.headers = headers or {}
        self.url = SimpleNamespace(path="/api/test")


@pytest.fixture
def admin_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database_path = tmp_path / "admin.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "admin_db_path", database_path)
    return database_path


def test_initial_admin_requires_only_username_and_password(admin_database: Path) -> None:
    assert set(InitAdminRequest.model_fields) == {"username", "password"}
    user = initialization_service.create_initial_admin("admin", "correct-horse-1")
    assert user.username == "admin"
    with sqlite3.connect(admin_database) as conn:
        assert conn.execute("SELECT username FROM admin_users").fetchall() == [("admin",)]


def test_initial_admin_cannot_be_created_twice(admin_database: Path) -> None:
    initialization_service.create_initial_admin("admin-one", "correct-horse-1")
    with pytest.raises(AppError) as repeated:
        initialization_service.create_initial_admin("admin-two", "correct-horse-2")
    assert repeated.value.code == "ADMIN_ALREADY_EXISTS"
    assert repeated.value.status_code == 409


def test_initial_admin_creation_is_concurrent_safe(admin_database: Path) -> None:
    def initialize(username: str):
        try:
            return initialization_service.create_initial_admin(username, "correct-horse-1")
        except AppError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(initialize, ("admin-one", "admin-two")))

    assert sum(not isinstance(result, AppError) for result in results) == 1
    assert any(isinstance(result, AppError) and result.code == "ADMIN_ALREADY_EXISTS" for result in results)
    with sqlite3.connect(admin_database) as conn:
        assert conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0] == 1


def test_legacy_initialization_file_is_ignored(admin_database: Path) -> None:
    legacy_path = settings.data_dir / ("init-admin" + ".token")
    legacy_path.write_text("obsolete-value\n", encoding="utf-8")
    user = initialization_service.create_initial_admin("admin", "correct-horse-1")
    assert user.username == "admin"
    assert legacy_path.read_text(encoding="utf-8") == "obsolete-value\n"


def test_initialized_account_can_login(admin_database: Path) -> None:
    initialization_service.create_initial_admin("admin", "correct-horse-1")
    engine = create_engine(f"sqlite:///{admin_database.as_posix()}")
    with Session(engine) as db:
        result = auth_service.login(db, "admin", "correct-horse-1", "192.168.1.20", "test")
        assert result.token
        assert result.user.username == "admin"


def test_proxy_headers_require_a_trusted_direct_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    monkeypatch.setattr(settings, "trusted_proxies", "")
    spoofed = FakeRequest("203.0.113.10", {"x-forwarded-for": "192.168.1.2"})
    assert auth_policy_service.client_ip_from_request(spoofed) == "203.0.113.10"
    assert auth_policy_service.request_is_local(spoofed) == (False, "203.0.113.10")

    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    monkeypatch.setattr(settings, "trusted_proxies", "10.0.0.5/32,172.18.0.0/16,::1/128")
    trusted = FakeRequest("10.0.0.5", {"x-forwarded-for": "198.51.100.8, 172.18.0.3"})
    assert auth_policy_service.client_ip_from_request(trusted) == "198.51.100.8"
    assert auth_policy_service.request_is_local(trusted) == (False, "198.51.100.8")

    untrusted = FakeRequest("203.0.113.11", {"x-forwarded-for": "192.168.1.2"})
    assert auth_policy_service.client_ip_from_request(untrusted) == "203.0.113.11"
    assert auth_policy_service.request_is_local(untrusted) == (False, "203.0.113.11")

    ipv6 = FakeRequest("::1", {"forwarded": 'for="[2001:db8::1234]:443"'})
    assert auth_policy_service.client_ip_from_request(ipv6) == "2001:db8::1234"


def test_untrusted_private_proxy_hop_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    monkeypatch.setattr(settings, "trusted_proxies", "10.0.0.5/32")
    request = FakeRequest("10.0.0.5", {"x-forwarded-for": "198.51.100.8, 192.168.1.9"})
    assert auth_policy_service.client_ip_from_request(request) == "192.168.1.9"
    assert auth_policy_service.request_is_local(request) == (False, "192.168.1.9")


def test_login_rate_limit_threshold_success_and_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import login_rate_limiter as module

    now = [1000.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    limiter = LoginRateLimiter()
    for _ in range(module.PAIR_FAILURE_LIMIT - 1):
        assert limiter.record_failure("198.51.100.10", "admin") == 0
        limiter.check("198.51.100.10", "admin")
    assert limiter.record_failure("198.51.100.10", "admin") == module.BLOCK_SECONDS
    with pytest.raises(AppError) as blocked:
        limiter.check("198.51.100.10", "admin")
    assert blocked.value.status_code == 429
    assert blocked.value.headers == {"Retry-After": str(module.BLOCK_SECONDS)}

    limiter.record_success("198.51.100.10", "admin")
    limiter.check("198.51.100.10", "admin")
    limiter.record_failure("198.51.100.20", "old")
    now[0] += module.ENTRY_TTL_SECONDS + 1
    limiter.check("198.51.100.21", "new")
    assert not limiter._pairs and not limiter._ips


def test_login_rate_limit_caps_random_username_state(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import login_rate_limiter as module

    monkeypatch.setattr(module, "MAX_PAIR_ENTRIES", 3)
    limiter = LoginRateLimiter()
    for index in range(10):
        limiter.record_failure("198.51.100.30", f"random-{index}")
    assert len(limiter._pairs) == 3


def test_login_rate_limit_aggregates_random_usernames_by_ip() -> None:
    from app.services import login_rate_limiter as module

    limiter = LoginRateLimiter()
    retry_after = 0
    for index in range(module.IP_FAILURE_LIMIT):
        retry_after = limiter.record_failure("198.51.100.40", f"random-{index}")
    assert retry_after == module.BLOCK_SECONDS
    with pytest.raises(AppError) as blocked:
        limiter.check("198.51.100.40", "another-name")
    assert blocked.value.status_code == 429


def test_csv_formula_prefixes_are_sanitized_without_changing_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    for dangerous in ("=1+1", "+cmd", "-10+20", "@SUM(A1:A2)", "\t=1", "\r=1"):
        assert sanitize_csv_text(dangerous) == f"'{dangerous}"
    assert sanitize_csv_text("Breaking Bad") == "Breaking Bad"

    monkeypatch.setattr(
        fntv_schema_adapter,
        "history_page",
        lambda *_args, **_kwargs: {
            "items": [{"id": "=1+1", "username": "+cmd", "display_title": "Breaking Bad", "progress_percent": 12.5}],
        },
    )
    row = next(csv.DictReader(io.StringIO(fntv_schema_adapter.history_csv())))
    assert row["id"] == "'=1+1"
    assert row["username"] == "'+cmd"
    assert row["display_title"] == "Breaking Bad"
    assert row["progress_percent"] == "12.5"


def test_password_change_invalidates_old_token_and_new_token_works(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "auth.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "app_secret_key", "s" * security.MIN_SIGNING_KEY_LENGTH)
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    with Session(engine) as db:
        user = AdminUser(
            username="admin",
            password_hash=security.hash_password("old-password"),
            role="admin",
            created_at=1,
            updated_at=1,
            token_version=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        old_token = security.create_access_token(str(user.id), user.token_version)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=old_token)
        request = FakeRequest("203.0.113.50")
        assert get_current_admin(request, credentials, db).id == user.id

        replacement = auth_service.change_password(db, user, "old-password", "new-password")
        with pytest.raises(AppError) as rejected:
            get_current_admin(request, credentials, db)
        assert rejected.value.status_code == 401
        new_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=replacement.token)
        assert get_current_admin(request, new_credentials, db).id == user.id


def test_token_version_migration_preserves_existing_admin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "legacy.db"
    password_hash = security.hash_password("legacy-password")
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            "CREATE TABLE admin_users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, password_hash TEXT NOT NULL, "
            "role TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, last_login_at INTEGER)"
        )
        conn.execute(
            "INSERT INTO admin_users VALUES (1, 'admin', ?, 'admin', 1, 1, NULL)",
            (password_hash,),
        )
    migrate_admin_schema(database_path)
    migrate_admin_schema(database_path)
    with sqlite3.connect(database_path) as conn:
        assert conn.execute("SELECT username, token_version FROM admin_users").fetchone() == ("admin", 1)
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "app_secret_key", "m" * security.MIN_SIGNING_KEY_LENGTH)
    with Session(engine) as db:
        result = auth_service.login(db, "admin", "legacy-password", "127.0.0.1", None)
        assert result.user.username == "admin"


def test_invalid_login_message_does_not_reveal_user_existence(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'login.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            AdminUser(
                username="admin",
                password_hash=security.hash_password("correct-password"),
                role="admin",
                created_at=1,
                updated_at=1,
                token_version=1,
            )
        )
        db.commit()
        errors = []
        for username in ("admin", "missing"):
            with pytest.raises(AppError) as caught:
                auth_service.login(db, username, "wrong-password", "198.51.100.60", None)
            errors.append((caught.value.code, caught.value.message, caught.value.status_code))
        assert errors[0] == errors[1] == ("INVALID_CREDENTIALS", "用户名或密码错误", 401)
