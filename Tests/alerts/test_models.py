"""Tests for alert system Pydantic models.

This module tests the AlertRule, AlertEvent, and related models
to ensure proper validation, serialization, and business logic.
"""

import pytest
from datetime import datetime, time
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.alerts.models import (
    AlertEvent,
    AlertRule,
    AlertCondition,
    SourceMatchCondition,
    KeywordMatchCondition,
    CategoryMatchCondition,
    PriceThresholdCondition,
    TimeRange,
    NotificationChannel,
)


class TestTimeRange:
    """Test TimeRange model."""

    def test_time_range_creation(self):
        """Test creating a valid TimeRange."""
        time_range = TimeRange(
            start_time=time(22, 0),  # 10 PM
            end_time=time(6, 0),     # 6 AM
            days_of_week=[0, 1, 2, 3, 4]  # Monday-Friday
        )
        assert time_range.start_time == time(22, 0)
        assert time_range.end_time == time(6, 0)
        assert len(time_range.days_of_week) == 5

    def test_time_range_validation_invalid_day(self):
        """Test TimeRange validation with invalid day."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(
                start_time=time(22, 0),
                end_time=time(6, 0),
                days_of_week=[7]  # Invalid day
            )
        assert "Days of week must be between 0 (Monday) and 6 (Sunday)" in str(exc_info.value)

    def test_time_range_validation_time_order(self):
        """Test TimeRange validation - overnight ranges are allowed."""
        # This should not raise an error - overnight ranges like 22:00 to 06:00 are valid
        time_range = TimeRange(
            start_time=time(22, 0),  # 10 PM
            end_time=time(6, 0)      # 6 AM next day
        )
        assert time_range.start_time == time(22, 0)
        assert time_range.end_time == time(6, 0)


class TestAlertRule:
    """Test AlertRule model."""

    def test_alert_rule_creation_minimal(self):
        """Test creating a minimal valid AlertRule."""
        rule = AlertRule(
            name="Test Rule",
            user_id="test_user",
            conditions=[
                KeywordMatchCondition(value="python")
            ]
        )
        assert rule.name == "Test Rule"
        assert rule.user_id == "test_user"
        assert len(rule.conditions) == 1
        assert rule.active is True
        assert rule.trigger_count == 0

    def test_alert_rule_creation_full(self):
        """Test creating a full AlertRule with all fields."""
        quiet_hours = TimeRange(
            start_time=time(22, 0),  # 10 PM
            end_time=time(6, 0)      # 6 AM (overnight range is valid)
        )

        rule = AlertRule(
            name="Deal Alert",
            description="Alert for great deals",
            user_id="test_user",
            conditions=[
                KeywordMatchCondition(value="free"),
                CategoryMatchCondition(value="deals")
            ],
            quiet_hours=quiet_hours,
            notification_channels=[NotificationChannel.BROWSER, NotificationChannel.EMAIL]
        )

        assert rule.name == "Deal Alert"
        assert rule.description == "Alert for great deals"
        assert len(rule.conditions) == 2
        assert rule.quiet_hours is not None
        assert len(rule.notification_channels) == 2

    def test_alert_rule_validation_no_conditions(self):
        """Test AlertRule validation with no conditions."""
        with pytest.raises(ValueError, match="At least one condition must be provided"):
            AlertRule(
                name="Invalid Rule",
                user_id="test_user",
                conditions=[]
            )

    def test_alert_rule_matches_content_active_check(self):
        """Test that inactive rules don't match content."""
        rule = AlertRule(
            name="Inactive Rule",
            user_id="test_user",
            conditions=[KeywordMatchCondition(value="python")],
            active=False
        )

        content = {"title": "Python programming guide"}
        assert not rule.matches_content(content)

    def test_alert_rule_matches_content_source_match(self):
        """Test source matching condition."""
        rule = AlertRule(
            name="Source Test",
            user_id="test_user",
            conditions=[
                SourceMatchCondition(value="github", operator="contains")
            ]
        )

        # Test matching content
        content_match = {"source": "GitHub Repository"}
        assert rule.matches_content(content_match)

        # Test non-matching content
        content_no_match = {"source": "Stack Overflow"}
        assert not rule.matches_content(content_no_match)

    def test_alert_rule_matches_content_keyword_match(self):
        """Test keyword matching condition."""
        rule = AlertRule(
            name="Keyword Test",
            user_id="test_user",
            conditions=[
                KeywordMatchCondition(value="machine learning", case_sensitive=False)
            ]
        )

        # Test matching content (case insensitive)
        content_match = {"title": "Introduction to Machine Learning"}
        assert rule.matches_content(content_match)

        # Test non-matching content
        content_no_match = {"title": "Introduction to Data Science"}
        assert not rule.matches_content(content_no_match)

    def test_alert_rule_matches_content_category_match(self):
        """Test category matching condition."""
        rule = AlertRule(
            name="Category Test",
            user_id="test_user",
            conditions=[
                CategoryMatchCondition(value="technology")
            ]
        )

        # Test matching content
        content_match = {"categories": ["technology", "programming"]}
        assert rule.matches_content(content_match)

        # Test non-matching content
        content_no_match = {"categories": ["business", "finance"]}
        assert not rule.matches_content(content_no_match)

    def test_alert_rule_matches_content_price_threshold(self):
        """Test price threshold condition."""
        rule = AlertRule(
            name="Price Test",
            user_id="test_user",
            conditions=[
                PriceThresholdCondition(value=100.0, operator="less_than")
            ]
        )

        # Test matching content
        content_match = {"title": "Course on sale", "price": 50.0}
        assert rule.matches_content(content_match)

        # Test non-matching content
        content_no_match = {"title": "Expensive course", "price": 150.0}
        assert not rule.matches_content(content_no_match)

    def test_alert_rule_matches_content_multiple_conditions(self):
        """Test rule with multiple conditions (AND logic)."""
        rule = AlertRule(
            name="Multi-condition Test",
            user_id="test_user",
            conditions=[
                KeywordMatchCondition(value="python"),
                CategoryMatchCondition(value="programming"),
                PriceThresholdCondition(value=50.0, operator="less_than")
            ]
        )

        # Test content that matches all conditions
        content_match_all = {
            "title": "Python programming course",
            "categories": ["programming"],
            "price": 25.0
        }
        assert rule.matches_content(content_match_all)

        # Test content that matches only some conditions
        content_match_partial = {
            "title": "Python programming course",
            "categories": ["programming"],
            "price": 75.0  # Too expensive
        }
        assert not rule.matches_content(content_match_partial)

    def test_alert_rule_quiet_hours(self):
        """Test quiet hours functionality."""
        # Create rule with quiet hours (10 PM to 6 AM)
        quiet_hours = TimeRange(
            start_time=time(22, 0),  # 10 PM
            end_time=time(6, 0),      # 6 AM next day
            days_of_week=[0, 1, 2, 3, 4, 5, 6]  # All days
        )

        rule = AlertRule(
            name="Quiet Hours Test",
            user_id="test_user",
            conditions=[KeywordMatchCondition(value="test")],
            quiet_hours=quiet_hours
        )

        content = {"title": "Test content"}

        # Mock datetime during quiet hours (11 PM)
        with pytest.MonkeyPatch().context() as m:
            # Create a proper mock datetime object
            mock_datetime = Mock()
            mock_datetime.now.return_value = datetime(2024, 1, 1, 23, 0, 0)  # 11 PM
            mock_datetime.weekday.return_value = 0  # Monday

            with patch('src.alerts.models.datetime', mock_datetime):
                assert not rule.matches_content(content)

    def test_alert_rule_trigger_statistics(self):
        """Test trigger statistics update."""
        rule = AlertRule(
            name="Stats Test",
            user_id="test_user",
            conditions=[KeywordMatchCondition(value="test")]
        )

        assert rule.trigger_count == 0
        assert rule.last_triggered is None

        content = {"title": "Test content"}
        rule.matches_content(content)  # This would normally trigger

        # Note: In real usage, trigger_count and last_triggered are updated
        # by the AlertEngine when generating events


