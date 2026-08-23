import sqlite3
import unittest

from app.services.report_service import MAX_DAYS, MAX_TREND_DAYS, normalize_days, play_trend


class NormalizeReportDaysTests(unittest.TestCase):
    def test_default_report_range_remains_capped_at_180_days(self) -> None:
        self.assertEqual(normalize_days(365), MAX_DAYS)

    def test_play_trend_range_can_use_365_day_cap(self) -> None:
        self.assertEqual(normalize_days(365, max_days=MAX_TREND_DAYS), MAX_TREND_DAYS)
        self.assertEqual(normalize_days(999, max_days=MAX_TREND_DAYS), MAX_TREND_DAYS)

    def test_play_trend_returns_full_year_for_365_request(self) -> None:
        with sqlite3.connect(":memory:") as connection:
            connection.row_factory = sqlite3.Row
            items = play_trend("365", conn=connection)
        self.assertEqual(len(items), MAX_TREND_DAYS)


if __name__ == "__main__":
    unittest.main()
