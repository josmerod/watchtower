"""Models for Developer News & Tips Aggregator."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl

from src.models.base import AIEnhancedModel


class NewsSourceType(str, Enum):
    """Types of news sources."""

    HACKERNEWS = "HackerNews"
    DEVTO = "Dev.to"
    NEWSAPI = "NewsAPI"
    REDDIT = "Reddit"
    OTHER = "Other"


class DeveloperNewsItem(AIEnhancedModel):
    """Model representing a single developer news item."""

    id: str = Field(..., description="Unique identifier for the news item")
    title: str = Field(..., description="Title of the news item")
    url: HttpUrl = Field(..., description="URL to the original content")
    source: NewsSourceType = Field(..., description="Source of the news")
    author: str | None = Field(None, description="Author of the content")
    published_at: datetime = Field(..., description="Publication timestamp")

    # Intelligence fields
    summary: str | None = Field(None, description="AI/Heuristic summary of the content")
    tags: list[str] = Field(default_factory=list, description="Extracted tags/categories")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance to user tech stack")
    trend_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Trend score (0-1)")

    # Metadata
    original_score: int | None = Field(None, description="Score from original source (e.g., HN points)")
    comments_count: int | None = Field(None, description="Number of comments")


class NewsTrend(BaseModel):
    """Model representing a detected trend in developer news."""

    keyword: str = Field(..., description="The trending keyword or topic")
    velocity: float = Field(..., description="Growth rate of the trend")
    volume: int = Field(..., description="Number of items matching this trend")
    related_items: list[str] = Field(default_factory=list, description="IDs of related news items")
    detected_at: datetime = Field(default_factory=datetime.now, description="When the trend was detected")
