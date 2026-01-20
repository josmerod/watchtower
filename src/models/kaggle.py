"""Models for Kaggle data sources.

Part of Phase 2 ETL implementation for data science platform aggregation.
Includes datasets, competitions, kernels, and user profiles.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class KaggleContentType(str, Enum):
    """Kaggle content types."""

    DATASET = "dataset"
    COMPETITION = "competition"
    KERNEL = "kernel"
    NOTEBOOK = "notebook"
    MODEL = "model"


class KaggleCompetitionStatus(str, Enum):
    """Competition status."""

    ACTIVE = "active"
    UPCOMING = "upcoming"
    COMPLETED = "completed"


class KaggleDatasetModel(TimestampedModel):
    """Model for a Kaggle dataset.

    Represents one of 100K+ datasets on Kaggle.
    """

    # Core dataset fields
    dataset_id: str = Field(description="Kaggle dataset ID")
    title: str = Field(description="Dataset title")
    subtitle: str | None = Field(default=None, description="Dataset subtitle")
    url: str = Field(description="Dataset URL")
    description: str | None = Field(default=None, description="Dataset description")

    # Creator
    creator_id: str | None = Field(default=None, description="Creator user ID")
    creator_name: str | None = Field(default=None, description="Creator username")

    # Usage metrics
    total_downloads: int = Field(default=0, ge=0, description="Total downloads")
    total_votes: int = Field(default=0, ge=0, description="Total upvotes")
    total_kernels: int = Field(default=0, ge=0, description="Number of kernels using this")
    total_views: int = Field(default=0, ge=0, description="Total views")

    # Size metrics
    size_bytes: int | None = Field(default=None, ge=0, description="Dataset size in bytes")
    file_count: int = Field(default=0, ge=0, description="Number of files")
    file_size_total: str | None = Field(default=None, description="Human-readable file size")

    # Usability rating
    usability_rating: float | None = Field(default=None, ge=0, le=10, description="Usability rating")

    # Tags and categories
    tags: list[str] = Field(default_factory=list, description="Dataset tags")
    categories: list[str] = Field(default_factory=list, description="Dataset categories")

    # License
    license_name: str | None = Field(default=None, description="License name")

    # Timestamps
    api_created_at: datetime | None = Field(default=None, description="Creation date from API")
    last_updated: datetime | None = Field(default=None, description="Last update date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional data")


class KaggleCompetitionModel(TimestampedModel):
    """Model for a Kaggle competition.

    Represents one of 500+ competitions on Kaggle.
    """

    # Core competition fields
    competition_id: str = Field(description="Kaggle competition ID")
    title: str = Field(description="Competition title")
    slug: str = Field(description="URL slug")
    url: str = Field(description="Competition URL")
    description: str | None = Field(default=None, description="Competition description")

    # Organization
    organization_id: str | None = Field(default=None, description="Organization ID")
    organization_name: str | None = Field(default=None, description="Organization name")

    # Status
    status: KaggleCompetitionStatus = Field(description="Competition status")
    enabled_date: datetime | None = Field(default=None, description="When competition started")

    # Prizes
    prize_amount: int | None = Field(default=None, ge=0, description="Prize amount in USD")
    prize_currency: str | None = Field(default=None, description="Prize currency")

    # Metrics
    total_teams: int = Field(default=0, ge=0, description="Number of teams")
    total_participants: int = Field(default=0, ge=0, description="Number of participants")
    total_submissions: int | None = Field(default=None, ge=0, description="Total submissions")

    # Timeline
    deadline: datetime | None = Field(default=None, description="Submission deadline")

    # Tags
    tags: list[str] = Field(default_factory=list, description="Competition tags")

    # Reward
    reward_quantity: int | None = Field(default=None, ge=0, description="Reward quantity")
    reward_type: str | None = Field(default=None, description="Reward type")

    # Timestamps
    api_created_at: datetime | None = Field(default=None, description="Creation date from API")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional data")


class KaggleMetricsModel(TimestampedModel):
    """Model for Kaggle ETL metrics."""

    # Discovery metrics
    total_datasets_discovered: int = Field(default=0, description="Total datasets discovered")
    total_competitions_discovered: int = Field(default=0, description="Total competitions discovered")

    # Category breakdown
    category_distribution: dict[str, int] = Field(default_factory=dict, description="Datasets by category")

    # Usage metrics
    total_downloads: int = Field(default=0, description="Total downloads across all datasets")
    total_views: int = Field(default=0, description="Total views across all items")

    # Competition metrics
    active_competitions: int = Field(default=0, description="Active competitions")
    total_prize_money: int = Field(default=0, description="Total prize money")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
