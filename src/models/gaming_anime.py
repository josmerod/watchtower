"""Models for GamerPower and AniList.

Part of Phase 2 ETL implementation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class GiveawayStatus(str, Enum):
    """Giveaway status types."""

    ACTIVE = "active"
    EXPIRED = "expired"
    UPCOMING = "upcoming"


class GamerPowerGiveawayModel(TimestampedModel):
    """Model for a GamerPower giveaway.

    Represents game giveaways from GamerPower.com.
    """

    # Core fields
    giveaway_id: str = Field(description="Giveaway ID")
    title: str = Field(description="Giveaway title")
    url: str = Field(description="Giveaway URL")
    description: str | None = Field(default=None, description="Giveaway description")

    # Platform
    platform: str = Field(description="Platform (PC, Xbox, PlayStation, Switch, etc.)")
    platform_type: str | None = Field(default=None, description="Platform type")

    # Status
    status: GiveawayStatus = Field(description="Giveaway status")

    # Value
    value_usd: float | None = Field(default=None, description="Estimated value in USD")
    value_str: str | None = Field(default=None, description="Human-readable value")

    # Metrics
    total_keys: int = Field(default=0, ge=0, description="Total number of keys/copies")
    available_keys: int = Field(default=0, ge=0, description="Available keys")

    # Dates
    start_date: datetime | None = Field(default=None, description="Start date")
    end_date: datetime | None = Field(default=None, description="End date")

    # Timestamps
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional data")


class AniListMediaType(str, Enum):
    """AniList media types."""

    ANIME = "anime"
    MANGA = "manga"


class AniListMediaModel(TimestampedModel):
    """Model for AniList anime/manga entry.

    Represents anime or manga from AniList.co.
    """

    # Core fields
    media_id: int = Field(description="AniList media ID")
    title_romaji: str = Field(description="Title in romaji")
    title_english: str | None = Field(default=None, description="English title")
    title_native: str | None = Field(default=None, description="Native (Japanese) title")
    url: str = Field(description="AniList URL")
    description: str | None = Field(default=None, description="Synopsis")

    # Type and format
    type: AniListMediaType = Field(description="Media type (anime/manga)")
    format: str | None = Field(default=None, description="Format (TV, OVA, Movie, etc.)")
    status: str | None = Field(default=None, description="Releasing/finished status")

    # Source and genre
    source: str | None = Field(default=None, description="Source material (manga, original, etc.)")
    genres: list[str] = Field(default_factory=list, description="Genres")
    tags: list[str] = Field(default_factory=list, description="Tags")

    # Studios
    studios: list[str] = Field(default_factory=list, description="Animation studios")

    # Metrics
    average_score: float | None = Field(default=None, ge=0, le=100, description="Average user score (out of 100)")
    mean_score: float | None = Field(default=None, ge=0, le=100, description="Mean score (out of 100)")
    popularity: int = Field(default=0, ge=0, description="Popularity ranking")
    favourites: int = Field(default=0, ge=0, description="Number of user favourites")

    # Episode/chapter counts
    episodes: int | None = Field(default=None, ge=0, description="Number of episodes")
    chapters: int | None = Field(default=None, ge=0, description="Number of chapters")
    volumes: int | None = Field(default=None, ge=0, description="Number of volumes")

    # Dates
    start_date: str | None = Field(default=None, description="Start date (FuzzyDate)")
    end_date: str | None = Field(default=None, description="End date (FuzzyDate)")

    # Season
    season: str | None = Field(default=None, description="Season (winter, spring, summer, fall)")
    season_year: int | None = Field(default=None, ge=2000, le=2100, description="Season year")

    # Cover image
    cover_image: str | None = Field(default=None, description="Cover image URL")
    banner_image: str | None = Field(default=None, description="Banner image URL")

    # Timestamps
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier (ID)")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional GraphQL data")

    @property
    def is_airing(self) -> bool:
        """Check if anime is currently airing.

        Returns:
            True if status is "releasing".
        """
        return self.status == "releasing"

    @property
    def is_highly_rated(self) -> bool:
        """Check if highly rated.

        Returns:
            True if score > 80.
        """
        return bool(self.average_score and self.average_score > 80)
