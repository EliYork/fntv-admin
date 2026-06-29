from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import fntv_schema_adapter as adapter  # noqa: E402


def _connect() -> sqlite3.Connection:
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
            original_title TEXT,
            filename TEXT,
            type TEXT,
            parent_guid TEXT,
            season_number INTEGER,
            episode_number INTEGER
        );
        CREATE TABLE item_user_play (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_guid TEXT,
            item_guid TEXT,
            update_time INTEGER,
            create_time INTEGER,
            visible INTEGER DEFAULT 1
        );
        """
    )
    return conn


def test_today_plays_normalizes_millisecond_timestamps(conn: sqlite3.Connection) -> None:
    schema = adapter.detect_schema(conn=conn)
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    yesterday_ms = (today_start - 60) * 1000
    today_ms = (today_start + 60) * 1000
    conn.executemany(
        'INSERT INTO item_user_play (user_guid, item_guid, update_time, create_time, visible) VALUES (?, ?, ?, ?, ?)',
        [
            ("u1", "m1", yesterday_ms, today_start - 60, 1),
            ("u1", "m1", today_ms, today_start + 60, 1),
        ],
    )
    assert adapter._count_play_records(conn, schema) == 2
    assert adapter._count_today_plays(conn, schema) == 1


def test_media_title_fallback_skips_hash_title(conn: sqlite3.Connection) -> None:
    conn.executemany(
        'INSERT INTO item (guid, title, original_title, filename, type, parent_guid, season_number, episode_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("series-1", "剧集甲", None, None, "Series", None, None, None),
            ("season-1", "1", None, None, "Season", "series-1", 1, None),
            ("episode-1", "0123456789abcdef0123456789abcdef", None, "第一集.mkv", "Episode", "season-1", 1, 1),
        ],
    )
    schema = adapter.detect_schema(conn=conn)
    row = conn.execute('SELECT * FROM item WHERE guid = "episode-1"').fetchone()
    assert row is not None
    title = adapter._hierarchy_title(conn, schema, dict(row), max_depth=4)
    assert title == "剧集甲 - S01E01 - 第一集.mkv"
    item = adapter._media_row(dict(row), schema, {}, {}, {"season-1": "剧集甲 - S01"}, {})
    assert item["title"] == "剧集甲 - S01E01 - 第一集.mkv"


def main() -> None:
    conn = _connect()
    try:
        test_today_plays_normalizes_millisecond_timestamps(conn)
        test_media_title_fallback_skips_hash_title(conn)
    finally:
        conn.close()
    print("dashboard media smoke passed")


if __name__ == "__main__":
    main()
