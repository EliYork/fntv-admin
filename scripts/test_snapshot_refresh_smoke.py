#!/usr/bin/env python3
"""Smoke tests for snapshot TTL lazy refresh (打开页面才刷新，超过间隔才刷新)."""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import threading
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


def test_overdue_schedule_never_returns_a_past_next_refresh(tmp_root: Path) -> None:
    now = int(time.time())
    original_interval = fntv_snapshot.snapshot_refresh_interval_seconds
    try:
        fntv_snapshot.snapshot_refresh_interval_seconds = lambda: 900
        schedule = fntv_snapshot._snapshot_schedule({"snapshot_last_refresh_at": now - 3600}, now=now)
        assert schedule == {"state": "due", "due": True, "next_refresh_at": now}
        retry = fntv_snapshot._snapshot_schedule(
            {"snapshot_last_refresh_at": now - 3600, "snapshot_last_attempt_at": now - 60},
            now=now,
        )
        assert retry["state"] == "retry_wait"
        assert retry["next_refresh_at"] == now + 840
    finally:
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
        refresh = fntv_snapshot.refresh_fntv_snapshot()
        assert refresh["ok"] is False
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


def test_concurrent_manual_refresh_runs_only_once(tmp_root: Path) -> None:
    original_copy = fntv_snapshot._copy_fntv_snapshot_locked
    original_enabled = fntv_snapshot.snapshot_enabled
    entered = threading.Event()
    release = threading.Event()
    calls = 0

    def fake_copy() -> dict[str, object]:
        nonlocal calls
        calls += 1
        entered.set()
        assert release.wait(2)
        return {"ok": True}

    first_result: dict[str, object] = {}
    try:
        fntv_snapshot.snapshot_enabled = lambda: True
        fntv_snapshot._copy_fntv_snapshot_locked = fake_copy
        worker = threading.Thread(target=lambda: first_result.update(fntv_snapshot.refresh_fntv_snapshot()))
        worker.start()
        assert entered.wait(2)
        second = fntv_snapshot.refresh_fntv_snapshot()
        assert second["refresh_in_progress"] is True
        assert second["skipped"] is True
        release.set()
        worker.join(2)
        assert not worker.is_alive()
        assert first_result["ok"] is True
        assert calls == 1
    finally:
        release.set()
        fntv_snapshot._copy_fntv_snapshot_locked = original_copy
        fntv_snapshot.snapshot_enabled = original_enabled


def test_manual_and_automatic_refresh_share_the_same_gate(tmp_root: Path) -> None:
    original_copy = fntv_snapshot._copy_fntv_snapshot_locked
    original_enabled = fntv_snapshot.snapshot_enabled
    entered = threading.Event()
    release = threading.Event()
    calls = 0

    def fake_copy() -> dict[str, object]:
        nonlocal calls
        calls += 1
        entered.set()
        assert release.wait(2)
        return {"ok": True}

    try:
        fntv_snapshot.snapshot_enabled = lambda: True
        fntv_snapshot._copy_fntv_snapshot_locked = fake_copy
        automatic = fntv_snapshot.trigger_fntv_snapshot_refresh()
        assert automatic["started"] is True
        assert entered.wait(2)
        manual = fntv_snapshot.refresh_fntv_snapshot()
        assert manual["refresh_in_progress"] is True
        release.set()
        deadline = time.time() + 2
        while fntv_snapshot._refresh_lock.locked() and time.time() < deadline:
            threading.Event().wait(0.01)
        assert not fntv_snapshot._refresh_lock.locked()
        assert calls == 1
    finally:
        release.set()
        fntv_snapshot._copy_fntv_snapshot_locked = original_copy
        fntv_snapshot.snapshot_enabled = original_enabled


def test_process_refresh_lock_is_non_blocking(tmp_root: Path) -> None:
    cache_dir = tmp_root / "process-lock"
    original_cache = fntv_snapshot.settings.cache_dir
    first = None
    third = None
    try:
        fntv_snapshot.settings.cache_dir = cache_dir
        first = fntv_snapshot._try_acquire_process_refresh_lock()
        assert first is not None
        assert fntv_snapshot._try_acquire_process_refresh_lock() is None
        fntv_snapshot._release_process_refresh_lock(first)
        first = None
        third = fntv_snapshot._try_acquire_process_refresh_lock()
        assert third is not None
    finally:
        fntv_snapshot._release_process_refresh_lock(first)
        fntv_snapshot._release_process_refresh_lock(third)
        fntv_snapshot.settings.cache_dir = original_cache


