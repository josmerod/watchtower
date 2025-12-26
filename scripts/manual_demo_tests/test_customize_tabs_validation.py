#!/usr/bin/env python3
"""Playwright Validation Script for Dashboard Tab Customization
This script runs comprehensive E2E tests to validate the tab customization functionality
"""

import asyncio
import sys

from playwright.async_api import async_playwright, expect


async def run_tab_customization_tests():
    """Run comprehensive validation tests for tab customization"""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()

        try:
            print("🚀 Starting Tab Customization Validation Tests...")
            print("=" * 60)

            # Test 1: Navigate to dashboard and check basic functionality
            print("\n📍 Test 1: Dashboard Navigation and Basic Setup")
            await page.goto("http://localhost:7777")

            # Wait for dashboard to load
            await page.wait_for_selector("#dashboard-tabs", timeout=15000)
            print("✅ Dashboard loaded successfully")

            # Wait for tab preferences manager to be available
            await page.wait_for_function("window.tabPreferencesManager !== undefined", timeout=10000)
            print("✅ TabPreferencesManager loaded successfully")

            # Test 2: Open customization modal
            print("\n📍 Test 2: Customization Modal Opening")
            customize_button = page.locator('button[id*="customize-tabs-btn"]')
            await expect(customize_button).to_be_visible()
            await customize_button.click()

            modal = page.locator('div[id*="customize-tabs-modal-"]')
            await expect(modal).to_be_visible()
            print("✅ Customization modal opened successfully")

            # Test 3: Check modal content structure
            print("\n📍 Test 3: Modal Content Structure")
            await expect(page.locator("text=Customize Dashboard Tabs")).to_be_visible()
            await expect(page.locator("text=How to customize your dashboard:")).to_be_visible()
            print("✅ Modal content structure is correct")

            # Test 4: Wait for tabs to load in modal
            print("\n📍 Test 4: Tab Items Loading")
            await page.wait_for_selector(".customize-tab-item", timeout=10000)
            tab_items = page.locator(".customize-tab-item")
            tab_count = await tab_items.count()
            print(f"✅ {tab_count} tab items loaded successfully")

            # Verify expected tabs are present
            expected_tabs = ["Shortcuts", "News", "Videos", "Games", "Intelligence", "Courses"]
            for tab_name in expected_tabs:
                tab_element = tab_items.filter(has_text=tab_name)
                await expect(tab_element).to_be_visible()
                print(f"✅ Found expected tab: {tab_name}")

            # Test 5: Tab Visibility Toggle
            print("\n📍 Test 5: Tab Visibility Toggle")
            news_tab = tab_items.filter(has_text="News")
            news_toggle = news_tab.locator('input[type="checkbox"]')
            initial_state = await news_toggle.is_checked()

            await news_toggle.click()
            await page.wait_for_timeout(500)
            new_state = await news_toggle.is_checked()

            assert new_state != initial_state, "Toggle state should change"
            print(f"✅ News tab visibility toggled: {initial_state} → {new_state}")

            # Test 6: Drag and Drop Reordering
            print("\n📍 Test 6: Drag and Drop Reordering")
            if tab_count >= 2:
                first_tab = tab_items.first
                second_tab = tab_items.nth(1)

                first_tab_text = await first_tab.locator(".fw-medium").text_content()
                second_tab_text = await second_tab.locator(".fw-medium").text_content()

                print(f"🔄 Dragging '{first_tab_text}' to position of '{second_tab_text}'")
                await first_tab.drag_to(second_tab)
                await page.wait_for_timeout(1000)

                # Verify order changed
                updated_first = await tab_items.first.locator(".fw-medium").text_content()
                assert updated_first == second_tab_text, f"Expected '{second_tab_text}' at first position, got '{updated_first}'"
                print("✅ Tab reordering successful")

            # Test 7: Save Changes
            print("\n📍 Test 7: Save Changes")
            save_button = page.locator('button[id*="save-tabs-btn"]')
            await save_button.click()

            # Wait for success message
            await page.wait_for_selector("text=Success!", timeout=5000)
            print("✅ Changes saved successfully")

            # Test 8: Close Modal
            print("\n📍 Test 8: Close Modal")
            close_button = modal.locator(".btn-close")
            await close_button.click()
            await expect(modal).not_to_be_visible(timeout=3000)
            print("✅ Modal closed successfully")

            # Test 9: Verify Changes Applied to Dashboard
            print("\n📍 Test 9: Verify Dashboard Changes")
            await page.wait_for_timeout(2000)  # Wait for dynamic updates

            # Check if News tab visibility changed in main dashboard
            news_tab_main = page.locator('[tab_id="tab-news"]')
            if initial_state:
                # Was visible, should now be hidden
                await expect(news_tab_main).to_have_css("display", "none")
                print("✅ News tab correctly hidden in main dashboard")
            else:
                # Was hidden, should now be visible
                await expect(news_tab_main).to_have_css("display", "block")
                print("✅ News tab correctly visible in main dashboard")

            # Test 10: Reset to Default
            print("\n📍 Test 10: Reset to Default Configuration")
            await customize_button.click()
            await expect(modal).to_be_visible()
            await page.wait_for_selector(".customize-tab-item", timeout=10000)

            reset_button = page.locator('button[id*="reset-tabs-btn"]')

            # Handle confirmation dialog
            page.on("dialog", lambda dialog: dialog.accept())
            await reset_button.click()

            # Wait for reset success message
            await page.wait_for_selector("text=Reset!", timeout=5000)
            print("✅ Reset to default successful")

            # Verify News tab is back to default (visible)
            await news_tab.wait_for(state="visible")
            news_toggle_after_reset = await news_tab.locator('input[type="checkbox"]').is_checked()
            assert news_toggle_after_reset is True, "News tab should be visible after reset"
            print("✅ News tab correctly reset to default visibility")

            # Test 11: Tab Statistics
            print("\n📍 Test 11: Tab Statistics Display")
            stats_element = page.locator('div[id*="customize-tabs-stats-"]')
            await expect(stats_element).to_be_visible()

            stats_text = await stats_element.text_content()
            assert "of" in stats_text, "Stats should show 'X of Y tabs visible'"
            assert "tabs visible" in stats_text, "Stats should mention 'tabs visible'"
            print(f"✅ Statistics displayed correctly: {stats_text}")

            # Test 12: Responsive Design
            print("\n📍 Test 12: Responsive Design Test")
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(500)

            # Modal should still be functional on mobile
            await expect(modal).to_be_visible()
            await expect(tab_items.first).to_be_visible()
            print("✅ Modal responsive design working correctly")

            # Reset viewport size
            await page.set_viewport_size({"width": 1920, "height": 1080})

            # Test 13: Persistence Across Reload
            print("\n📍 Test 13: Preferences Persistence")
            # Make a specific change
            videos_tab = tab_items.filter(has_text="Videos")
            videos_toggle = videos_tab.locator('input[type="checkbox"]')
            await videos_toggle.click()
            await page.wait_for_timeout(500)

            await save_button.click()
            await page.wait_for_selector("text=Success!", timeout=5000)
            await close_button.click()

            # Reload page
            await page.reload()
            await page.wait_for_selector("#dashboard-tabs", timeout=15000)
            await page.wait_for_function("window.tabPreferencesManager !== undefined", timeout=10000)

            # Check if Videos tab is still hidden
            videos_tab_main = page.locator('[tab_id="tab-videos"]')
            await expect(videos_tab_main).to_have_css("display", "none")
            print("✅ Tab preferences persist across page reloads")

            print("\n" + "=" * 60)
            print("🎉 All Tab Customization Tests Passed Successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Test Failed: {e!s}")
            # Take screenshot for debugging
            await page.screenshot(path="test_failure_screenshot.png")
            print("📸 Screenshot saved as 'test_failure_screenshot.png'")
            raise

        finally:
            await browser.close()


