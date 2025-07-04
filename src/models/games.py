"""Game-related models for Watchtower."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, HttpUrl

from models.base import TimestampedModel


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


class AllKeyShopGameModel(TimestampedModel):
    """Model representing a game deal from AllKeyShop."""

    title: str = Field(description="Game title")
    url: HttpUrl = Field(description="Game store URL")
    image_url: HttpUrl | None = Field(default=None, description="Game cover image URL")

    # Price information
    current_price: float | None = Field(default=None, description="Current price in EUR")
    original_price: float | None = Field(default=None, description="Original price in EUR")
    discount_percentage: int | None = Field(default=None, description="Discount percentage")

    # Deal information
    deal_score: int | None = Field(default=None, description="AllKeyShop deal score")
    store_name: str | None = Field(default=None, description="Store offering the deal")
    store_rating: float | None = Field(default=None, description="Store rating")

    # Game information
    platform: GamePlatform = Field(default=GamePlatform.PC, description="Game platform")
    genre: GameGenre | None = Field(default=None, description="Game genre")
    rating: float | None = Field(default=None, description="Game rating")
    metacritic_score: int | None = Field(default=None, description="Metacritic score")

    # Release information
    release_date: datetime | None = Field(default=None, description="Game release date")

    # Additional metadata
    is_dlc: bool = Field(default=False, description="Whether this is DLC")
    is_early_access: bool = Field(default=False, description="Whether this is early access")
    is_preorder: bool = Field(default=False, description="Whether this is a preorder")

    # Sorting criteria used
    sort_criteria: str = Field(description="Sorting criteria used for extraction")
    page_number: int = Field(description="Page number from which this was extracted")

    # ETL metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="When this was extracted")

    @property
    def savings_amount(self) -> float | None:
        """Calculate savings amount in EUR."""
        if self.original_price and self.current_price:
            return self.original_price - self.current_price
        return None

    @property
    def is_good_deal(self) -> bool:
        """Determine if this is considered a good deal."""
        if self.deal_score and self.deal_score >= 80:
            return True
        return bool(self.discount_percentage and self.discount_percentage >= 50)

    @property
    def price_tier(self) -> str:
        """Categorize the game by price tier."""
        if not self.current_price:
            return "unknown"
        if self.current_price == 0:
            return "free"
        elif self.current_price <= 5:
            return "budget"
        elif self.current_price <= 20:
            return "mid-tier"
        elif self.current_price <= 60:
            return "premium"
        else:
            return "luxury"


class GameBundleModel(TimestampedModel):
    """Model representing a game bundle deal."""

    bundle_name: str = Field(description="Bundle name")
    url: HttpUrl = Field(description="Bundle URL")
    store_name: str = Field(description="Store offering the bundle")

    # Price information
    current_price: float = Field(description="Current bundle price")
    original_total_price: float | None = Field(default=None, description="Original total price of all games")
    savings_percentage: int | None = Field(default=None, description="Bundle savings percentage")

    # Bundle content
    games: list[str] = Field(description="List of games in the bundle")
    games_count: int = Field(description="Number of games in bundle")

    # Bundle metadata
    is_limited_time: bool = Field(default=False, description="Whether this is a limited time offer")
    expires_at: datetime | None = Field(default=None, description="Bundle expiration date")

    # ETL metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="When this was extracted")


class GameGiveawayModel(TimestampedModel):
    """Model representing a free game giveaway."""

    title: str = Field(description="Game title")
    url: HttpUrl = Field(description="Giveaway URL")
    platform: str = Field(description="Platform offering the giveaway")

    # Giveaway information
    original_price: float | None = Field(default=None, description="Original price of the game")
    giveaway_type: str = Field(description="Type of giveaway (permanent, limited, etc.)")

    # Time information
    starts_at: datetime | None = Field(default=None, description="When giveaway starts")
    expires_at: datetime | None = Field(default=None, description="When giveaway expires")

    # Requirements
    requirements: list[str] = Field(default_factory=list, description="Requirements to claim")

    # ETL metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="When this was extracted")

    @property
    def is_active(self) -> bool:
        """Check if giveaway is currently active."""
        now = datetime.utcnow()
        if self.expires_at and now > self.expires_at:
            return False
        return not (self.starts_at and now < self.starts_at)

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
