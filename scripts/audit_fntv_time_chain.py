#!/usr/bin/env python3
"""Read-only audit of recent FNOS playback timestamps and API normalization."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import fntv_schema_adapter as adapter  # noqa: E402
from app.utils.time import application_timezone_name, timestamp_as_application_datetime, unix_timestamp_seconds  # noqa: E402


def readonly_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def audit(path: Path, limit: int) -> dict[str, Any]:
    with closing(readonly_connection(path)) as connection:
        schema = adapter.detect_schema(conn=connection)
        play_table = schema.plays.table
        time_columns = adapter._play_time_columns(schema)
        time_expr = adapter._play_time_expr(schema, "p")
        if not play_table or not time_columns or not time_expr:
            return {"database": str(path), "error": "未识别播放记录表或时间字段", "records": []}

        clean_limit = max(3, min(20, limit))
        raw_rows, _ = adapter._play_rows(connection, schema, 1, clean_limit, {})
        api_items = adapter.history_page(1, clean_limit, {"range": "all"}, conn=connection)["items"]

        records: list[dict[str, Any]] = []
        for index, raw_row in enumerate(raw_rows):
            row = dict(raw_row)
            field = next((column for column in time_columns if row.get(column) not in (None, "", 0, "0")), time_columns[0])
            raw_value = row.get(field)
            seconds = unix_timestamp_seconds(raw_value)
            utc_time = datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec="seconds") if seconds is not None else None
            local_time = timestamp_as_application_datetime(raw_value)
            api_item = api_items[index] if index < len(api_items) else {}
            records.append(
                {
                    "record_id": str(api_item.get("id") or row.get("__rowid") or ""),
                    "raw_field": field,
                    "raw_value": raw_value,
                    "unit": "milliseconds" if seconds is not None and float(raw_value) >= 100_000_000_000 else "seconds",
                    "utc": utc_time,
                    "application_timezone": application_timezone_name(),
                    "application_time": local_time.isoformat(timespec="seconds") if local_time else None,
                    "history_api_played_at": api_item.get("played_at"),
                    "frontend_wall_clock": str(api_item.get("played_at") or "").replace("T", " ")[:19] or None,
                }
            )
        return {"database": str(path), "play_table": play_table, "time_columns": time_columns, "records": records}


def main() -> int:
    parser = argparse.ArgumentParser(description="只读审计最近飞牛播放记录的 UTC / 应用时区 / API 时间链路")
    parser.add_argument("database", type=Path, help="trimmedia.db 路径")
    parser.add_argument("--limit", type=int, default=5, help="审计记录数，范围 3-20，默认 5")
    args = parser.parse_args()
    if not args.database.is_file():
        print(f"database does not exist: {args.database}", file=sys.stderr)
        return 2
    print(json.dumps(audit(args.database, args.limit), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
