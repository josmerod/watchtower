"""Models for Developer News & Tips Aggregator."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class NewsSourceType(str, Enum):
    """Types of news sources."""

    HACKERNEWS = "HackerNews"
    DEVTO = "Dev.to"
    NEWSAPI = "NewsAPI"
    REDDIT = "Reddit"
    OTHER = "Other"


class DeveloperNewsItem(BaseModel):
    """Model representing a single developer news item."""

    id: str = Field(..., description="Unique identifier for the news item")
    title: str = Field(..., description="Title of the news item")
    url: HttpUrl = Field(..., description="URL to the original content")
    source: NewsSourceType = Field(..., description="Source of the news")
    author: Optional[str] = Field(None, description="Author of the content")
    published_at: datetime = Field(..., description="Publication timestamp")
    
    # Intelligence fields
    summary: Optional[str] = Field(None, description="AI/Heuristic summary of the content")
    tags: List[str] = Field(default_factory=list, description="Extracted tags/categories")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance to user tech stack")
    trend_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Trend score (0-1)")
    
    # Metadata
    original_score: Optional[int] = Field(None, description="Score from original source (e.g., HN points)")
    comments_count: Optional[int] = Field(None, description="Number of comments")


class NewsTrend(BaseModel):
    """Model representing a detected trend in developer news."""

    keyword: str = Field(..., description="The trending keyword or topic")
    velocity: float = Field(..., description="Growth rate of the trend")
    volume: int = Field(..., description="Number of items matching this trend")
    related_items: List[str] = Field(default_factory=list, description="IDs of related news items")
    detected_at: datetime = Field(default_factory=datetime.now, description="When the trend was detected")
