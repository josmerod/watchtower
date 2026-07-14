"""Proxy Manager for ETL processes.

Handles proxy rotation and session creation to avoid IP bans.
"""

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy rotation and session creation."""

    def __init__(self, proxies: list[str] | None = None):
        self.settings = get_settings()
        self.proxies = proxies or self.settings.scraping.proxies
        self.current_proxy_index = 0

        if self.proxies:
            logger.info(f"Initialized ProxyManager with {len(self.proxies)} proxies.")
        else:
            logger.debug("ProxyManager initialized with no proxies (direct connection).")

    def get_proxy(self) -> dict | None:
        """Get a proxy dictionary for requests."""
        if not self.proxies:
            return None

        # Simple round-robin for now
        proxy_url = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)

        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def get_session(self, retries: int = 3, backoff_factor: float = 2.0) -> requests.Session:
        """Get a configured requests.Session with proxy and retries."""
        session = requests.Session()

        # Configure Proxy
        proxies = self.get_proxy()
        if proxies:
            session.proxies.update(proxies)
            logger.debug(f"Session configured with proxy: {proxies['http'].split('@')[-1] if '@' in proxies['http'] else '***'}")

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

        # standard headers
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})

        return session
