"""One plain HTTP GET per page, shared by the Valencia event sources.

Nothing here keeps a session or rotates proxies: a source is a public page read
once per run with an identifiable User-Agent. A 403 or 429 is not retried and
does not trip a retry loop: it means the host does not want the traffic, so the
rest of the run leaves that host alone and the composer reports it.
"""

import time
from urllib.parse import urlsplit

import requests

from src.constants.etl import SCRAPER_BRANDED_USER_AGENT

REQUEST_TIMEOUT_SECONDS = 30
PAUSE_BETWEEN_REQUESTS_SECONDS = 1.0
_BLOCKED_STATUSES = (403, 429)

_blocked_hosts: set[str] = set()


class SourceBlockedError(RuntimeError):
    """The host answered 403 or 429 (or already had during this run): stop asking it."""

    def __init__(self, url: str, status_code: int, retry_after: str = ""):
        self.url = url
        self.host = urlsplit(url).netloc
        self.status_code = status_code
        self.retry_after = retry_after
        detail = f" (Retry-After: {retry_after})" if retry_after else ""
        super().__init__(f"HTTP {status_code} from {self.host}{detail}: {url}")


def blocked_hosts() -> set[str]:
    """Hosts that answered 403 or 429 earlier in this run."""
    return set(_blocked_hosts)


def reset_blocked_hosts() -> None:
    """Forget the blocked hosts. Only tests call it: a run is a process of its own in production, and a retry inside a run must keep leaving the host alone."""
    _blocked_hosts.clear()


def pause() -> None:
    """Wait between two requests, so a run never hits a host back to back."""
    time.sleep(PAUSE_BETWEEN_REQUESTS_SECONDS)


def fetch_page(url: str, *, user_agent: str = SCRAPER_BRANDED_USER_AGENT) -> bytes:
    """GET ``url`` once and return the raw body.

    ``requests.get`` is looked up on the module when the call is made, not
    imported by name, so a test that patches ``requests.get`` anywhere is seen
    by every source.

    Args:
        url: Public page to read.
        user_agent: Value of the User-Agent header.

    Returns:
        The response body as bytes.

    Raises:
        SourceBlockedError: The host answered 403 or 429, or had already done so
            during this run; no request is made in the second case.
        requests.HTTPError: Any other 4xx/5xx answer.
    """
    host = urlsplit(url).netloc
    if host in _blocked_hosts:
        raise SourceBlockedError(url, 0)
    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=REQUEST_TIMEOUT_SECONDS)
    if response.status_code in _BLOCKED_STATUSES:
        _blocked_hosts.add(host)
        raise SourceBlockedError(url, response.status_code, str(response.headers.get("Retry-After") or ""))
    response.raise_for_status()
    return response.content
