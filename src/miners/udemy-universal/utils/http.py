"""HTTP utility functions.

Provides centralized HTTP request handling with retry logic,
error handling, and cloudscraper integration.
"""

import time
from typing import Any

import cloudscraper
import requests


def fetch_page_content(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    allow_redirects: bool = True,
    use_cloudscraper: bool = False,
) -> str | None:
    """Fetch page content with retry logic.

    Args:
        url: URL to fetch
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
        allow_redirects: Whether to follow redirects
        use_cloudscraper: Use cloudscraper to bypass anti-bot protection

    Returns:
        Page content as string, or None if all retries failed
    """
    session = _create_session(use_cloudscraper)

    if headers:
        session.headers.update(headers)

    for attempt in range(3):  # 3 retry attempts
        try:
            response = session.get(
                url,
                timeout=timeout,
                allow_redirects=allow_redirects,
            )
            response.raise_for_status()
            return response.text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (404, 403):
                # Don't retry for 404/403 errors
                return None
            if attempt < 2:
                time.sleep(2**attempt)  # Exponential backoff
                continue
            return None

        except (requests.exceptions.RequestException, OSError) as e:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            return None

    return None


def _create_session(use_cloudscraper: bool = False) -> requests.Session:
    """Create a requests session.

    Args:
        use_cloudscraper: Whether to use cloudscraper

    Returns:
        Session object
    """
    if use_cloudscraper:
        return cloudscraper.create_scraper()

    session = requests.Session()
    session.keep_alive = False
    return session


def follow_redirect(url: str, headers: dict[str, str] | None = None, timeout: int = 10) -> str | None:
    """Follow redirects to get final URL.

    Args:
        url: URL to follow
        headers: Optional HTTP headers
        timeout: Request timeout in seconds

    Returns:
        Final URL after redirects, or None if failed
    """
    try:
        response = requests.head(
            url,
            headers=headers or {},
            allow_redirects=True,
            timeout=timeout,
        )
        return response.url
    except requests.RequestException:
        return None
