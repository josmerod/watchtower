"""Giveaways models and canonical contracts for Watchtower."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class UnifiedGiveawayModel(BaseModel):
    """Canonical giveaway contract used by the dashboard.

    Fields are purposefully generic to unify multiple sources (games, education, software).
    """

    title: str = Field(description="Item title")
    url: HttpUrl = Field(description="Destination URL to claim/learn more")
    platform: str = Field(description="Platform or store offering the giveaway")
    category: str = Field(description="Domain category (e.g., games, education, software)")

    # Status/availability
    availability: str | None = Field(default=None, description="Availability status label")
    promotion_end: datetime | None = Field(default=None, description="When promotion ends, if any")
    is_active: bool = Field(default=True, description="Whether it can be claimed now")

    # Metadata (optional)
    fetched_at: datetime | None = Field(default=None, description="Fetch timestamp (UTC)")
    source: str | None = Field(default=None, description="Upstream source identifier")

    # Aliases and coercions from heterogeneous inputs
    @field_validator("url", mode="before")
    @classmethod
    def coerce_url(cls, v: Any) -> Any:
        # Accept 'link' as an alias
        if isinstance(v, str):
            return v
        return v

    @field_validator("platform", mode="before")
    @classmethod
    def coerce_platform(cls, v: Any, values: dict[str, Any]) -> Any:
        # Accept 'store' as an alias
        if v is None and isinstance(values, dict):
            store = values.get("store")
            if store:
                return store
        return v

    @field_validator("promotion_end", mode="before")
    @classmethod
    def parse_promotion_end(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                if v.endswith("Z"):
                    v = v[:-1] + "+00:00"
                return datetime.fromisoformat(v)
            except Exception:
                return None
        return None

    @field_validator("is_active", mode="before")
    @classmethod
    def compute_is_active(cls, v: Any, values: dict[str, Any]) -> bool:
        # If explicitly provided, respect it
        if isinstance(v, bool):
            return v
        # Else infer from promotion_end
        promotion_end = values.get("promotion_end")
        if isinstance(promotion_end, datetime):
            return promotion_end > datetime.utcnow()
        # Default to True
        return True
