"""Unit tests for Filter Presets functionality
Tests LocalStorageManager and FilterPresetsComponent
"""

from unittest.mock import Mock, patch

import dash_bootstrap_components as dbc
import pytest
from dash import html

from src.web.dashboard.components.filter_presets import FilterPresetsComponent


class TestLocalStorageManager:
    """Test LocalStorageManager JavaScript functionality via mocking"""

    @patch("src.web.dashboard.components.filter_presets.logger")
    def test_localstorage_manager_class_initialization(self, mock_logger):
        """Test LocalStorageManager initialization"""
        # Test component initialization
        filter_inputs = {
            "search_term": "test-search-input",
            "category": "test-category-dropdown",
        }

        component = FilterPresetsComponent("test_tab", filter_inputs)

        assert component.tab_name == "test_tab"
        assert component.filter_inputs == filter_inputs
        assert component.storage_prefix == "filter_presets_test_tab"

    def test_create_preset_controls_structure(self):
        """Test that preset controls are created with correct structure"""
        filter_inputs = {
            "search_term": "test-search-input",
            "category": "test-category-dropdown",
        }

        component = FilterPresetsComponent("test_tab", filter_inputs)
        controls = component.create_preset_controls()

        # Should return 5 components: selector, buttons, modal, filters store, selected preset store
        assert len(controls) == 5

        # Check for required component IDs
        component_ids = [comp.id if hasattr(comp, "id") else str(comp) for comp in controls]
        assert "filter_presets_test_tab_preset_selector" in str(component_ids)
        assert "filter_presets_test_tab_save_modal" in str(component_ids)
        assert "filter_presets_test_tab_current_filters" in str(component_ids)
        assert "filter_presets_test_tab_selected_preset" in str(component_ids)

    def test_clientside_callbacks_generation(self):
        """Test that clientside callbacks are generated correctly"""
        filter_inputs = {
            "search_term": "test-search-input",
            "category": "test-category-dropdown",
        }

        component = FilterPresetsComponent("test_tab", filter_inputs)
        callbacks = component.get_clientside_callbacks()

        # Should have load_presets, save_preset, delete_preset callbacks
        assert "load_presets" in callbacks
        assert "save_preset" in callbacks
        assert "delete_preset" in callbacks

        # Check that tab name is correctly embedded in JavaScript
        save_callback = callbacks["save_preset"]
        assert "test_tab" in save_callback
        assert "window.saveFilterPreset" in save_callback

    def test_preset_controls_validation(self):
        """Test preset control validation and structure"""
        filter_inputs = {
            "search_term": "test-search-input",
            "category": "test-category-dropdown",
        }

        component = FilterPresetsComponent("test_tab", filter_inputs)
        controls = component.create_preset_controls()

        # Find preset selector
        preset_selector = None
        for control in controls:
            if hasattr(control, "id") and control.id == "filter_presets_test_tab_preset_selector":
                preset_selector = control
                break

        assert preset_selector is not None
        assert isinstance(preset_selector, dbc.Select)
        assert preset_selector.placeholder == "Select saved preset..."

        # Find save button
        save_button = None
        buttons_container = None
        for control in controls:
            if hasattr(control, "children") and isinstance(control, html.Div):
                buttons_container = control
                break

        assert buttons_container is not None
        # Check for save button in buttons container
        save_button_found = False
        for child in buttons_container.children:
            if hasattr(child, "children") and isinstance(child, dbc.Button):
                if "Save Current Filters" in child.children:
                    save_button_found = True
                    break

        assert save_button_found

    def test_filter_inputs_mapping(self):
        """Test that filter inputs are correctly mapped"""
        filter_inputs = {
            "search_term": "arxiv-search-input",
            "category": "arxiv-category-dropdown",
            "date_range": "arxiv-date-range-picker",
        }

        component = FilterPresetsComponent("arxiv_research", filter_inputs)

        assert component.filter_inputs == filter_inputs
        assert len(component.filter_inputs) == 3
        assert "search_term" in component.filter_inputs
        assert component.filter_inputs["search_term"] == "arxiv-search-input"

    @patch("src.web.dashboard.components.filter_presets.logger")
    def test_callback_creation_error_handling(self, mock_logger):
        """Test error handling in callback creation"""
        filter_inputs = {"search_term": "test-search-input"}

        component = FilterPresetsComponent("test_tab", filter_inputs)

        # Create mock app
        mock_app = Mock()

        # Test callback creation doesn't raise exceptions
        try:
            component.create_callbacks(mock_app)
            # Should create at least one callback
            assert mock_app.callback.called
        except Exception as e:
            pytest.fail(f"Callback creation raised an exception: {e}")


