"""Startup Intelligence data models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from src.models.base import AIEnhancedModel, TimestampedModel


class StartupNewsItem(TimestampedModel, AIEnhancedModel):
    """Model for startup news and product launches."""

    title: str = Field(description="Title of the article or product")
    url: str = Field(description="URL to the content")
    source: Literal["techcrunch", "product_hunt"] = Field(description="Source of the data")
    summary: str | None = Field(default=None, description="Summary or description")
    tags: list[str] = Field(default_factory=list, description="Tags or categories")
    published_at: datetime = Field(description="Publication timestamp")
    author: str | None = Field(default=None, description="Author or maker")

    # Engagement metrics
    votes: int = Field(default=0, description="Upvotes (for Product Hunt)")
    comments: int = Field(default=0, description="Comment count")

    # Metadata
    thumbnail_url: str | None = Field(default=None, description="Thumbnail image URL")
    funding_mentioned: bool = Field(default=False, description="Whether funding is mentioned")
    company_mentioned: list[str] = Field(default_factory=list, description="Companies mentioned")

    # For Product Hunt
    tagline: str | None = Field(default=None, description="Product tagline")

    class Config:
        """Pydantic config."""

        use_enum_values = True
