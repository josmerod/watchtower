"""Pydantic models for the recommendation system.

This module defines the data models used throughout the recommendation system,
including ActivityEvent for tracking user interactions and Recommendation
for storing generated recommendations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


class ActivityType(str, Enum):
    """Types of user activities that can be tracked."""

    CLICK = "click"
    VIEW = "view"
    SEARCH = "search"
    FILTER = "filter"
    FEEDBACK = "feedback"
    DISMISS = "dismiss"


class RecommendationType(str, Enum):
    """Types of recommendations that can be generated."""

    TOP_SOURCE = "top_source"
    TOP_CATEGORY = "top_category"
    SIMILAR_CONTENT = "similar_content"
    TRENDING = "trending"


class ActivityEvent(BaseModel):
    """Model for tracking a single user activity event."""

    user_id: str = Field(..., description="Unique identifier for the user")
    action: ActivityType = Field(..., description="Type of activity performed")
    content_id: str = Field(..., description="Identifier of the content interacted with")
    content_type: str = Field(..., description="Type of content (e.g., 'arxiv_paper', 'news_article')")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the activity occurred")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context about the activity")

    # Enhanced tracking metrics
    duration_seconds: float | None = Field(None, description="Time spent on content if applicable")
    source_category: str | None = Field(None, description="Category of the content source")
    title: str | None = Field(None, description="Title of the content for similarity matching")

    @validator('duration_seconds')
    def validate_duration(cls, v):
        """Validate duration is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Duration must be non-negative")
        return v


class Recommendation(BaseModel):
    """Model for a single content recommendation."""

    id: str = Field(..., description="Unique identifier for this recommendation")
    user_id: str = Field(..., description="User this recommendation is for")
    type: RecommendationType = Field(..., description="Type of recommendation")
    content_id: str = Field(..., description="Identifier of the recommended content")
    content_type: str = Field(..., description="Type of content recommended")
    title: str = Field(..., description="Display title of the recommendation")
    description: str = Field(..., description="Why this is recommended to the user")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this recommendation")
    generated_at: datetime = Field(default_factory=datetime.now, description="When this recommendation was generated")
    expires_at: datetime | None = Field(None, description="When this recommendation expires")

    # Metadata for different recommendation types
    metadata: dict[str, Any] = Field(default_factory=dict, description="Type-specific metadata")

    # User interaction tracking
    dismissed: bool = Field(default=False, description="Whether user has dismissed this recommendation")
    feedback: bool | None = Field(None, description="User feedback (True=helpful, False=not helpful)")
    feedback_timestamp: datetime | None = Field(None, description="When feedback was provided")

    @validator('expires_at')
    def validate_expiry(cls, v, values):
        """Validate expiry date is after generation date."""
        if v is not None and 'generated_at' in values:
            if v <= values['generated_at']:
                raise ValueError("Expiry date must be after generation date")
        return v


class UserRecommendations(BaseModel):
    """Container for all recommendations for a specific user."""

    user_id: str = Field(..., description="User these recommendations are for")
    generated_at: datetime = Field(default_factory=datetime.now, description="When recommendations were generated")
    recommendations: list[Recommendation] = Field(default_factory=list, description="List of recommendations")

    # Generation metadata
    activity_window_days: int = Field(default=30, description="Days of activity data used")
    total_activities_analyzed: int = Field(default=0, description="Number of activities analyzed")

    # Quality metrics
    avg_score: float = Field(default=0.0, description="Average confidence score")
    diversity_score: float = Field(default=0.0, description="Content diversity score")

    def add_recommendation(self, recommendation: Recommendation) -> None:
        """Add a recommendation and update metrics."""
        self.recommendations.append(recommendation)
        self._update_metrics()

    def _update_metrics(self) -> None:
        """Update recommendation quality metrics."""
        if not self.recommendations:
            self.avg_score = 0.0
            self.diversity_score = 0.0
            return

        # Calculate average confidence score
        self.avg_score = sum(r.score for r in self.recommendations) / len(self.recommendations)

        # Calculate content diversity (unique content types / total recommendations)
        unique_types = len(set(r.content_type for r in self.recommendations))
        self.diversity_score = unique_types / len(self.recommendations)

    def get_active_recommendations(self, max_age_days: int = 7) -> list[Recommendation]:
        """Get recommendations that are still valid and not dismissed."""
        now = datetime.now()
        cutoff_date = now - timedelta(days=max_age_days)

        return [
            r for r in self.recommendations
            if not r.dismissed
            and (r.expires_at is None or r.expires_at > now)
            and r.generated_at > cutoff_date
        ]


class UserActivityProfile(BaseModel):
    """Profile of user activity patterns and preferences."""

    user_id: str = Field(..., description="User this profile is for")
    last_updated: datetime = Field(default_factory=datetime.now, description="When profile was last updated")
    total_activities: int = Field(default=0, description="Total number of activities tracked")

    # Content preferences
    top_sources: list[str] = Field(default_factory=list, description="Most frequently accessed sources")
    top_categories: list[str] = Field(default_factory=list, description="Most engaged content categories")
    favorite_content_types: list[str] = Field(default_factory=list, description="Preferred content types")

    # Behavioral patterns
    avg_session_duration: float = Field(default=0.0, description="Average time spent per content item")
    peak_activity_hours: list[int] = Field(default_factory=list, description="Hours when user is most active")
    interaction_frequency: dict[ActivityType, int] = Field(default_factory=dict, description="Count of each activity type")

    # Content engagement metrics
    click_through_rate: float = Field(default=0.0, description="Rate of clicking on recommendations")
    feedback_ratio: float = Field(default=0.0, description="Ratio of helpful to not helpful feedback")
    dismissal_rate: float = Field(default=0.0, description="Rate of dismissing recommendations")

    def update_from_activities(self, activities: list[ActivityEvent]) -> None:
        """Update profile based on recent activity data."""
        if not activities:
            return

        self.last_updated = datetime.now()
        self.total_activities = len(activities)

        # Calculate top sources and categories
        source_counts = {}
        category_counts = {}
        content_type_counts = {}
        activity_counts = {}
        session_durations = []

        for activity in activities:
            # Count sources
            if activity.content_type:
                source_counts[activity.content_type] = source_counts.get(activity.content_type, 0) + 1

            # Count categories
            if activity.source_category:
                category_counts[activity.source_category] = category_counts.get(activity.source_category, 0) + 1

            # Count content types
            if activity.content_type:
                content_type_counts[activity.content_type] = content_type_counts.get(activity.content_type, 0) + 1

            # Count activity types
            activity_counts[activity.action] = activity_counts.get(activity.action, 0) + 1

            # Track session durations
            if activity.duration_seconds:
                session_durations.append(activity.duration_seconds)

        # Update top sources (top 5)
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        self.top_sources = [source for source, _ in sorted_sources[:5]]

        # Update top categories (top 3)
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        self.top_categories = [category for category, _ in sorted_categories[:3]]

        # Update favorite content types
        sorted_types = sorted(content_type_counts.items(), key=lambda x: x[1], reverse=True)
        self.favorite_content_types = [content_type for content_type, _ in sorted_types[:5]]

        # Update interaction frequency
        self.interaction_frequency = {ActivityType(k): v for k, v in activity_counts.items()}

        # Calculate average session duration
        self.avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0.0
