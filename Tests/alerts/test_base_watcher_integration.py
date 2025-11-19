"""Integration tests for BaseWatcher and AlertEngine.

This module tests the integration between BaseWatcher and the alert system.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.watchers.base_watcher import BaseWatcher
from src.alerts.models import AlertRule, KeywordMatchCondition, NotificationChannel


class TestBaseWatcherIntegration:
    """Test BaseWatcher integration with alert system."""

    @pytest.fixture
    def mock_watcher(self):
        """Create a mock BaseWatcher for testing."""
        class MockWatcher(BaseWatcher):
            def extract_value(self, html_content: str):
                return f"Extracted value from {self.name}"

            def has_changed(self, old_value, new_value):
                return old_value != new_value

            def fetch_page(self):
                return "<html>Mock HTML content</html>"

        return MockWatcher(
            name="test_watcher",
            url="https://example.com/test",
            check_interval=1  # 1 second for testing
        )

    @pytest.fixture
    def sample_alert_rule(self):
        """Create a sample alert rule for testing."""
        return AlertRule(
            id="test_rule",
            name="Test Watcher Alert",
            user_id="default_user",
            conditions=[
                KeywordMatchCondition(value="extracted value", operator="contains")
            ],
            notification_channels=[NotificationChannel.BROWSER]
        )

    @pytest.fixture
    def rules_file_data(self, sample_alert_rule):
        """Create rules file data for mocking."""
        return json.dumps([sample_alert_rule.dict()], indent=2, default=str)

    def test_watcher_initialization_without_alert_engine(self, mock_watcher):
        """Test watcher initialization when AlertEngine is not available."""
        # Mock the import failure
        with patch('src.watchers.base_watcher.AlertEngine', None):
            with patch('src.alerts.engine.AlertEngine', side_effect=ImportError("Module not found")):
                # Re-initialize watcher to trigger the import error
                watcher = MockWatcher(
                    name="test_watcher_no_alerts",
                    url="https://example.com/test"
                )
                assert watcher.alert_engine is None

    def test_watcher_initialization_with_alert_engine(self, mock_watcher):
        """Test watcher initialization with AlertEngine available."""
        # AlertEngine should be initialized
        assert mock_watcher.alert_engine is not None

    def test_trigger_alarm_without_alert_engine(self, mock_watcher):
        """Test trigger_alarm when AlertEngine is not available."""
        mock_watcher.alert_engine = None

        # Should not raise an exception
        mock_watcher.trigger_alarm("old_value", "new_value")

    @patch('src.alerts.engine.ensure_directories')
    @patch('builtins.open')
    @patch('json.dump')
    @patch('pathlib.Path.exists')
    def test_trigger_alarm_with_alert_engine(self, mock_path_exists, mock_json_dump, mock_open, mock_ensure_dirs, mock_watcher, rules_file_data):
        """Test trigger_alarm with AlertEngine integration."""
        # Setup mocks
        mock_path_exists.return_value = True
        mock_ensure_dirs.return_value = None

        # Mock the rule loading
        with patch.object(mock_watcher.alert_engine, '_load_user_rules') as mock_load_rules:
            with patch.object(mock_watcher.alert_engine, 'evaluate_content') as mock_evaluate:
                # Setup rule data
                mock_path_instance = Mock()
                mock_path_instance.exists.return_value = True
                mock_path_instance.open = mock_open(read_data=rules_file_data)

                with patch('pathlib.Path', return_value=mock_path_instance):
                    # Mock rules loading
                    sample_rule = AlertRule(
                        id="test_rule",
                        name="Test Rule",
                        user_id="default_user",
                        conditions=[KeywordMatchCondition(value="value")]
                    )
                    mock_load_rules.return_value = [sample_rule]

                    # Mock evaluation to return events
                    from src.alerts.models import AlertEvent
                    mock_events = [
                        AlertEvent(
                            rule_id="test_rule",
                            rule_name="Test Rule",
                            user_id="default_user",
                            content_id="test_content",
                            content={"title": "Test"},
                            content_hash="hash123"
                        )
                    ]
                    mock_evaluate.return_value = mock_events

                    # Trigger the alarm
                    mock_watcher.trigger_alarm("old_value", "new_value")

                    # Verify evaluation was called
                    mock_evaluate.assert_called_once()
                    call_args = mock_evaluate.call_args
                    assert call_args[0][1] == "default_user"  # user_id

                    # Verify content was prepared correctly
                    content = call_args[0][0]
                    assert content["source"] == mock_watcher.name
                    assert content["old_value"] == "old_value"
                    assert content["new_value"] == "new_value"

    def test_prepare_content_for_alerts(self, mock_watcher):
        """Test content preparation for alert evaluation."""
        old_value = "previous_value"
        new_value = "new_value"

        content = mock_watcher._prepare_content_for_alerts(old_value, new_value)

        # Verify content structure
        assert content["source"] == mock_watcher.name
        assert content["watcher_name"] == mock_watcher.name
        assert content["old_value"] == old_value
        assert content["new_value"] == new_value
        assert content["url"] == mock_watcher.url
        assert content["event_type"] == "watcher_change"
        assert "categories" in content
        assert "tags" in content
        assert "timestamp" in content

    def test_prepare_content_for_alerts_with_object_value(self, mock_watcher):
        """Test content preparation when new_value is an object."""
        class TestObject:
            def __init__(self):
                self.title = "Test Title"
                self.description = "Test Description"
                self._private_field = "should not be included"
                self.price = 99.99

        old_value = "previous"
        new_value = TestObject()

        content = mock_watcher._prepare_content_for_alerts(old_value, new_value)

        # Verify object attributes are included
        assert content["title"] == "Test Title"
        assert content["description"] == "Test Description"
        assert content["price"] == 99.99
        assert "_private_field" not in content

    def test_prepare_content_for_alerts_error_handling(self, mock_watcher):
        """Test error handling in content preparation."""
        # Mock datetime.now() to raise an exception
        with patch('src.watchers.base_watcher.datetime', side_effect=Exception("Time error")):
            content = mock_watcher._prepare_content_for_alerts("old", "new")
            assert content is None

    def test_alert_evaluation_error_handling(self, mock_watcher):
        """Test error handling in alert evaluation."""
        # Mock AlertEngine.evaluate_content to raise an exception
        mock_watcher.alert_engine.evaluate_content = Mock(side_effect=Exception("Evaluation error"))

        # Should not raise an exception
        mock_watcher._trigger_alert_evaluation("old", "new")

    def test_full_watcher_workflow_with_alerts(self, mock_watcher):
        """Test the complete watcher workflow with alert integration."""
        # Setup initial state
        initial_state = {
            "last_check": datetime.now().isoformat(),
            "last_value": None,
            "first_seen": datetime.now().isoformat(),
        }

        with patch.object(mock_watcher, '_load_state', return_value=initial_state):
            with patch.object(mock_watcher, '_save_state'):
                with patch.object(mock_watcher.alert_engine, '_load_user_rules', return_value=[]):
                    with patch.object(mock_watcher, 'fetch_page', return_value="<html>test</html>"):
                        with patch.object(mock_watcher, 'extract_value', return_value="test_value"):
                            # First check (no previous value)
                            mock_watcher.check()

                            # Second check (change detected)
                            mock_watcher.trigger_alarm = Mock()  # Mock to verify call
                            mock_watcher.check()

                            # Verify trigger_alarm was called
                            mock_watcher.trigger_alarm.assert_called_once()

    def test_watcher_with_multiple_alert_events(self, mock_watcher):
        """Test watcher triggering multiple alert events."""
        # Mock multiple alert events
        from src.alerts.models import AlertEvent
        mock_events = [
            AlertEvent(
                rule_id=f"rule_{i}",
                rule_name=f"Rule {i}",
                user_id="default_user",
                content_id=f"content_{i}",
                content={"title": f"Test {i}"},
                content_hash=f"hash_{i}"
            )
            for i in range(3)
        ]

        with patch.object(mock_watcher.alert_engine, 'evaluate_content', return_value=mock_events):
            with patch.object(mock_watcher.alert_engine, '_load_user_rules', return_value=[]):
                mock_watcher._trigger_alert_evaluation("old", "new")

                # Should generate 3 events
                assert mock_watcher.alert_engine.evaluate_content.call_count == 1

    def test_watcher_content_id_generation(self, mock_watcher):
        """Test that content IDs are generated correctly."""
        content = mock_watcher._prepare_content_for_alerts("old", "new")

        # Should contain watcher name and timestamp
        assert mock_watcher.name in content["id"]
        assert content["id"].startswith(mock_watcher.name)
        assert len(content["id"]) > len(mock_watcher.name)

    def test_watcher_content_categories_and_tags(self, mock_watcher):
        """Test that content categories and tags are properly set."""
        content = mock_watcher._prepare_content_for_alerts("old", "new")

        assert "watcher" in content["categories"]
        assert "change" in content["categories"]
        assert mock_watcher.name in content["tags"]
        assert "alert" in content["tags"]