async def run_performance_validation():
    """Run performance validation tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print("\n⚡ Performance Validation Tests")
            print("=" * 40)

            # Test modal load time
            start_time = asyncio.get_event_loop().time()
            await page.goto("http://localhost:7777")
            await page.wait_for_selector("#dashboard-tabs", timeout=15000)

            customize_button = page.locator('button[id*="customize-tabs-btn"]')
            await customize_button.click()

            await page.wait_for_selector(".customize-tab-item", timeout=10000)
            load_time = asyncio.get_event_loop().time() - start_time

            assert load_time < 5.0, f"Modal should load within 5 seconds, took {load_time:.2f}s"
            print(f"✅ Modal load time: {load_time:.2f}s (within 5s limit)")

            # Test drag performance
            tab_items = page.locator(".customize-tab-item")
            if await tab_items.count() >= 2:
                first_tab = tab_items.first
                second_tab = tab_items.nth(1)

                drag_start = asyncio.get_event_loop().time()
                await first_tab.drag_to(second_tab)
                drag_time = asyncio.get_event_loop().time() - drag_start

                assert drag_time < 2.0, f"Drag should complete within 2 seconds, took {drag_time:.2f}s"
                print(f"✅ Drag performance: {drag_time:.2f}s (within 2s limit)")

            print("✅ Performance validation completed")

        finally:
            await browser.close()


async def main():
    """Main validation function"""
    print("🧪 Starting Comprehensive Tab Customization Validation")
    print("This script will test the complete tab customization functionality")

    try:
        # Run main functionality tests
        await run_tab_customization_tests()

        # Run performance tests
        await run_performance_validation()

        print("\n🏆 All validation tests completed successfully!")
        print("The dashboard tab customization feature is working correctly.")

    except Exception as e:
        print(f"\n💥 Validation failed: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the validation
    asyncio.run(main())
