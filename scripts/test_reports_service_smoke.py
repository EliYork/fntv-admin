from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import report_service  # noqa: E402


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE user (
            guid TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            passwd TEXT,
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
            visible INTEGER DEFAULT 1
        );
        CREATE TABLE item_user_play (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_guid TEXT,
            item_guid TEXT,
            update_time INTEGER,
            create_time INTEGER,
            ts INTEGER,
            watched INTEGER,
            resolution TEXT,
            visible INTEGER DEFAULT 1
        );
        """
    )
    return conn


def _seed(conn: sqlite3.Connection) -> None:
    now = int(time.time())
    yesterday = now - 86_400
    older = now - (40 * 86_400)
    conn.executemany(
        'INSERT INTO "user" (guid, username, passwd, visible) VALUES (?, ?, ?, ?)',
        [
            ("u1", "alice", "secret-a", 1),
            ("u2", "bob", "secret-b", 1),
            ("u-hidden", "hidden", "secret-c", 0),
        ],
    )
    conn.executemany(
        'INSERT INTO "item" (guid, title, original_title, filename, type, parent_guid, runtime, visible) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("series-1", "剧集 A", None, None, "Series", None, 0, 1),
            ("m1", "电影一", None, "movie-one.mkv", "Movie", None, 7_200, 1),
            ("e1", "第一集", None, "episode-one.mkv", "Episode", "series-1", 3_600, 1),
            ("m-hidden", "隐藏媒体", None, "hidden.mkv", "Movie", None, 3_600, 0),
        ],
    )
    conn.executemany(
        'INSERT INTO "item_user_play" (user_guid, item_guid, update_time, create_time, ts, watched, resolution, visible) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("u1", "m1", now * 1000, now, 3_600, 1, "1080p", 1),
            ("u1", "e1", yesterday, yesterday, 1_800, 0, "", 1),
            ("u2", "m1", older, older, 7_200, 1, "4K", 1),
            ("u-hidden", "m1", now, now, 10, 0, "720p", 1),
            ("u1", "m-hidden", now, now, 10, 0, "480p", 1),
            ("u1", "m1", now, now, 10, 0, "480p", 0),
        ],
    )


def test_overview(conn: sqlite3.Connection) -> None:
    data = report_service.overview(conn=conn)
    assert data["total_users"] == 2
    assert data["total_media"] == 3
    assert data["total_play_records"] == 3
    assert data["watched_records"] == 2
    assert data["active_users_7d"] == 1
    assert data["plays_7d"] == 2
    assert data["plays_30d"] == 2
    assert data["total_watch_seconds"] == 12_600
    assert data["avg_progress_percent"] is not None
    assert data["generated_at"]


def test_top_users(conn: sqlite3.Connection) -> None:
    rows = report_service.top_users(days="all", limit=99, conn=conn)
    assert len(rows) == 2
    assert rows[0]["username"] == "alice"
    assert rows[0]["play_count"] == 2
    assert rows[0]["watched_count"] == 1
    assert rows[0]["watch_seconds"] == 5_400
    assert "passwd" not in rows[0]


def test_top_media(conn: sqlite3.Connection) -> None:
    rows = report_service.top_media(days="all", limit=99, conn=conn)
    assert len(rows) == 2
    assert rows[0]["title"] == "电影一"
    assert rows[0]["play_count"] == 2
    episode = next(row for row in rows if row["item_guid"] == "e1")
    assert episode["title"] == "第一集"
    assert episode["parent_title"] == "剧集 A"


def test_play_trend(conn: sqlite3.Connection) -> None:
    rows = report_service.play_trend(days=7, conn=conn)
    non_zero = [row for row in rows if row["play_count"]]
    assert len(non_zero) == 2
    assert sum(row["play_count"] for row in non_zero) == 2
    assert sum(row["watched_count"] for row in non_zero) == 1


def test_distribution_and_limits(conn: sqlite3.Connection) -> None:
    assert report_service.normalize_limit(99) == 50
    assert report_service.normalize_days(999) == 180
    media_types = {row["type"]: row["count"] for row in report_service.media_type_distribution(conn=conn)}
    assert media_types["Movie"] == 1
    resolutions = report_service.resolution_distribution(days="all", conn=conn)
    assert {row["resolution"] for row in resolutions} == {"1080p", "4K", "未知"}


def main() -> None:
    conn = _connect()
    try:
        _seed(conn)
        test_overview(conn)
        test_top_users(conn)
        test_top_media(conn)
        test_play_trend(conn)
        test_distribution_and_limits(conn)
    finally:
        conn.close()
    print("reports service smoke passed")


if __name__ == "__main__":
    main()
