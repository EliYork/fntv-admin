from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.services import fntv_schema_adapter as adapter
from app.services import report_service
from app.utils.time import (
    application_timezone_name,
    format_timestamp,
    local_day_bounds,
    timestamp_as_application_datetime,
)
from scripts.audit_fntv_time_chain import audit


KNOWN_UTC = datetime(2026, 8, 26, 5, 49, 32, tzinfo=timezone.utc)
KNOWN_SECONDS = int(KNOWN_UTC.timestamp())


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE user (guid TEXT PRIMARY KEY, username TEXT, visible INTEGER DEFAULT 1);
        CREATE TABLE item (guid TEXT PRIMARY KEY, title TEXT, visible INTEGER DEFAULT 1);
        CREATE TABLE item_user_play (
            id INTEGER PRIMARY KEY,
            user_guid TEXT,
            item_guid TEXT,
            update_time INTEGER,
            create_time INTEGER,
            watched INTEGER,
            ts INTEGER,
            visible INTEGER DEFAULT 1
        );
        INSERT INTO user (guid, username, visible) VALUES ('u1', 'alice', 1);
        INSERT INTO item (guid, title, visible) VALUES ('i1', 'sample', 1);
        """
    )
    return connection


class TimestampNormalizationTests(unittest.TestCase):
    def test_unix_seconds_and_milliseconds_have_the_same_rfc3339_result(self) -> None:
        with patch.dict(os.environ, {"TZ": "Asia/Shanghai"}):
            expected = "2026-08-26T13:49:32+08:00"
            self.assertEqual(format_timestamp(KNOWN_SECONDS), expected)
            self.assertEqual(format_timestamp(KNOWN_SECONDS * 1000), expected)
            self.assertEqual(adapter.normalize_timestamp(KNOWN_SECONDS), expected)

    def test_application_timezone_does_not_depend_on_process_local_timezone(self) -> None:
        with patch.dict(os.environ, {"TZ": "Asia/Shanghai"}):
            converted = timestamp_as_application_datetime(KNOWN_SECONDS)
            self.assertIsNotNone(converted)
            assert converted is not None
            self.assertEqual(converted.utcoffset().total_seconds(), 8 * 3600)
            self.assertEqual((converted.hour, converted.minute, converted.second), (13, 49, 32))

    def test_invalid_timezone_falls_back_to_documented_default(self) -> None:
        with patch.dict(os.environ, {"TZ": "Invalid/Timezone"}):
            self.assertEqual(application_timezone_name(), "Asia/Shanghai")
            self.assertEqual(format_timestamp(KNOWN_SECONDS), "2026-08-26T13:49:32+08:00")

    def test_dst_zone_uses_natural_local_day_instead_of_fixed_offset(self) -> None:
        with patch.dict(os.environ, {"TZ": "America/New_York"}):
            current = datetime(2026, 3, 8, 12, 0, tzinfo=ZoneInfo("America/New_York"))
            start, end = local_day_bounds(current)
            self.assertEqual(end - start, 23 * 3600)


class CrossMidnightReportTests(unittest.TestCase):
    def test_history_today_trend_hourly_and_csv_share_application_day(self) -> None:
        with patch.dict(os.environ, {"TZ": "Asia/Shanghai"}):
            today_start, _ = local_day_bounds()
            connection = make_connection()
            try:
                connection.executemany(
                    "INSERT INTO item_user_play (id, user_guid, item_guid, update_time, create_time, watched, ts, visible) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                    [
                        (1, "u1", "i1", (today_start - 1) * 1000, (today_start - 1) * 1000, 0, 10),
                        (2, "u1", "i1", (today_start + 1) * 1000, (today_start + 1) * 1000, 1, 20),
                    ],
                )
                schema = adapter.detect_schema(conn=connection)
                self.assertEqual(adapter._count_today_plays(connection, schema), 1)

                history = adapter.history_page(1, 20, {"range": "all"}, conn=connection)
                self.assertTrue(history["items"][0]["played_at"].endswith("+08:00"))
                self.assertIn("T00:00:01", history["items"][0]["played_at"])
                self.assertIn("T23:59:59", history["items"][1]["played_at"])

                trend = report_service.play_trend(2, conn=connection)
                non_zero = [item for item in trend if item["play_count"]]
                self.assertEqual([item["play_count"] for item in non_zero], [1, 1])
                self.assertEqual([item["watched_count"] for item in non_zero], [0, 1])

                hourly = report_service.hourly_distribution("all", conn=connection)
                self.assertEqual(hourly[23]["play_count"], 1)
                self.assertEqual(hourly[0]["play_count"], 1)

                csv_text = adapter.history_csv({"range": "all"}, conn=connection)
                self.assertIn("T00:00:01+08:00", csv_text)
                self.assertIn("T23:59:59+08:00", csv_text)
            finally:
                connection.close()

    def test_top_users_does_not_require_matching_media_rows(self) -> None:
        with patch.dict(os.environ, {"TZ": "Asia/Shanghai"}):
            connection = make_connection()
            try:
                connection.execute(
                    "INSERT INTO item_user_play (id, user_guid, item_guid, update_time, create_time, watched, ts, visible) VALUES (1, 'u1', 'missing-media', ?, ?, 0, 10, 1)",
                    (KNOWN_SECONDS * 1000, KNOWN_SECONDS * 1000),
                )
                rows = report_service.top_users("all", 10, conn=connection)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["username"], "alice")
                self.assertEqual(rows[0]["play_count"], 1)
            finally:
                connection.close()


class ReadonlyAuditScriptTests(unittest.TestCase):
    def test_audit_reports_raw_utc_application_api_and_frontend_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(os.environ, {"TZ": "Asia/Shanghai"}):
            path = Path(temp_dir) / "trimmedia.db"
            connection = sqlite3.connect(path)
            try:
                connection.executescript(
                    """
                    CREATE TABLE user (guid TEXT PRIMARY KEY, username TEXT, visible INTEGER);
                    CREATE TABLE item (guid TEXT PRIMARY KEY, title TEXT, visible INTEGER);
                    CREATE TABLE item_user_play (
                        id INTEGER PRIMARY KEY, user_guid TEXT, item_guid TEXT,
                        update_time INTEGER, create_time INTEGER, ts INTEGER,
                        watched INTEGER, visible INTEGER
                    );
                    INSERT INTO user VALUES ('u1', 'alice', 1);
                    INSERT INTO item VALUES ('i1', 'sample', 1);
                    """
                )
                connection.execute(
                    "INSERT INTO item_user_play VALUES (1, 'u1', 'i1', ?, ?, 30, 0, 1)",
                    (KNOWN_SECONDS * 1000, KNOWN_SECONDS * 1000),
                )
                connection.commit()
            finally:
                connection.close()

            result = audit(path, 5)
            record = result["records"][0]
            self.assertEqual(record["raw_field"], "update_time")
            self.assertEqual(record["unit"], "milliseconds")
            self.assertEqual(record["utc"], "2026-08-26T05:49:32+00:00")
            self.assertEqual(record["application_time"], "2026-08-26T13:49:32+08:00")
            self.assertEqual(record["history_api_played_at"], "2026-08-26T13:49:32+08:00")
            self.assertEqual(record["frontend_wall_clock"], "2026-08-26 13:49:32")

if __name__ == "__main__":
    unittest.main()
