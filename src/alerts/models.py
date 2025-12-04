"""Pydantic models for the alert system.

This module defines the data models used throughout the alert system,
including AlertRule for defining notification criteria and AlertEvent
for storing generated alert notifications.
"""

from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, validator


class TimeRange(BaseModel):
    """Model for defining quiet hours time ranges."""

    start_time: time = Field(..., description="Start time for quiet hours")
    end_time: time = Field(..., description="End time for quiet hours")
    days_of_week: list[int] = Field(
        default=[0, 1, 2, 3, 4, 5, 6],  # All days by default
        description="Days of week (0=Monday, 6=Sunday)",
    )

    @validator("days_of_week")
    def validate_days(cls, v):
        """Validate days of week are within valid range."""
        if any(day < 0 or day > 6 for day in v):
            raise ValueError("Days of week must be between 0 (Monday) and 6 (Sunday)")
        return v


class NotificationChannel(str, Enum):
    """Available notification channels."""

    BROWSER = "browser"
    EMAIL = "email"
    TELEGRAM = "telegram"


class AlertCondition(BaseModel):
    """Base model for alert conditions."""

    condition_type: str = Field(..., description="Type of condition (source_match, keyword_match, etc.)")
    value: Any = Field(..., description="Value for the condition")
    operator: str = Field(default="equals", description="Comparison operator")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"  # Prevent additional fields


class SourceMatchCondition(AlertCondition):
    """Condition for matching specific content sources."""

    condition_type: Literal["source_match"] = "source_match"
    value: str = Field(..., description="Source name or pattern to match")
    operator: str = Field(default="contains", description="Match operator")


class KeywordMatchCondition(AlertCondition):
    """Condition for matching keywords in content."""

    condition_type: Literal["keyword_match"] = "keyword_match"
    value: str = Field(..., description="Keyword or phrase to match")
    operator: str = Field(default="contains", description="Match operator")
    case_sensitive: bool = Field(default=False, description="Whether match is case sensitive")


class CategoryMatchCondition(AlertCondition):
    """Condition for matching NLP content categories."""

    condition_type: Literal["category_match"] = "category_match"
    value: str = Field(..., description="Category to match")
    operator: str = Field(default="equals", description="Match operator")


class PriceThresholdCondition(AlertCondition):
    """Condition for matching price thresholds."""

    condition_type: Literal["price_threshold"] = "price_threshold"
    value: float = Field(..., description="Price threshold value")
    operator: str = Field(default="less_than", description="Comparison operator")
    currency: str = Field(default="USD", description="Currency code")


