"""Models for NewsAPI.org data sources.

Part of Phase 1 ETL implementation for expanded news aggregation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from src.models.base import TimestampedModel


class NewsArticleSourceModel(TimestampedModel):
    """Model for a news source (publisher/outlet)."""

    source_id: str = Field(description="NewsAPI source ID")
    name: str = Field(description="Source name")
    description: str | None = Field(default=None, description="Source description")
    url: str | None = Field(default=None, description="Source homepage URL")
    category: str | None = Field(default=None, description="Source category (business, entertainment, etc.)")
    language: str | None = Field(default=None, description="Source language (ISO 639-1)")
    country: str | None = Field(default=None, description="Source country (ISO 3166-1 alpha-2)")

    sort_priority: int = Field(default=0, description="Sort priority (higher = more important)")
    is_active: bool = Field(default=True, description="Whether source is active")

    metadata: dict[str, Any] | None = Field(default=None, description="Additional source metadata")


class NewsApiArticleModel(TimestampedModel):
    """Enhanced model for NewsAPI articles.

    Supports all 150K+ global sources from NewsAPI.org.
    """

    # Core article fields
    title: str = Field(description="Article title")
    url: str = Field(description="Article URL")
    content: str | None = Field(default=None, description="Full article content or excerpt")
    excerpt: str | None = Field(default=None, description="Article summary/description")

    # Authorship and source
    author: str | None = Field(default=None, description="Article author(s)")
    source_name: str = Field(description="Source/publisher name")
    source_id: str = Field(description="NewsAPI source ID")

    # Publication metadata
    published_at: datetime | None = Field(default=None, description="Publication timestamp")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When article was scraped")

    # Classification
    category: str | None = Field(default=None, description="Article category")
    tags: list[str] = Field(default_factory=list, description="Article tags")
    language: str = Field(default="en", description="Article language code")

    # Identifiers and deduplication
    original_id: str = Field(description="Original unique identifier (typically URL)")
    duplicate_of: str | None = Field(default=None, description="ID of original article if duplicate")

    # NewsAPI-specific fields
    newsapi_url_to_image: str | None = Field(default=None, description="URL to article image")
    newsapi_published_at: str | None = Field(default=None, description="Original publishedAt string")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Full raw API response")

    @field_validator("url", "newsapi_url_to_image", mode="before")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Validate URL format.

        Args:
            v: URL string to validate.

        Returns:
            Validated URL or None.
        """
        if v and not v.startswith(("http://", "https://")):
            return None
        return v

    @property
    def image_url(self) -> str | None:
        """Get primary image URL.

        Returns:
            Image URL if available.
        """
        return self.newsapi_url_to_image

    @property
    def domain(self) -> str | None:
        """Extract domain from URL.

        Returns:
            Domain name or None.
        """
        if self.url:
            from urllib.parse import urlparse

            parsed = urlparse(self.url)
            return parsed.netloc
        return None


class NewsApiMetricsModel(TimestampedModel):
    """Model for NewsAPI usage metrics."""

    # Request metrics
    total_requests: int = Field(default=0, description="Total API requests made")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")

    # Article metrics
    articles_fetched: int = Field(default=0, description="Total articles fetched")
    articles_transformed: int = Field(default=0, description="Successfully transformed articles")
    articles_loaded: int = Field(default=0, description="Successfully loaded articles")

    # Source metrics
    sources_queried: int = Field(default=0, description="Number of unique sources queried")
    sources_with_articles: int = Field(default=0, description="Sources returning articles")

    # Category breakdown
    category_counts: dict[str, int] = Field(default_factory=dict, description="Article count by category")
    language_counts: dict[str, int] = Field(default_factory=dict, description="Article count by language")

    # Performance
    avg_response_time_ms: float | None = Field(default=None, description="Average API response time")
    rate_limit_hits: int = Field(default=0, description="Number of rate limit errors")

    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics metadata")
