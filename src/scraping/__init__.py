"""Scraping framework with Strategy pattern.

Provides generic scraping strategies and manager for web scraping.
"""

from src.scraping.scraper_manager import (
    ScraperManager,
    ScraperManagerError,
    get_scraper_manager,
    scrape_url,
)
from src.scraping.strategy.scraping_strategy import (
    CloudScraperStrategy,
    HTTPScrapingStrategy,
    HybridScrapingStrategy,
    PlaywrightScrapingStrategy,
    ScrapingContext,
    ScrapingMethod,
    ScrapingResult,
    ScrapingStrategy,
)

__all__ = [
    "CloudScraperStrategy",
    "HTTPScrapingStrategy",
    "HybridScrapingStrategy",
    "PlaywrightScrapingStrategy",
    # Manager
    "ScraperManager",
    "ScraperManagerError",
    # Models
    "ScrapingContext",
    "ScrapingMethod",
    "ScrapingResult",
    # Strategies
    "ScrapingStrategy",
    # Convenience
    "get_scraper_manager",
    "scrape_url",
]
