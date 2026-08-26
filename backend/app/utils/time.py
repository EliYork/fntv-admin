from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_APPLICATION_TIMEZONE = "Asia/Shanghai"


def application_timezone_name() -> str:
    candidate = (os.getenv("TZ") or DEFAULT_APPLICATION_TIMEZONE).strip()
    try:
        ZoneInfo(candidate)
        return candidate
    except (ZoneInfoNotFoundError, ValueError):
        return DEFAULT_APPLICATION_TIMEZONE


def application_timezone() -> ZoneInfo:
    return ZoneInfo(application_timezone_name())


def application_now() -> datetime:
    return datetime.now(application_timezone())


def unix_timestamp_seconds(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    # Current FNOS schemas use Unix seconds or milliseconds. Values below this
    # threshold are usually years or durations rather than absolute timestamps.
    if number >= 100_000_000_000:
        number /= 1000
    if number < 100_000_000:
        return None
    return number


def timestamp_as_application_datetime(value: Any) -> datetime | None:
    seconds = unix_timestamp_seconds(value)
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(seconds, application_timezone())
    except (OSError, OverflowError, ValueError):
        return None


def format_timestamp(value: Any) -> str | None:
    local_time = timestamp_as_application_datetime(value)
    return local_time.isoformat(timespec="seconds") if local_time else None


def local_day_bounds(now: datetime | None = None) -> tuple[int, int]:
    timezone = application_timezone()
    current = now or datetime.now(timezone)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone)
    else:
        current = current.astimezone(timezone)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp())


def recent_local_day_start(days: int, now: datetime | None = None) -> int:
    clean_days = max(1, int(days))
    today_start, _ = local_day_bounds(now)
    start = datetime.fromtimestamp(today_start, application_timezone()) - timedelta(days=clean_days - 1)
    return int(start.timestamp())


def application_date_range(days: int, now: datetime | None = None) -> list[date]:
    clean_days = max(1, int(days))
    if now is None:
        current = application_now()
    elif now.tzinfo is None:
        current = now.replace(tzinfo=application_timezone())
    else:
        current = now.astimezone(application_timezone())
    today = current.date()
    start = today - timedelta(days=clean_days - 1)
    return [start + timedelta(days=index) for index in range(clean_days)]


def now_ts() -> int:
    return int(time.time())