def test_failed_refresh_preserves_existing_snapshot(tmp_root: Path) -> None:
    cache_dir = tmp_root / "preserve-old"
    cache_dir.mkdir(exist_ok=True)
    snap = cache_dir / "trimmedia.snapshot.db"
    conn = sqlite3.connect(snap)
    conn.execute("CREATE TABLE old_data (id INTEGER)")
    conn.commit()
    conn.close()
    original_source = fntv_snapshot.settings.fntv_db_path
    original_cache = fntv_snapshot.settings.cache_dir
    original_enabled = fntv_snapshot.settings.snapshot_enabled
    original_admin = fntv_snapshot.settings.admin_db_path
    try:
        fntv_snapshot.settings.fntv_db_path = tmp_root / "missing-source.db"
        fntv_snapshot.settings.cache_dir = cache_dir
        fntv_snapshot.settings.admin_db_path = tmp_root / "missing-admin.db"
        fntv_snapshot.settings.snapshot_enabled = True
        result = fntv_snapshot.refresh_fntv_snapshot()
        assert result["ok"] is False
        assert snap.exists()
        with sqlite3.connect(f"file:{snap.as_posix()}?mode=ro", uri=True) as old:
            assert old.execute("SELECT name FROM sqlite_master WHERE name='old_data'").fetchone()
        resolved = fntv_snapshot.resolve_active_fntv_database()
        assert resolved["active_database"] == "snapshot"
        assert resolved["degraded"] is True
    finally:
        fntv_snapshot.settings.fntv_db_path = original_source
        fntv_snapshot.settings.cache_dir = original_cache
        fntv_snapshot.settings.snapshot_enabled = original_enabled
        fntv_snapshot.settings.admin_db_path = original_admin


def test_failed_refresh_without_snapshot_reports_no_active_database(tmp_root: Path) -> None:
    cache_dir = tmp_root / "no-old"
    cache_dir.mkdir(exist_ok=True)
    original_source = fntv_snapshot.settings.fntv_db_path
    original_cache = fntv_snapshot.settings.cache_dir
    original_enabled = fntv_snapshot.settings.snapshot_enabled
    original_admin = fntv_snapshot.settings.admin_db_path
    try:
        fntv_snapshot.settings.fntv_db_path = tmp_root / "still-missing-source.db"
        fntv_snapshot.settings.cache_dir = cache_dir
        fntv_snapshot.settings.admin_db_path = tmp_root / "still-missing-admin.db"
        fntv_snapshot.settings.snapshot_enabled = True
        result = fntv_snapshot.refresh_fntv_snapshot()
        assert result["ok"] is False
        resolved = fntv_snapshot.resolve_active_fntv_database()
        assert resolved["active_database"] == "none"
        assert resolved["availability"] == "unavailable"
    finally:
        fntv_snapshot.settings.fntv_db_path = original_source
        fntv_snapshot.settings.cache_dir = original_cache
        fntv_snapshot.settings.snapshot_enabled = original_enabled
        fntv_snapshot.settings.admin_db_path = original_admin


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
    test_overdue_schedule_never_returns_a_past_next_refresh(tmp_root)
    test_failed_refresh_falls_back_to_source(tmp_root)
    test_concurrent_manual_refresh_runs_only_once(tmp_root)
    test_manual_and_automatic_refresh_share_the_same_gate(tmp_root)
    test_process_refresh_lock_is_non_blocking(tmp_root)
    test_failed_refresh_preserves_existing_snapshot(tmp_root)
    test_failed_refresh_without_snapshot_reports_no_active_database(tmp_root)
    test_fresh_snapshot_is_used_without_refresh(tmp_root)
    test_record_refresh_failure_writes_attempt(tmp_root)
    print("snapshot refresh smoke passed")


if __name__ == "__main__":
    main()
