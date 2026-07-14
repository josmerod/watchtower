#!/usr/bin/env python3
"""Simplified Tab Customization Validation Script"""

import asyncio
import sys

from playwright.async_api import async_playwright, expect


async def run_tests():
    """Run tab customization validation tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()

        try:
            print("Starting Tab Customization Tests...")

            # Navigate to dashboard
            await page.goto("http://localhost:7777")
            await page.wait_for_selector("#dashboard-tabs", timeout=15000)
            print("✅ Dashboard loaded")

            # Wait for tab preferences
            await page.wait_for_function("window.tabPreferencesManager !== undefined", timeout=10000)
            print("✅ TabPreferencesManager loaded")

            # Test 1: Open customization modal
            customize_button = page.locator('button[id*="customize-tabs-btn"]')
            await expect(customize_button).to_be_visible()
            await customize_button.click()
            print("✅ Customization button clicked")

            # Check modal opens
            modal = page.locator('div[id*="customize-tabs-modal-"]')
            await expect(modal).to_be_visible(timeout=5000)
            print("✅ Modal opened successfully")

            # Test 2: Check modal content
            await expect(page.locator("text=Customize Dashboard Tabs")).to_be_visible()
            print("✅ Modal title displayed")

            # Wait for tabs to load
            await page.wait_for_selector(".customize-tab-item", timeout=10000)
            tab_items = page.locator(".customize-tab-item")
            tab_count = await tab_items.count()
            print(f"✅ {tab_count} tab items loaded")

            # Test 3: Tab visibility toggle
            news_tab = tab_items.filter(has_text="News")
            news_toggle = news_tab.locator('input[type="checkbox"]')
            initial_state = await news_toggle.is_checked()

            await news_toggle.click()
            await page.wait_for_timeout(500)
            new_state = await news_toggle.is_checked()

            assert new_state != initial_state, "Toggle state should change"
            print(f"✅ News tab toggled: {initial_state} -> {new_state}")

            # Test 4: Save changes
            save_button = page.locator('button[id*="save-tabs-btn"]')
            await save_button.click()

            await page.wait_for_selector("text=Success!", timeout=5000)
            print("✅ Changes saved successfully")

            # Test 5: Close modal
            close_button = modal.locator(".btn-close")
            await close_button.click()
            await expect(modal).not_to_be_visible(timeout=3000)
            print("✅ Modal closed")

            # Test 6: Reset functionality
            await customize_button.click()
            await expect(modal).to_be_visible()
            await page.wait_for_selector(".customize-tab-item", timeout=10000)

            reset_button = page.locator('button[id*="reset-tabs-btn"]')

            # Handle confirmation dialog
            page.on("dialog", lambda dialog: dialog.accept())
            await reset_button.click()

            await page.wait_for_selector("text=Reset!", timeout=5000)
            print("✅ Reset to default successful")

            print("\n🎉 All basic tests passed!")
            return True

        except Exception as e:
            print(f"❌ Test failed: {e!s}")
            await page.screenshot(path="test_failure.png")
            print("📸 Screenshot saved as test_failure.png")
            return False

        finally:
            await browser.close()


async def main():
    """Main function"""
    try:
        success = await run_tests()
        if success:
            print("\n✅ Tab customization validation completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Tab customization validation failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Critical error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
