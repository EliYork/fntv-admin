#!/usr/bin/env python3
"""Smoke tests for snapshot TTL lazy refresh (打开页面才刷新，超过间隔才刷新)."""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.db import fntv_snapshot  # noqa: E402


def _make_admin_db(path: Path, interval: str | None) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT, value_type TEXT, updated_at INTEGER)")
    if interval is not None:
        conn.execute(
            "INSERT INTO settings (key, value, value_type, updated_at) VALUES (?, ?, ?, ?)",
            ("snapshot_refresh_interval_seconds", interval, "string", 0),
        )
    conn.commit()
    conn.close()


def test_interval_falls_back_to_settings_default(tmp_root: Path) -> None:
    original_path = settings.admin_db_path
    original_default = settings.snapshot_refresh_interval_seconds
    try:
        settings.admin_db_path = tmp_root / "no-admin.db"
        settings.snapshot_refresh_interval_seconds = 3600
        assert fntv_snapshot.snapshot_refresh_interval_seconds() == 3600
    finally:
        settings.admin_db_path = original_path
        settings.snapshot_refresh_interval_seconds = original_default


def test_interval_reads_admin_db(tmp_root: Path) -> None:
    db = tmp_root / "admin-read.db"
    _make_admin_db(db, "1800")
    original_path = settings.admin_db_path
    try:
        settings.admin_db_path = db
        assert fntv_snapshot.snapshot_refresh_interval_seconds() == 1800
    finally:
        settings.admin_db_path = original_path


def test_interval_ignores_invalid_value(tmp_root: Path) -> None:
    db = tmp_root / "admin-invalid.db"
    _make_admin_db(db, "not-a-number")
    original_path = settings.admin_db_path
    try:
        settings.admin_db_path = db
        assert fntv_snapshot.snapshot_refresh_interval_seconds() == settings.snapshot_refresh_interval_seconds
    finally:
        settings.admin_db_path = original_path


def test_stale_logic(tmp_root: Path) -> None:
    now = int(time.time())
    original_read_meta = fntv_snapshot._read_meta
    original_interval = fntv_snapshot.snapshot_refresh_interval_seconds
    try:
        fntv_snapshot.snapshot_refresh_interval_seconds = lambda: 3600
        # meta 缺失 → 过期
        fntv_snapshot._read_meta = lambda: {}
        assert fntv_snapshot._snapshot_stale() is True
        # 刚刷新过 → 未过期
        fntv_snapshot._read_meta = lambda: {"snapshot_last_refresh_at": now - 60}
        assert fntv_snapshot._snapshot_stale() is False
        # 超过间隔 → 过期
        fntv_snapshot._read_meta = lambda: {"snapshot_last_refresh_at": now - 7200}
        assert fntv_snapshot._snapshot_stale() is True
        # 刷新失败后，间隔内抑制重试
        fntv_snapshot._read_meta = lambda: {
            "snapshot_last_refresh_at": now - 7200,
            "snapshot_last_attempt_at": now - 60,
        }
        assert fntv_snapshot._snapshot_stale() is False
        # interval=0 → 永不自动刷新
        fntv_snapshot.snapshot_refresh_interval_seconds = lambda: 0
        fntv_snapshot._read_meta = lambda: {}
        assert fntv_snapshot._snapshot_stale() is False
    finally:
        fntv_snapshot._read_meta = original_read_meta
        fntv_snapshot.snapshot_refresh_interval_seconds = original_interval


