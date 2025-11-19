"""Tests for the AlertEngine class.

This module tests the core alert rule evaluation logic,
including content matching, deduplication, and event generation.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.alerts.engine import AlertEngine
from src.alerts.models import (
    AlertRule,
    AlertEvent,
    KeywordMatchCondition,
    SourceMatchCondition,
    CategoryMatchCondition,
    PriceThresholdCondition,
    TimeRange,
    NotificationChannel
)


class TestAlertEngine:
    """Test AlertEngine functionality."""

    @pytest.fixture
    def alert_engine(self):
        """Create a fresh AlertEngine instance for each test."""
        return AlertEngine()

    @pytest.fixture
    def sample_rule(self):
        """Create a sample alert rule for testing."""
        return AlertRule(
            id="test_rule_1",
            name="Test Python Rule",
            user_id="test_user",
            conditions=[
                KeywordMatchCondition(value="python", operator="contains")
            ],
            notification_channels=[NotificationChannel.BROWSER]
        )

    @pytest.fixture
    def sample_content(self):
        """Create sample content for testing."""
        return {
            "id": "content_123",
            "title": "Python programming guide",
            "description": "Learn Python programming",
            "url": "https://example.com/python-guide",
            "source": "example_source",
            "categories": ["programming", "tutorial"],
            "price": None,
            "tags": ["python", "programming"]
        }

    def test_alert_engine_initialization(self, alert_engine):
        """Test AlertEngine initialization."""
        assert alert_engine.logger is not None
        assert alert_engine.settings is not None
        assert alert_engine._evaluations_count == 0
        assert alert_engine._matches_count == 0
        assert alert_engine._errors_count == 0

    def test_evaluate_content_no_rules(self, alert_engine, sample_content):
        """Test evaluating content when user has no rules."""
        events = alert_engine.evaluate_content(sample_content, "no_rules_user")
        assert events == []

    def test_evaluate_content_with_matching_rule(self, alert_engine, sample_content, sample_rule):
        """Test evaluating content that matches a rule."""
        # Mock the rule loading
        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [sample_rule]

            events = alert_engine.evaluate_content(sample_content, "test_user")

            assert len(events) == 1
            assert isinstance(events[0], AlertEvent)
            assert events[0].rule_id == sample_rule.id
            assert events[0].rule_name == sample_rule.name
            assert events[0].user_id == sample_rule.user_id
            assert events[0].content_id == sample_content["id"]

    def test_evaluate_content_no_matching_rules(self, alert_engine, sample_content):
        """Test evaluating content that doesn't match any rules."""
        non_matching_rule = AlertRule(
            id="no_match_rule",
            name="No Match Rule",
            user_id="test_user",
            conditions=[
                KeywordMatchCondition(value="nonexistent_keyword", operator="contains")
            ]
        )

        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [non_matching_rule]

            events = alert_engine.evaluate_content(sample_content, "test_user")
            assert events == []

    def test_evaluate_content_inactive_rule(self, alert_engine, sample_content, sample_rule):
        """Test that inactive rules don't trigger alerts."""
        sample_rule.active = False

        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [sample_rule]

            events = alert_engine.evaluate_content(sample_content, "test_user")
            assert events == []

    def test_evaluate_content_multiple_matching_rules(self, alert_engine, sample_content):
        """Test content matching multiple rules."""
        rule1 = AlertRule(
            id="rule_1",
            name="Python Rule",
            user_id="test_user",
            conditions=[KeywordMatchCondition(value="python")]
        )

        rule2 = AlertRule(
            id="rule_2",
            name="Programming Rule",
            user_id="test_user",
            conditions=[CategoryMatchCondition(value="programming")]
        )

        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [rule1, rule2]

            events = alert_engine.evaluate_content(sample_content, "test_user")
            assert len(events) == 2

    def test_deduplication_same_content(self, alert_engine, sample_content, sample_rule):
        """Test that duplicate content within window is suppressed."""
        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [sample_rule]

            # First evaluation
            events1 = alert_engine.evaluate_content(sample_content, "test_user")
            assert len(events1) == 1

            # Second evaluation with same content (should be deduplicated)
            events2 = alert_engine.evaluate_content(sample_content, "test_user")
            assert len(events2) == 0

    def test_deduplication_different_content(self, alert_engine, sample_content, sample_rule):
        """Test that different content is not deduplicated."""
        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [sample_rule]

            # First evaluation
            events1 = alert_engine.evaluate_content(sample_content, "test_user")
            assert len(events1) == 1

            # Second evaluation with different content
            different_content = sample_content.copy()
            different_content["title"] = "JavaScript programming guide"
            events2 = alert_engine.evaluate_content(different_content, "test_user")
            assert len(events2) == 1

    def test_content_hash_generation(self, alert_engine, sample_content):
        """Test content hash generation consistency."""
        hash1 = alert_engine._generate_content_hash(sample_content)
        hash2 = alert_engine._generate_content_hash(sample_content)
        assert hash1 == hash2

        # Different content should produce different hash
        different_content = sample_content.copy()
        different_content["title"] = "Different title"
        hash3 = alert_engine._generate_content_hash(different_content)
        assert hash1 != hash3

    def test_load_user_rules_file_not_exists(self, alert_engine):
        """Test loading rules when file doesn't exist."""
        rules = alert_engine._load_user_rules("nonexistent_user")
        assert rules == []

    def test_load_user_rules_file_exists(self, alert_engine, sample_rule):
        """Test loading rules from file."""
        rules_data = [sample_rule.dict()]

        mock_file_data = json.dumps(rules_data, indent=2, default=str)

        with patch('builtins.open', mock_open(read_data=mock_file_data)):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('src.alerts.engine.Path') as mock_path:
                    # Mock the Path object chain
                    mock_path_instance = Mock()
                    mock_path.return_value = mock_path_instance
                    mock_path_instance.exists.return_value = True

                    rules = alert_engine._load_user_rules("test_user")
                    assert len(rules) == 1
                    assert rules[0].name == sample_rule.name

    def test_create_alert_event(self, alert_engine, sample_rule, sample_content):
        """Test alert event creation."""
        content_hash = alert_engine._generate_content_hash(sample_content)

        event = alert_engine._create_alert_event(sample_rule, sample_content, content_hash)

        assert isinstance(event, AlertEvent)
        assert event.rule_id == sample_rule.id
        assert event.rule_name == sample_rule.name
        assert event.user_id == sample_rule.user_id
        assert event.content == sample_content
        assert event.content_hash == content_hash
        assert "Alert: Test Python Rule" in event.message

    def test_store_alert_events(self, alert_engine):
        """Test storing alert events to file system."""
        events = [
            AlertEvent(
                rule_id="rule_1",
                rule_name="Test Rule",
                user_id="test_user",
                content_id="content_1",
                content={"title": "Test"},
                content_hash="hash123"
            )
        ]

        with patch('src.alerts.engine.ensure_directories'):
            with patch('builtins.open', mock_open()):
                with patch('json.dump') as mock_dump:
                    alert_engine._store_alert_events("test_user", events)

                    # Verify json.dump was called
                    assert mock_dump.call_count == 1
                    mock_dump.assert_called()

    def test_get_metrics(self, alert_engine):
        """Test getting alert engine metrics."""
        # Manually set some metrics
        alert_engine._evaluations_count = 10
        alert_engine._matches_count = 3
        alert_engine._errors_count = 1

        metrics = alert_engine.get_metrics()

        assert metrics["evaluations_count"] == 10
        assert metrics["matches_count"] == 3
        assert metrics["errors_count"] == 1
        assert metrics["match_rate"] == 30.0  # 3/10 * 100

    def test_reload_rules_specific_user(self, alert_engine):
        """Test reloading rules for specific user."""
        # Add some cached rules first
        cache_key = "user_test_user"
        alert_engine._rules_cache[cache_key] = [Mock()]
        alert_engine._rules_cache_timestamp[cache_key] = datetime.now()

        alert_engine.reload_rules("test_user")

        assert cache_key not in alert_engine._rules_cache
        assert cache_key not in alert_engine._rules_cache_timestamp

    def test_reload_rules_all_users(self, alert_engine):
        """Test reloading rules for all users."""
        # Add some cached rules first
        alert_engine._rules_cache["user_1"] = [Mock()]
        alert_engine._rules_cache["user_2"] = [Mock()]

        alert_engine.reload_rules()

        assert len(alert_engine._rules_cache) == 0
        assert len(alert_engine._rules_cache_timestamp) == 0

    def test_clear_dedup_cache(self, alert_engine):
        """Test clearing deduplication cache."""
        # Add some entries to cache
        alert_engine._dedup_cache["hash1"] = datetime.now()
        alert_engine._dedup_cache["hash2"] = datetime.now()

        assert len(alert_engine._dedup_cache) == 2

        alert_engine.clear_dedup_cache()

        assert len(alert_engine._dedup_cache) == 0

    def test_cleanup_dedup_cache(self, alert_engine):
        """Test cleanup of old deduplication cache entries."""
        now = datetime.now()
        old_time = now - timedelta(hours=2)  # Older than 1-hour window
        recent_time = now - timedelta(minutes=30)  # Within window

        alert_engine._dedup_cache = {
            "old_hash": old_time,
            "recent_hash": recent_time
        }

        alert_engine._cleanup_dedup_cache(now)

        assert "old_hash" not in alert_engine._dedup_cache
        assert "recent_hash" in alert_engine._dedup_cache


