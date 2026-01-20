"""Models for Dev.to (Developer blogs).

Part of Phase 3 ETL implementation for developer content aggregation.
Author: Phase 3 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class DevtoTag(str, Enum):
    """Popular Dev.to tags."""

    JAVASCRIPT = "javascript"
    PYTHON = "python"
    REACT = "react"
    WEBDEV = "webdev"
    TUTORIAL = "tutorial"
    BEGINNERS = "beginners"
    PROGRAMMING = "programming"
    CODING = "coding"
    DEVELOPMENT = "development"
    DISCUSSION = "discussion"


class DevtoArticleModel(TimestampedModel):
    """Model for a Dev.to article.

    Represents developer blog posts from Dev.to community.
    """

    # Core article fields
    article_id: int = Field(description="Dev.to article ID")
    title: str = Field(description="Article title")
    url: str = Field(description="Article URL")
    description: str | None = Field(default=None, description="Article description/excerpt")
    body_markdown: str | None = Field(default=None, description="Article body in markdown")

    # Author information
    author_id: int = Field(description="Author user ID")
    author_username: str = Field(description="Author username")
    author_name: str | None = Field(default=None, description="Author display name")
    author_url: str | None = Field(default=None, description="Author profile URL")
    author_image_url: str | None = Field(default=None, description="Author avatar URL")

    # Organization
    organization_id: int | None = Field(default=None, description="Organization ID")
    organization_name: str | None = Field(default=None, description="Organization name")
    organization_slug: str | None = Field(default=None, description="Organization slug")

    # Cover image
    cover_image_url: str | None = Field(default=None, description="Cover image URL")

    # Tags and classification
    tags: list[str] = Field(default_factory=list, description="Article tags")
    tag_list: list[str] = Field(default_factory=list, description="Tag list (alias)")

    # Metrics
    views_count: int = Field(default=0, ge=0, description="Number of views")
    reactions_count: int = Field(default=0, ge=0, description="Number of reactions")
    comments_count: int = Field(default=0, ge=0, description="Number of comments")
    positive_reactions_count: int = Field(default=0, ge=0, description="Positive reactions")

    # Reading time
    reading_time_minutes: int = Field(default=0, ge=0, description="Estimated reading time in minutes")

    # Publication status
    published: bool = Field(default=True, description="Whether article is published")
    published_at: datetime | None = Field(default=None, description="Publication date")

    # Timestamps
    last_comment_at: datetime | None = Field(default=None, description="Last comment date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier (ID)")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional API data")

    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate.

        Returns:
            Engagement ratio (reactions per 100 views).
        """
        if self.views_count == 0:
            return 0.0
        return (self.reactions_count / self.views_count) * 100

    @property
    def is_trending(self) -> bool:
        """Check if article is trending.

        Returns:
            True if high engagement and recent.
        """
        if not self.published_at:
            return False
        days_since_published = max(1, (datetime.utcnow() - self.published_at).days)
        return self.engagement_rate > 5 and days_since_published <= 7

    @property
    def is_highly_engaged(self) -> bool:
        """Check if highly engaged.

        Returns:
            True if reactions > 50 or comments > 20.
        """
        return self.reactions_count > 50 or self.comments_count > 20


class DevtoUserModel(TimestampedModel):
    """Model for a Dev.to user.

    Represents a developer/author on Dev.to.
    """

    # Core user fields
    user_id: int = Field(description="Dev.to user ID")
    username: str = Field(description="Username/handle")
    name: str | None = Field(default=None, description="Display name")
    summary: str | None = Field(default=None, description="User bio")
    url: str | None = Field(default=None, description="Profile URL")

    # Avatar
    profile_image_url: str | None = Field(default=None, description="Profile image URL")

    # Location
    location: str | None = Field(default=None, description="User location")

    # Education
    education: str | None = Field(default=None, description="Education background")

    # Work
    joined_at: datetime | None = Field(default=None, description="Registration date")

    # Metrics
    followers_count: int = Field(default=0, ge=0, description="Number of followers")
    following_count: int = Field(default=0, ge=0, description="Number following")

    # Timestamps
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier (ID)")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional API data")


class DevtoMetricsModel(TimestampedModel):
    """Model for Dev.to ETL metrics."""

    # API request metrics
    successful_requests: int = Field(default=0, description="Successful API requests")
    failed_requests: int = Field(default=0, description="Failed API requests")

    # Discovery metrics
    total_articles_discovered: int = Field(default=0, description="Total articles discovered")
    total_users_discovered: int = Field(default=0, description="Total users discovered")
    new_articles_this_run: int = Field(default=0, description="New articles this run")

    # Tag distribution
    tag_distribution: dict[str, int] = Field(default_factory=dict, description="Articles by tag")

    # Engagement metrics
    total_views: int = Field(default=0, description="Total views across all articles")
    total_reactions: int = Field(default=0, description="Total reactions")
    total_comments: int = Field(default=0, description="Total comments")

    # Reading metrics
    avg_reading_time: float | None = Field(default=None, description="Average reading time")
    total_reading_time_minutes: int = Field(default=0, description="Total reading time")

    # Author metrics
    active_authors: int = Field(default=0, description="Authors with articles")
    total_followers: int = Field(default=0, description="Total followers across authors")

    # Trending metrics
    trending_articles: int = Field(default=0, description="Trending articles")
    highly_engaged_articles: int = Field(default=0, description="Highly engaged articles")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
