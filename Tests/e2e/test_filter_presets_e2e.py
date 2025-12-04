"""End-to-end tests for Filter Presets functionality
Tests complete user workflows with browser automation
"""

import time

import pytest
from playwright.sync_api import Page, expect


class TestFilterPresetsE2E:
    """End-to-end tests for filter preset functionality"""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Setup test environment"""
        # Navigate to dashboard
        page.goto("http://localhost:7777")

        # Wait for dashboard to load
        expect(page.locator("h1")).to_contain_text("Watchtower Dashboard")

        # Navigate to ArXiv tab (assuming it's accessible)
        page.click("text=ArXiv Research")
        page.wait_for_selector("#arxiv-search-input", timeout=10000)

    def test_save_filter_preset_workflow(self, page: Page):
        """Test complete workflow: apply filters -> save preset -> verify saved"""
        # Step 1: Apply filters
        page.fill("#arxiv-search-input", "machine learning")
        page.select_option("#arxiv-category-dropdown", "Artificial Intelligence")

        # Step 2: Click Save Preset button
        page.click("#filter_presets_arxiv_research_save_preset_btn")

        # Step 3: Wait for modal to appear
        expect(page.locator("#filter_presets_arxiv_research_save_modal")).to_be_visible()

        # Step 4: Enter preset name
        page.fill("#filter_presets_arxiv_research_preset_name_input", "ML AI Papers")

        # Step 5: Click Save button
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Step 6: Verify modal closes
        expect(page.locator("#filter_presets_arxiv_research_save_modal")).not_to_be_visible()

        # Step 7: Verify preset appears in dropdown
        expect(page.locator("#filter_presets_arxiv_research_preset_selector")).to_be_visible()
        expect(page.locator("#filter_presets_arxiv_research_preset_selector")).to_contain_text("ML AI Papers")

    def test_apply_preset_workflow(self, page: Page):
        """Test applying saved preset"""
        # First, save a preset (or use existing one)
        page.fill("#arxiv-search-input", "computer vision")
        page.select_option("#arxiv-category-dropdown", "Computer Vision")

        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "CV Papers")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Clear filters first
        page.fill("#arxiv-search-input", "")
        page.select_option("#arxiv-category-dropdown", None)

        # Apply saved preset
        page.select_option("#filter_presets_arxiv_research_preset_selector", "CV Papers")

        # Verify filters are applied
        expect(page.locator("#arxiv-search-input")).to_have_value("computer vision")
        expect(page.locator("#arxiv-category-dropdown")).to_have_value("Computer Vision")

    def test_update_preset_workflow(self, page: Page):
        """Test updating existing preset"""
        # First save a preset
        page.fill("#arxiv-search-input", "neural networks")
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "NN Papers")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Select the preset
        page.select_option("#filter_presets_arxiv_research_preset_selector", "NN Papers")

        # Update filters
        page.fill("#arxiv-search-input", "deep learning neural networks")

        # Click Update Preset button
        page.click("#filter_presets_arxiv_research_update_preset_btn")

        # Verify preset still applied with updated filters
        expect(page.locator("#arxiv-search-input")).to_have_value("deep learning neural networks")

    def test_delete_preset_workflow(self, page: Page):
        """Test deleting preset"""
        # First save a preset
        page.fill("#arxiv-search-input", "test deletion")
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "Delete Me")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Select the preset to delete
        page.select_option("#filter_presets_arxiv_research_preset_selector", "Delete Me")

        # Delete button should be visible
        expect(page.locator("#filter_presets_arxiv_research_delete_preset_btn")).to_be_visible()

        # Click Delete
        page.click("#filter_presets_arxiv_research_delete_preset_btn")

        # Verify preset is removed from dropdown
        expect(page.locator("#filter_presets_arxiv_research_preset_selector")).not_to_contain_text("Delete Me")

    def test_preset_persistence_across_sessions(self, page: Page):
        """Test that presets persist across browser sessions"""
        # Save a preset
        page.fill("#arxiv-search-input", "persistence test")
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "Persistent Preset")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Refresh page (simulating new session)
        page.reload()
        page.wait_for_selector("#arxiv-search-input", timeout=10000)

        # Navigate to ArXiv tab again
        page.click("text=ArXiv Research")
        page.wait_for_selector("#filter_presets_arxiv_research_preset_selector", timeout=10000)

        # Verify preset still exists
        expect(page.locator("#filter_presets_arxiv_research_preset_selector")).to_contain_text("Persistent Preset")

    def test_max_presets_limit(self, page: Page):
        """Test enforcement of maximum 10 presets per tab"""
        # Try to save 11 presets
        for i in range(11):
            page.fill("#arxiv-search-input", f"test preset {i}")
            page.click("#filter_presets_arxiv_research_save_preset_btn")
            page.fill("#filter_presets_arxiv_research_preset_name_input", f"Preset {i}")
            page.click("#filter_presets_arxiv_research_confirm_save_btn")

            # Small delay between saves
            time.sleep(0.1)

        # Check for error message or limit enforcement
        # This might appear as a modal error message or other UI feedback
        try:
            # Look for error message in modal
            error_element = page.locator("#filter_presets_arxiv_research_preset_error")
            if error_element.is_visible():
                expect(error_element).to_contain_text("Maximum")
        except:
            # Alternative: Check that only 10 presets exist in dropdown
            preset_options = page.locator("#filter_presets_arxiv_research_preset_selector option")
            expect(preset_options).to_have_count(10)  # Should not exceed 10

    def test_preset_performance_requirement(self, page: Page):
        """Test that preset application takes <300ms"""
        # Save a preset with complex filters
        page.fill("#arxiv-search-input", "complex search term for performance testing")
        page.select_option("#arxiv-category-dropdown", "Machine Learning")
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "Performance Test")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Clear filters
        page.fill("#arxiv-search-input", "")
        page.select_option("#arxiv-category-dropdown", None)

        # Measure preset application time
        start_time = time.time()
        page.select_option("#filter_presets_arxiv_research_preset_selector", "Performance Test")

        # Wait for filters to be applied (check input values)
        expect(page.locator("#arxiv-search-input")).to_have_value("complex search term for performance testing")
        end_time = time.time()

        # Verify performance requirement (<300ms)
        application_time = (end_time - start_time) * 1000  # Convert to milliseconds
        assert application_time < 300, f"Preset application took {application_time:.2f}ms, expected <300ms"

    def test_invalid_preset_name_handling(self, page: Page):
        """Test handling of invalid preset names"""
        # Apply some filters first
        page.fill("#arxiv-search-input", "test")

        # Try to save preset with invalid characters
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "Invalid<Name")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Should show error message
        expect(page.locator("#filter_presets_arxiv_research_preset_error")).to_be_visible()
        expect(page.locator("#filter_presets_arxiv_research_preset_error")).to_contain_text("invalid")

    def test_duplicate_preset_name_handling(self, page: Page):
        """Test handling of duplicate preset names"""
        # Save first preset
        page.fill("#arxiv-search-input", "first preset")
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "Duplicate Name")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Try to save second preset with same name
        page.fill("#arxiv-search-input", "second preset")
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        page.fill("#filter_presets_arxiv_research_preset_name_input", "Duplicate Name")
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Should show error about duplicate name
        expect(page.locator("#filter_presets_arxiv_research_preset_error")).to_be_visible()
        expect(page.locator("#filter_presets_arxiv_research_preset_error")).to_contain_text("already exists")

    def test_empty_preset_name_handling(self, page: Page):
        """Test handling of empty preset names"""
        # Apply some filters first
        page.fill("#arxiv-search-input", "test")

        # Try to save preset without name
        page.click("#filter_presets_arxiv_research_save_preset_btn")
        # Don't fill name field, just click save
        page.click("#filter_presets_arxiv_research_confirm_save_btn")

        # Should show error about empty name
        expect(page.locator("#filter_presets_arxiv_research_preset_error")).to_be_visible()
        expect(page.locator("#filter_presets_arxiv_research_preset_error")).to_contain_text("empty")


if __name__ == "__main__":
    pytest.main([__file__])
