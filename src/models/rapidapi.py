"""Models for RapidAPI Marketplace data sources.

Part of Phase 1 ETL implementation for 40K+ API marketplace integration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from src.models.base import TimestampedModel


class ApiCategory(str, Enum):
    """RapidAPI API categories."""

    DATA = "Data"
    SPORTS = "Sports"
    MEDIA = "Media"
    WEATHER = "Weather"
    FINANCE = "Finance"
    TOOLS = "Tools"
    COMPUTER = "Computer"
    DEVELOPMENT = "Development"
    BUSINESS = "Business"
    SOCIAL = "Social"
    SHOPPING = "Shopping"
    TRAVEL = "Travel"
    TRANSPORTATION = "Transportation"
    ENTERTAINMENT = "Entertainment"
    SCIENCE = "Science"
    HEALTH = "Health"
    SECURITY = "Security"
    OTHER = "Other"


class RapidApiApiModel(TimestampedModel):
    """Model for a single API from RapidAPI Marketplace.

    Represents one of 40,000+ APIs available on RapidAPI.
    """

    # Core API information
    api_id: str = Field(description="RapidAPI API ID")
    name: str = Field(description="API name")
    description: str | None = Field(default=None, description="API description")
    url: str | None = Field(default=None, description="API landing page URL")

    # API metadata
    category: ApiCategory = Field(description="Primary API category")
    subcategories: list[str] = Field(default_factory=list, description="Additional subcategories")

    # Pricing and models
    is_free: bool = Field(default=False, description="Whether API has free tier")
    pricing_model: str | None = Field(default=None, description="Pricing model (freemium, paid, etc.)")
    price_range: str | None = Field(default=None, description="Price range if applicable")

    # Popularity and quality metrics
    popularity_score: float | None = Field(default=None, ge=0, le=100, description="API popularity score")
    rating: float | None = Field(default=None, ge=0, le=5, description="User rating (0-5)")
    review_count: int = Field(default=0, ge=0, description="Number of reviews")

    # Usage metrics
    call_count: int | None = Field(default=None, ge=0, description="Number of API calls")
    latency_ms: float | None = Field(default=None, ge=0, description="Average latency")

    # Developer info
    developer_name: str | None = Field(default=None, description="API developer/provider name")
    developer_website: str | None = Field(default=None, description="Developer website URL")

    # Technical specifications
    api_type: str | None = Field(default=None, description="API type (REST, GraphQL, etc.)")
    documentation_url: str | None = Field(default=None, description="Documentation URL")
    supports_https: bool = Field(default=True, description="Whether API supports HTTPS")
    requires_auth: bool = Field(default=True, description="Whether API requires authentication")

    # Tags and keywords
    tags: list[str] = Field(default_factory=list, description="API tags for search/discovery")
    keywords: list[str] = Field(default_factory=list, description="Search keywords")

    # Status and availability
    is_active: bool = Field(default=True, description="Whether API is currently active")
    last_updated: datetime | None = Field(default=None, description="Last API update timestamp")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Full raw API response")

    @property
    def tier(self) -> str:
        """Get API pricing tier.

        Returns:
            Pricing tier as string.
        """
        if self.is_free and self.price_range is None:
            return "Free"
        elif self.is_free and self.price_range:
            return "Freemium"
        else:
            return "Paid"

    @field_validator("rating", mode="before")
    @classmethod
    def validate_rating(cls, v: Any) -> float | None:
        """Validate rating is within 0-5 range.

        Args:
            v: Rating value to validate.

        Returns:
            Validated rating or None.
        """
        if v is None:
            return None
        try:
            rating = float(v)
            return max(0.0, min(5.0, rating))
        except (ValueError, TypeError):
            return None


class RapidApiCollectionModel(TimestampedModel):
    """Model for RapidAPI API collections.

    Collections are curated groups of related APIs.
    """

    collection_id: str = Field(description="Collection ID")
    name: str = Field(description="Collection name")
    description: str | None = Field(default=None, description="Collection description")

    # Collection metadata
    category: ApiCategory | None = Field(default=None, description="Collection category")
    api_count: int = Field(default=0, ge=0, description="Number of APIs in collection")
    featured_apis: list[str] = Field(default_factory=list, description="Featured API IDs")

    # Popularity
    popularity_score: float | None = Field(default=None, ge=0, le=100, description="Collection popularity")

    # URLs
    url: str | None = Field(default=None, description="Collection URL")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional collection data")


class RapidApiMetricsModel(TimestampedModel):
    """Model for RapidAPI usage and discovery metrics."""

    # Discovery metrics
    total_apis_discovered: int = Field(default=0, description="Total APIs discovered")
    new_apis_this_run: int = Field(default=0, description="New APIs discovered this run")
    updated_apis_this_run: int = Field(default=0, description="Existing APIs updated")

    # Category breakdown
    category_distribution: dict[str, int] = Field(default_factory=dict, description="APIs by category")
    tier_distribution: dict[str, int] = Field(default_factory=dict, description="APIs by pricing tier")

    # Quality metrics
    avg_api_rating: float | None = Field(default=None, description="Average API rating")
    highly_rated_apis: int = Field(default=0, description="APIs with rating >= 4.0")
    free_apis: int = Field(default=0, description="Number of free APIs")

    # Collection metrics
    collections_discovered: int = Field(default=0, description="Collections discovered")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
