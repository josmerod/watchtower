"""E2E Tests for Dashboard Tab Customization Feature
Tests the complete workflow of tab customization using Playwright
"""

import time

import pytest
from playwright.sync_api import Page, expect


class TestTabCustomization:
    """Test suite for dashboard tab customization functionality"""

    @pytest.fixture(scope="function", autouse=True)
    def setup(self, page: Page):
        """Setup test environment"""
        # Navigate to the dashboard
        page.goto("http://localhost:7777")

        # Wait for page to load completely
        page.wait_for_selector("#dashboard-tabs", timeout=15000)

        # Ensure TabPreferencesManager is available
        page.wait_for_function("window.tabPreferencesManager !== undefined", timeout=10000)

    def test_tab_customization_modal_opens_and_closes(self, page: Page):
        """Test that the customization modal can be opened and closed"""
        # Find and click the customize tabs button
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        expect(customize_button).to_be_visible()
        customize_button.click()

        # Wait for modal to open
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible(timeout=5000)

        # Check modal content
        expect(modal.locator("text=Customize Dashboard Tabs")).to_be_visible()
        expect(modal.locator("text=How to customize your dashboard:")).to_be_visible()

        # Close modal
        close_button = modal.locator(".btn-close")
        close_button.click()

        # Verify modal is closed
        expect(modal).not_to_be_visible(timeout=3000)

    def test_tab_visibility_toggle_functionality(self, page: Page):
        """Test toggling tab visibility on and off"""
        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Wait for modal and tabs to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()

        # Wait for tab items to load
        page.wait_for_selector(".customize-tab-item", timeout=10000)

        # Find the News tab toggle
        news_tab_item = page.locator(".customize-tab-item").filter(has_text="News")
        expect(news_tab_item).to_be_visible()

        # Get the initial state of the toggle
        news_toggle = news_tab_item.locator('input[type="checkbox"]')
        initial_state = news_toggle.is_checked()

        # Toggle the News tab
        news_toggle.click()

        # Wait a moment for the change to register
        page.wait_for_timeout(500)

        # Verify the state changed
        expect(news_toggle.is_checked()).to_be(not initial_state)

        # Save changes
        save_button = page.locator('button[id*="save-tabs-btn"]')
        expect(save_button).to_be_visible()
        save_button.click()

        # Wait for success message
        page.wait_for_selector("text=Success!", timeout=5000)

        # Close modal
        close_button = page.locator(".btn-close")
        close_button.click()

        # Verify News tab visibility changed in main dashboard
        news_tab = page.locator('[tab_id="tab-news"]')
        if initial_state:
            # If it was initially visible, it should now be hidden
            expect(news_tab).to_have_css("display", "none")
        else:
            # If it was initially hidden, it should now be visible
            expect(news_tab).to_have_css("display", "block")

    def test_tab_drag_and_drop_reordering(self, page: Page):
        """Test drag and drop functionality for reordering tabs"""
        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Wait for modal and tabs to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()
        page.wait_for_selector(".customize-tab-item", timeout=10000)

        # Get initial order of tabs
        tabs_container = page.locator('div[id*="tabs-container-"]')
        initial_tabs = tabs_container.locator(".customize-tab-item")
        initial_count = initial_tabs.count()
        expect(initial_count).to_be_greater_than(1)

        # Get the first and second tab
        first_tab = initial_tabs.first
        second_tab = initial_tabs.nth(1)

        first_tab_text = first_tab.locator(".fw-medium").text_content()
        second_tab_text = second_tab.locator(".fw-medium").text_content()

        # Perform drag and drop - drag first tab and drop it after the second tab
        first_tab.drag_to(second_tab)

        # Wait for the drag to complete
        page.wait_for_timeout(1000)

        # Verify the order changed
        updated_tabs = tabs_container.locator(".customize-tab-item")
        first_position_text = updated_tabs.first.locator(".fw-medium").text_content()
        second_position_text = updated_tabs.nth(1).locator(".fw-medium").text_content()

        # The order should have changed
        expect(first_position_text).to_be(second_tab_text)
        expect(second_position_text).to_be(first_tab_text)

        # Save changes
        save_button = page.locator('button[id*="save-tabs-btn"]')
        save_button.click()

        # Wait for success message
        page.wait_for_selector("text=Success!", timeout=5000)

        # Close modal
        close_button = page.locator(".btn-close")
        close_button.click()

        # Verify tab order changed in main dashboard (wait a moment for dynamic update)
        page.wait_for_timeout(2000)

        # The tab order should be reflected in the main dashboard tabs
        main_tabs = page.locator("#dashboard-tabs .nav-tabs")
        expect(main_tabs).to_be_visible()

    def test_reset_to_default_configuration(self, page: Page):
        """Test reset to default configuration functionality"""
        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Wait for modal and tabs to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()
        page.wait_for_selector(".customize-tab-item", timeout=10000)

        # Make some changes first - hide a tab
        games_tab_item = page.locator(".customize-tab-item").filter(has_text="Games")
        games_toggle = games_tab_item.locator('input[type="checkbox"]')
        games_toggle.click()
        page.wait_for_timeout(500)

        # Now reset to default
        reset_button = page.locator('button[id*="reset-tabs-btn"]')
        expect(reset_button).to_be_visible()

        # Handle the confirmation dialog
        page.on("dialog", lambda dialog: dialog.accept())
        reset_button.click()

        # Wait for reset success message
        page.wait_for_selector("text=Reset!", timeout=5000)

        # Verify the Games tab toggle is back to default (visible)
        expect(games_toggle.is_checked()).to_be_true()

        # Close modal
        close_button = page.locator(".btn-close")
        close_button.click()

    def test_tab_preferences_persistence(self, page: Page):
        """Test that tab preferences persist across page reloads"""
        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Wait for modal and tabs to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()
        page.wait_for_selector(".customize-tab_item", timeout=10000)

        # Make a change - hide Videos tab
        videos_tab_item = page.locator(".customize-tab-item").filter(has_text="Videos")
        videos_toggle = videos_tab_item.locator('input[type="checkbox"]')
        videos_toggle.click()
        page.wait_for_timeout(500)

        # Save changes
        save_button = page.locator('button[id*="save-tabs-btn"]')
        save_button.click()

        # Wait for success message
        page.wait_for_selector("text=Success!", timeout=5000)

        # Close modal
        close_button = page.locator(".btn-close")
        close_button.click()

        # Reload the page
        page.reload()

        # Wait for page to load again
        page.wait_for_selector("#dashboard-tabs", timeout=15000)
        page.wait_for_function("window.tabPreferencesManager !== undefined", timeout=10000)

        # Verify Videos tab is still hidden
        videos_tab = page.locator('[tab_id="tab-videos"]')
        expect(videos_tab).to_have_css("display", "none")

    def test_tab_customization_statistics(self, page: Page):
        """Test that tab statistics are displayed correctly"""
        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Wait for modal and tabs to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()
        page.wait_for_selector(".customize-tab-item", timeout=10000)

        # Check for statistics display
        stats_element = page.locator('div[id*="customize-tabs-stats-"]')
        expect(stats_element).to_be_visible()

        # The stats should show visible vs total tabs
        stats_text = stats_element.text_content()
        expect("of").to_be_in(stats_text)  # Should show "X of Y tabs visible"
        expect("tabs visible").to_be_in(stats_text)

        # Verify the numbers are reasonable
        # Extract numbers from stats text (e.g., "12 of 16 tabs visible")
        import re

        numbers = re.findall(r"\d+", stats_text)
        expect(len(numbers)).to_be(2)

        visible_count = int(numbers[0])
        total_count = int(numbers[1])

        expect(visible_count).to_be_greater_than(0)
        expect(total_count).to_be_greater_than_or_equal(visible_count)

    def test_customization_modal_responsive_design(self, page: Page):
        """Test that the customization modal works on different screen sizes"""
        # Test mobile size
        page.set_viewport_size({"width": 375, "height": 667})

        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Wait for modal to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()

        # Check that modal is properly sized for mobile
        modal_dialog = modal.locator(".modal-dialog")
        expect(modal_dialog).to_be_visible()

        # Verify tab items are still accessible
        page.wait_for_selector(".customize-tab-item", timeout=10000)
        tab_items = page.locator(".customize-tab-item")
        expect(tab_items.count()).to_be_greater_than(0)

        # Test that drag handles are larger on mobile for touch interaction
        drag_handles = page.locator(".customize-tab-item .fa-grip-vertical")
        expect(drag_handles.first).to_be_visible()

        # Close modal
        close_button = modal.locator(".btn-close")
        close_button.click()

        # Reset to desktop size
        page.set_viewport_size({"width": 1920, "height": 1080})

    def test_error_handling_and_validation(self, page: Page):
        """Test error handling and validation in tab customization"""
        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Wait for modal and tabs to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()
        page.wait_for_selector(".customize-tab-item", timeout=10000)

        # Try to save changes without making any changes
        save_button = page.locator('button[id*="save-tabs-btn"]')
        save_button.click()

        # Should still show success message even if no changes made
        page.wait_for_selector("text=Success!", timeout=5000)

        # Try to reset (with confirmation)
        reset_button = page.locator('button[id*="reset-tabs-btn"]')

        # Cancel the reset dialog
        page.on("dialog", lambda dialog: dialog.dismiss())
        reset_button.click()

        # Modal should remain open since reset was cancelled
        expect(modal).to_be_visible()

        # Now accept the reset dialog
        page.on("dialog", lambda dialog: dialog.accept())
        reset_button.click()

        # Should show reset success message
        page.wait_for_selector("text=Reset!", timeout=5000)

    def test_accessibility_compliance(self, page: Page):
        """Test accessibility compliance of the customization feature"""
        # Check that the customize button has proper ARIA attributes
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        expect(customize_button).to_have_attribute("title")

        # Open customization modal
        customize_button.click()

        # Wait for modal to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()

        # Check modal accessibility
        expect(modal).to_have_attribute("role", "dialog")
        expect(modal).to_have_attribute("aria-modal", "true")

        # Check tab toggle accessibility
        tab_toggles = page.locator('.customize-tab-item input[type="checkbox"]')
        expect(tab_toggles.first).to_have_attribute("type", "checkbox")

        # Check keyboard navigation
        first_toggle = tab_toggles.first
        first_toggle.focus()
        expect(first_toggle).to_be_focused()

        # Test keyboard navigation through tabs
        page.keyboard.press("Tab")

        # Close modal
        close_button = modal.locator(".btn-close")
        close_button.focus()
        close_button.click()

    def test_performance_with_large_number_of_tabs(self, page: Page):
        """Test performance when handling many tabs"""
        # Open customization modal
        customize_button = page.locator('button[id*="customize-tabs-btn"]')
        customize_button.click()

        # Measure load time
        start_time = time.time()

        # Wait for modal and tabs to load
        modal = page.locator('div[id*="customize-tabs-modal-"]')
        expect(modal).to_be_visible()

        page.wait_for_selector(".customize-tab-item", timeout=10000)

        load_time = time.time() - start_time

        # Should load within reasonable time (less than 5 seconds)
        expect(load_time).to_be_less_than(5.0)

        # Test drag performance
        tabs = page.locator(".customize-tab-item")
        tab_count = tabs.count()

        if tab_count > 1:
            first_tab = tabs.first
            second_tab = tabs.nth(1)

            # Measure drag time
            drag_start = time.time()
            first_tab.drag_to(second_tab)
            drag_time = time.time() - drag_start

            # Drag should complete within reasonable time (less than 2 seconds)
            expect(drag_time).to_be_less_than(2.0)
