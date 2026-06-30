from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db import fntv_snapshot  # noqa: E402
from app.core.deps import get_current_admin  # noqa: E402
from app.routers import dashboard, downloads, favorites, reports  # noqa: E402
from app.services import fntv_schema_adapter as adapter  # noqa: E402
from app.services import report_service, system_service  # noqa: E402


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE user (
            guid TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            visible INTEGER DEFAULT 1
        );
        CREATE TABLE item (
            guid TEXT PRIMARY KEY,
            title TEXT,
            original_title TEXT,
            filename TEXT,
            type TEXT,
            parent_guid TEXT,
            runtime INTEGER,
            season_number INTEGER,
            episode_number INTEGER,
            visible INTEGER DEFAULT 1
        );
        CREATE TABLE media_stream (
            item_guid TEXT,
            duration INTEGER,
            codec_type TEXT
        );
        CREATE TABLE item_user_play (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_guid TEXT,
            item_guid TEXT,
            media_guid TEXT,
            update_time INTEGER,
            create_time INTEGER,
            ts INTEGER,
            watched INTEGER,
            resolution TEXT,
            visible INTEGER DEFAULT 1
        );
        CREATE TABLE item_user_favorite (
            user_guid TEXT,
            item_guid TEXT,
            create_time INTEGER
        );
        CREATE TABLE download_task (
            user_guid TEXT,
            media_file TEXT,
            output_file TEXT,
            resolution TEXT,
            status INTEGER,
            create_time INTEGER,
            update_time INTEGER
        );
        """
    )
    return conn


def _seed(conn: sqlite3.Connection) -> None:
    now = int(time.time())
    now_ms = now * 1000
    old_ms = (now - (10 * 86_400)) * 1000
    today_start = int(time.localtime(now).tm_hour)
    conn.executemany(
        'INSERT INTO "user" (guid, username, visible) VALUES (?, ?, ?)',
        [("u1", "alice", 1), ("u2", "bob", 1)],
    )
    conn.executemany(
        'INSERT INTO "item" (guid, title, type, parent_guid, runtime, season_number, episode_number, visible) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("series-1", "剧集 A", "Series", None, 0, None, None, 1),
            ("season-1", "第一季", "Season", "series-1", 0, 1, None, 1),
            ("e1", "第一集", "Episode", "season-1", 44, 1, 1, 1),
            ("m1", "电影一", "Movie", None, 7200, None, None, 1),
        ],
    )
    conn.execute('INSERT INTO media_stream (item_guid, duration, codec_type) VALUES (?, ?, ?)', ("e1", 3600, "video"))
    conn.executemany(
        'INSERT INTO item_user_play (user_guid, item_guid, update_time, create_time, ts, watched, resolution, visible) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("u1", "e1", now_ms, now_ms, 1200, 0, "1080p", 1),
            ("u2", "m1", old_ms, old_ms, 3600, 1, "4K", 1),
        ],
    )
    conn.execute('INSERT INTO item_user_favorite (user_guid, item_guid, create_time) VALUES (?, ?, ?)', ("u1", "e1", now_ms))
    conn.execute(
        'INSERT INTO download_task (user_guid, media_file, output_file, resolution, status, create_time, update_time) VALUES (?, ?, ?, ?, ?, ?, ?)',
        ("u2", "movie-one.mkv", "/downloads/movie-one.mkv", "4K", 2, old_ms, now_ms),
    )
    assert 0 <= today_start <= 23


def test_hourly_distribution(conn: sqlite3.Connection) -> None:
    rows = report_service.hourly_distribution(days="all", conn=conn)
    assert len(rows) == 24
    assert sum(row["play_count"] for row in rows) == 2
    assert all(0 <= row["hour"] <= 23 for row in rows)


def test_active_watches_use_recent_update_time(conn: sqlite3.Connection) -> None:
    rows = adapter.active_watches(window_seconds=300, conn=conn)
    assert len(rows) == 1
    assert rows[0]["username"] == "alice"
    assert rows[0]["window_seconds"] == 300
    assert rows[0]["progress_percent"] == 33.3
    assert rows[0]["display_title"].startswith("剧集 A")


def test_favorites_and_downloads_are_paged_readonly_lists(conn: sqlite3.Connection) -> None:
    favorites = adapter.favorites_page(page=1, page_size=20, keyword="第一", conn=conn)
    assert favorites["capability"] is True
    assert favorites["total"] == 1
    assert favorites["items"][0]["username"] == "alice"
    downloads = adapter.downloads_page(page=1, page_size=20, keyword="movie", status="2", conn=conn)
    assert downloads["capability"] is True
    assert downloads["total"] == 1
    assert downloads["items"][0]["status_text"] == "已完成"


def test_missing_optional_tables_return_empty_capability_false() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE user (guid TEXT PRIMARY KEY, username TEXT);
        CREATE TABLE item (guid TEXT PRIMARY KEY, title TEXT);
        CREATE TABLE item_user_play (user_guid TEXT, item_guid TEXT);
        """
    )
    try:
        assert adapter.favorites_page(1, 20, conn=conn)["capability"] is False
        assert adapter.downloads_page(1, 20, conn=conn)["capability"] is False
    finally:
        conn.close()


