"""Models for Medium (Tech publications).

Part of Phase 3 ETL implementation for tech publication aggregation.
Author: Phase 3 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class MediumPublicationType(str, Enum):
    """Medium publication types."""

    TECH = "technology"
    DATA_SCIENCE = "data-science"
    AI = "artificial-intelligence"
    PROGRAMMING = "programming"
    STARTUP = "startup"
    BUSINESS = "business"
    SCIENCE = "science"


class MediumArticleModel(TimestampedModel):
    """Model for a Medium article.

    Represents articles from Medium publications and blogs.
    """

    # Core article fields
    article_id: str = Field(description="Medium article ID")
    title: str = Field(description="Article title")
    url: str = Field(description="Article URL")
    subtitle: str | None = Field(default=None, description="Article subtitle")
    excerpt: str | None = Field(default=None, description="Article excerpt")

    # Author information
    author_id: str = Field(description="Author ID")
    author_name: str = Field(description="Author name")
    author_username: str | None = Field(default=None, description="Author username")
    author_url: str | None = Field(default=None, description="Author profile URL")

    # Publication
    publication_id: str | None = Field(default=None, description="Publication ID")
    publication_name: str | None = Field(default=None, description="Publication name")
    publication_url: str | None = Field(default=None, description="Publication URL")

    # Content metrics
    claps_count: int = Field(default=0, ge=0, description="Number of claps")
    responses_count: int = Field(default=0, ge=0, description="Number of responses/comments")
    reading_time_minutes: int = Field(default=0, ge=0, description="Estimated reading time")

    # Additional metadata
    image_url: str | None = Field(default=None, description="Article cover image")
    tags: list[str] = Field(default_factory=list, description="Article tags")
    topics: list[str] = Field(default_factory=list, description="Article topics")

    # Publication status
    published_at: datetime | None = Field(default=None, description="Publication date")
    updated_at: datetime | None = Field(default=None, description="Last update date")
    first_published_at: datetime | None = Field(default=None, description="First publication date")

    # Status
    status: str | None = Field(default=None, description="Article status")
    is_premium: bool = Field(default=False, description="Whether premium content")

    # SEO
    slug: str | None = Field(default=None, description="URL slug")

    # Timestamps
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional API data")

    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate.

        Returns:
            Engagement ratio (claps per estimated view).
        """
        # Medium doesn't expose view count publicly
        # Use claps as proxy
        return float(self.claps_count)

    @property
    def is_trending(self) -> bool:
        """Check if article is trending.

        Returns:
            True if high clap count and recent.
        """
        if not self.published_at:
            return False
        days_since_published = max(1, (datetime.utcnow() - self.published_at).days)
        return self.claps_count > 100 and days_since_published <= 7

    @property
    def is_viral(self) -> bool:
        """Check if article went viral.

        Returns:
            True if claps > 1000.
        """
        return self.claps_count > 1000


class MediumPublicationModel(TimestampedModel):
    """Model for a Medium publication.

    Represents a Medium publication (e.g., Towards Data Science).
    """

    # Core publication fields
    publication_id: str = Field(description="Publication ID")
    name: str = Field(description="Publication name")
    slug: str = Field(description="URL slug")
    url: str = Field(description="Publication URL")
    description: str | None = Field(default=None, description="Publication description")

    # Branding
    image_url: str | None = Field(default=None, description="Publication logo")

    # Metrics
    followers_count: int = Field(default=0, ge=0, description="Number of followers")

    # Metadata
    domain: str | None = Field(default=None, description="Custom domain")

    # Timestamps
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional API data")


class MediumAuthorModel(TimestampedModel):
    """Model for a Medium author.

    Represents a writer/author on Medium.
    """

    # Core author fields
    author_id: str = Field(description="Author ID")
    name: str = Field(description="Author name")
    username: str | None = Field(default=None, description="Username/handle")
    url: str | None = Field(default=None, description="Profile URL")
    bio: str | None = Field(default=None, description="Author bio")

    # Avatar
    image_url: str | None = Field(default=None, description="Profile image")

    # Location
    location: str | None = Field(default=None, description="Author location")

    # Metrics
    followers_count: int = Field(default=0, ge=0, description="Number of followers")
    following_count: int = Field(default=0, ge=0, description="Number following")

    # Social
    twitter_username: str | None = Field(default=None, description="Twitter handle")
    facebook_url: str | None = Field(default=None, description="Facebook profile")

    # Timestamps
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional API data")


class MediumMetricsModel(TimestampedModel):
    """Model for Medium ETL metrics."""

    # API request metrics
    successful_requests: int = Field(default=0, description="Successful API requests")
    failed_requests: int = Field(default=0, description="Failed API requests")

    # Discovery metrics
    total_articles_discovered: int = Field(default=0, description="Total articles discovered")
    total_authors_discovered: int = Field(default=0, description="Total authors discovered")
    total_publications_discovered: int = Field(default=0, description="Total publications discovered")
    new_articles_this_run: int = Field(default=0, description="New articles this run")

    # Tag/topic distribution
    tag_distribution: dict[str, int] = Field(default_factory=dict, description="Articles by tag")
    topic_distribution: dict[str, int] = Field(default_factory=dict, description="Articles by topic")

    # Engagement metrics
    total_claps: int = Field(default=0, description="Total claps across all articles")
    total_responses: int = Field(default=0, description="Total responses/comments")

    # Reading metrics
    avg_reading_time: float | None = Field(default=None, description="Average reading time")

    # Content quality
    premium_articles: int = Field(default=0, description="Premium articles")
    viral_articles: int = Field(default=0, description="Viral articles (>1000 claps)")

    # Author metrics
    active_authors: int = Field(default=0, description="Authors with articles")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
