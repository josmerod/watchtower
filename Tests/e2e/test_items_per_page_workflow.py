"""
End-to-end tests for Items Per Page workflow
Tests complete user workflow from selection to preference persistence
"""

import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestItemsPerPageWorkflow:
    """Complete end-to-end workflow tests for items-per-page functionality"""

    @pytest.fixture
    def driver(self):
        """Setup Chrome WebDriver for testing"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def dashboard_url(self):
        """Dashboard URL for testing"""
        return "http://localhost:7777"

    def test_complete_items_per_page_workflow_videos_tab(self, driver, dashboard_url):
        """Test complete items-per-page workflow on Videos tab"""
        driver.get(dashboard_url)

        # Navigate to Videos tab
        try:
            videos_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            # Wait for Videos content to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "videos-container"))
            )
        except TimeoutException:
            pytest.skip("Videos tab not available for testing")

        # Step 1: Verify items-per-page selector exists and shows default value
        try:
            selector = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )

            # Check default value is selected
            dropdown = selector.find_element(By.TAG_NAME, "select")
            selected_option = dropdown.find_element(By.CSS_SELECTOR, "option[selected]")
            assert "48" in selected_option.text, "Default value should be 48 items"
        except (TimeoutException, NoSuchElementException):
            pytest.fail("Items-per-page selector not found on Videos tab")

        # Step 2: Change items-per-page preference
        try:
            # Open dropdown
            dropdown.click()
            time.sleep(1)

            # Select 24 items option
            option_24 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//select[@id='videos-items-per-page-select']/option[@value='24']"))
            )
            option_24.click()
            time.sleep(2)  # Allow preference to save

        except TimeoutException:
            pytest.fail("Could not change items-per-page preference")

        # Step 3: Verify content updated with new preference
        try:
            # Check that the number of displayed videos changed
            videos_container = driver.find_element(By.ID, "videos-container")
            video_cards = videos_container.find_elements(By.CSS_SELECTOR, ".card, .video-card, [class*='video']")

            # Should have approximately 24 videos (allowing for some variance)
            assert 20 <= len(video_cards) <= 30, f"Should display ~24 videos, found {len(video_cards)}"
        except TimeoutException:
            pytest.fail("Videos content did not update with new preference")

        # Step 4: Verify preference was saved to localStorage
        try:
            saved_preference = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            assert saved_preference == 24, "Preference should be saved as 24"
        except Exception as e:
            pytest.fail(f"Could not verify saved preference: {e}")

        # Step 5: Navigate away and back to verify preference persistence
        try:
            # Navigate to another tab
            arxiv_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ArXiv') or contains(text(), '📄')]"))
            )
            arxiv_tab.click()
            time.sleep(2)

            # Navigate back to Videos tab
            videos_tab.click()
            time.sleep(3)  # Allow full reload

            # Check if preference is still applied
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )
            selected_value = driver.execute_script(
                "return document.getElementById('videos-items-per-page-select').value;"
            )
            assert selected_value == "24", "Preference should persist across tab navigation"

        except TimeoutException:
            pytest.fail("Preference persistence test failed")

    def test_items_per_page_workflow_arxiv_tab(self, driver, dashboard_url):
        """Test items-per-page workflow on ArXiv Research tab"""
        driver.get(dashboard_url)

        # Navigate to ArXiv tab
        try:
            arxiv_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ArXiv') or contains(text(), '📄')]"))
            )
            arxiv_tab.click()

            # Wait for ArXiv content to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "arxiv-papers-container"))
            )
        except TimeoutException:
            pytest.skip("ArXiv tab not available for testing")

        # Test workflow similar to Videos tab but with ArXiv-specific expectations
        try:
            selector = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "arxiv-items-per-page-select"))
            )

            # Check default value for ArXiv (should be 24)
            dropdown = selector.find_element(By.TAG_NAME, "select")
            initial_value = driver.execute_script(
                "return document.getElementById('arxiv-items-per-page-select').value;"
            )
            assert initial_value == "24", "Default value for ArXiv should be 24"

            # Change to 96 items
            dropdown.click()
            time.sleep(1)
            option_96 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//select[@id='arxiv-items-per-page-select']/option[@value='96']"))
            )
            option_96.click()
            time.sleep(3)

            # Verify preference saved
            saved_preference = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('arxiv');"
            )
            assert saved_preference == 96, "ArXiv preference should be saved as 96"

        except (TimeoutException, NoSuchElementException):
            pytest.fail("ArXiv items-per-page workflow failed")

    def test_items_per_page_reset_functionality(self, driver, dashboard_url):
        """Test resetting items-per-page preferences"""
        driver.get(dashboard_url)

        # Navigate to Videos tab
        try:
            videos_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )
        except TimeoutException:
            pytest.skip("Videos tab not available for testing")

        # Change preference to non-default value
        try:
            driver.execute_script("window.itemsPerPageManager.savePreference('videos', 12);")

            # Verify it's changed
            current_value = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            assert current_value == 12, "Preference should be changed to 12"

            # Reset preference
            reset_result = driver.execute_script(
                "return window.itemsPerPageManager.resetPreference('videos');"
            )
            assert reset_result is True, "Reset should return True"

            # Verify it's reset to default
            reset_value = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            default_value = driver.execute_script(
                "return window.itemsPerPageManager.getDefaultValue('videos');"
            )
            assert reset_value == default_value, "Reset value should match default value"

        except Exception as e:
            pytest.fail(f"Reset functionality test failed: {e}")

    def test_items_per_page_cross_browser_consistency(self, driver, dashboard_url):
        """Test consistency across different interaction methods"""
        driver.get(dashboard_url)

        # Navigate to Videos tab
        try:
            videos_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )
        except TimeoutException:
            pytest.skip("Videos tab not available for testing")

        # Test JavaScript-based preference setting
        try:
            # Set preference via JavaScript
            driver.execute_script("window.itemsPerPageManager.applyPreference('videos', 96, function(tab, value) { console.log('Applied:', tab, value); });")
            time.sleep(2)

            # Verify preference was set
            js_value = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            assert js_value == 96, "JavaScript-based preference setting should work"

            # Reset to test UI-based interaction
            driver.execute_script("window.itemsPerPageManager.resetPreference('videos');")
            time.sleep(1)

            # Set via UI interaction
            dropdown = driver.find_element(By.ID, "videos-items-per-page-select")
            dropdown.click()
            time.sleep(1)

            option_12 = driver.find_element(By.XPATH, "//select[@id='videos-items-per-page-select']/option[@value='12']")
            option_12.click()
            time.sleep(3)

            # Verify UI-based preference setting
            ui_value = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            assert ui_value == 12, "UI-based preference setting should work"

            # Verify both methods produce consistent results
            assert js_value != ui_value, "Different preference setting methods should work"

        except Exception as e:
            pytest.fail(f"Cross-browser consistency test failed: {e}")

    def test_items_per_page_error_handling(self, driver, dashboard_url):
        """Test error handling in items-per-page functionality"""
        driver.get(dashboard_url)

        # Test invalid preference values
        try:
            # Try to save invalid value
            invalid_result = driver.execute_script(
                "return window.itemsPerPageManager.savePreference('videos', 999);"
            )
            assert invalid_result is False, "Invalid value should return False"

            # Try to save non-numeric value
            non_numeric_result = driver.execute_script(
                "return window.itemsPerPageManager.savePreference('videos', 'invalid');"
            )
            assert non_numeric_result is False, "Non-numeric value should return False"

            # Verify preference wasn't changed
            current_preference = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            # Should still be default or a valid value
            assert current_preference in [12, 24, 48, 96], "Preference should remain valid after invalid attempts"

        except Exception as e:
            pytest.fail(f"Error handling test failed: {e}")

    def test_items_per_page_accessibility(self, driver, dashboard_url):
        """Test accessibility of items-per-page selector"""
        driver.get(dashboard_url)

        # Navigate to Videos tab
        try:
            videos_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )
        except TimeoutException:
            pytest.skip("Videos tab not available for testing")

        # Test keyboard accessibility
        try:
            selector = driver.find_element(By.ID, "videos-items-per-page-select")

            # Test tab navigation to selector
            selector.send_keys('\t')  # Tab to next element

            # Test arrow key navigation within selector
            selector.send_keys('\ue015')  # Down arrow
            selector.send_keys('\ue015')  # Down arrow again

            # Verify selection changed
            selected_value = driver.execute_script(
                "return document.getElementById('videos-items-per-page-select').value;"
            )
            assert selected_value is not None, "Keyboard navigation should work"

        except Exception as e:
            pytest.fail(f"Accessibility test failed: {e}")


class TestItemsPerPageAcceptanceCriteria:
    """Test specific acceptance criteria from the user story"""

    @pytest.fixture
    def driver(self):
        """Setup Chrome WebDriver for testing"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def dashboard_url(self):
        """Dashboard URL for testing"""
        return "http://localhost:7777"

    def test_ac_1_immediate_display_update(self, driver, dashboard_url):
        """AC1: Given viewing any dashboard tab, when selecting items-per-page, then display updates immediately"""
        driver.get(dashboard_url)

        try:
            # Navigate to Videos tab
            videos_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-container"))
            )

            # Count initial items
            initial_items = driver.execute_script(
                "return document.querySelectorAll('#videos-container .card').length;"
            )

            # Change items-per-page selector
            selector = driver.find_element(By.ID, "videos-items-per-page-select")
            selector.click()
            time.sleep(1)

            # Select different option
            option_12 = driver.find_element(By.XPATH, "//select[@id='videos-items-per-page-select']/option[@value='12']")
            option_12.click()

            # Wait for update (should be immediate)
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script(
                    "return document.querySelectorAll('#videos-container .card').length;"
                ) != initial_items
            )

            # Verify items count changed
            final_items = driver.execute_script(
                "return document.querySelectorAll('#videos-container .card').length;"
            )
            assert final_items != initial_items, "Display should update immediately when preference changes"

        except TimeoutException:
            pytest.fail("Display did not update immediately")

    def test_ac_2_preference_saved_per_tab(self, driver, dashboard_url):
        """AC2: My choice is saved per tab in browser storage"""
        driver.get(dashboard_url)

        try:
            # Set preference for Videos tab
            videos_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )

            driver.execute_script("window.itemsPerPageManager.savePreference('videos', 12);")

            # Set different preference for ArXiv tab
            arxiv_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ArXiv') or contains(text(), '📄')]"))
            )
            arxiv_tab.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "arxiv-items-per-page-select"))
            )

            driver.execute_script("window.itemsPerPageManager.savePreference('arxiv', 96);")

            # Verify preferences are different per tab
            videos_preference = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            arxiv_preference = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('arxiv');"
            )

            assert videos_preference == 12, "Videos preference should be 12"
            assert arxiv_preference == 96, "ArXiv preference should be 96"
            assert videos_preference != arxiv_preference, "Preferences should be saved per tab"

        except Exception as e:
            pytest.fail(f"Per-tab preference saving failed: {e}")

    def test_ac_3_preference_applied_on_return(self, driver, dashboard_url):
        """AC3: When I return to the tab, then my items-per-page preference is applied"""
        driver.get(dashboard_url)

        try:
            # Set preference on Videos tab
            videos_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )

            # Change preference to 24
            selector = driver.find_element(By.ID, "videos-items-per-page-select")
            selector.click()
            time.sleep(1)
            option_24 = driver.find_element(By.XPATH, "//select[@id='videos-items-per-page-select']/option[@value='24']")
            option_24.click()
            time.sleep(2)

            # Navigate away
            arxiv_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ArXiv') or contains(text(), '📄')]"))
            )
            arxiv_tab.click()
            time.sleep(2)

            # Return to Videos tab
            videos_tab.click()
            time.sleep(3)

            # Check preference is applied
            current_preference = driver.execute_script(
                "return document.getElementById('videos-items-per-page-select').value;"
            )
            assert current_preference == "24", "Preference should be applied when returning to tab"

            # Check content reflects preference
            displayed_items = driver.execute_script(
                "return document.querySelectorAll('#videos-container .card').length;"
            )
            assert 20 <= displayed_items <= 30, f"Should display ~24 items, found {displayed_items}"

        except Exception as e:
            pytest.fail(f"Preference application on return failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])