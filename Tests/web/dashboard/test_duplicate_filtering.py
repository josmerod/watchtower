"""Tests for dashboard duplicate filtering utilities."""

import json
import tempfile
from pathlib import Path

import pytest

from src.web.dashboard.deduplication_utils import (
    filter_duplicates,
    get_duplicate_groups,
    get_duplicate_summary,
    create_show_duplicates_button,
    load_and_filter_data,
    enhance_item_with_duplicate_info,
)


class TestDuplicateFiltering:
    """Test suite for dashboard duplicate filtering utilities."""

    def test_filter_duplicates_show_false(self):
        """Test filtering duplicates when show_duplicates is False."""
        data = [
            {"id": 1, "title": "Item 1", "is_duplicate": False},
            {"id": 2, "title": "Item 2", "is_duplicate": True},
            {"id": 3, "title": "Item 3", "is_duplicate": False},
            {"id": 4, "title": "Item 4", "is_duplicate": True},
        ]

        result = filter_duplicates(data, show_duplicates=False)

        # Should return only non-duplicate items
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3

        # All returned items should have is_duplicate=False
        for item in result:
            assert item.get("is_duplicate", False) is False

    def test_filter_duplicates_show_true(self):
        """Test filtering duplicates when show_duplicates is True."""
        data = [
            {"id": 1, "title": "Item 1", "is_duplicate": False},
            {"id": 2, "title": "Item 2", "is_duplicate": True},
            {"id": 3, "title": "Item 3", "is_duplicate": False},
        ]

        result = filter_duplicates(data, show_duplicates=True)

        # Should return all items
        assert len(result) == 3
        assert result == data

    def test_filter_duplicates_no_is_duplicate_field(self):
        """Test filtering items without is_duplicate field."""
        data = [
            {"id": 1, "title": "Item 1"},
            {"id": 2, "title": "Item 2"},
        ]

        result = filter_duplicates(data, show_duplicates=False)

        # Should return all items (default to non-duplicate)
        assert len(result) == 2
        assert result == data

    def test_filter_duplicates_empty_data(self):
        """Test filtering empty data."""
        result = filter_duplicates([], show_duplicates=False)
        assert result == []

    def test_get_duplicate_groups(self):
        """Test grouping items by duplicate_group_id."""
        data = [
            {"id": 1, "title": "Item 1", "duplicate_group_id": "group1", "is_duplicate": False},
            {"id": 2, "title": "Item 2", "duplicate_group_id": "group1", "is_duplicate": True},
            {"id": 3, "title": "Item 3", "duplicate_group_id": "group2", "is_duplicate": True},
            {"id": 4, "title": "Item 4", "duplicate_group_id": "group2", "is_duplicate": False},
            {"id": 5, "title": "Item 5"},  # No group
        ]

        groups = get_duplicate_groups(data)

        # Should find 2 groups
        assert len(groups) == 2
        assert "group1" in groups
        assert "group2" in groups

        # Check group contents
        assert len(groups["group1"]) == 2
        assert len(groups["group2"]) == 2

        group1_ids = {item["id"] for item in groups["group1"]}
        group2_ids = {item["id"] for item in groups["group2"]}

        assert group1_ids == {1, 2}
        assert group2_ids == {3, 4}

    def test_get_duplicate_groups_no_groups(self):
        """Test getting groups when no items have duplicate_group_id."""
        data = [
            {"id": 1, "title": "Item 1"},
            {"id": 2, "title": "Item 2"},
        ]

        groups = get_duplicate_groups(data)

        # Should return empty dict
        assert groups == {}

    def test_get_duplicate_summary(self):
        """Test getting duplicate summary statistics."""
        data = [
            {"id": 1, "title": "Item 1", "is_duplicate": False, "duplicate_group_id": None},
            {"id": 2, "title": "Item 2", "is_duplicate": True, "duplicate_group_id": "group1"},
            {"id": 3, "title": "Item 3", "is_duplicate": True, "duplicate_group_id": "group1"},
            {"id": 4, "title": "Item 4", "is_duplicate": True, "duplicate_group_id": "group2"},
            {"id": 5, "title": "Item 5", "is_duplicate": False, "duplicate_group_id": None},
        ]

        summary = get_duplicate_summary(data)

        assert summary["total_items"] == 5
        assert summary["unique_items"] == 2
        assert summary["duplicate_items"] == 3
        assert summary["duplicate_groups"] == 2

    def test_get_duplicate_summary_no_duplicates(self):
        """Test summary when no duplicates exist."""
        data = [
            {"id": 1, "title": "Item 1", "is_duplicate": False},
            {"id": 2, "title": "Item 2", "is_duplicate": False},
        ]

        summary = get_duplicate_summary(data)

        assert summary["total_items"] == 2
        assert summary["unique_items"] == 2
        assert summary["duplicate_items"] == 0
        assert summary["duplicate_groups"] == 0

    def test_create_show_duplicates_button_with_duplicates(self):
        """Test creating button when duplicates exist."""
        data = [
            {"id": 1, "title": "Item 1", "is_duplicate": False},
            {"id": 2, "title": "Item 2", "is_duplicate": True},
        ]

        button = create_show_duplicates_button("test-button", data, False)

        # Check button properties (will be a Dash component)
        assert button is not None
        # Button should be enabled (has duplicates)
        assert button.disabled is False

    def test_create_show_duplicates_button_no_duplicates(self):
        """Test creating button when no duplicates exist."""
        data = [
            {"id": 1, "title": "Item 1", "is_duplicate": False},
            {"id": 2, "title": "Item 2", "is_duplicate": False},
        ]

        button = create_show_duplicates_button("test-button", data, False)

        # Button should be disabled (no duplicates)
        assert button.disabled is True

    def test_create_show_duplicates_button_custom_text(self):
        """Test creating button with custom text."""
        data = []

        button = create_show_duplicates_button(
            "test-button",
            data,
            False,
            button_text="Custom Button Text"
        )

        # Should use custom text
        assert button.children == "Custom Button Text"

    def test_load_and_filter_data_file_not_found(self):
        """Test loading data when file doesn't exist."""
        non_existent_file = "/tmp/non_existent_file.json"

        result = load_and_filter_data(non_existent_file)

        # Should return empty list
        assert result == []

    def test_load_and_filter_data_valid_file(self):
        """Test loading and filtering data from valid file."""
        # Create temporary file with test data
        test_data = [
            {"id": 1, "title": "Item 1", "is_duplicate": False},
            {"id": 2, "title": "Item 2", "is_duplicate": True},
            {"id": 3, "title": "Item 3", "is_duplicate": False},
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            # Load without showing duplicates
            result = load_and_filter_data(temp_file, show_duplicates=False)

            # Should return only non-duplicate items
            assert len(result) == 2
            assert all(not item.get("is_duplicate", False) for item in result)

            # Load with showing duplicates
            result_with_duplicates = load_and_filter_data(temp_file, show_duplicates=True)

            # Should return all items
            assert len(result_with_duplicates) == 3

        finally:
            # Clean up
            Path(temp_file).unlink()

    def test_load_and_filter_data_with_max_items(self):
        """Test loading data with max_items limit."""
        # Create temporary file with many items
        test_data = [
            {"id": i, "title": f"Item {i}", "is_duplicate": i % 3 == 0}
            for i in range(10)
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            # Load with max_items limit
            result = load_and_filter_data(temp_file, max_items=5)

            # Should return at most 5 items
            assert len(result) <= 5

        finally:
            # Clean up
            Path(temp_file).unlink()

    def test_load_and_filter_data_single_object(self):
        """Test loading data when file contains single object instead of array."""
        single_object = {"id": 1, "title": "Single Item", "is_duplicate": False}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(single_object, f)
            temp_file = f.name

        try:
            result = load_and_filter_data(temp_file)

            # Should handle single object correctly
            assert len(result) == 1
            assert result[0]["id"] == 1

        finally:
            # Clean up
            Path(temp_file).unlink()

    def test_enhance_item_with_duplicate_info(self):
        """Test enhancing item with duplicate display information."""
        item = {
            "id": 1,
            "title": "Test Item",
            "is_duplicate": True,
            "duplicate_group_id": "group1",
            "quality_score": 85.5
        }

        enhanced = enhance_item_with_duplicate_info(item)

        # Should add duplicate badge info
        assert enhanced["duplicate_badge"] == "Duplicate"
        assert enhanced["duplicate_color"] == "warning"

        # Should add quality display
        assert enhanced["quality_display"] == "Quality: 85.5/100"

        # Should preserve original fields
        assert enhanced["id"] == 1
        assert enhanced["title"] == "Test Item"

    def test_enhance_item_original_duplicate_info(self):
        """Test enhancing original (non-duplicate) item."""
        item = {
            "id": 1,
            "title": "Test Item",
            "is_duplicate": False,
            "duplicate_group_id": "group1",
            "quality_score": 90.0
        }

        enhanced = enhance_item_with_duplicate_info(item)

        # Should add original badge info
        assert enhanced["duplicate_badge"] == "Original"
        assert enhanced["duplicate_color"] == "success"

    def test_enhance_item_no_duplicate_info(self):
        """Test enhancing item without duplicate information."""
        item = {
            "id": 1,
            "title": "Test Item"
        }

        enhanced = enhance_item_with_duplicate_info(item)

        # Should default to original status
        assert enhanced["duplicate_badge"] == "Original"
        assert enhanced["duplicate_color"] == "success"

    def test_enhance_item_no_quality_score(self):
        """Test enhancing item without quality score."""
        item = {
            "id": 1,
            "title": "Test Item",
            "is_duplicate": False
        }

        enhanced = enhance_item_with_duplicate_info(item)

        # Should not add quality display
        assert "quality_display" not in enhanced

    def test_enhance_item_with_quality_score(self):
        """Test enhancing item with quality score."""
        item = {
            "id": 1,
            "title": "Test Item",
            "quality_score": 75.3
        }

        enhanced = enhance_item_with_duplicate_info(item)

        # Should add quality display
        assert enhanced["quality_display"] == "Quality: 75.3/100"


if __name__ == "__main__":
    pytest.main([__file__])