class AlertRule(BaseModel):
    """Alert rule definition model."""

    id: str | None = None
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable rule name")
    description: str | None = Field(None, max_length=500, description="Rule description")
    user_id: str = Field(..., description="User who owns this rule")

    # Rule conditions
    conditions: list[AlertCondition] = Field(default_factory=list, description="List of conditions that must be met")

    # Rule configuration
    active: bool = Field(default=True, description="Whether this rule is currently active")
    quiet_hours: TimeRange | None = Field(None, description="Quiet hours when rule doesn't trigger")
    notification_channels: list[NotificationChannel] = Field(
        default=[NotificationChannel.BROWSER],
        description="Channels to send notifications through",
    )

    # Rule metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_triggered: datetime | None = None
    trigger_count: int = Field(default=0)

    @validator("conditions")
    def validate_conditions(cls, v):
        """Validate that at least one condition is provided."""
        if not v:
            raise ValueError("At least one condition must be provided")
        return v

    # Note: Quiet hours validation is handled in the matches_content method
    # to properly handle overnight time ranges like 22:00 to 06:00

    def matches_content(self, content: dict[str, Any]) -> bool:
        """Check if this rule matches the given content.

        Args:
            content: Content dictionary with metadata fields

        Returns:
            True if rule conditions match the content
        """
        if not self.active:
            return False

        # Check quiet hours
        if self.quiet_hours:
            now = datetime.now()
            if self._is_in_quiet_hours(now):
                return False

        # Check all conditions (AND logic - all must match)
        for condition in self.conditions:
            if not self._evaluate_condition(condition, content):
                return False

        return True

    def _is_in_quiet_hours(self, now: datetime) -> bool:
        """Check if current time is within quiet hours."""
        if not self.quiet_hours:
            return False

        current_time = now.time()
        current_day = now.weekday()

        # Check if current day is in quiet hours
        if current_day not in self.quiet_hours.days_of_week:
            return False

        # Check if current time is within time range
        start = self.quiet_hours.start_time
        end = self.quiet_hours.end_time

        # Handle overnight ranges (e.g., 22:00 to 06:00)
        if start > end:
            return current_time >= start or current_time <= end
        else:
            return start <= current_time <= end

    def _evaluate_condition(self, condition: AlertCondition, content: dict[str, Any]) -> bool:
        """Evaluate a single condition against content."""
        if condition.condition_type == "source_match":
            return self._evaluate_source_match(condition, content)
        elif condition.condition_type == "keyword_match":
            return self._evaluate_keyword_match(condition, content)
        elif condition.condition_type == "category_match":
            return self._evaluate_category_match(condition, content)
        elif condition.condition_type == "price_threshold":
            return self._evaluate_price_threshold(condition, content)
        else:
            return False

    def _evaluate_source_match(self, condition: AlertCondition, content: dict[str, Any]) -> bool:
        """Evaluate source match condition."""
        source = content.get("source", "")
        value = str(condition.value).lower()
        source_lower = source.lower()

        if condition.operator == "equals":
            return source_lower == value
        elif condition.operator == "contains":
            return value in source_lower
        elif condition.operator == "starts_with":
            return source_lower.startswith(value)
        elif condition.operator == "ends_with":
            return source_lower.endswith(value)
        else:
            return source_lower == value

    def _evaluate_keyword_match(self, condition: AlertCondition, content: dict[str, Any]) -> bool:
        """Evaluate keyword match condition."""
        # Search in title, description, and content fields
        searchable_fields = [
            content.get("title", ""),
            content.get("description", ""),
            content.get("content", ""),
            " ".join(content.get("tags", [])),
        ]

        combined_text = " ".join(str(field).lower() for field in searchable_fields)
        keyword = str(condition.value).lower()

        # Handle case sensitivity
        if isinstance(condition, KeywordMatchCondition) and not condition.case_sensitive:
            combined_text = combined_text.lower()
            keyword = keyword.lower()

        if condition.operator == "equals":
            return keyword == combined_text
        elif condition.operator == "contains":
            return keyword in combined_text
        elif condition.operator == "starts_with":
            return combined_text.startswith(keyword)
        elif condition.operator == "ends_with":
            return combined_text.endswith(keyword)
        else:
            return keyword in combined_text

    def _evaluate_category_match(self, condition: AlertCondition, content: dict[str, Any]) -> bool:
        """Evaluate category match condition."""
        content_categories = content.get("categories", [])
        if not isinstance(content_categories, list):
            content_categories = [content_categories]

        target_category = str(condition.value)

        if condition.operator == "equals":
            return target_category in content_categories
        elif condition.operator == "contains":
            return any(target_category.lower() in str(cat).lower() for cat in content_categories)
        else:
            return target_category in content_categories

    def _evaluate_price_threshold(self, condition: AlertCondition, content: dict[str, Any]) -> bool:
        """Evaluate price threshold condition."""
        price = content.get("price")
        if price is None:
            return False

        try:
            price_value = float(price)
            threshold = float(condition.value)

            if condition.operator == "equals":
                return price_value == threshold
            elif condition.operator == "less_than":
                return price_value < threshold
            elif condition.operator == "greater_than":
                return price_value > threshold
            elif condition.operator == "less_equal":
                return price_value <= threshold
            elif condition.operator == "greater_equal":
                return price_value >= threshold
            else:
                return price_value < threshold  # Default to less_than
        except (ValueError, TypeError):
            return False


class AlertEvent(BaseModel):
    """Model for storing alert events."""

    id: str | None = None
    rule_id: str = Field(..., description="ID of the rule that triggered this alert")
    rule_name: str = Field(..., description="Name of the rule that triggered this alert")
    user_id: str = Field(..., description="User who should receive this alert")

    # Content information
    content_id: str = Field(..., description="Unique identifier for the content")
    content: dict[str, Any] = Field(..., description="The content that triggered the alert")
    content_hash: str = Field(..., description="Hash of content for deduplication")

    # Event metadata
    triggered_at: datetime = Field(default_factory=datetime.now)
    severity: str = Field(default="info", description="Alert severity level")
    message: str | None = Field(None, description="Alert message")

    # Processing status
    processed: bool = Field(default=False, description="Whether alert has been processed/ sent")
    sent_via: list[NotificationChannel] = Field(default_factory=list, description="Channels this alert was sent through")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"  # Prevent additional fields

    def mark_processed(self, channels: list[NotificationChannel]) -> None:
        """Mark alert as processed and record channels used."""
        self.processed = True
        self.sent_via = channels
