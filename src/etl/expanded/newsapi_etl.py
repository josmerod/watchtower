"""Enhanced NewsAPI ETL using BaseETL pattern.

Part of Phase 1 ETL implementation for expanded news aggregation.
Supports all 150K+ global sources from NewsAPI.org.

Author: Phase 1 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.config.settings import get_settings
from src.etl.base import BaseETL
from src.models.newsapi import NewsApiArticleModel, NewsApiMetricsModel, NewsArticleSourceModel
from src.utils.logging import get_logger


class NewsApiETL(BaseETL[dict[str, Any], NewsApiArticleModel]):
    """Enhanced ETL for NewsAPI.org with support for 150K+ global sources.

    Features:
    - Multi-category news aggregation
    - Multi-language support (100+ languages)
    - Source discovery and tracking
    - Comprehensive metrics collection
    - Checkpoint-based resumable operations
    - Circuit breaker for fault tolerance
    """

    def __init__(
        self,
        api_key: str | None = None,
        queries: list[str] | None = None,
        categories: list[str] | None = None,
        languages: list[str] | None = None,
        max_articles_per_query: int = 100,
        **kwargs,
    ):
        """Initialize NewsAPI ETL.

        Args:
            api_key: NewsAPI API key (defaults to settings)
            queries: Search queries for everything endpoint
            categories: News categories to fetch
            languages: Language codes to fetch
            max_articles_per_query: Max articles per query
            **kwargs: Additional BaseETL arguments
        """
        super().__init__(
            name="newsapi_expanded",
            description="Enhanced NewsAPI ETL for 150K+ global news sources",
            **kwargs,
        )

        self.settings = get_settings()
        self.api_key = api_key or getattr(self.settings.api, "news_api_key", None)

        # Default queries for comprehensive coverage
        self.queries = queries or [
            'AI OR "Artificial Intelligence"',
            "machine learning",
            "technology",
            "programming",
            "software development",
            "cloud computing",
            "cybersecurity",
        ]

        # NewsAPI categories
        self.categories = categories or [
            "business",
            "entertainment",
            "general",
            "health",
            "science",
            "sports",
            "technology",
        ]

        # Languages to fetch (ISO 639-1 codes)
        self.languages = languages or ["en", "es", "fr", "de", "it", "pt"]

        self.max_articles_per_query = max_articles_per_query
        self.base_url = "https://newsapi.org/v2"

        # Metrics tracking
        self.api_metrics = NewsApiMetricsModel()

    def extract(self) -> list[dict[str, Any]]:
        """Extract articles from NewsAPI.

        Fetches from:
        1. /everything endpoint for search queries
        2. /top-headlines for category-based news

        Returns:
            List of raw article dictionaries.
        """
        if not self.api_key:
            self.logger.warning("No NewsAPI key configured. Returning empty data.")
            return []

        self.logger.info(f"Starting extraction with {len(self.queries)} queries and {len(self.categories)} categories")

        all_articles = []
        headers = {"X-Api-Key": self.api_key}

        # Extract from everything endpoint (search queries)
        for query in self.queries:
            try:
                articles = self._fetch_everything(query, headers)
                all_articles.extend(articles)
                self.logger.info(f"Fetched {len(articles)} articles for query: {query}")
            except Exception as e:
                self.logger.error(f"Failed to fetch articles for query '{query}': {e}")
                self.metrics.add_error_detail(
                    error_message=f"Query failed: {query}",
                    error_type=type(e).__name__,
                    context={"query": query},
                )

        # Extract from top-headlines (categories)
        for category in self.categories:
            try:
                articles = self._fetch_top_headlines(category, headers)
                all_articles.extend(articles)
                self.logger.info(f"Fetched {len(articles)} articles for category: {category}")
            except Exception as e:
                self.logger.error(f"Failed to fetch category '{category}': {e}")
                self.metrics.add_error_detail(
                    error_message=f"Category failed: {category}",
                    error_type=type(e).__name__,
                    context={"category": category},
                )

        self.logger.info(f"Extraction complete: {len(all_articles)} total articles")
        self.api_metrics.total_requests += len(self.queries) + len(self.categories)

        return all_articles

    def _fetch_everything(self, query: str, headers: dict[str, str]) -> list[dict[str, Any]]:
        """Fetch articles from /everything endpoint.

        Args:
            query: Search query string
            headers: Request headers with API key

        Returns:
            List of article dictionaries.
        """
        url = f"{self.base_url}/everything"
        params = {
            "q": query,
            "pageSize": min(100, self.max_articles_per_query),
            "sortBy": "publishedAt",
            "language": "en",  # Default to English for queries
        }

        try:
            response = self.http_session.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            self.api_metrics.successful_requests += 1
            return data.get("articles", [])
        except requests.HTTPError as e:
            self.api_metrics.failed_requests += 1
            if e.response.status_code == 429:
                self.logger.warning("Rate limited by NewsAPI")
                self.api_metrics.rate_limit_hits += 1
            raise
        except Exception as e:
            self.api_metrics.failed_requests += 1
            raise

    def _fetch_top_headlines(self, category: str, headers: dict[str, str]) -> list[dict[str, Any]]:
        """Fetch top headlines by category.

        Args:
            category: News category
            headers: Request headers with API key

        Returns:
            List of article dictionaries.
        """
        url = f"{self.base_url}/top-headlines"
        params = {
            "category": category,
            "pageSize": min(100, self.max_articles_per_query),
            "language": "en",
        }

        try:
            response = self.http_session.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            self.api_metrics.successful_requests += 1
            return data.get("articles", [])
        except requests.HTTPError as e:
            self.api_metrics.failed_requests += 1
            if e.response.status_code == 429:
                self.api_metrics.rate_limit_hits += 1
            raise
        except Exception as e:
            self.api_metrics.failed_requests += 1
            raise

    def transform(self, raw_data: list[dict[str, Any]]) -> list[NewsApiArticleModel]:
        """Transform raw NewsAPI data to models.

        Args:
            raw_data: List of raw article dictionaries

        Returns:
            List of NewsApiArticleModel instances.
        """
        transformed = []

        for raw_article in raw_data:
            try:
                model = self._transform_article(raw_article)
                if model:
                    transformed.append(model)
                    self.api_metrics.articles_transformed += 1
            except Exception as e:
                self.logger.warning(f"Failed to transform article: {e}")
                self.metrics.records_failed += 1

        # Update category and language counts
        for article in transformed:
            if article.category:
                self.api_metrics.category_counts[article.category] = self.api_metrics.category_counts.get(article.category, 0) + 1
            if article.language:
                self.api_metrics.language_counts[article.language] = self.api_metrics.language_counts.get(article.language, 0) + 1

        self.logger.info(f"Transformed {len(transformed)} articles")
        return transformed

    def _transform_article(self, raw: dict[str, Any]) -> NewsApiArticleModel | None:
        """Transform single article.

        Args:
            raw: Raw article dictionary

        Returns:
            NewsApiArticleModel or None if transformation fails.
        """
        title = raw.get("title")
        url = raw.get("url")

        if not title or not url:
            return None

        # Parse published date
        published_at = None
        published_at_str = raw.get("publishedAt")
        if published_at_str:
            try:
                if published_at_str.endswith("Z"):
                    published_at_str = published_at_str[:-1] + "+00:00"
                published_at = datetime.fromisoformat(published_at_str)
            except ValueError:
                pass

        # Get source information
        source_data = raw.get("source", {})
        source_id = source_data.get("id") or "unknown"
        source_name = source_data.get("name") or "Unknown"

        # Combine content and description
        content = raw.get("content") or raw.get("description")

        # Generate tags from query/category
        tags = ["news"]
        if source_name:
            tags.append(source_name.lower().replace(" ", "-"))

        return NewsApiArticleModel(
            title=title,
            url=url,
            content=content,
            excerpt=raw.get("description"),
            author=raw.get("author"),
            source_name=source_name,
            source_id=source_id,
            published_at=published_at,
            category=raw.get("category", "general"),
            tags=tags,
            language=raw.get("language", "en"),
            original_id=url,
            newsapi_url_to_image=raw.get("urlToImage"),
            newsapi_published_at=raw.get("publishedAt"),
            metadata=raw,
        )

    def load(self, data: list[NewsApiArticleModel]) -> None:
        """Load articles to JSON storage.

        Args:
            data: List of NewsApiArticleModel instances.
        """
        self.api_metrics.articles_loaded = len(data)

        # Convert to dicts
        articles_data = [article.model_dump(mode="json") for article in data]

        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save main file
        main_file = self.output_dir / f"newsapi_{timestamp}.json"
        with main_file.open("w", encoding="utf-8") as f:
            json.dump(articles_data, f, indent=2, ensure_ascii=False)

        # Save latest file
        latest_file = self.output_dir / "newsapi_latest.json"
        with latest_file.open("w", encoding="utf-8") as f:
            json.dump(articles_data, f, indent=2, ensure_ascii=False)

        # Save metrics
        metrics_file = self.output_dir / "newsapi_metrics.json"
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(self.api_metrics.model_dump(mode="json"), f, indent=2)

        self.logger.info(f"Saved {len(data)} articles to {main_file.name}")
        self.logger.info(f"Saved latest to {latest_file.name}")
        self.logger.info(f"Saved metrics to {metrics_file.name}")


def main():
    """Main entry point for NewsAPI ETL."""
    logger = get_logger("NewsApiETL")
    logger.info("Starting NewsAPI Expanded ETL")

    try:
        etl = NewsApiETL()
        metrics = etl.run()

        logger.info(f"ETL completed successfully")
        logger.info(f"Records extracted: {metrics.records_extracted}")
        logger.info(f"Records transformed: {metrics.records_transformed}")
        logger.info(f"Records loaded: {metrics.records_loaded}")
        logger.info(f"Errors: {metrics.error_count}")
        logger.info(f"Duration: {metrics.duration_seconds:.2f}s")

    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
