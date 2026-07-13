from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float
    stale_expires_at: float | None = None


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int, stale_ttl_seconds: int | None = None):
        self.ttl_seconds = ttl_seconds
        self.stale_ttl_seconds = stale_ttl_seconds
        self._entries: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        now = time.monotonic()
        if entry.expires_at < now:
            if entry.stale_expires_at is not None and entry.stale_expires_at < now:
                self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        now = time.monotonic()
        stale_expires_at = (
            now + self.stale_ttl_seconds if self.stale_ttl_seconds is not None else None
        )
        self._entries[key] = CacheEntry(
            value=value,
            expires_at=now + self.ttl_seconds,
            stale_expires_at=stale_expires_at,
        )

    def get_stale(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.stale_expires_at is not None and entry.stale_expires_at < time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    def clear(self) -> None:
        self._entries.clear()
