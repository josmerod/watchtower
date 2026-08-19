"""Tiny TTL cache for per-tab data loaders (spec 15 M2).

Replaces the module-level ``_CACHE = {"ts": ..., "data": ...}`` +
``except NameError`` antipattern found across tab modules. Loaders stay as
plain functions; the cache box is explicit and supports ``force_refresh``
for the standard refresh button.
"""

import threading
import time
from collections.abc import Callable
from typing import Any


class TTLDataCache:
    """Cache the result of a loader callable for a fixed time-to-live.

    Args:
        ttl_seconds: How long a cached value stays fresh.
    """

    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = ttl_seconds
        self._value: Any = None
        self._loaded_at: float = 0.0
        self._has_value = False
        self._lock = threading.Lock()

    def get(self, loader: Callable[[], Any], force_refresh: bool = False) -> Any:
        """Return the cached value, invoking ``loader`` when stale.

        Args:
            loader: Zero-argument callable producing the data.
            force_refresh: Skip the cache and reload regardless of age.
        """
        with self._lock:
            if not force_refresh and self._has_value and (time.time() - self._loaded_at) < self.ttl_seconds:
                return self._value
        value = loader()
        with self._lock:
            self._value = value
            self._loaded_at = time.time()
            self._has_value = True
        return value

    def invalidate(self) -> None:
        """Drop the cached value so the next ``get`` reloads."""
        with self._lock:
            self._has_value = False
            self._value = None


def get_timestamp() -> float:
    """Return the current epoch timestamp (seam for tests)."""
    return time.time()
