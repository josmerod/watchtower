"""Tests for the notifications tab functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Mock the imports that might not be available
import sys
from unittest.mock import MagicMock

# Create mock modules for potentially missing dependencies
sys.modules['src.alerts'] = MagicMock()
sys.modules['src.alerts.models'] = MagicMock()
sys.modules['src.alerts.engine'] = MagicMock()
sys.modules['src.utils'] = MagicMock()
sys.modules['src.utils.file_system'] = MagicMock()
sys.modules['src.utils.logging'] = MagicMock()
sys.modules['src.web.dashboard.components.rule_form'] = MagicMock()

# Import the notifications tab after mocking
from src.web.dashboard.components.notifications_tab import (
    NotificationsManager,
    _get_rule_id,
    render_notifications_tab,
    render_rules_list,
)


class TestNotificationsManager:
    """Test the NotificationsManager class."""

    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project root for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_dir = temp_path / "data" / "alerts" / "default_user"
            data_dir.mkdir(parents=True, exist_ok=True)
            yield temp_path

    @pytest.fixture
    def manager(self, temp_project_root):
        """Create a NotificationsManager instance with mocked project root."""
        with patch('src.web.dashboard.components.notifications_tab.get_project_root_fallback') as mock_get_root:
            mock_get_root.return_value = temp_project_root
            with patch('src.web.dashboard.components.notifications_tab.ensure_directories_fallback') as mock_ensure:
                manager = NotificationsManager()
                mock_ensure.assert_called_once()
                return manager

    def test_manager_initialization(self, manager):
        """Test that the manager initializes correctly."""
        assert manager.user_id == "default_user"
        assert manager.data_dir.name == "data"
        assert manager.project_root.exists()

    def test_load_rules_empty(self, manager):
        """Test loading rules when no rules file exists."""
        rules = manager.load_rules()
        assert rules == []

    def test_save_and_load_rule(self, manager):
        """Test saving and loading a rule."""
        # Create a mock rule dictionary
        rule_data = {
            "name": "Test Rule",
            "description": "A test rule",
            "conditions": [
                {
                    "condition_type": "keyword_match",
                    "value": "python",
                    "operator": "contains"
                }
            ],
            "active": True,
            "notification_channels": ["browser"]
        }

        # Save the rule
        result = manager.save_rule(rule_data)
        assert result is True

        # Load rules and verify
        rules = manager.load_rules()
        assert len(rules) == 1
        assert rules[0]["name"] == "Test Rule"
        assert rules[0]["conditions"][0]["value"] == "python"

    def test_delete_rule(self, manager):
        """Test deleting a rule."""
        # Create and save a rule
        rule_data = {
            "id": "test-rule-123",
            "name": "Test Rule",
            "conditions": [{"condition_type": "keyword_match", "value": "test"}],
            "active": True,
            "notification_channels": ["browser"]
        }

        manager.save_rule(rule_data)
        assert len(manager.load_rules()) == 1

        # Delete the rule
        result = manager.delete_rule("test-rule-123")
        assert result is True
        assert len(manager.load_rules()) == 0

    def test_get_available_sources(self, manager):
        """Test getting available sources."""
        sources = manager.get_available_sources()
        assert isinstance(sources, list)

    def test_get_available_categories(self, manager):
        """Test getting available categories."""
        categories = manager.get_available_categories()
        assert isinstance(categories, list)
        assert "Technology" in categories
        assert "Science" in categories


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_rule_id_with_object(self):
        """Test getting rule ID from object with id attribute."""
        rule = Mock()
        rule.id = "test-id"
        assert _get_rule_id(rule) == "test-id"

    def test_get_rule_id_with_dict(self):
        """Test getting rule ID from dictionary."""
        rule = {"id": "test-id", "name": "Test Rule"}
        assert _get_rule_id(rule) == "test-id"

    def test_get_rule_id_with_string(self):
        """Test getting rule ID from string."""
        rule = "test-id"
        assert _get_rule_id(rule) == "test-id"

    def test_get_rule_id_empty(self):
        """Test getting rule ID when no ID exists."""
        rule = {"name": "Test Rule"}
        assert _get_rule_id(rule) == ""

        rule = Mock(spec=[])
        del rule.id
        assert _get_rule_id(rule) == ""


class TestRenderFunctions:
    """Test the render functions."""

    def test_render_rules_list_empty(self):
        """Test rendering rules list with no rules."""
        result = render_rules_list([])
        # Should return a container with an alert
        assert "No alert rules configured yet" in str(result)

    def test_render_rules_list_with_rules(self):
        """Test rendering rules list with rules."""
        rules = [
            {
                "id": "test-rule-1",
                "name": "Test Rule 1",
                "description": "A test rule",
                "active": True,
                "conditions": [
                    {"condition_type": "keyword_match", "value": "python"}
                ],
                "notification_channels": ["browser"],
                "trigger_count": 0,
                "last_triggered": None
            }
        ]

        result = render_rules_list(rules)
        # Should contain the rule name
        assert "Test Rule 1" in str(result)
        # Should contain the condition
        assert "Keyword: python" in str(result)

    @patch('src.web.dashboard.components.notifications_tab.NotificationsManager')
    def test_render_notifications_tab(self, mock_manager_class):
        """Test rendering the notifications tab."""
        # Mock the manager instance
        mock_manager = Mock()
        mock_manager.load_rules.return_value = []
        mock_manager_class.return_value = mock_manager

        result = render_notifications_tab()
        assert result is not None
        # Should contain the main structure
        assert "Alert Rules" in str(result)


class TestNotificationsManagerIntegration:
    """Integration tests for NotificationsManager."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            alerts_dir = temp_path / "data" / "alerts" / "default_user"
            alerts_dir.mkdir(parents=True, exist_ok=True)
            yield temp_path

    def test_round_trip_rule_management(self, temp_data_dir):
        """Test complete round-trip of rule management."""
        with patch('src.web.dashboard.components.notifications_tab.get_project_root_fallback') as mock_get_root:
            mock_get_root.return_value = temp_data_dir

            manager = NotificationsManager()

            # Create a complex rule
            rule_data = {
                "id": "complex-rule",
                "name": "Complex Test Rule",
                "description": "A complex rule with multiple conditions",
                "conditions": [
                    {
                        "condition_type": "keyword_match",
                        "value": "machine learning",
                        "operator": "contains",
                        "case_sensitive": False
                    },
                    {
                        "condition_type": "category_match",
                        "value": "Technology",
                        "operator": "equals"
                    }
                ],
                "active": True,
                "notification_channels": ["browser", "email"],
                "trigger_count": 5,
                "last_triggered": "2024-01-01T12:00:00Z"
            }

            # Save rule
            assert manager.save_rule(rule_data) is True

            # Load and verify
            rules = manager.load_rules()
            assert len(rules) == 1
            loaded_rule = rules[0]

            if isinstance(loaded_rule, dict):
                assert loaded_rule["name"] == "Complex Test Rule"
                assert len(loaded_rule["conditions"]) == 2
                assert loaded_rule["conditions"][0]["value"] == "machine learning"
                assert "browser" in loaded_rule["notification_channels"]
                assert "email" in loaded_rule["notification_channels"]

            # Update rule
            rule_data["name"] = "Updated Rule"
            rule_data["active"] = False
            assert manager.save_rule(rule_data) is True

            # Verify update
            updated_rules = manager.load_rules()
            assert len(updated_rules) == 1
            updated_rule = updated_rules[0]
            if isinstance(updated_rule, dict):
                assert updated_rule["name"] == "Updated Rule"
                assert updated_rule["active"] is False

            # Delete rule
            assert manager.delete_rule("complex-rule") is True
            assert len(manager.load_rules()) == 0

    def test_error_handling(self, temp_data_dir):
        """Test error handling in NotificationsManager."""
        with patch('src.web.dashboard.components.notifications_tab.get_project_root_fallback') as mock_get_root:
            mock_get_root.return_value = temp_data_dir

            manager = NotificationsManager()

            # Test saving invalid rule data
            invalid_rule = {
                # Missing required fields
                "name": "Invalid Rule"
                # No conditions
            }

            # Should still save but handle gracefully
            result = manager.save_rule(invalid_rule)
            # The function should not crash, even if validation fails
            assert isinstance(result, bool)

            # Test deleting non-existent rule
            result = manager.delete_rule("non-existent-id")
            # Should handle gracefully
            assert isinstance(result, bool)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])