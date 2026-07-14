"""Common retry utilities for Watchtower ETL scripts.

Provides:
  - ``with_retry``: Decorator to retry any function on transient network errors.
  - ``fetch_with_retry``: One-liner to fetch a URL (urllib) with retry logic.

Retry policy
------------
- 3 retries (4 total attempts: 1 initial + 3 retries)
- Exponential backoff: ~1 s, 2 s, 4 s
- Retryable exceptions:
    ``urllib.error.URLError``, ``urllib.error.HTTPError``,
    ``TimeoutError``, ``ConnectionError``,
    and (when *requests* is available) ``requests.exceptions.RequestException``.

Usage
-----
Decorator::

    from src.utils.retry import with_retry

    @with_retry
    def fetch_data():
        ...

Function::

    from src.utils.retry import fetch_with_retry

    content = fetch_with_retry("https://example.com/feed.xml", timeout=60)
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("watchtower.retry")

# ---------------------------------------------------------------------------
# Retryable exception set
# ---------------------------------------------------------------------------
_RETRY_BASE: tuple[type[BaseException], ...] = (
    urllib.error.URLError,
    urllib.error.HTTPError,
    TimeoutError,
    ConnectionError,
)

try:
    from requests.exceptions import RequestException as _RequestsRequestException  # type: ignore[import-untyped]

    RETRYABLE_ERRORS: tuple[type[BaseException], ...] = (
        *_RETRY_BASE,
        _RequestsRequestException,
    )
except ImportError:  # pragma: no cover – requests not installed
    RETRYABLE_ERRORS = _RETRY_BASE

# ---------------------------------------------------------------------------
# Shared tenacity configuration
# ---------------------------------------------------------------------------
_TENACITY_KW: dict[str, Any] = {
    "stop": stop_after_attempt(4),  # 1 initial + 3 retries
    "wait": wait_exponential(multiplier=1, min=1, max=4),  # ~1s, 2s, 4s
    "retry": retry_if_exception_type(RETRYABLE_ERRORS),
    "before_sleep": before_sleep_log(logger, logging.WARNING),
    "reraise": True,
}

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def with_retry(func: F | None = None, *, max_retries: int = 3) -> F:
    """Decorator that retries *func* on transient network / HTTP errors.

    Parameters
    ----------
    func:
        The function to wrap.  May be ``None`` when the decorator is used
        with arguments (``@with_retry(max_retries=5)``).
    max_retries:
        Number of retry attempts (default 3 → 4 total calls).

    Example
    -------
    ::

        @with_retry
        def fetch():
            return requests.get(...)

        @with_retry(max_retries=5)
        def fetch():
            ...
    """
    kw = {**_TENACITY_KW, "stop": stop_after_attempt(max_retries + 1)}

    def _decorator(fn: F) -> F:
        return retry(**kw)(fn)  # type: ignore[return-value]

    if func is not None:
        return _decorator(func)
    return _decorator  # type: ignore[return-value]


def fetch_with_retry(
    url: str,
    *,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
) -> bytes:
    """Fetch *url* via ``urllib.request`` and return the response **bytes**.

    Retries automatically on transient errors (see module docstring).

    Parameters
    ----------
    url:
        The URL to fetch.
    timeout:
        Socket timeout in seconds (default 30).
    headers:
        Optional HTTP headers merged into the request.

    Returns
    -------
    bytes
        The full response body.

    Raises
    -------
    Exception
        The last exception encountered after all retries are exhausted.
    """
    req = urllib.request.Request(url, headers=headers or {})

    @retry(**_TENACITY_KW)
    def _do_fetch() -> bytes:
        logger.info("Fetching %s (timeout=%ds)", url, timeout)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    return _do_fetch()
