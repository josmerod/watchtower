"""Base scraper interface using Strategy pattern.

This module defines the abstract interface that all site-specific scrapers
must implement, enabling easy addition of new scrapers without modifying
existing code (Open/Closed Principle).
"""

from abc import ABC, abstractmethod
from typing import Any

from bs4 import BeautifulSoup

from ..config import SCRAPER_TIMEOUT_SECONDS, DEFAULT_HEADERS
from ..domain.models import Course, ScraperResult
from ..utils.http import fetch_page_content
from ..utils.html_parser import parse_html


class BaseScraper(ABC):
    """Abstract base class for all course scrapers.

    Implements the Strategy pattern, allowing different scraping
    implementations to be used interchangeably.

    Attributes:
        site_code: Internal site code (e.g., 'du', 'uf', 'tb')
        site_name: Human-readable site name
        debug: Enable debug logging
        timeout: HTTP request timeout in seconds
        max_retries: Maximum number of retries for failed requests
    """

    def __init__(
        self,
        site_code: str,
        site_name: str,
        debug: bool = False,
        timeout: int = SCRAPER_TIMEOUT_SECONDS,
        max_retries: int = 5,
    ):
        """Initialize the scraper.

        Args:
            site_code: Internal site code
            site_name: Human-readable site name
            debug: Enable debug logging
            timeout: HTTP request timeout
            max_retries: Maximum retries for failed requests
        """
        self.site_code = site_code
        self.site_name = site_name
        self.debug = debug
        self.timeout = timeout
        self.max_retries = max_retries

        # Result tracking
        self._result = ScraperResult(source=site_name)

    @abstractmethod
    def scrape(self) -> ScraperResult:
        """Execute the scraping process.

        This method must be implemented by all scrapers to perform
        the actual scraping logic for their target site.

        Returns:
            ScraperResult containing found courses and metadata
        """
        pass

    def fetch_page(
        self, url: str, headers: dict[str, str] | None = None
    ) -> str | None:
        """Fetch a page's content.

        Args:
            url: URL to fetch
            headers: Optional HTTP headers

        Returns:
            Page content as string, or None if fetch failed
        """
        if headers is None:
            headers = DEFAULT_HEADERS

        return fetch_page_content(url, headers=headers, timeout=self.timeout)

    def parse_html(self, content: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object.

        Args:
            content: HTML content string

        Returns:
            BeautifulSoup object
        """
        return parse_html(content)

    def log_debug(self, message: str) -> None:
        """Log debug message if debug mode is enabled.

        Args:
            message: Message to log
        """
        if self.debug:
            print(f"[{self.site_code.upper()}] {message}")

    def log_error(self, message: str) -> None:
        """Log error message.

        Args:
            message: Error message to log
        """
        print(f"[{self.site_code.upper()}] ERROR: {message}")
        self._result.errors.append(message)

    def create_course(
        self, title: str, url: str, coupon_code: str | None = None
    ) -> Course:
        """Create a Course entity.

        Args:
            title: Course title
            url: Course URL
            coupon_code: Optional coupon code

        Returns:
            Course entity
        """
        return Course(
            title=title.strip(),
            url=url.strip(),
            source=self.site_code,
            coupon_code=coupon_code,
        )

    def clean_title(self, title: str | None) -> str:
        """Clean and normalize course title.

        Args:
            title: Raw title string

        Returns:
            Cleaned title string
        """
        if not title:
            return "N/A"
        return " ".join(title.strip().split())


class PlaywrightScraper(BaseScraper):
    """Base class for scrapers that require Playwright for JavaScript rendering.

    Provides common Playwright setup and teardown logic for scrapers
    that need to interact with dynamic content.

    Attributes:
        use_playwright: Whether Playwright is available and should be used
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the Playwright-enabled scraper.

        Args:
            *args: Arguments passed to BaseScraper
            **kwargs: Keyword arguments passed to BaseScraper
        """
        super().__init__(*args, **kwargs)

        # Check if Playwright is available
        try:
            from playwright.sync_api import sync_playwright

            self.sync_playwright = sync_playwright
            self.use_playwright = True
            self.log_debug("Playwright is available")
        except ImportError:
            self.sync_playwright = None  # type: ignore
            self.use_playwright = False
            self.log_debug("Playwright not available, falling back to requests")

    def fetch_with_playwright(
        self,
        url: str,
        user_agent: str | None = None,
        wait_until: str = "networkidle",
        timeout: int | None = None,
    ) -> str | None:
        """Fetch page using Playwright browser.

        Args:
            url: URL to fetch
            user_agent: Custom user agent string
            wait_until: Wait condition ('networkidle', 'domcontentloaded', 'load')
            timeout: Page load timeout in milliseconds (None for default)

        Returns:
            Page content as string, or None if fetch failed
        """
        if not self.use_playwright:
            return self.fetch_page(url)

        if timeout is None:
            timeout = self.timeout * 1000  # Convert to ms

        try:
            with self.sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                context = browser.new_context(user_agent=user_agent or DEFAULT_HEADERS["user-agent"])
                page = context.new_page()
                page.goto(url, wait_until=wait_until, timeout=timeout)
                content = page.content()
                browser.close()
                return content
        except Exception as e:
            self.log_error(f"Playwright error: {e}")
            # Fallback to regular requests
            return self.fetch_page(url)


class ScraperFactory:
    """Factory for creating scraper instances.

    Implements the Factory pattern to centralize scraper creation
    and make it easy to add new scrapers.
    """

    _scrapers: dict[str, type[BaseScraper]] = {}

    @classmethod
    def register(cls, site_code: str, scraper_class: type[BaseScraper]) -> None:
        """Register a scraper class.

        Args:
            site_code: Site code (e.g., 'du', 'uf', 'tb')
            scraper_class: Scraper class to register
        """
        cls._scrapers[site_code] = scraper_class

    @classmethod
    def create(cls, site_code: str, **kwargs: Any) -> BaseScraper:
        """Create a scraper instance.

        Args:
            site_code: Site code to create
            **kwargs: Additional arguments passed to scraper constructor

        Returns:
            Scraper instance

        Raises:
            ValueError: If site_code is not registered
        """
        if site_code not in cls._scrapers:
            raise ValueError(f"Unknown scraper: {site_code}")

        scraper_class = cls._scrapers[site_code]
        return scraper_class(site_code=site_code, **kwargs)

    @classmethod
    def get_registered_scrapers(cls) -> list[str]:
        """Get list of registered scraper codes.

        Returns:
            List of registered site codes
        """
        return list(cls._scrapers.keys())
