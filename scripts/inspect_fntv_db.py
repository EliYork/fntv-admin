#!/usr/bin/env python3
"""Inspect a Feiniu TV SQLite database using a read-only connection."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


CORE_HINTS = {
    "user": ("user", "account", "member"),
    "item": ("item", "media", "video", "movie", "episode"),
    "item_user_play": ("play", "history", "watch", "progress"),
}


def open_readonly(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"database does not exist: {path}")
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(row["name"]) for row in rows]


def table_columns(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    escaped = table.replace('"', '""')
    rows = conn.execute(f'PRAGMA table_info("{escaped}")').fetchall()
    return [
        {
            "cid": row["cid"],
            "name": row["name"],
            "type": row["type"],
            "notnull": bool(row["notnull"]),
            "default": row["dflt_value"],
            "primary_key": bool(row["pk"]),
        }
        for row in rows
    ]


def identify_core_tables(tables: list[str]) -> dict[str, list[str]]:
    lower_pairs = [(name, name.lower()) for name in tables]
    result: dict[str, list[str]] = {}
    for key, hints in CORE_HINTS.items():
        result[key] = [name for name, lower in lower_pairs if any(hint in lower for hint in hints)]
    return result


def inspect(path: Path) -> dict[str, Any]:
    with open_readonly(path) as conn:
        tables = list_tables(conn)
        return {
            "database": str(path),
            "table_count": len(tables),
            "tables": [{"name": table, "columns": table_columns(conn, table)} for table in tables],
            "core_candidates": identify_core_tables(tables),
            "readonly": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Feiniu TV SQLite schema without writing.")
    parser.add_argument("database", help="Path to trimmedia.db")
    parser.add_argument("--json", action="store_true", help="Print full JSON output")
    args = parser.parse_args()

    try:
        report = inspect(Path(args.database))
    except Exception as exc:  # noqa: BLE001
        print(f"failed to inspect database in read-only mode: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"database: {report['database']}")
    print(f"readonly: {report['readonly']}")
    print(f"tables: {report['table_count']}")
    print()
    for table in report["tables"]:
        print(f"[{table['name']}]")
        for column in table["columns"]:
            pk = " pk" if column["primary_key"] else ""
            required = " notnull" if column["notnull"] else ""
            print(f"  - {column['name']} {column['type']}{required}{pk}")
        print()
    print("core candidates:")
    for key, matches in report["core_candidates"].items():
        print(f"  {key}: {', '.join(matches) if matches else '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

