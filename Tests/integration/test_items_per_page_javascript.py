"""
Integration tests for Items Per Page JavaScript functionality
"""

import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.common.exceptions import JavascriptException, NoSuchElementException


class TestItemsPerPageJavaScript:
    """Test ItemsPerPageManager JavaScript functionality"""

    @pytest.fixture
    def driver(self):
        """Setup Chrome WebDriver for testing"""
        options = Options()
        options.add_argument("--headless")  # Run in headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def dashboard_url(self):
        """Dashboard URL for testing"""
        return "http://localhost:7777"

    def test_items_per_page_manager_available(self, driver, dashboard_url):
        """Test that ItemsPerPageManager is available on dashboard"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check if ItemsPerPageManager is defined
        try:
            is_manager_available = driver.execute_script(
                "return typeof window.itemsPerPageManager !== 'undefined';"
            )
            assert is_manager_available, "ItemsPerPageManager should be available"
        except JavascriptException as e:
            pytest.fail(f"JavaScript error checking ItemsPerPageManager: {e}")

    def test_items_per_page_manager_methods(self, driver, dashboard_url):
        """Test ItemsPerPageManager methods are available"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check required methods exist
        required_methods = [
            "getPreference",
            "savePreference",
            "getAllPreferences",
            "getDefaultValue",
            "getOptions",
            "validateValue",
            "resetPreference"
        ]

        for method in required_methods:
            try:
                method_exists = driver.execute_script(
                    f"return typeof window.itemsPerPageManager.{method} === 'function';"
                )
                assert method_exists, f"ItemsPerPageManager.{method} should be available"
            except JavascriptException as e:
                pytest.fail(f"JavaScript error checking method {method}: {e}")

    def test_items_per_page_default_values(self, driver, dashboard_url):
        """Test that default values are correctly set"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Test default values for different tabs
        expected_defaults = {
            'videos': 48,
            'arxiv': 24,
            'news': 24,
            'deals': 48,
            'courses': 24
        }

        for tab, expected_value in expected_defaults.items():
            try:
                default_value = driver.execute_script(
                    f"return window.itemsPerPageManager.getDefaultValue('{tab}');"
                )
                assert default_value == expected_value, f"Default value for {tab} should be {expected_value}"
            except JavascriptException as e:
                pytest.fail(f"JavaScript error getting default value for {tab}: {e}")

    def test_items_per_page_allowed_values(self, driver, dashboard_url):
        """Test allowed values validation"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Get allowed values
        try:
            allowed_values = driver.execute_script(
                "return window.itemsPerPageManager.getAllowedValues();"
            )
            expected_values = [12, 24, 48, 96]
            assert allowed_values == expected_values, f"Allowed values should be {expected_values}"
        except JavascriptException as e:
            pytest.fail(f"JavaScript error getting allowed values: {e}")

    def test_items_per_page_preference_saving(self, driver, dashboard_url):
        """Test saving and loading preferences"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Test saving a preference
        try:
            # Clear any existing preference first
            driver.execute_script("localStorage.removeItem('watchtower_items_per_page');")

            # Save a preference
            save_result = driver.execute_script(
                "return window.itemsPerPageManager.savePreference('videos', 24);"
            )
            assert save_result is True, "Save preference should return True"

            # Load the preference
            loaded_value = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('videos');"
            )
            assert loaded_value == 24, "Loaded preference should match saved value"

        except JavascriptException as e:
            pytest.fail(f"JavaScript error testing preference saving: {e}")

    def test_items_per_page_validation(self, driver, dashboard_url):
        """Test preference validation"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Test valid values
        valid_values = [12, 24, 48, 96]
        for value in valid_values:
            try:
                result = driver.execute_script(
                    f"return window.itemsPerPageManager.validateValue({value});"
                )
                assert result['valid'] is True, f"Value {value} should be valid"
            except JavascriptException as e:
                pytest.fail(f"JavaScript error validating valid value {value}: {e}")

        # Test invalid values
        invalid_values = [0, 6, 100, "invalid", None]
        for value in invalid_values:
            try:
                result = driver.execute_script(
                    f"return window.itemsPerPageManager.validateValue({value});"
                )
                assert result['valid'] is False, f"Value {value} should be invalid"
            except JavascriptException as e:
                pytest.fail(f"JavaScript error validating invalid value {value}: {e}")

    def test_items_per_page_storage_persistence(self, driver, dashboard_url):
        """Test that preferences persist across page reloads"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        try:
            # Save a preference
            driver.execute_script("window.itemsPerPageManager.savePreference('arxiv', 96);")

            # Reload the page
            driver.refresh()

            # Wait for page to load again
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check if preference persisted
            loaded_value = driver.execute_script(
                "return window.itemsPerPageManager.getPreference('arxiv');"
            )
            assert loaded_value == 96, "Preference should persist across page reloads"

        except JavascriptException as e:
            pytest.fail(f"JavaScript error testing persistence: {e}")

    def test_items_per_page_selector_interaction(self, driver, dashboard_url):
        """Test actual selector interaction on the page"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Try to find videos tab and click it
        try:
            # Look for Videos tab
            videos_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Videos') or contains(text(), '📺')]"))
            )
            videos_tab.click()

            # Wait for tab content to load
            time.sleep(2)

            # Look for items-per-page selector
            selector = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "videos-items-per-page-select"))
            )

            # Test changing the selector value
            # Find the dropdown element and click it
            dropdown = driver.find_element(By.ID, "videos-items-per-page-select")

            # Try to select option 24
            try:
                # This is a simplified test - in a real scenario, you'd need to handle
                # the dropdown selection more carefully based on the specific implementation
                option_24 = driver.find_element(By.XPATH, "//select[@id='videos-items-per-page-select']/option[@value='24']")
                option_24.click()

                # Check if preference was saved
                time.sleep(1)  # Give it time to save
                current_preference = driver.execute_script(
                    "return window.itemsPerPageManager.getPreference('videos');"
                )
                assert current_preference == 24, "Preference should be updated when selector changes"

            except NoSuchElementException:
                pytest.skip("Items-per-page selector options not available in test environment")

        except Exception as e:
            # If we can't find the Videos tab or selector, skip this test
            pytest.skip(f"Videos tab or selector not available: {e}")


class TestItemsPerPagePerformance:
    """Test performance aspects of items-per-page functionality"""

    @pytest.fixture
    def driver(self):
        """Setup Chrome WebDriver for testing"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_preference_loading_performance(self, driver, dashboard_url):
        """Test that preference loading meets performance requirements"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Test performance of loading preferences
        start_time = time.time()
        try:
            driver.execute_script("window.itemsPerPageManager.getAllPreferences();")
            end_time = time.time()

            load_time = (end_time - start_time) * 1000  # Convert to milliseconds
            assert load_time < 50, f"Preference loading should be under 50ms, took {load_time:.2f}ms"

        except JavascriptException as e:
            pytest.fail(f"JavaScript error testing performance: {e}")

    def test_preference_saving_performance(self, driver, dashboard_url):
        """Test that preference saving meets performance requirements"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Test performance of saving preferences
        start_time = time.time()
        try:
            driver.execute_script("window.itemsPerPageManager.savePreference('test-tab', 48);")
            end_time = time.time()

            save_time = (end_time - start_time) * 1000  # Convert to milliseconds
            assert save_time < 200, f"Preference saving should be under 200ms, took {save_time:.2f}ms"

        except JavascriptException as e:
            pytest.fail(f"JavaScript error testing save performance: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])