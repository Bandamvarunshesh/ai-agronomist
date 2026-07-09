from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._entries[key] = CacheEntry(
            value=value,
            expires_at=time.monotonic() + self.ttl_seconds,
        )

    def get_stale(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        return entry.value

    def clear(self) -> None:
        self._entries.clear()
