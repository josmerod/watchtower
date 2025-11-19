"""Pydantic models for analytics and trend analysis.

This module provides data models for:
- Trend indicators and analysis results
- Trend badges and UI display information
- Analytics metrics and confidence intervals
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, confloat, constr


class TrendDirection(str, Enum):
    """Enumeration of possible trend directions."""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    UNKNOWN = "unknown"


class TrendIndicator(BaseModel):
    """Model for individual trend indicators with metadata.

    Represents a single trend analysis result with direction,
    percentage change, and confidence metrics.
    """
    # Core trend data
    trend_direction: TrendDirection = Field(
        ...,
        description="Direction of the trend (rising/falling/stable)"
    )
    percentage_change: confloat(ge=-100.0, le=1000.0) = Field(
        ...,
        description="Percentage change from previous period"
    )
    confidence_score: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Confidence in trend detection (0-1)"
    )

    # Trend metadata
    item_id: str = Field(..., description="Unique identifier for the trended item")
    item_type: constr(min_length=1, max_length=50) = Field(
        ...,
        description="Type of item (category, keyword, source, etc.)"
    )
    item_name: constr(min_length=1, max_length=200) = Field(
        ...,
        description="Display name of the trending item"
    )

    # Historical data for context
    previous_value: float = Field(..., description="Value in previous period")
    current_value: float = Field(..., description="Value in current period")

    # Time and analysis context
    analysis_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the trend was calculated"
    )
    window_days: int = Field(
        default=7,
        description="Number of days in the analysis window"
    )

    # Additional metadata
    category: Optional[str] = Field(None, description="Category of the trended item")
    source: Optional[str] = Field(None, description="Data source for trend calculation")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional trend-specific metadata"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True


class TrendAnalysis(BaseModel):
    """Model for comprehensive trend analysis results.

    Contains aggregate trend data, confidence intervals,
    and statistical metrics for trend analysis.
    """
    # Analysis metadata
    analysis_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the analysis was performed"
    )
    window_days: int = Field(
        default=7,
        description="Analysis window in days"
    )
    total_items_analyzed: int = Field(
        ...,
        description="Total number of items included in analysis"
    )

    # Trend indicators
    trending_items: List[TrendIndicator] = Field(
        ...,
        description="List of all trend indicators"
    )

    # Aggregate statistics
    rising_trends: int = Field(
        ...,
        description="Count of rising trends"
    )
    falling_trends: int = Field(
        ...,
        description="Count of falling trends"
    )
    stable_trends: int = Field(
        ...,
        description="Count of stable trends"
    )

    # Quality metrics
    average_confidence: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Average confidence score across all trends"
    )
    significant_trends: int = Field(
        ...,
        description="Number of trends with confidence > 0.7"
    )

    # Analysis parameters
    threshold_percentage: confloat(ge=0.0, le=100.0) = Field(
        default=30.0,
        description="Minimum percentage change for trend detection"
    )
    min_data_points: int = Field(
        default=3,
        description="Minimum data points required for trend analysis"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TrendBadge(BaseModel):
    """Model for trend badge display information.

    Contains UI-specific data for displaying trend badges
    in dashboard components.
    """
    # Badge content
    display_text: constr(min_length=1, max_length=50) = Field(
        ...,
        description="Text displayed on the badge"
    )
    emoji: str = Field(
        default="📈",
        description="Emoji or icon for the badge"
    )

    # Badge styling
    color_scheme: constr(min_length=1, max_length=20) = Field(
        default="info",
        description="Bootstrap color scheme for the badge"
    )
    tooltip: Optional[constr(max_length=200)] = Field(
        None,
        description="Tooltip text displayed on hover"
    )

    # Trend data
    percentage_change: confloat(ge=-100.0, le=1000.0) = Field(
        ...,
        description="Percentage change to display"
    )
    is_trending: bool = Field(
        ...,
        description="Whether this item meets trending criteria"
    )

    # Additional UI context
    confidence_display: Optional[str] = Field(
        None,
        description="Formatted confidence score for display"
    )
    time_period: str = Field(
        default="this week",
        description="Time period description for the trend"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class TrendFilter(BaseModel):
    """Model for trend filtering configuration.

    Contains parameters for filtering content based on trend criteria.
    """
    # Filter criteria
    show_trending_only: bool = Field(
        default=False,
        description="Whether to show only trending items"
    )
    min_percentage_change: confloat(ge=-100.0, le=1000.0) = Field(
        default=0.0,
        description="Minimum percentage change to include"
    )
    min_confidence: confloat(ge=0.0, le=1.0) = Field(
        default=0.0,
        description="Minimum confidence score to include"
    )

    # Trend direction filters
    include_rising: bool = Field(
        default=True,
        description="Include rising trends"
    )
    include_falling: bool = Field(
        default=True,
        description="Include falling trends"
    )
    include_stable: bool = Field(
        default=True,
        description="Include stable trends"
    )

    # Category filters
    allowed_categories: List[str] = Field(
        default_factory=list,
        description="List of categories to include (empty = all)"
    )
    blocked_categories: List[str] = Field(
        default_factory=list,
        description="List of categories to exclude"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


# Convenience type aliases
TrendIndicators = List[TrendIndicator]
TrendBadges = List[TrendBadge]