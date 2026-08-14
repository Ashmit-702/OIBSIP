"""A tiny thread-safe TTL cache.

OpenWeatherMap's free tier caps requests per minute. Flask's dev server
(and most production WSGI servers) can handle several requests
concurrently, so two users searching the same city seconds apart would
otherwise both hit the upstream API. This cache collapses repeat lookups
within a short time window, and uses a lock because dict access isn't
guaranteed atomic across threads for read-then-write patterns like ours.
"""

import threading
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 600):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