def test_failed_refresh_falls_back_to_source(tmp_root: Path) -> None:
    blocked_cache = tmp_root / "cache-as-file"
    blocked_cache.write_text("not a directory", encoding="utf-8")
    original_source = fntv_snapshot.settings.fntv_db_path
    original_cache = fntv_snapshot.settings.cache_dir
    original_enabled = fntv_snapshot.settings.snapshot_enabled
    original_sdo = fntv_snapshot.source_direct_ok
    original_status = dict(fntv_snapshot._last_status)
    try:
        fntv_snapshot.source_direct_ok = lambda: True
        fntv_snapshot.settings.fntv_db_path = tmp_root / "source.db"
        fntv_snapshot.settings.cache_dir = blocked_cache
        fntv_snapshot.settings.snapshot_enabled = True
        fntv_snapshot._last_status = {}
        result = fntv_snapshot.resolve_active_fntv_database()
        assert result["active_database"] == "source"
        assert result["fallback_to_source"] is True
        assert result["degraded"] is True
        assert result["snapshot_ok"] is False
        assert result["snapshot_error"] == "SNAPSHOT_REFRESH_FAILED"
    finally:
        fntv_snapshot.settings.fntv_db_path = original_source
        fntv_snapshot.settings.cache_dir = original_cache
        fntv_snapshot.settings.snapshot_enabled = original_enabled
        fntv_snapshot.source_direct_ok = original_sdo
        fntv_snapshot._last_status = original_status


def test_fresh_snapshot_is_used_without_refresh(tmp_root: Path) -> None:
    cache_dir = tmp_root / "cache"
    cache_dir.mkdir(exist_ok=True)
    snap = cache_dir / "trimmedia.snapshot.db"
    conn = sqlite3.connect(snap)
    conn.execute("CREATE TABLE probe (id INTEGER)")
    conn.commit()
    conn.close()
    (cache_dir / "trimmedia.snapshot.json").write_text(
        json.dumps({"snapshot_last_refresh_at": int(time.time()) - 60}),
        encoding="utf-8",
    )
    original_source = fntv_snapshot.settings.fntv_db_path
    original_cache = fntv_snapshot.settings.cache_dir
    original_enabled = fntv_snapshot.settings.snapshot_enabled
    original_sdo = fntv_snapshot.source_direct_ok
    original_status = dict(fntv_snapshot._last_status)
    try:
        fntv_snapshot.source_direct_ok = lambda: True
        fntv_snapshot.settings.fntv_db_path = tmp_root / "source.db"
        fntv_snapshot.settings.cache_dir = cache_dir
        fntv_snapshot.settings.snapshot_enabled = True
        fntv_snapshot._last_status = {
            "snapshot_ok": True,
            "snapshot_error": None,
            "snapshot_error_type": None,
            "snapshot_error_message": None,
        }
        result = fntv_snapshot.resolve_active_fntv_database()
        assert result["active_database"] == "snapshot"
        assert result["degraded"] is False
        assert result["fallback_to_source"] is False
    finally:
        fntv_snapshot.settings.fntv_db_path = original_source
        fntv_snapshot.settings.cache_dir = original_cache
        fntv_snapshot.settings.snapshot_enabled = original_enabled
        fntv_snapshot.source_direct_ok = original_sdo
        fntv_snapshot._last_status = original_status


def test_record_refresh_failure_writes_attempt(tmp_root: Path) -> None:
    cache_dir = tmp_root / "cache"
    cache_dir.mkdir(exist_ok=True)
    original_cache = fntv_snapshot.settings.cache_dir
    try:
        fntv_snapshot.settings.cache_dir = cache_dir
        fntv_snapshot._record_refresh_failure()
        data = json.loads(fntv_snapshot.snapshot_meta_path().read_text(encoding="utf-8"))
        assert "snapshot_last_attempt_at" in data
        assert abs(int(data["snapshot_last_attempt_at"]) - int(time.time())) < 5
    finally:
        fntv_snapshot.settings.cache_dir = original_cache


def main() -> None:
    tmp_root = ROOT / ".tmp_smoke"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(exist_ok=True)
    test_interval_falls_back_to_settings_default(tmp_root)
    test_interval_reads_admin_db(tmp_root)
    test_interval_ignores_invalid_value(tmp_root)
    test_stale_logic(tmp_root)
    test_failed_refresh_falls_back_to_source(tmp_root)
    test_fresh_snapshot_is_used_without_refresh(tmp_root)
    test_record_refresh_failure_writes_attempt(tmp_root)
    print("snapshot refresh smoke passed")


if __name__ == "__main__":
    main()
