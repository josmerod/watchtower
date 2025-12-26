"""Scraping Strategy Pattern - Generic framework for web scraping.

Implements Strategy pattern for different scraping approaches:
- HTTP scraping (requests, cloudscraper)
- Browser scraping (Playwright, Selenium)
- API scraping (REST, GraphQL)
- Hybrid scraping (combination of approaches)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ScrapingMethod(Enum):
    """Enumeration of available scraping methods."""

    HTTP = "http"  # Simple HTTP requests
    CLOUDSCRAPER = "cloudscraper"  # Anti-bot bypass
    PLAYWRIGHT = "playwright"  # Headless browser
    SELENIUM = "selenium"  # Headless browser (alternative)
    API = "api"  # REST/GraphQL API
    HYBRID = "hybrid"  # Combination of methods


class ScrapingContext(BaseModel):
    """Context for scraping operations.

    Contains configuration and state for scraping strategy.
    """

    url: str
    method: ScrapingMethod
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    headers: dict[str, str] | None = None
    user_agent: str | None = None
    proxy: str | None = None
    wait_for_selector: str | None = None
    screenshot: bool = False
    debug: bool = False

    # Additional parameters
    extra_params: dict[str, Any] = {}


class ScrapingResult(BaseModel):
    """Result from scraping operation.

    Contains scraped data and metadata.
    """

    success: bool
    content: str | None = None
    data: dict[str, Any] | list[Any] | None = None
    error: str | None = None
    status_code: int | None = None
    method_used: ScrapingMethod | None = None
    response_time_ms: float | None = None
    screenshot_path: str | None = None

    # Metadata
    url: str | None = None
    timestamp: str | None = None

    @property
    def has_content(self) -> bool:
        """Check if result has content."""
        return self.content is not None and len(self.content) > 0

    @property
    def has_data(self) -> bool:
        """Check if result has structured data."""
        return self.data is not None


class ScrapingStrategy(ABC):
    """Abstract base class for scraping strategies.

    Implements the Strategy pattern, allowing different scraping
    approaches to be used interchangeably.
    """

    def __init__(self, context: ScrapingContext):
        """Initialize the strategy.

        Args:
            context: Scraping context with configuration
        """
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def scrape(self) -> ScrapingResult:
        """Execute the scraping operation.

        Returns:
            ScrapingResult with scraped data
        """
        pass

    def can_execute(self) -> bool:
        """Check if strategy can execute.

        Returns:
            True if required dependencies are available
        """
        return True

    def log_debug(self, message: str) -> None:
        """Log debug message.

        Args:
            message: Message to log
        """
        if self.context.debug:
            self.logger.debug(f"[{self.__class__.__name__}] {message}")

    def log_error(self, message: str) -> None:
        """Log error message.

        Args:
            message: Error message to log
        """
        self.logger.error(f"[{self.__class__.__name__}] {message}")


class HTTPScrapingStrategy(ScrapingStrategy):
    """Strategy for simple HTTP scraping.

    Uses requests library for basic HTTP requests.
    Suitable for static pages and simple APIs.
    """

    def scrape(self) -> ScrapingResult:
        """Scrape using HTTP requests.

        Returns:
            ScrapingResult with page content
        """
        import time
        from datetime import datetime

        import requests

        start_time = time.time()

        try:
            self.log_debug(f"Fetching URL: {self.context.url}")

            headers = self.context.headers or {
                "User-Agent": self.context.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            response = requests.get(
                self.context.url,
                headers=headers,
                timeout=self.context.timeout,
                proxies={"http": self.context.proxy, "https": self.context.proxy} if self.context.proxy else None,
            )

            response_time_ms = (time.time() - start_time) * 1000

            return ScrapingResult(
                success=response.status_code == 200,
                content=response.text,
                status_code=response.status_code,
                method_used=ScrapingMethod.HTTP,
                response_time_ms=response_time_ms,
                url=self.context.url,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.log_error(f"HTTP scraping failed: {e}")

            return ScrapingResult(
                success=False,
                error=str(e),
                method_used=ScrapingMethod.HTTP,
                response_time_ms=response_time_ms,
                url=self.context.url,
                timestamp=datetime.utcnow().isoformat(),
            )


class CloudScraperStrategy(ScrapingStrategy):
    """Strategy for bypassing anti-bot protection.

    Uses cloudscraper library to bypass Cloudflare and other anti-bot measures.
    """

    def scrape(self) -> ScrapingResult:
        """Scrape using cloudscraper.

        Returns:
            ScrapingResult with page content
        """
        import time
        from datetime import datetime

        try:
            import cloudscraper
        except ImportError:
            return ScrapingResult(
                success=False,
                error="cloudscraper not installed",
                method_used=ScrapingMethod.CLOUDSCRAPER,
                url=self.context.url,
            )

        start_time = time.time()

        try:
            self.log_debug(f"Fetching URL with cloudscraper: {self.context.url}")

            scraper = cloudscraper.create_scraper(
                browser="chrome",
                delay=self.context.retry_delay,
            )

            response = scraper.get(
                self.context.url,
                timeout=self.context.timeout,
            )

            response_time_ms = (time.time() - start_time) * 1000

            return ScrapingResult(
                success=response.status_code == 200,
                content=response.text,
                status_code=response.status_code,
                method_used=ScrapingMethod.CLOUDSCRAPER,
                response_time_ms=response_time_ms,
                url=self.context.url,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.log_error(f"CloudScraper failed: {e}")

            return ScrapingResult(
                success=False,
                error=str(e),
                method_used=ScrapingMethod.CLOUDSCRAPER,
                response_time_ms=response_time_ms,
                url=self.context.url,
                timestamp=datetime.utcnow().isoformat(),
            )

    def can_execute(self) -> bool:
        """Check if cloudscraper is available."""
        try:
            import cloudscraper

            return True
        except ImportError:
            return False


class PlaywrightScrapingStrategy(ScrapingStrategy):
    """Strategy for dynamic JavaScript pages.

    Uses Playwright for browser automation and JavaScript rendering.
    """

    def scrape(self) -> ScrapingResult:
        """Scrape using Playwright browser.

        Returns:
            ScrapingResult with page content
        """
        import time
        from datetime import datetime

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ScrapingResult(
                success=False,
                error="Playwright not installed",
                method_used=ScrapingMethod.PLAYWRIGHT,
                url=self.context.url,
            )

        start_time = time.time()

        try:
            self.log_debug(f"Fetching URL with Playwright: {self.context.url}")

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )

                context = browser.new_context(
                    user_agent=self.context.user_agent or "Mozilla/5.0",
                    proxy={"server": self.context.proxy} if self.context.proxy else None,
                )

                page = context.new_page()

                # Navigate to page
                page.goto(
                    self.context.url,
                    wait_until="networkidle",
                    timeout=self.context.timeout * 1000,
                )

                # Wait for specific selector if provided
                if self.context.wait_for_selector:
                    page.wait_for_selector(self.context.wait_for_selector, timeout=5000)

                # Take screenshot if requested
                screenshot_path = None
                if self.context.screenshot:
                    screenshot_path = f"screenshot_{int(time.time())}.png"
                    page.screenshot(path=screenshot_path)

                # Get content
                content = page.content()

                browser.close()

                response_time_ms = (time.time() - start_time) * 1000

                return ScrapingResult(
                    success=True,
                    content=content,
                    method_used=ScrapingMethod.PLAYWRIGHT,
                    response_time_ms=response_time_ms,
                    screenshot_path=screenshot_path,
                    url=self.context.url,
                    timestamp=datetime.utcnow().isoformat(),
                )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.log_error(f"Playwright scraping failed: {e}")

            return ScrapingResult(
                success=False,
                error=str(e),
                method_used=ScrapingMethod.PLAYWRIGHT,
                response_time_ms=response_time_ms,
                url=self.context.url,
                timestamp=datetime.utcnow().isoformat(),
            )

    def can_execute(self) -> bool:
        """Check if Playwright is available."""
        try:
            from playwright.sync_api import sync_playwright

            return True
        except ImportError:
            return False


class HybridScrapingStrategy(ScrapingStrategy):
    """Strategy that tries multiple methods in order.

    Falls back through strategies until one succeeds.
    """

    def __init__(
        self,
        context: ScrapingContext,
        strategies: list[type[ScrapingStrategy]] | None = None,
    ):
        """Initialize hybrid strategy.

        Args:
            context: Scraping context
            strategies: Ordered list of strategies to try
        """
        super().__init__(context)

        # Default strategy order: Playwright -> CloudScraper -> HTTP
        self.strategies = strategies or [
            PlaywrightScrapingStrategy,
            CloudScraperStrategy,
            HTTPScrapingStrategy,
        ]

    def scrape(self) -> ScrapingResult:
        """Try each strategy in order until one succeeds.

        Returns:
            ScrapingResult from first successful strategy
        """
        for strategy_class in self.strategies:
            try:
                strategy = strategy_class(self.context)

                if not strategy.can_execute():
                    self.log_debug(f"Skipping {strategy_class.__name__} (not available)")
                    continue

                self.log_debug(f"Trying {strategy_class.__name__}")
                result = strategy.scrape()

                if result.success:
                    self.log_debug(f"Success with {strategy_class.__name__}")
                    return result

                self.log_debug(f"{strategy_class.__name__} failed: {result.error}")

            except Exception as e:
                self.log_error(f"Strategy {strategy_class.__name__} raised exception: {e}")
                continue

        # All strategies failed
        return ScrapingResult(
            success=False,
            error="All scraping strategies failed",
            method_used=ScrapingMethod.HYBRID,
            url=self.context.url,
        )
