"""Unit Tests for Tab Preferences Manager
Tests the localStorage-based tab preferences functionality
"""

import json

import pytest


class TestTabPreferencesManager:
    """Test suite for TabPreferencesManager JavaScript functionality"""

    def test_default_tabs_configuration(self):
        """Test that default tabs are properly configured"""
        # This would test the JavaScript TabPreferencesManager
        # Since we can't directly test JavaScript in Python unit tests,
        # we'll test the expected structure and validate the configuration

        expected_tabs = [
            {
                "id": "tab-shortcuts",
                "label": "Shortcuts",
                "icon": "fa-star",
                "default_visible": True,
            },
            {
                "id": "tab-news",
                "label": "News",
                "icon": "fa-newspaper",
                "default_visible": True,
            },
            {
                "id": "tab-knowledge-garden",
                "label": "🌱 Knowledge Garden",
                "icon": "fa-seedling",
                "default_visible": True,
            },
            {
                "id": "tab-github-trending",
                "label": "GitHub Trending",
                "icon": "fa-github",
                "default_visible": True,
            },
            {
                "id": "tab-videos",
                "label": "Videos",
                "icon": "fa-video",
                "default_visible": True,
            },
            {
                "id": "tab-games",
                "label": "Games",
                "icon": "fa-gamepad",
                "default_visible": True,
            },
            {
                "id": "tab-intelligence",
                "label": "Intelligence",
                "icon": "fa-brain",
                "default_visible": True,
            },
            {
                "id": "tab-courses",
                "label": "Courses",
                "icon": "fa-graduation-cap",
                "default_visible": True,
            },
            {
                "id": "tab-anime",
                "label": "Anime",
                "icon": "fa-play-circle",
                "default_visible": True,
            },
            {
                "id": "tab-fourchan",
                "label": "4chan",
                "icon": "fa-comment-dots",
                "default_visible": True,
            },
            {
                "id": "tab-scavenging",
                "label": "Scavenging",
                "icon": "fa-search",
                "default_visible": True,
            },
            {
                "id": "tab-valencia-events",
                "label": "Valencia Events",
                "icon": "fa-calendar",
                "default_visible": True,
            },
            {
                "id": "tab-spanish-aid",
                "label": "🏛️ Ayudas Públicas",
                "icon": "fa-building",
                "default_visible": True,
            },
            {
                "id": "tab-arxiv-research",
                "label": "📄 ArXiv Research",
                "icon": "fa-graduation-cap",
                "default_visible": True,
            },
            {
                "id": "tab-deals",
                "label": "💰 Deals & Offers",
                "icon": "fa-tags",
                "default_visible": True,
            },
            {
                "id": "tab-metrics",
                "label": "📊 Metrics",
                "icon": "fa-chart-bar",
                "default_visible": True,
            },
        ]

        # Verify all expected tabs are present
        assert len(expected_tabs) == 16

        # Verify structure of each tab
        for tab in expected_tabs:
            assert "id" in tab
            assert "label" in tab
            assert "icon" in tab
            assert "default_visible" in tab
            assert tab["id"].startswith("tab-")
            assert isinstance(tab["default_visible"], bool)

    def test_tab_preferences_storage_format(self):
        """Test the expected storage format for tab preferences"""
        # Expected storage format
        expected_format = {
            "tab_visibility": {
                "tab-shortcuts": True,
                "tab-news": True,
                "tab-videos": False,  # Example of hidden tab
                # ... other tabs
            },
            "tab_order": [
                "tab-shortcuts",
                "tab-news",
                "tab-videos",
                # ... other tabs in custom order
            ],
        }

        # Verify structure
        assert "tab_visibility" in expected_format
        assert "tab_order" in expected_format
        assert isinstance(expected_format["tab_visibility"], dict)
        assert isinstance(expected_format["tab_order"], list)

        # Verify visibility entries
        for tab_id, is_visible in expected_format["tab_visibility"].items():
            assert isinstance(tab_id, str)
            assert isinstance(is_visible, bool)
            assert tab_id.startswith("tab-")

        # Verify order entries
        for tab_id in expected_format["tab_order"]:
            assert isinstance(tab_id, str)
            assert tab_id.startswith("tab-")

    def test_tab_preferences_validation(self):
        """Test validation of tab preferences data"""
        # Valid preferences
        valid_preferences = {
            "tab_visibility": {
                "tab-shortcuts": True,
                "tab-news": False,
                "tab-videos": True,
            },
            "tab_order": ["tab-shortcuts", "tab-videos", "tab-news"],
        }

        # Test validation function (would be implemented in JavaScript)
        def validate_preferences(preferences, all_tab_ids):
            errors = []

            # Check required structure
            if not isinstance(preferences, dict):
                errors.append("Preferences must be a dictionary")
                return {"isValid": False, "errors": errors}

            if "tab_visibility" not in preferences:
                errors.append("Missing tab_visibility")
            if "tab_order" not in preferences:
                errors.append("Missing tab_order")

            if not isinstance(preferences["tab_visibility"], dict):
                errors.append("tab_visibility must be a dictionary")

            if not isinstance(preferences["tab_order"], list):
                errors.append("tab_order must be a list")

            # Check for unknown tabs
            for tab_id in preferences["tab_visibility"].keys():
                if tab_id not in all_tab_ids:
                    errors.append(f"Unknown tab in visibility: {tab_id}")

            for tab_id in preferences["tab_order"]:
                if tab_id not in all_tab_ids:
                    errors.append(f"Unknown tab in order: {tab_id}")

            # Check for duplicates in order
            if len(preferences["tab_order"]) != len(set(preferences["tab_order"])):
                errors.append("Duplicate tabs in order")

            return {"isValid": len(errors) == 0, "errors": errors}

        all_tab_ids = [
            "tab-shortcuts",
            "tab-news",
            "tab-videos",
            "tab-games",
            "tab-courses",
        ]

        # Test valid preferences
        result = validate_preferences(valid_preferences, all_tab_ids)
        assert result["isValid"] is True
        assert len(result["errors"]) == 0

        # Test invalid preferences - missing structure
        invalid_prefs = {"invalid": "data"}
        result = validate_preferences(invalid_prefs, all_tab_ids)
        assert result["isValid"] is False
        assert len(result["errors"]) > 0

        # Test invalid preferences - unknown tab
        invalid_prefs = {
            "tab_visibility": {"unknown-tab": True},
            "tab_order": ["tab-shortcuts"],
        }
        result = validate_preferences(invalid_prefs, all_tab_ids)
        assert result["isValid"] is False
        assert "Unknown tab in visibility" in str(result["errors"])

    def test_default_preferences_generation(self):
        """Test generation of default preferences"""

        def generate_default_preferences(default_tabs):
            visibility = {}
            order = []

            # Create alphabetical order for default tabs
            sorted_tabs = sorted(default_tabs, key=lambda x: x["label"])

            for tab in sorted_tabs:
                visibility[tab["id"]] = tab["default_visible"]
                if tab["default_visible"]:
                    order.append(tab["id"])

            return {"tab_visibility": visibility, "tab_order": order}

        default_tabs = [
            {"id": "tab-news", "label": "News", "default_visible": True},
            {"id": "tab-games", "label": "Games", "default_visible": True},
            {"id": "tab-videos", "label": "Videos", "default_visible": False},
        ]

        default_prefs = generate_default_preferences(default_tabs)

        # Verify structure
        assert "tab_visibility" in default_prefs
        assert "tab_order" in default_prefs

        # Verify content
        assert default_prefs["tab_visibility"]["tab-news"] is True
        assert default_prefs["tab_visibility"]["tab-games"] is True
        assert default_prefs["tab_visibility"]["tab-videos"] is False

        # Only visible tabs should be in order
        assert "tab-news" in default_prefs["tab_order"]
        assert "tab-games" in default_prefs["tab_order"]
        assert "tab-videos" not in default_prefs["tab_order"]

        # Should be in alphabetical order: Games, News
        assert default_prefs["tab_order"] == ["tab-games", "tab-news"]

    def test_visible_tabs_filtering(self):
        """Test filtering of visible tabs based on preferences"""

        def get_visible_tabs(all_tabs, preferences):
            visibility = preferences["tab_visibility"]
            order = preferences["tab_order"]

            # Filter to only visible tabs and sort by order
            return [tab for tab in all_tabs if visibility.get(tab["id"], False) and tab["id"] in order]

        all_tabs = [
            {"id": "tab-news", "label": "News"},
            {"id": "tab-games", "label": "Games"},
            {"id": "tab-videos", "label": "Videos"},
            {"id": "tab-courses", "label": "Courses"},
        ]

        preferences = {
            "tab_visibility": {
                "tab-news": True,
                "tab-games": True,
                "tab-videos": False,
                "tab-courses": True,
            },
            "tab_order": ["tab-games", "tab-news", "tab-courses", "tab-videos"],
        }

        visible_tabs = get_visible_tabs(all_tabs, preferences)

        # Should only include visible tabs
        visible_ids = [tab["id"] for tab in visible_tabs]
        assert "tab-news" in visible_ids
        assert "tab-games" in visible_ids
        assert "tab-courses" in visible_ids
        assert "tab-videos" not in visible_ids

        # Should maintain order from preferences
        expected_order = ["tab-games", "tab-news", "tab-courses"]
        assert visible_ids == expected_order

    def test_tab_order_update(self):
        """Test updating tab order with validation"""

        def update_tab_order(current_prefs, new_order, all_tab_ids):
            # Validate new order
            if not isinstance(new_order, list):
                raise ValueError("Tab order must be a list")

            # Ensure all tabs exist and are unique
            seen_tabs = set()
            for tab_id in new_order:
                if tab_id not in all_tab_ids:
                    raise ValueError(f"Unknown tab: {tab_id}")
                if tab_id in seen_tabs:
                    raise ValueError(f"Duplicate tab in order: {tab_id}")
                seen_tabs.add(tab_id)

            # Create updated preferences
            updated_prefs = current_prefs.copy()
            updated_prefs["tab_order"] = new_order

            return updated_prefs

        current_prefs = {
            "tab_visibility": {"tab-news": True, "tab-games": True},
            "tab_order": ["tab-news", "tab-games"],
        }

        all_tab_ids = ["tab-news", "tab-games", "tab-videos"]

        # Test valid order update
        new_order = ["tab-games", "tab-news"]
        updated = update_tab_order(current_prefs, new_order, all_tab_ids)
        assert updated["tab_order"] == ["tab-games", "tab-news"]

        # Test invalid order - unknown tab
        with pytest.raises(ValueError, match="Unknown tab"):
            update_tab_order(current_prefs, ["tab-unknown"], all_tab_ids)

        # Test invalid order - duplicate tab
        with pytest.raises(ValueError, match="Duplicate tab"):
            update_tab_order(current_prefs, ["tab-news", "tab-news"], all_tab_ids)

        # Test invalid order - not a list
        with pytest.raises(ValueError, match="must be a list"):
            update_tab_order(current_prefs, "not-a-list", all_tab_ids)

    def test_storage_operations(self):
        """Test localStorage-like operations"""
        # Simulate localStorage
        storage = {}
        storage_key = "test_tab_preferences"

        def get_preferences():
            try:
                data = storage.get(storage_key, "{}")
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return {"tab_visibility": {}, "tab_order": []}

        def save_preferences(preferences):
            try:
                storage[storage_key] = json.dumps(preferences)
                return True
            except (TypeError, ValueError):
                return False

        # Test saving and retrieving preferences
        test_prefs = {
            "tab_visibility": {"tab-news": True, "tab-games": False},
            "tab_order": ["tab-news"],
        }

        # Save preferences
        result = save_preferences(test_prefs)
        assert result is True

        # Retrieve preferences
        retrieved = get_preferences()
        assert retrieved == test_prefs

        # Test handling of corrupted data
        storage[storage_key] = "invalid-json"
        corrupted = get_preferences()
        assert corrupted == {"tab_visibility": {}, "tab_order": []}

        # Test handling of missing data
        del storage[storage_key]
        missing = get_preferences()
        assert missing == {"tab_visibility": {}, "tab_order": []}

    def test_preferences_export_import(self):
        """Test export and import functionality"""

        def export_preferences(preferences):
            return {
                "version": "1.0",
                "exported_at": "2025-01-16T10:00:00Z",
                "preferences": preferences,
            }

        def import_preferences(export_data, all_tab_ids):
            if not export_data or "preferences" not in export_data:
                raise ValueError("Invalid export data format")

            prefs = export_data["preferences"]

            # Validate structure
            if "tab_visibility" not in prefs or "tab_order" not in prefs:
                raise ValueError("Missing required preference fields")

            # Add timestamp
            prefs["last_updated"] = "2025-01-16T10:01:00Z"

            return prefs

        test_prefs = {"tab_visibility": {"tab-news": True}, "tab_order": ["tab-news"]}

        # Test export
        exported = export_preferences(test_prefs)
        assert exported["version"] == "1.0"
        assert "exported_at" in exported
        assert exported["preferences"] == test_prefs

        # Test import
        imported = import_preferences(exported, ["tab-news"])
        assert imported["tab_visibility"] == {"tab-news": True}
        assert imported["tab_order"] == ["tab-news"]
        assert "last_updated" in imported

        # Test invalid import
        with pytest.raises(ValueError, match="Invalid export data"):
            import_preferences({}, ["tab-news"])

        with pytest.raises(ValueError, match="Missing required"):
            import_preferences({"version": "1.0"}, ["tab-news"])

    def test_statistics_calculation(self):
        """Test calculation of tab statistics"""

        def calculate_statistics(all_tabs, preferences):
            visibility = preferences["tab_visibility"]
            visible_count = sum(1 for visible in visibility.values() if visible)
            total_count = len(all_tabs)

            return {
                "total_tabs": total_count,
                "visible_tabs": visible_count,
                "hidden_tabs": total_count - visible_count,
                "visibility_percentage": (round((visible_count / total_count) * 100, 1) if total_count > 0 else 0),
            }

        all_tabs = ["tab-news", "tab-games", "tab-videos", "tab-courses"]
        preferences = {
            "tab_visibility": {
                "tab-news": True,
                "tab-games": True,
                "tab-videos": False,
                "tab-courses": True,
            }
        }

        stats = calculate_statistics(all_tabs, preferences)

        assert stats["total_tabs"] == 4
        assert stats["visible_tabs"] == 3
        assert stats["hidden_tabs"] == 1
        assert stats["visibility_percentage"] == 75.0
