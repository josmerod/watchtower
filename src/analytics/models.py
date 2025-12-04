from datetime import datetime

from pydantic import BaseModel, Field


class TrendIndicator(BaseModel):
    """Represents a specific trend metric for an item or category."""

    direction: str = Field(..., description="Trend direction: 'up', 'down', 'stable'")
    percentage_change: float = Field(..., description="Percentage change over the period")
    period_days: int = Field(default=7, description="Number of days in the analysis period")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of the trend")


class TrendBadge(BaseModel):
    """UI representation of a trend."""

    label: str = Field(..., description="Text to display on the badge (e.g., '🔥 Trending')")
    color: str = Field(
        default="danger",
        description="Bootstrap color class (e.g., 'danger', 'success')",
    )
    tooltip: str = Field(..., description="Tooltip text explaining the trend")


class TrendAnalysis(BaseModel):
    """Complete trend analysis for an item."""

    item_id: str
    is_trending: bool = False
    trend_score: float = Field(default=0.0, description="Composite score indicating trend strength")
    indicators: dict[str, TrendIndicator] = Field(
        default_factory=dict,
        description="Specific indicators (e.g., 'views', 'mentions')",
    )
    badge: TrendBadge | None = None
    analyzed_at: datetime = Field(default_factory=datetime.now)