class TestAlertEngineIntegration:
    """Integration tests for AlertEngine with various content types."""

    @pytest.fixture
    def alert_engine(self):
        """Create a fresh AlertEngine instance."""
        return AlertEngine()

    def test_price_content_evaluation(self, alert_engine):
        """Test evaluation with price-based content."""
        # Create a rule for price threshold
        price_rule = AlertRule(
            id="price_rule",
            name="Cheap Deals",
            user_id="test_user",
            conditions=[
                PriceThresholdCondition(value=20.0, operator="less_than")
            ]
        )

        # Content with price below threshold
        cheap_content = {
            "title": "Course on sale",
            "price": 15.99,
            "source": "udemy"
        }

        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [price_rule]

            events = alert_engine.evaluate_content(cheap_content, "test_user")
            assert len(events) == 1

    def test_source_matching_evaluation(self, alert_engine):
        """Test evaluation with source-based content."""
        source_rule = AlertRule(
            id="source_rule",
            name="GitHub Alerts",
            user_id="test_user",
            conditions=[
                SourceMatchCondition(value="github", operator="contains")
            ]
        )

        github_content = {
            "title": "New repository",
            "source": "GitHub Repository"
        }

        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [source_rule]

            events = alert_engine.evaluate_content(github_content, "test_user")
            assert len(events) == 1

    def test_complex_rule_evaluation(self, alert_engine):
        """Test evaluation with complex multi-condition rules."""
        complex_rule = AlertRule(
            id="complex_rule",
            name="Free Python Courses",
            user_id="test_user",
            conditions=[
                KeywordMatchCondition(value="python"),
                CategoryMatchCondition(value="programming"),
                PriceThresholdCondition(value=0.0, operator="less_equal")
            ]
        )

        # Content that matches all conditions
        matching_content = {
            "title": "Python Programming",
            "categories": ["programming"],
            "price": 0.0,
            "source": "free_tutorials"
        }

        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [complex_rule]

            events = alert_engine.evaluate_content(matching_content, "test_user")
            assert len(events) == 1

    def test_rule_error_handling(self, alert_engine):
        """Test error handling during rule evaluation."""
        # Create a rule that will cause an error
        problematic_rule = Mock(spec=AlertRule)
        problematic_rule.matches_content.side_effect = Exception("Test error")

        with patch.object(alert_engine, '_load_user_rules') as mock_load_rules:
            mock_load_rules.return_value = [problematic_rule]

            content = {"title": "Test content"}

            # Should not raise exception, but handle gracefully
            events = alert_engine.evaluate_content(content, "test_user")
            assert events == []

            # Should increment error count
            assert alert_engine._errors_count == 1