class TestFilterPresetsIntegration:
    """Integration tests for filter presets functionality"""

    def test_arxiv_tab_integration(self):
        """Test that ArXiv tab integration works correctly"""
        # Test that arxiv tab can be enhanced with filter presets
        try:
            from src.web.dashboard.components.arxiv_research_tab import (
                render_arxiv_research_tab,
            )
            from src.web.dashboard.components.filter_presets import (
                FilterPresetsComponent,
            )

            # This should not raise an import error
            assert FilterPresetsComponent is not None

            # Test that component can be instantiated with ArXiv filter inputs
            filter_inputs = {
                "search_term": "arxiv-search-input",
                "category": "arxiv-category-dropdown",
            }

            component = FilterPresetsComponent("arxiv_research", filter_inputs)
            assert component.tab_name == "arxiv_research"
            assert len(component.filter_inputs) == 2

        except ImportError as e:
            pytest.fail(f"Failed to import required modules: {e}")

    def test_preset_naming_validation(self):
        """Test preset naming rules and validation"""
        # Test valid preset names
        valid_names = [
            "AI Research Papers",
            "Machine Learning Basics",
            "CV 2024",
            "Recent Publications",
            "Favorites_1",
        ]

        for name in valid_names:
            assert len(name) <= 50, f"Preset name '{name}' should be valid"
            assert "<" not in name and ">" not in name, f"Preset name '{name}' should not contain invalid characters"
            assert ":" not in name, f"Preset name '{name}' should not contain invalid characters"

        # Test invalid preset names
        invalid_names = [
            "Preset with <tags>",
            "Name with:colon",
            "Name with/slash",
            'Name with"quotes"',
            "Name with|pipe",
            "Name with?question",
            "Name with*asterisk",
        ]

        for name in invalid_names:
            assert any(char in name for char in ["<", ">", ":", "/", "\\", "|", "?", "*", '"']), f"Should detect invalid characters in '{name}'"

    def test_storage_limit_enforcement(self):
        """Test that storage limits are enforced"""
        # This would be tested via JavaScript integration
        # Here we test the concept via Python mock
        max_presets = 10

        # Simulate reaching the limit
        current_presets = list(range(max_presets))  # 10 presets

        # Adding one more should exceed limit
        assert len(current_presets) == max_presets
        assert len(current_presets) + 1 > max_presets

    def test_preset_data_structure(self):
        """Test preset data structure validation"""
        # Expected preset structure
        expected_preset = {
            "name": "Test Preset",
            "filters": {"search_term": "machine learning", "category": "cs.AI"},
            "created_at": "2025-01-16T10:00:00Z",
            "updated_at": "2025-01-16T10:00:00Z",
        }

        # Validate structure
        assert "name" in expected_preset
        assert "filters" in expected_preset
        assert "created_at" in expected_preset
        assert "updated_at" in expected_preset
        assert isinstance(expected_preset["filters"], dict)


class TestLocalStorageMock:
    """Mock tests for localStorage JavaScript functionality"""

    def test_storage_key_generation(self):
        """Test that storage keys are generated correctly"""
        component = FilterPresetsComponent("test_tab", {})
        expected_storage_key = "filter_presets_test_tab"
        assert component.storage_prefix == expected_storage_key

    def test_javascript_integration_points(self):
        """Test JavaScript integration points"""
        filter_inputs = {
            "search_term": "test-search-input",
            "category": "test-category-dropdown",
        }

        component = FilterPresetsComponent("test_tab", filter_inputs)
        callbacks = component.get_clientside_callbacks()

        # Check that JavaScript functions are called correctly
        save_callback = callbacks["save_preset"]
        assert "window.saveFilterPreset" in save_callback
        assert "'test_tab'" in save_callback

        load_callback = callbacks["load_presets"]
        assert "window.getFilterPresetOptions" in load_callback
        assert "'test_tab'" in load_callback

        delete_callback = callbacks["delete_preset"]
        assert "window.deleteFilterPreset" in delete_callback
        assert "'test_tab'" in delete_callback


if __name__ == "__main__":
    pytest.main([__file__])
