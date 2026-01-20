"""Models for Package Registry data sources.

Part of Phase 1 ETL implementation for package registry analytics.
Includes: npm, PyPI, crates.io, RubyGems, NuGet, Go Packages.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class PackageRegistry(str, Enum):
    """Package registry types."""

    NPM = "npm"
    PYPI = "pypi"
    CRATES_IO = "crates_io"
    RUBYGEMS = "rubygems"
    NUGET = "nuget"
    GO = "go"


class PackageTrendDirection(str, Enum):
    """Package trend direction."""

    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


class PackageModel(TimestampedModel):
    """Model for a package from any registry.

    Supports multiple package registries with unified schema.
    """

    # Core package fields
    package_id: str = Field(description="Package unique ID")
    name: str = Field(description="Package name")
    registry: PackageRegistry = Field(description="Package registry")
    url: str | None = Field(default=None, description="Package URL")
    description: str | None = Field(default=None, description="Package description")
    readme: str | None = Field(default=None, description="Package README content")

    # Version information
    version: str | None = Field(default=None, description="Latest version")
    versions_count: int = Field(default=0, ge=0, description="Total number of versions")

    # Author and maintainer
    author_name: str | None = Field(default=None, description="Author name")
    author_email: str | None = Field(default=None, description="Author email")
    maintainers: list[str] = Field(default_factory=list, description="Maintainer usernames")

    # Publisher
    publisher_name: str | None = Field(default=None, description="Publisher/organization name")
    publisher_username: str | None = Field(default=None, description="Publisher username")

    # Statistics
    downloads_total: int = Field(default=0, ge=0, description="Total downloads")
    downloads_weekly: int | None = Field(default=None, ge=0, description="Downloads in last week")
    downloads_monthly: int | None = Field(default=None, ge=0, description="Downloads in last month")
    stars_count: int = Field(default=0, ge=0, description="GitHub stars (if available)")
    forks_count: int = Field(default=0, ge=0, description="GitHub forks (if available)")

    # Popularity and quality
    popularity_score: float | None = Field(default=None, ge=0, le=100, description="Popularity score")
    quality_score: float | None = Field(default=None, ge=0, le=100, description="Quality score")
    trend_direction: PackageTrendDirection = Field(default=PackageTrendDirection.UNKNOWN, description="Trend direction")

    # Dependencies
    dependencies_count: int = Field(default=0, ge=0, description="Number of dependencies")
    dev_dependencies_count: int = Field(default=0, ge=0, description="Number of dev dependencies")
    dependents_count: int | None = Field(default=None, ge=0, description="Number of packages depending on this")

    # Keywords and topics
    keywords: list[str] = Field(default_factory=list, description="Package keywords")
    topics: list[str] = Field(default_factory=list, description="GitHub topics (if available)")

    # Programming language
    language: str | None = Field(default=None, description="Primary programming language")

    # License
    license: str | None = Field(default=None, description="Package license")

    # Repository
    repository_url: str | None = Field(default=None, description="GitHub repository URL")
    repository_stars: int | None = Field(default=None, ge=0, description="Repository stars")
    repository_forks: int | None = Field(default=None, ge=0, description="Repository forks")

    # Homepage
    homepage_url: str | None = Field(default=None, description="Package homepage URL")

    # Creation and update
    created_at: datetime | None = Field(default=None, description="Package creation date")
    updated_at: datetime | None = Field(default=None, description="Last update date")
    published_at: datetime | None = Field(default=None, description="Latest version publish date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Size metrics
    size_bytes: int | None = Field(default=None, ge=0, description="Package size in bytes")
    install_size_bytes: int | None = Field(default=None, ge=0, description="Install size in bytes")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Registry-specific data")

    @property
    def is_popular(self) -> bool:
        """Check if package is popular.

        Returns:
            True if package has >1000 weekly downloads.
        """
        return self.downloads_weekly and self.downloads_weekly > 1000

    @property
    def is_trending(self) -> bool:
        """Check if package is trending.

        Returns:
            True if package is rising.
        """
        return self.trend_direction == PackageTrendDirection.RISING


class PackageMetricsModel(TimestampedModel):
    """Model for package registry ETL metrics."""

    # Discovery metrics
    total_packages_discovered: int = Field(default=0, description="Total packages discovered")
    new_packages_this_run: int = Field(default=0, description="New packages this run")

    # Registry breakdown
    registry_distribution: dict[str, int] = Field(default_factory=dict, description="Packages by registry")
    language_distribution: dict[str, int] = Field(default_factory=dict, description="Packages by language")

    # Download metrics
    total_downloads: int = Field(default=0, description="Total downloads across all packages")
    avg_downloads_weekly: float | None = Field(default=None, description="Average weekly downloads")

    # Quality metrics
    popular_packages: int = Field(default=0, description="Packages with >1000 weekly downloads")
    trending_packages: int = Field(default=0, description="Trending packages")

    # Dependency metrics
    avg_dependencies: float | None = Field(default=None, description="Average dependencies per package")
    total_dependents: int = Field(default=0, description="Total dependents across all packages")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
