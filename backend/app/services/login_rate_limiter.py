from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field

from app.core.errors import AppError

PAIR_FAILURE_LIMIT = 5
IP_FAILURE_LIMIT = 20
WINDOW_SECONDS = 5 * 60
BLOCK_SECONDS = 5 * 60
ENTRY_TTL_SECONDS = 15 * 60
MAX_PAIR_ENTRIES = 2048
MAX_IP_ENTRIES = 512


@dataclass
class _FailureEntry:
    failures: deque[float] = field(default_factory=deque)
    blocked_until: float = 0
    last_seen: float = 0


class LoginRateLimiter:
    def __init__(self) -> None:
        self._pairs: OrderedDict[str, _FailureEntry] = OrderedDict()
        self._ips: OrderedDict[str, _FailureEntry] = OrderedDict()
        self._lock = threading.Lock()

    def check(self, client_ip: str | None, username: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._cleanup(now)
            retry_after = max(
                self._retry_after(self._pairs.get(self._pair_key(client_ip, username)), now),
                self._retry_after(self._ips.get(self._ip_key(client_ip)), now),
            )
        if retry_after > 0:
            self._raise_rate_limited(retry_after)

    def record_failure(self, client_ip: str | None, username: str) -> int:
        now = time.monotonic()
        with self._lock:
            self._cleanup(now)
            pair = self._record(
                self._pairs,
                self._pair_key(client_ip, username),
                PAIR_FAILURE_LIMIT,
                now,
                MAX_PAIR_ENTRIES,
            )
            ip_entry = self._record(self._ips, self._ip_key(client_ip), IP_FAILURE_LIMIT, now, MAX_IP_ENTRIES)
            return max(self._retry_after(pair, now), self._retry_after(ip_entry, now))

    def record_success(self, client_ip: str | None, username: str) -> None:
        with self._lock:
            self._pairs.pop(self._pair_key(client_ip, username), None)
            self._ips.pop(self._ip_key(client_ip), None)

    def reset(self) -> None:
        with self._lock:
            self._pairs.clear()
            self._ips.clear()

    def _record(
        self,
        table: OrderedDict[str, _FailureEntry],
        key: str,
        limit: int,
        now: float,
        capacity: int,
    ) -> _FailureEntry:
        entry = table.pop(key, _FailureEntry())
        self._prune_failures(entry, now)
        entry.failures.append(now)
        entry.last_seen = now
        if len(entry.failures) >= limit:
            entry.blocked_until = max(entry.blocked_until, now + BLOCK_SECONDS)
        table[key] = entry
        while len(table) > capacity:
            table.popitem(last=False)
        return entry

    def _cleanup(self, now: float) -> None:
        for table in (self._pairs, self._ips):
            expired = [key for key, entry in table.items() if now - entry.last_seen > ENTRY_TTL_SECONDS and entry.blocked_until <= now]
            for key in expired:
                table.pop(key, None)

    @staticmethod
    def _prune_failures(entry: _FailureEntry, now: float) -> None:
        cutoff = now - WINDOW_SECONDS
        while entry.failures and entry.failures[0] <= cutoff:
            entry.failures.popleft()

    @staticmethod
    def _retry_after(entry: _FailureEntry | None, now: float) -> int:
        return max(0, math.ceil(entry.blocked_until - now - 1e-9)) if entry else 0

    @staticmethod
    def _ip_key(client_ip: str | None) -> str:
        return client_ip or "<unknown>"

    @classmethod
    def _pair_key(cls, client_ip: str | None, username: str) -> str:
        return f"{cls._ip_key(client_ip)}\0{username.strip().casefold()}"

    @staticmethod
    def _raise_rate_limited(retry_after: int) -> None:
        raise AppError(
            "LOGIN_RATE_LIMITED",
            "登录尝试过于频繁，请稍后重试",
            429,
            headers={"Retry-After": str(retry_after)},
        )


login_rate_limiter = LoginRateLimiter()
