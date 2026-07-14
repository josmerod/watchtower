"""Scraper Manager - Centralized scraping with strategy selection.

Provides high-level interface for scraping operations with automatic
strategy selection, retry logic, and caching.
"""

from __future__ import annotations

import logging
from typing import Any

from src.scraping.strategy.scraping_strategy import (
    CloudScraperStrategy,
    ScrapingContext,
    ScrapingMethod,
    ScrapingResult,
    ScrapingStrategy,
)


class ScraperManagerError(Exception):
    """Exception raised when scraper manager operations fail."""

    pass


class ScraperManager:
    """Manager for web scraping operations.

    Provides:
    - Automatic strategy selection
    - Retry logic with exponential backoff
    - Result caching
    - Error handling and logging
    """

    def __init__(
        self,
        default_method: ScrapingMethod = ScrapingMethod.HYBRID,
        default_timeout: int = 30,
        default_max_retries: int = 3,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize scraper manager.

        Args:
            default_method: Default scraping method
            default_timeout: Default request timeout
            default_max_retries: Default retry count
            enable_caching: Enable result caching
            cache_ttl_seconds: Cache time-to-live
        """
        self.default_method = default_method
        self.default_timeout = default_timeout
        self.default_max_retries = default_max_retries
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl_seconds

        self._cache: dict[str, tuple[ScrapingResult, float]] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def scrape(
        self,
        url: str,
        method: ScrapingMethod | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> ScrapingResult:
        """Scrape a URL with automatic retry and caching.

        Args:
            url: URL to scrape
            method: Scraping method (uses default if None)
            timeout: Request timeout
            max_retries: Maximum retry attempts
            **kwargs: Additional context parameters

        Returns:
            ScrapingResult with scraped data

        Raises:
            ScraperManagerError: If all retries fail
        """
        # Check cache
        if self.enable_caching and url in self._cache:
            result, timestamp = self._cache[url]
            import time

            if time.time() - timestamp < self.cache_ttl:
                self._logger.debug(f"Cache hit for {url}")
                return result

        # Create context
        context = ScrapingContext(
            url=url,
            method=method or self.default_method,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries or self.default_max_retries,
            **kwargs,
        )

        # Create strategy
        strategy = self._create_strategy(context)

        # Execute with retries
        result = self._execute_with_retry(strategy)

        # Cache result
        if self.enable_caching and result.success:
            import time

            self._cache[url] = (result, time.time())

        return result

    def scrape_batch(
        self,
        urls: list[str],
        method: ScrapingMethod | None = None,
        **kwargs: Any,
    ) -> dict[str, ScrapingResult]:
        """Scrape multiple URLs.

        Args:
            urls: List of URLs to scrape
            method: Scraping method
            **kwargs: Additional context parameters

        Returns:
            Dictionary mapping URLs to results
        """
        results = {}

        for url in urls:
            try:
                result = self.scrape(url, method=method, **kwargs)
                results[url] = result
            except Exception as e:
                self._logger.error(f"Failed to scrape {url}: {e}")
                results[url] = ScrapingResult(
                    success=False,
                    error=str(e),
                    url=url,
                )

        return results

    def _create_strategy(self, context: ScrapingContext) -> ScrapingStrategy:
        """Create scraping strategy based on context.

        Args:
            context: Scraping context

        Returns:
            ScrapingStrategy instance

        Raises:
            ScraperManagerError: If method not supported
        """
        from src.scraping.strategy.scraping_strategy import (
            HTTPScrapingStrategy,
            HybridScrapingStrategy,
            PlaywrightScrapingStrategy,
        )

        strategy_map = {
            ScrapingMethod.HTTP: HTTPScrapingStrategy,
            ScrapingMethod.CLOUDSCRAPER: CloudScraperStrategy,
            ScrapingMethod.PLAYWRIGHT: PlaywrightScrapingStrategy,
            ScrapingMethod.HYBRID: HybridScrapingStrategy,
        }

        strategy_class = strategy_map.get(context.method)

        if strategy_class is None:
            raise ScraperManagerError(f"Unsupported scraping method: {context.method}")

        return strategy_class(context)

    def _execute_with_retry(self, strategy: ScrapingStrategy) -> ScrapingResult:
        """Execute strategy with retry logic.

        Args:
            strategy: Scraping strategy to execute

        Returns:
            ScrapingResult

        Raises:
            ScraperManagerError: If all retries fail
        """
        import time

        last_error = None

        for attempt in range(strategy.context.max_retries):
            try:
                result = strategy.scrape()

                if result.success:
                    if attempt > 0:
                        self._logger.info(f"Success on attempt {attempt + 1}")

                    return result

                last_error = result.error

                # Don't retry on client errors (4xx)
                if result.status_code and 400 <= result.status_code < 500:
                    self._logger.warning(f"Client error {result.status_code}, not retrying")
                    return result

            except Exception as e:
                last_error = str(e)
                self._logger.error(f"Attempt {attempt + 1} failed: {e}")

            # Wait before retry
            if attempt < strategy.context.max_retries - 1:
                delay = strategy.context.retry_delay * (2**attempt)  # Exponential backoff
                self._logger.debug(f"Retrying in {delay}s...")
                time.sleep(delay)

        # All retries failed
        return ScrapingResult(
            success=False,
            error=f"All retries failed. Last error: {last_error}",
            url=strategy.context.url,
        )

    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self._logger.debug("Cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        import time

        valid_entries = sum(1 for _, timestamp in self._cache.values() if time.time() - timestamp < self.cache_ttl)

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_ttl_seconds": self.cache_ttl,
        }


# Singleton instance
_default_manager: ScraperManager | None = None


def get_scraper_manager() -> ScraperManager:
    """Get the default scraper manager (singleton).

    Returns:
        ScraperManager instance
    """
    global _default_manager

    if _default_manager is None:
        _default_manager = ScraperManager()

    return _default_manager


def scrape_url(
    url: str,
    method: ScrapingMethod | None = None,
    **kwargs: Any,
) -> ScrapingResult:
    """Convenience function to scrape a URL.

    Args:
        url: URL to scrape
        method: Scraping method
        **kwargs: Additional parameters

    Returns:
        ScrapingResult with scraped data
    """
    manager = get_scraper_manager()
    return manager.scrape(url, method=method, **kwargs)
