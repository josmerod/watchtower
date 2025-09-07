"""Game-related models for Watchtower."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel


class GamePlatform(str, Enum):
    """Supported game platforms."""

    PC = "pc"
    XBOX = "xbox"
    PLAYSTATION = "playstation"
    NINTENDO = "nintendo"
    MOBILE = "mobile"
    VR = "vr"


class GameGenre(str, Enum):
    """Game genres."""

    ACTION = "action"
    ADVENTURE = "adventure"
    RPG = "rpg"
    SIMULATION = "simulation"
    STRATEGY = "strategy"
    SPORTS = "sports"
    RACING = "racing"
    SHOOTER = "shooter"
    PUZZLE = "puzzle"
    PLATFORMER = "platformer"
    FIGHTING = "fighting"
    HORROR = "horror"
    INDIE = "indie"


class PriceType(str, Enum):
    """Price type for game deals."""

    STANDARD = "standard"
    DISCOUNTED = "discounted"
    FREE = "free"
    BUNDLE = "bundle"



class GameBundleModel(TimestampedModel):
    """Model representing a game bundle deal."""

    bundle_name: str = Field(description="Bundle name")
    url: HttpUrl = Field(description="Bundle URL")
    store_name: str = Field(description="Store offering the bundle")

    # Price information
    current_price: float = Field(description="Current bundle price")
    original_total_price: Optional[float] = Field(
        default=None, description="Original total price of all games"
    )
    savings_percentage: Optional[int] = Field(
        default=None, description="Bundle savings percentage"
    )

    # Bundle content
    games: List[str] = Field(description="List of games in the bundle")
    games_count: int = Field(description="Number of games in bundle")

    # Bundle metadata
    is_limited_time: bool = Field(
        default=False, description="Whether this is a limited time offer"
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="Bundle expiration date"
    )

    # ETL metadata
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this was extracted"
    )


class GameGiveawayModel(TimestampedModel):
    """Model representing a free game giveaway."""

    title: str = Field(description="Game title")
    url: HttpUrl = Field(description="Giveaway URL")
    platform: str = Field(description="Platform offering the giveaway")

    # Giveaway information
    original_price: Optional[float] = Field(
        default=None, description="Original price of the game"
    )
    giveaway_type: str = Field(
        description="Type of giveaway (permanent, limited, etc.)"
    )

    # Time information
    starts_at: Optional[datetime] = Field(
        default=None, description="When giveaway starts"
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="When giveaway expires"
    )

    # Requirements
    requirements: List[str] = Field(
        default_factory=list, description="Requirements to claim"
    )

    # ETL metadata
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this was extracted"
    )

    @property
    def is_active(self) -> bool:
        """Check if giveaway is currently active."""
        now = datetime.utcnow()
        if self.expires_at and now > self.expires_at:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        return True

    @property
    def urgency_level(self) -> str:
        """Determine urgency level for claiming."""
        if not self.expires_at:
            return "low"

        now = datetime.utcnow()
        time_left = self.expires_at - now

        if time_left.days == 0:
            return "urgent"
        elif time_left.days <= 3:
            return "high"
        elif time_left.days <= 7:
            return "medium"
        else:
            return "low"
