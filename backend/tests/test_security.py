from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core import security
from app.core.config import settings


def test_placeholder_key_uses_persistent_managed_secret(tmp_path: Path) -> None:
    original_admin_path = settings.admin_db_path
    original_configured_key = settings.app_secret_key
    original_cached_key = security._managed_signing_key
    try:
        settings.admin_db_path = tmp_path / "admin.db"
        settings.app_secret_key = "change-this-to-a-long-random-string"
        security._managed_signing_key = None
        with sqlite3.connect(settings.admin_db_path) as conn:
            conn.execute("CREATE TABLE system_secrets (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

        first = security.signing_key()
        security._managed_signing_key = None
        second = security.signing_key()

        assert first == second
        assert len(first) >= security.MIN_SIGNING_KEY_LENGTH
        with sqlite3.connect(settings.admin_db_path) as conn:
            stored = conn.execute("SELECT value FROM system_secrets WHERE key = ?", ("jwt_signing_secret",)).fetchone()
        assert stored is not None and stored[0] == first
    finally:
        settings.admin_db_path = original_admin_path
        settings.app_secret_key = original_configured_key
        security._managed_signing_key = original_cached_key


def test_explicit_strong_key_takes_precedence(tmp_path: Path) -> None:
    original_admin_path = settings.admin_db_path
    original_configured_key = settings.app_secret_key
    try:
        configured = "a" * security.MIN_SIGNING_KEY_LENGTH
        settings.admin_db_path = tmp_path / "admin.db"
        settings.app_secret_key = configured

        assert security.signing_key() == configured
        assert not settings.admin_db_path.exists()
    finally:
        settings.admin_db_path = original_admin_path
        settings.app_secret_key = original_configured_key
