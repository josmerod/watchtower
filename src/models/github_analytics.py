"""Models for GitHub Analytics data sources.

Part of Phase 1 ETL implementation for GitHub repositories analytics.
Includes: Trendshift.io, Ossinsight, LibHunt, BestOfJS, Python Package Explorer.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class TrendDirection(str, Enum):
    """Trend direction for repositories."""

    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


class GithubRepoModel(TimestampedModel):
    """Enhanced model for GitHub repository analytics data.

    Aggregates data from multiple GitHub analytics platforms.
    """

    # Core repository fields
    repo_id: str = Field(description="Repository unique ID")
    name: str = Field(description="Repository name")
    full_name: str = Field(description="Full repository name (owner/repo)")
    url: str = Field(description="Repository URL")
    description: str | None = Field(default=None, description="Repository description")

    # Owner information
    owner_id: str = Field(description="Repository owner ID")
    owner_name: str = Field(description="Repository owner name")
    owner_type: str = Field(description="Owner type (user, organization)")

    # Statistics
    stars_count: int = Field(default=0, ge=0, description="GitHub stars")
    forks_count: int = Field(default=0, ge=0, description="GitHub forks")
    watchers_count: int = Field(default=0, ge=0, description="GitHub watchers")
    open_issues_count: int = Field(default=0, ge=0, description="Open GitHub issues")

    # Language and topics
    primary_language: str | None = Field(default=None, description="Primary programming language")
    languages: dict[str, int] = Field(default_factory=dict, description="Language usage bytes")
    topics: list[str] = Field(default_factory=list, description="Repository topics")

    # Trending metrics
    trend_direction: TrendDirection = Field(default=TrendDirection.UNKNOWN, description="Trend direction")
    trend_score: float | None = Field(default=None, ge=0, le=100, description="Trend score")
    position: int | None = Field(default=None, ge=1, description="Trending position")
    daily_stars: int | None = Field(default=None, ge=0, description="Stars gained today")

    # Activity metrics
    commits_count: int | None = Field(default=None, ge=0, description="Total commits")
    contributors_count: int | None = Field(default=None, ge=0, description="Number of contributors")
    releases_count: int | None = Field(default=None, ge=0, description="Number of releases")
    last_commit_at: datetime | None = Field(default=None, description="Last commit timestamp")
    last_release_at: datetime | None = Field(default=None, description="Last release timestamp")

    # Creation and metadata
    created_at: datetime | None = Field(default=None, description="Repository creation date")
    updated_at: datetime | None = Field(default=None, description="Last update date")
    pushed_at: datetime | None = Field(default=None, description="Last push date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # License
    license_key: str | None = Field(default=None, description="License SPDX key")
    license_name: str | None = Field(default=None, description="License name")

    # Size metrics
    size: int | None = Field(default=None, ge=0, description="Repository size in KB")

    # Source platform
    data_source: str = Field(description="Data source platform (trendshift, ossinsight, etc.)")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional platform-specific data")

    @property
    def is_trending(self) -> bool:
        """Check if repository is trending.

        Returns:
            True if repository is trending.
        """
        return self.trend_direction == TrendDirection.RISING

    @property
    def age_days(self) -> int | None:
        """Calculate repository age in days.

        Returns:
            Age in days or None.
        """
        if self.created_at:
            delta = datetime.utcnow() - self.created_at
            return delta.days
        return None


class GithubAnalyticsMetricsModel(TimestampedModel):
    """Model for GitHub analytics ETL metrics."""

    # Discovery metrics
    total_repos_discovered: int = Field(default=0, description="Total repositories discovered")
    new_repos_this_run: int = Field(default=0, description="New repositories this run")
    trending_repos: int = Field(default=0, description="Number of trending repos")

    # Language breakdown
    language_distribution: dict[str, int] = Field(default_factory=dict, description="Repos by language")
    topic_distribution: dict[str, int] = Field(default_factory=dict, description="Repos by topic")

    # Statistics
    total_stars: int = Field(default=0, description="Total stars across all repos")
    total_forks: int = Field(default=0, description="Total forks across all repos")
    avg_stars: float | None = Field(default=None, description="Average stars per repo")

    # Platform source
    platform_counts: dict[str, int] = Field(default_factory=dict, description="Repos by data source platform")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
