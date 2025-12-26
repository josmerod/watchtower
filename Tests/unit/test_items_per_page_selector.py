"""Unit tests for Items Per Page Selector component"""

from unittest.mock import Mock, patch

import pytest

from src.web.dashboard.components.items_per_page_selector import (
    create_items_per_page_selector,
    load_initial_preference,
    register_items_per_page_callback,
)


class TestItemsPerPageSelector:
    """Test cases for items-per-page selector component"""

    def test_create_items_per_page_selector(self):
        """Test creating items-per-page selector component"""
        selector = create_items_per_page_selector("videos", default_value=48)

        # Check that it's a Bootstrap Col component
        assert hasattr(selector, "children")

        # Check that it contains the expected components
        children = selector.children if hasattr(selector, "children") else []
        labels = [child for child in children if hasattr(child, "children") and "Items per page:" in str(child.children)]

        # Should contain the label
        assert len(labels) > 0, "Should contain 'Items per page:' label"

        # Should have proper width configuration
        assert hasattr(selector, "width")
        assert selector.width == 12
        assert selector.md == 2
        assert selector.lg == 2

    # def test_create_items_per_page_selector_different_sizes(self):
    #     """Test creating selector with different sizes"""
    #     # Feature not implemented
    #     pass

    def test_create_items_per_page_selector_different_defaults(self):
        """Test creating selector with different default values"""
        selector_24 = create_items_per_page_selector("arxiv", default_value=24)
        selector_96 = create_items_per_page_selector("deals", default_value=96)

        # Both should be created successfully
        assert selector_24 is not None
        assert selector_96 is not None

    def test_load_initial_preference(self):
        """Test generation of initial preference loading script"""
        script = load_initial_preference("videos")

        # Should be a script string
        assert isinstance(script, str)

        # Should contain the tab name
        script_content = script
        assert "videos" in script_content
        assert "itemsPerPageManager" in script_content
        assert "getPreference" in script_content

    @patch("src.web.dashboard.components.items_per_page_selector.clientside_callback")
    def test_register_items_per_page_callback(self, mock_clientside_callback):
        """Test registration of client-side callback"""
        # Mock app object
        mock_app = Mock()

        # Register callback
        register_items_per_page_callback("videos")

        # Verify that clientside_callback was called
        mock_clientside_callback.assert_called_once()

        # Get the callback arguments
        args, kwargs = mock_clientside_callback.call_args

        # Check that the callback function contains the tab name
        callback_function = args[0]
        assert "videos" in callback_function

        # Check output and input parameters
        # Check output and input parameters in positional args
        # args[0] is code, args[1] is Output, args[2] is Input
        # Note: args contents might be Dash objects, check str representation or id
        output_arg = args[1]
        input_arg = args[2]
        
        assert "videos-items-per-page-select" in str(output_arg)
        assert "videos-items-per-page-select" in str(input_arg)
        assert kwargs["prevent_initial_call"] is True


class TestItemsPerPageSelectorIntegration:
    """Integration tests for items-per-page selector"""

    def test_selector_with_valid_tab_names(self):
        """Test selector creation with various valid tab names"""
        valid_tabs = ["videos", "arxiv", "news", "deals", "courses", "games"]

        for tab_name in valid_tabs:
            selector = create_items_per_page_selector(tab_name)
            assert selector is not None
            # The selector should have the correct ID structure
            selector_str = str(selector)
            assert tab_name in selector_str.lower()

    def test_selector_with_special_characters(self):
        """Test selector creation with tab names containing special characters"""
        special_tabs = ["knowledge-garden", "spanish-aid", "giveaways"]

        for tab_name in special_tabs:
            selector = create_items_per_page_selector(tab_name)
            assert selector is not None
            selector_str = str(selector)
            # Should handle hyphenated names correctly
            assert tab_name.replace("-", "") in selector_str.replace("-", "")

    def test_load_initial_preference_format(self):
        """Test that initial preference loading script has correct format"""
        script = load_initial_preference("test-tab")

        # Should be a string that contains JavaScript code
        script_content = script

        # Should contain necessary JavaScript elements
        required_elements = [
            "window.itemsPerPageManager",
            "getPreference",
            "getElementById",
            "test-tab-items-per-page-select",
            ".querySelector",
            ".value",
        ]

        for element in required_elements:
            assert element in script_content, f"Script should contain {element}"


class TestItemsPerPageSelectorErrorHandling:
    """Test error handling for items-per-page selector"""

    def test_create_selector_with_empty_tab_name(self):
        """Test selector creation with empty tab name"""
        # Should not raise an exception
        selector = create_items_per_page_selector("")
        assert selector is not None

    def test_create_selector_with_none_tab_name(self):
        """Test selector creation with None tab name"""
        # Should not raise an exception
        selector = create_items_per_page_selector(None)
        assert selector is not None

    def test_load_initial_preference_with_special_characters(self):
        """Test initial preference loading with special characters in tab name"""
        special_tabs = ["tab_with_underscore", "tab-with-dash", "TabWithCaps"]

        for tab_name in special_tabs:
            script = load_initial_preference(tab_name)
            script_content = script

            # Should handle various naming conventions
            assert tab_name in script_content or tab_name.lower() in script_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
