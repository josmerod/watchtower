"""Proxy Manager for ETL processes.

Handles proxy rotation and session creation to avoid IP bans.

Sessions are cached per (retries, backoff_factor) key so that repeated calls
within the same ProxyManager lifecycle reuse the underlying ``requests.Session``
instead of leaking connection pools.  Call :meth:`close` (or use the context
manager) to release all cached sessions.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Default browser User-Agent — kept as a module constant so every session
# uses the same string and so tests can monkey-patch it if needed.
_DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


class ProxyManager:
    """Manages proxy rotation and session creation.

    Sessions are cached by ``(retries, backoff_factor)`` to avoid creating
    a new ``requests.Session`` (and its associated connection pool) on every
    HTTP request.  The cache is keyed on the retry configuration because two
    callers that request different retry budgets must receive distinct
    adapter-mounted sessions.

    Use :meth:`close` when done, or use the manager as a context manager::

        with ProxyManager() as pm:
            session = pm.get_session()
            ...

    Inside an ETL pipeline, :meth:`BaseETL.run` calls ``close`` automatically
    in its ``finally`` block.
    """

    def __init__(self, proxies: list[str] | None = None):
        self.settings = get_settings()
        self.proxies = proxies or self.settings.scraping.proxies
        self.current_proxy_index = 0

        # Cache: (retries, backoff_factor) -> requests.Session
        self._session_cache: dict[tuple[int, float], requests.Session] = {}

        # Track how many sessions each proxy index has been assigned to,
        # so we can advance the round-robin pointer deterministically.
        # (For simplicity we just continue the round-robin on each new session.)
        if self.proxies:
            logger.info(f"Initialized ProxyManager with {len(self.proxies)} proxies.")
        else:
            logger.debug("ProxyManager initialized with no proxies (direct connection).")

    # ------------------------------------------------------------------
    # Proxy helpers
    # ------------------------------------------------------------------

    def get_proxy(self) -> dict | None:
        """Get a proxy dictionary for requests.

        Returns:
            ``{"http": url, "https": url}`` dict or ``None`` when no
            proxies are configured.
        """
        if not self.proxies:
            return None

        # Simple round-robin
        proxy_url = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)

        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def get_session(self, retries: int = 3, backoff_factor: float = 2.0) -> requests.Session:
        """Get a configured ``requests.Session`` with proxy and retries.

        The session is **cached** for the given ``(retries, backoff_factor)``
        key, so subsequent calls with the same arguments return the *same*
        ``Session`` object — avoiding the creation of new connection pools
        on every HTTP request.

        Args:
            retries: Total number of retry attempts on retryable status codes.
            backoff_factor: Exponential backoff multiplier for retries.

        Returns:
            A configured ``requests.Session`` instance.  The caller must NOT
            close it; :meth:`close` releases all cached sessions.
        """
        cache_key = (retries, backoff_factor)

        cached = self._session_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Reusing cached session for key={cache_key}")
            return cached

        session = self._build_session(retries, backoff_factor)
        self._session_cache[cache_key] = session
        return session

    def _build_session(self, retries: int, backoff_factor: float) -> requests.Session:
        """Create a new ``requests.Session`` configured with proxy + retries."""
        session = requests.Session()

        # Configure Proxy
        proxies = self.get_proxy()
        if proxies:
            session.proxies.update(proxies)
            logger.debug(
                f"Session configured with proxy: {proxies['http'].split('@')[-1] if '@' in proxies['http'] else '***'}"
            )

        # Configure Retries
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Standard headers
        session.headers.update({"User-Agent": _DEFAULT_UA})

        return session

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def cached_session_count(self) -> int:
        """Number of sessions currently held in the cache."""
        return len(self._session_cache)

    def close(self) -> None:
        """Close all cached sessions and release connection pools.

        Safe to call multiple times — after :meth:`close`, the cache is
        empty and subsequent :meth:`get_session` calls will create fresh
        sessions.
        """
        if not self._session_cache:
            return

        closed = 0
        for key, session in self._session_cache.items():
            try:
                session.close()
                closed += 1
            except Exception:
                logger.warning(f"Error closing cached session key={key}", exc_info=True)

        self._session_cache.clear()
        logger.debug(f"ProxyManager closed {closed} cached session(s).")

    # Context-manager protocol ------------------------------------------------

    def __enter__(self) -> ProxyManager:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()

    def __del__(self) -> None:
        """Best-effort cleanup — never let sessions leak silently."""
        try:
            self.close()
        except Exception:
            pass
