from __future__ import annotations

import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.db import fntv_readonly, fntv_snapshot, schema_check  # noqa: E402
from app.services import system_service  # noqa: E402


def _create_fntv_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE user (
            guid TEXT PRIMARY KEY,
            username TEXT
        );
        CREATE TABLE item (
            guid TEXT PRIMARY KEY,
            title TEXT,
            type TEXT
        );
        CREATE TABLE item_user_play (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_guid TEXT,
            item_guid TEXT,
            update_time INTEGER,
            ts INTEGER,
            watched INTEGER
        );
        """
    )
    return conn


def _source_status() -> dict[str, object]:
    return {
        "snapshot_enabled": False,
        "source_path_container": "/fntv/trimmedia.db",
        "source_exists": True,
        "source_readable": True,
        "source_readonly_configured": True,
        "snapshot_path_container": "/data/cache/trimmedia.snapshot.db",
        "snapshot_exists": False,
        "snapshot_dir_exists": False,
        "snapshot_dir_writable": False,
        "snapshot_tmp_path": "/data/cache/trimmedia.snapshot.tmp.db",
        "snapshot_last_refresh_at": None,
        "snapshot_ok": None,
        "snapshot_error": None,
        "snapshot_error_type": None,
        "snapshot_error_message": None,
        "active_database": "none",
    }


@contextmanager
def _patched_database_status_source(open_result):
    original_snapshot_status = system_service.snapshot_status
    original_open = system_service.open_fntv_connection
    system_service.snapshot_status = _source_status
    system_service.open_fntv_connection = open_result
    try:
        yield
    finally:
        system_service.snapshot_status = original_snapshot_status
        system_service.open_fntv_connection = original_open


def test_readonly_uri_uses_configured_path() -> None:
    expected = "file:/fntv/trimmedia.db?mode=ro"
    assert fntv_readonly._readonly_uri(Path("/fntv/trimmedia.db")) == expected
    assert fntv_snapshot._readonly_uri(Path("/fntv/trimmedia.db")) == expected
    assert schema_check._readonly_uri(Path("/fntv/trimmedia.db")) == expected


def test_database_status_source_direct_ok_after_reports_import() -> None:
    conn = _create_fntv_db()
    try:
        from app.services import report_service  # noqa: F401

        with _patched_database_status_source(lambda: conn):
            status = system_service.database_status(detail=True)["fntv"]
    finally:
        conn.close()
    assert status["source_exists"] is True
    assert status["source_readable"] is True
    assert status["source_direct_ok"] is True
    assert status["active_database"] == "source"
    assert status["availability"] == "available"
    assert status["ok"] is True
    assert status["source_test_query"] == "sqlite_master"
    assert status["source_direct_error_type"] is None
    assert status["source_direct_error_message"] is None
    assert status["detected_table_count"] >= 3
    assert status["core_candidates"] == {
        "user_table": "user",
        "item_table": "item",
        "play_table": "item_user_play",
    }


def test_database_status_exposes_source_direct_error() -> None:
    def raise_sqlite_error():
        raise sqlite3.DatabaseError("file is not a database")

    with _patched_database_status_source(raise_sqlite_error):
        status = system_service.database_status(detail=True)["fntv"]
    assert status["source_exists"] is True
    assert status["source_readable"] is True
    assert status["source_direct_ok"] is False
    assert status["source_test_query"] == "sqlite_master"
    assert status["source_direct_error_type"]
    assert status["source_direct_error_message"]
    assert "/" not in status["source_direct_error_message"].replace("file:", "")
    assert "\\" not in status["source_direct_error_message"]


def main() -> None:
    test_readonly_uri_uses_configured_path()
    test_database_status_source_direct_ok_after_reports_import()
    test_database_status_exposes_source_direct_error()
    print("database status smoke passed")


if __name__ == "__main__":
    main()
