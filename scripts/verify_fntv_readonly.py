#!/usr/bin/env python3
"""Verify Feiniu database read-only guardrails."""

from __future__ import annotations

import argparse
import ast
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITE_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "VACUUM", "REINDEX", "CREATE")
ALLOWED_FILES = {
    ROOT / "backend/app/db/fntv_readonly.py",
    ROOT / "backend/app/models/admin.py",
    ROOT / "backend/app/db/admin_db.py",
    ROOT / "scripts/verify_fntv_readonly.py",
}


def check_compose_ro() -> list[str]:
    compose = ROOT / "docker-compose.yml"
    text = compose.read_text(encoding="utf-8")
    return [] if ":/fntv/trimmedia.db:ro" in text else ["docker-compose.yml is missing :ro for /fntv/trimmedia.db"]


def scan_backend_sql() -> list[str]:
    errors: list[str] = []
    for path in (ROOT / "backend/app").rglob("*.py"):
        if path in ALLOWED_FILES:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(ROOT)} cannot be parsed: {exc}")
            continue
        strings = [node.value.upper() for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
        candidates = [value.strip() for value in strings]
        for keyword in WRITE_KEYWORDS:
            if any(re.match(rf"^{keyword}(\s|$)", value) for value in candidates):
                errors.append(f"{path.relative_to(ROOT)} contains write keyword {keyword}")
    return errors


def probe_readonly_database(path: Path) -> list[str]:
    if not path:
        return []
    if not path.exists():
        return [f"database does not exist: {path}"]
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON")
        conn.execute("CREATE TABLE __fntv_admin_write_probe(id INTEGER)")
    except sqlite3.Error:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return ["read-only write probe unexpectedly succeeded"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify fntv-admin read-only constraints.")
    parser.add_argument("--database", type=Path, help="Optional trimmedia.db path for a real read-only write probe")
    args = parser.parse_args()

    errors = [*check_compose_ro(), *scan_backend_sql()]
    if args.database:
        errors.extend(probe_readonly_database(args.database))

    if errors:
        print("read-only verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("read-only verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
