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
    # Strategies
    "ScrapingStrategy",
    "HTTPScrapingStrategy",
    "CloudScraperStrategy",
    "PlaywrightScrapingStrategy",
    "HybridScrapingStrategy",
    # Models
    "ScrapingContext",
    "ScrapingResult",
    "ScrapingMethod",
    # Manager
    "ScraperManager",
    "ScraperManagerError",
    # Convenience
    "get_scraper_manager",
    "scrape_url",
]
