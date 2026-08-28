"""Pydantic models for the Watchtower API."""

from typing import Any

from pydantic import BaseModel, Field


class UnifiedItem(BaseModel):
    """Unified model for news and knowledge items."""

    title: str = Field(..., description="Title of the item")
    url: str | None = Field(None, description="URL of the item")  # Using str to be lenient with faulty URLs
    source: str = Field(..., description="Source name")
    published_at: str | None = Field(None, description="Publication date (ISO 8601 or formatted string)")
    category: str | None = Field(None, description="Category of the item")

    # Validation/Cleanup is handled by the data loader transforming raw dicts into this model
    # We allow extra fields to pass through if needed, but for now we stick to the core ones

    model_config = {"extra": "ignore"}


class RadarItem(BaseModel):
    """Single entry of the merged technology-radar feed."""

    title: str = Field(..., description="Article/release title")
    link: str | None = Field(None, description="Article URL, when the source provides one")
    source: str = Field(..., description="Stable radar source key (e.g. 'google_ai')")
    published: str = Field("", description="Publication date (ISO 8601 or formatted string; empty when unknown)")
    category: str = Field(..., description="Radar category (e.g. 'AI', 'Cloud', 'Self-Hosting')")


class MarketsResponse(BaseModel):
    """Envelope for GET /api/v1/markets."""

    generated_at: str | None = Field(None, description="Timestamp of the snapshot (from item 'fetched_at', falling back to file mtime)")
    count: int = Field(..., description="Number of items returned (after the limit)")
    items: list[dict[str, Any]] = Field(..., description="Coin quotes as stored by the CoinGecko ETL")


class RadarResponse(BaseModel):
    """Envelope for GET /api/v1/radar."""

    generated_at: str | None = Field(None, description="Newest source-file mtime (UTC ISO 8601)")
    count: int = Field(..., description="Number of items returned (after the limit)")
    items: list[RadarItem] = Field(..., description="Merged radar entries, newest first")