def test_history_filters_and_csv_enhanced_fields(conn: sqlite3.Connection) -> None:
    page = adapter.history_page(1, 20, {"range": "7d"}, conn=conn)
    assert page["total"] == 1
    csv_text = adapter.history_csv({"range": "all"}, conn=conn)
    for header in ("username", "display_title", "started_at", "played_at", "position", "runtime", "progress_percent", "item_guid", "user_guid"):
        assert header in csv_text.splitlines()[0]


def test_watched_diagnostics_do_not_return_rows(conn: sqlite3.Connection) -> None:
    diag = adapter.watched_field_diagnostics(conn=conn)
    assert diag["available"] is True
    assert diag["watched_min"] == 0
    assert diag["watched_max"] == 1
    assert diag["watched_nonzero_count"] == 1
    assert "rows" not in diag


def test_snapshot_disabled_and_failed_fallback_status() -> None:
    tmp_root = ROOT / ".tmp_smoke"
    tmp_root.mkdir(exist_ok=True)
    original_source = fntv_snapshot.settings.fntv_db_path
    original_cache = fntv_snapshot.settings.cache_dir
    original_enabled = fntv_snapshot.settings.snapshot_enabled
    original_source_direct_ok = fntv_snapshot.source_direct_ok
    try:
        fntv_snapshot.source_direct_ok = lambda: True
        fntv_snapshot.settings.fntv_db_path = tmp_root / "phase7c-source.db"
        fntv_snapshot.settings.cache_dir = tmp_root
        fntv_snapshot.settings.snapshot_enabled = False
        disabled = fntv_snapshot.resolve_active_fntv_database()
        assert disabled["active_database"] == "source"
        assert disabled["snapshot_enabled"] is False

        fntv_snapshot.settings.snapshot_enabled = True
        blocked_cache = tmp_root / "phase7c-cache-as-file"
        blocked_cache.write_text("not a directory", encoding="utf-8")
        fntv_snapshot.settings.cache_dir = blocked_cache
        failed = fntv_snapshot.resolve_active_fntv_database()
        assert failed["active_database"] == "source"
        assert failed["fallback_to_source"] is True
        assert failed["snapshot_ok"] is False
    finally:
        fntv_snapshot.settings.fntv_db_path = original_source
        fntv_snapshot.settings.cache_dir = original_cache
        fntv_snapshot.settings.snapshot_enabled = original_enabled
        fntv_snapshot.source_direct_ok = original_source_direct_ok


def test_new_routers_keep_auth_dependency() -> None:
    for router in (dashboard.router, reports.router, favorites.router, downloads.router):
        dependencies = [dependency.dependency for dependency in router.dependencies]
        assert get_current_admin in dependencies


def main() -> None:
    conn = _connect()
    try:
        _seed(conn)
        test_hourly_distribution(conn)
        test_active_watches_use_recent_update_time(conn)
        test_favorites_and_downloads_are_paged_readonly_lists(conn)
        test_history_filters_and_csv_enhanced_fields(conn)
        test_watched_diagnostics_do_not_return_rows(conn)
    finally:
        conn.close()
    test_missing_optional_tables_return_empty_capability_false()
    test_snapshot_disabled_and_failed_fallback_status()
    test_new_routers_keep_auth_dependency()
    print("phase7c smoke passed")


if __name__ == "__main__":
    main()
