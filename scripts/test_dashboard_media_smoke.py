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
            runtime INTEGER,
            season_number INTEGER,
            episode_number INTEGER
        );
        CREATE TABLE item_user_play (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_guid TEXT,
            item_guid TEXT,
            update_time INTEGER,
            create_time INTEGER,
            ts INTEGER,
            visible INTEGER DEFAULT 1
        );
        """
    )
    return conn


def test_today_plays_normalizes_millisecond_timestamps(conn: sqlite3.Connection) -> None:
    schema = adapter.detect_schema(conn=conn)
    today_start, _ = adapter._local_day_bounds()
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


def test_recent_activities_supports_twenty_items(conn: sqlite3.Connection) -> None:
    now = int(datetime.now().timestamp())
    conn.execute('INSERT INTO user (guid, username) VALUES (?, ?)', ("u1", "alice"))
    conn.execute('INSERT INTO item (guid, title, type) VALUES (?, ?, ?)', ("m1", "电影一", "Movie"))
    conn.executemany(
        'INSERT INTO item_user_play (user_guid, item_guid, update_time, create_time, visible) VALUES (?, ?, ?, ?, ?)',
        [("u1", "m1", now - index, now - index, 1) for index in range(25)],
    )
    schema = adapter.detect_schema(conn=conn)
    rows, _ = adapter._play_rows(conn, schema, 1, 20, {})
    assert len(rows) == 20


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


def test_media_title_deduplicates_repeated_parent_and_marker(conn: sqlite3.Connection) -> None:
    conn.executemany(
        'INSERT INTO item (guid, title, original_title, filename, type, parent_guid, season_number, episode_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("series-2", "低智商犯罪", None, None, "Series", None, None, None),
            ("season-2", "低智商犯罪 - S01", None, None, "Season", "series-2", 1, None),
            ("episode-2", "低智商犯罪 - S01E01 - S01E01", None, "第一集.mkv", "Episode", "season-2", 1, 1),
        ],
    )
    schema = adapter.detect_schema(conn=conn)
    row = conn.execute('SELECT * FROM item WHERE guid = "episode-2"').fetchone()
    assert row is not None
    title = adapter._hierarchy_title(conn, schema, dict(row), max_depth=4)
    assert title == "低智商犯罪 - S01E01 - 第一集.mkv"


def test_users_can_sort_by_play_count_desc(conn: sqlite3.Connection) -> None:
    now = int(datetime.now().timestamp())
    conn.executemany(
        'INSERT INTO user (guid, username) VALUES (?, ?)',
        [("u1", "alice"), ("u2", "bob")],
    )
    conn.executemany(
        'INSERT INTO item (guid, title, type) VALUES (?, ?, ?)',
        [("m1", "电影一", "Movie")],
    )
    conn.executemany(
        'INSERT INTO item_user_play (user_guid, item_guid, update_time, create_time, visible) VALUES (?, ?, ?, ?, ?)',
        [
            ("u1", "m1", now, now, 1),
            ("u2", "m1", now, now, 1),
            ("u2", "m1", now - 1, now - 1, 1),
        ],
    )
    page = adapter.users_page(1, 20, keyword=None, show_hidden=False, sort_by="play_count", sort_order="desc", conn=conn)
    assert [row["guid"] for row in page["items"]] == ["u2", "u1"]


def test_users_sort_rejects_unlisted_field(conn: sqlite3.Connection) -> None:
    conn.executemany(
        'INSERT INTO user (guid, username) VALUES (?, ?)',
        [("u1", "alice"), ("u2", "bob")],
    )
    page = adapter.users_page(1, 20, keyword=None, show_hidden=False, sort_by="username; DROP TABLE user", sort_order="desc", conn=conn)
    assert [row["guid"] for row in page["items"]] == ["u1", "u2"]


def test_runtime_normalization_treats_small_item_runtime_as_minutes(conn: sqlite3.Connection) -> None:
    assert adapter.normalize_runtime_seconds(44) == 2_640
    assert adapter.normalize_runtime_seconds(3_600) == 3_600
    assert adapter.normalize_runtime_seconds(3_600_000) == 3_600
    progress = adapter.format_play_progress(1_261, 44, watched=False)
    assert progress["runtime_seconds"] == 2_640
    assert progress["progress"] == "00:21:01 / 00:44:00"
    assert progress["progress_percent"] == 47.8


def test_play_rows_prefer_batched_media_stream_duration(conn: sqlite3.Connection) -> None:
    now = int(datetime.now().timestamp())
    conn.execute('CREATE TABLE media_stream (item_guid TEXT, duration INTEGER)')
    conn.execute('INSERT INTO user (guid, username) VALUES (?, ?)', ("u1", "alice"))
    conn.execute('INSERT INTO item (guid, title, type, runtime) VALUES (?, ?, ?, ?)', ("m1", "电影一", "Movie", 44))
    conn.execute('INSERT INTO media_stream (item_guid, duration) VALUES (?, ?)', ("m1", 3_600))
    conn.execute(
        'INSERT INTO item_user_play (user_guid, item_guid, update_time, create_time, ts, visible) VALUES (?, ?, ?, ?, ?, ?)',
        ("u1", "m1", now, now, 1_261, 1),
    )
    schema = adapter.detect_schema(conn=conn)
    raw_rows, _ = adapter._play_rows(conn, schema, 1, 20, {})
    rows = adapter._hydrate_play_rows(conn, schema, raw_rows)
    assert rows[0]["runtime_seconds"] == 3_600
    assert rows[0]["progress"] == "00:21:01 / 01:00:00"


def test_media_stream_duration_does_not_use_item_runtime_minutes_heuristic(conn: sqlite3.Connection) -> None:
    now = int(datetime.now().timestamp())
    conn.execute('CREATE TABLE media_stream (item_guid TEXT, duration INTEGER)')
    conn.execute('INSERT INTO user (guid, username) VALUES (?, ?)', ("u1", "alice"))
    conn.execute('INSERT INTO item (guid, title, type, runtime) VALUES (?, ?, ?, ?)', ("m1", "电影一", "Movie", 44))
    conn.execute('INSERT INTO media_stream (item_guid, duration) VALUES (?, ?)', ("m1", 44))
    conn.execute(
        'INSERT INTO item_user_play (user_guid, item_guid, update_time, create_time, ts, visible) VALUES (?, ?, ?, ?, ?, ?)',
        ("u1", "m1", now, now, 10, 1),
    )
    schema = adapter.detect_schema(conn=conn)
    raw_rows, _ = adapter._play_rows(conn, schema, 1, 20, {})
    rows = adapter._hydrate_play_rows(conn, schema, raw_rows)
    assert rows[0]["runtime_seconds"] == 44
    assert rows[0]["progress"] == "00:00:10 / 00:00:44"


def test_history_keyword_search_matches_parent_series_title(conn: sqlite3.Connection) -> None:
    now = int(datetime.now().timestamp())
    conn.executemany(
        'INSERT INTO item (guid, title, type, parent_guid, season_number, episode_number) VALUES (?, ?, ?, ?, ?, ?)',
        [
            ("series-3", "漫长的季节", "Series", None, None, None),
            ("season-3", "第一季", "Season", "series-3", 1, None),
            ("episode-3", "第 01 集", "Episode", "season-3", 1, 1),
        ],
    )
    conn.execute('INSERT INTO user (guid, username) VALUES (?, ?)', ("u1", "alice"))
    conn.execute(
        'INSERT INTO item_user_play (user_guid, item_guid, update_time, create_time, ts, visible) VALUES (?, ?, ?, ?, ?, ?)',
        ("u1", "episode-3", now, now, 30, 1),
    )
    schema = adapter.detect_schema(conn=conn)
    raw_rows, total = adapter._play_rows(conn, schema, 1, 20, {"keyword": "漫长的季节"})
    assert total == 1
    rows = adapter._hydrate_play_rows(conn, schema, raw_rows)
    assert rows[0]["display_title"].startswith("漫长的季节")


def main() -> None:
    for test in (
        test_today_plays_normalizes_millisecond_timestamps,
        test_recent_activities_supports_twenty_items,
        test_media_title_fallback_skips_hash_title,
        test_media_title_deduplicates_repeated_parent_and_marker,
        test_users_can_sort_by_play_count_desc,
        test_users_sort_rejects_unlisted_field,
        test_runtime_normalization_treats_small_item_runtime_as_minutes,
        test_play_rows_prefer_batched_media_stream_duration,
        test_media_stream_duration_does_not_use_item_runtime_minutes_heuristic,
        test_history_keyword_search_matches_parent_series_title,
    ):
        conn = _connect()
        try:
            test(conn)
        finally:
            conn.close()
    print("dashboard media smoke passed")


if __name__ == "__main__":
    main()