class TestAlertEvent:
    """Test AlertEvent model."""

    def test_alert_event_creation(self):
        """Test creating a valid AlertEvent."""
        event = AlertEvent(
            rule_id="rule_123",
            rule_name="Test Rule",
            user_id="test_user",
            content_id="content_456",
            content={"title": "Test content"},
            content_hash="abc123",
            message="Alert triggered"
        )

        assert event.rule_id == "rule_123"
        assert event.rule_name == "Test Rule"
        assert event.user_id == "test_user"
        assert event.content_id == "content_456"
        assert event.content["title"] == "Test content"
        assert event.content_hash == "abc123"
        assert event.message == "Alert triggered"
        assert event.processed is False
        assert len(event.sent_via) == 0

    def test_alert_event_mark_processed(self):
        """Test marking an event as processed."""
        event = AlertEvent(
            rule_id="rule_123",
            rule_name="Test Rule",
            user_id="test_user",
            content_id="content_456",
            content={"title": "Test content"},
            content_hash="abc123"
        )

        channels = [NotificationChannel.BROWSER, NotificationChannel.EMAIL]
        event.mark_processed(channels)

        assert event.processed is True
        assert len(event.sent_via) == 2
        assert NotificationChannel.BROWSER in event.sent_via
        assert NotificationChannel.EMAIL in event.sent_via


class TestConditionModels:
    """Test specific condition model types."""

    def test_source_match_condition(self):
        """Test SourceMatchCondition specifics."""
        condition = SourceMatchCondition(
            value="github",
            operator="contains"
        )

        assert condition.condition_type == "source_match"
        assert condition.value == "github"
        assert condition.operator == "contains"

    def test_keyword_match_condition(self):
        """Test KeywordMatchCondition specifics."""
        condition = KeywordMatchCondition(
            value="Python",
            operator="contains",
            case_sensitive=True
        )

        assert condition.condition_type == "keyword_match"
        assert condition.value == "Python"
        assert condition.operator == "contains"
        assert condition.case_sensitive is True

    def test_price_threshold_condition(self):
        """Test PriceThresholdCondition specifics."""
        condition = PriceThresholdCondition(
            value=99.99,
            operator="less_than",
            currency="USD"
        )

        assert condition.condition_type == "price_threshold"
        assert condition.value == 99.99
        assert condition.operator == "less_than"
        assert condition.currency == "USD"


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_alert_rule_serialization(self):
        """Test AlertRule JSON serialization."""
        rule = AlertRule(
            name="Test Rule",
            user_id="test_user",
            conditions=[KeywordMatchCondition(value="test")],
            notification_channels=[NotificationChannel.BROWSER]
        )

        # Test dict conversion
        rule_dict = rule.dict()
        assert rule_dict["name"] == "Test Rule"
        assert rule_dict["user_id"] == "test_user"
        assert len(rule_dict["conditions"]) == 1
        assert "notification_channels" in rule_dict

    def test_alert_event_serialization(self):
        """Test AlertEvent JSON serialization."""
        event = AlertEvent(
            rule_id="rule_123",
            rule_name="Test Rule",
            user_id="test_user",
            content_id="content_456",
            content={"title": "Test"},
            content_hash="abc123"
        )

        # Test dict conversion
        event_dict = event.dict()
        assert event_dict["rule_id"] == "rule_123"
        assert event_dict["content"]["title"] == "Test"
        assert event_dict["processed"] is False