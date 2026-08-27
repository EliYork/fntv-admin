from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import fntv_snapshot
from app.models import Base, Setting
from app.services.system_service import default_settings


def _admin_session(path: Path) -> Session:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_new_install_snapshot_defaults_are_enabled_for_fifteen_minutes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "snapshot_enabled", True)
    monkeypatch.setattr(settings, "snapshot_refresh_interval_seconds", 900)
    with _admin_session(tmp_path / "admin.db") as db:
        result = default_settings(db)
        assert result["snapshot_enabled"] == "true"
        assert result["snapshot_refresh_interval_seconds"] == "900"


def test_existing_snapshot_choices_are_not_overwritten(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "snapshot_enabled", True)
    monkeypatch.setattr(settings, "snapshot_refresh_interval_seconds", 900)
    with _admin_session(tmp_path / "admin.db") as db:
        db.add_all(
            [
                Setting(key="snapshot_enabled", value="false", value_type="bool", updated_at=1),
                Setting(key="snapshot_refresh_interval_seconds", value="3600", value_type="string", updated_at=1),
            ]
        )
        db.commit()
        result = default_settings(db)
        assert result["snapshot_enabled"] == "false"
        assert result["snapshot_refresh_interval_seconds"] == "3600"


def test_only_missing_snapshot_key_is_added(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "snapshot_enabled", True)
    monkeypatch.setattr(settings, "snapshot_refresh_interval_seconds", 900)
    with _admin_session(tmp_path / "admin.db") as db:
        db.add(Setting(key="snapshot_enabled", value="false", value_type="bool", updated_at=1))
        db.commit()
        result = default_settings(db)
        assert result["snapshot_enabled"] == "false"
        assert result["snapshot_refresh_interval_seconds"] == "900"
        assert db.get(Setting, "snapshot_enabled").value == "false"


def test_missing_cache_directory_is_recreated(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "trimmedia.db"
    cache = tmp_path / "missing" / "cache"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE item (guid TEXT PRIMARY KEY)")
    monkeypatch.setattr(settings, "admin_db_path", tmp_path / "absent-admin.db")
    monkeypatch.setattr(settings, "fntv_db_path", source)
    monkeypatch.setattr(settings, "cache_dir", cache)
    monkeypatch.setattr(settings, "snapshot_enabled", True)
    result = fntv_snapshot.refresh_fntv_snapshot()
    assert result["ok"] is True, result
    assert cache.is_dir()
    assert (cache / "trimmedia.snapshot.db").exists()


def test_snapshot_failure_keeps_readonly_source_fallback(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "trimmedia.db"
    cache_file = tmp_path / "cache-is-a-file"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE item (guid TEXT PRIMARY KEY)")
    cache_file.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(settings, "admin_db_path", tmp_path / "absent-admin.db")
    monkeypatch.setattr(settings, "fntv_db_path", source)
    monkeypatch.setattr(settings, "cache_dir", cache_file)
    monkeypatch.setattr(settings, "snapshot_enabled", True)
    result = fntv_snapshot.refresh_fntv_snapshot()
    assert result["ok"] is False
    assert result["fallback_to_source"] is True
    with fntv_snapshot.open_fntv_source_connection() as conn:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
