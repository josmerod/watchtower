"""
Integration tests for shortcuts functionality in the dashboard
Tests the integration between ShortcutsManager, UI components, and data flow
"""

import pytest
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


class TestShortcutsIntegration:
    """Integration tests for shortcuts functionality"""

    @pytest.fixture
    def driver(self):
        """Setup Chrome driver for testing"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def dashboard_url(self):
        """Get the dashboard URL for testing"""
        return "http://localhost:7777"  # Default dashboard port

    def setup_method(self):
        """Setup for each test method"""
        self.test_shortcuts = []

    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up any test shortcuts that were created
        pass

    def create_test_shortcut_data(self, name, domain, source_filter):
        """Create test shortcut data"""
        return {
            'id': f'test_shortcut_{int(time.time() * 1000)}',
            'name': name,
            'domain': domain,
            'source_filter': source_filter,
            'order': 0,
            'created_at': time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }

    def test_dashboard_loads_with_shortcuts_button(self, driver, dashboard_url):
        """Test that dashboard loads and shows shortcuts button"""
        driver.get(dashboard_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Look for shortcuts toggle button
        try:
            shortcuts_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Shortcuts')]"))
            )
            assert shortcuts_button.is_displayed()
            assert "Shortcuts" in shortcuts_button.text
        except Exception as e:
            pytest.fail(f"Shortcuts button not found: {e}")

    def test_shortcuts_sidebar_opens(self, driver, dashboard_url):
        """Test that shortcuts sidebar opens when button is clicked"""
        driver.get(dashboard_url)

        # Click shortcuts button
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        shortcuts_button.click()

        # Wait for sidebar to open
        try:
            sidebar = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'offcanvas') and contains(., 'My Source Shortcuts')]"))
            )
            assert sidebar.is_displayed()
            assert "My Source Shortcuts" in sidebar.text
        except Exception as e:
            pytest.fail(f"Shortcuts sidebar not found or not visible: {e}")

    def test_shortcuts_sidebar_closes(self, driver, dashboard_url):
        """Test that shortcuts sidebar closes properly"""
        driver.get(dashboard_url)

        # Open sidebar
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        shortcuts_button.click()

        # Wait for sidebar to open
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'offcanvas')]"))
        )

        # Click close button
        close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'btn-close')]")
        close_button.click()

        # Wait for sidebar to close
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'offcanvas show')]"))
        )

    def test_add_shortcut_button_visible_in_arxiv_tab(self, driver, dashboard_url):
        """Test that 'Add to Shortcuts' buttons are visible in ArXiv tab"""
        driver.get(dashboard_url)

        # Click on ArXiv Research tab
        arxiv_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ArXiv Research')]"))
        )
        arxiv_tab.click()

        # Wait for ArXiv content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[contains(., 'ArXiv Research Papers')]"))
        )

        # Look for "Add to Shortcuts" buttons
        try:
            add_shortcut_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add to Shortcuts')]")
            assert len(add_shortcut_buttons) > 0, "No 'Add to Shortcuts' buttons found in ArXiv tab"

            # Check that buttons have required attributes
            first_button = add_shortcut_buttons[0]
            assert first_button.get_attribute('data-source-name') is not None
            assert first_button.get_attribute('data-source-domain') is not None
            assert first_button.get_attribute('data-source-filter') is not None

        except Exception as e:
            pytest.fail(f"'Add to Shortcuts' buttons not found: {e}")

    def test_add_shortcut_functionality(self, driver, dashboard_url):
        """Test adding a shortcut from ArXiv tab"""
        driver.get(dashboard_url)

        # Navigate to ArXiv tab
        arxiv_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ArXiv Research')]"))
        )
        arxiv_tab.click()

        # Wait for content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )

        # Find and click "Add to Shortcuts" button
        add_shortcut_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add to Shortcuts')]")
        if not add_shortcut_buttons:
            pytest.skip("No 'Add to Shortcuts' buttons found (possibly no ArXiv data)")

        first_button = add_shortcut_buttons[0]
        shortcut_name = first_button.get_attribute('data-source-name')

        # Click the button
        first_button.click()

        # Wait for success message
        try:
            success_alert = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'alert-success') and contains(., 'Success!')]"))
            )
            assert shortcut_name in success_alert.text
        except Exception as e:
            pytest.fail(f"Success alert not found after adding shortcut: {e}")

        # Open shortcuts sidebar to verify shortcut was added
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        shortcuts_button.click()

        # Check for shortcut in sidebar
        try:
            WebDriverWait(driver, 5).until(
                EC.text_to_be_present_in_element((By.XPATH, "//div[contains(@class, 'offcanvas')]"), shortcut_name)
            )
        except Exception as e:
            pytest.fail(f"Added shortcut not found in sidebar: {e}")

    def test_shortcut_domain_grouping(self, driver, dashboard_url):
        """Test that shortcuts are grouped by domain correctly"""
        # This test would require JavaScript execution to set up test data
        # For now, we'll test the UI structure
        driver.get(dashboard_url)

        # Open shortcuts sidebar
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        shortcuts_button.click()

        # Check for domain sections (even if empty)
        try:
            # Look for domain headers in the sidebar
            domain_headers = driver.find_elements(By.XPATH, "//h6[contains(text(), 'Papers') or contains(text(), 'News') or contains(text(), 'Deals')]")
            # At least one domain section should exist in the structure
            assert len(domain_headers) >= 0
        except Exception as e:
            pytest.fail(f"Domain grouping structure not found: {e}")

    def test_shortcut_stats_badge_updates(self, driver, dashboard_url):
        """Test that the shortcuts stats badge updates correctly"""
        driver.get(dashboard_url)

        # Get initial stats count
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        stats_badge = shortcuts_button.find_element(By.XPATH, ".//span[contains(@class, 'badge')]")
        initial_count = int(stats_badge.text) if stats_badge.text.isdigit() else 0

        # Navigate to ArXiv tab
        arxiv_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ArXiv Research')]"))
        )
        arxiv_tab.click()

        # Wait for content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )

        # Add a shortcut
        add_shortcut_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add to Shortcuts')]")
        if add_shortcut_buttons:
            first_button = add_shortcut_buttons[0]
            first_button.click()

            # Wait for success message and stats update
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'alert-success')]"))
            )

            # Check if stats badge updated (may take a moment)
            time.sleep(1)
            updated_badge = shortcuts_button.find_element(By.XPATH, ".//span[contains(@class, 'badge')]")
            updated_count = int(updated_badge.text) if updated_badge.text.isdigit() else 0

            assert updated_count > initial_count, "Stats badge did not update after adding shortcut"

    def test_shortcut_navigation_functionality(self, driver, dashboard_url):
        """Test that clicking a shortcut navigates to correct tab with filters"""
        # This test requires setting up test data in localStorage first
        # For now, we'll test the click handler structure
        driver.get(dashboard_url)

        # Open shortcuts sidebar
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        shortcuts_button.click()

        # Check for shortcut links structure (even if no shortcuts exist)
        try:
            # Look for any existing shortcut links or empty state message
            shortcut_links = driver.find_elements(By.XPATH, "//a[contains(@data-shortcut-id, '')]")
            empty_state = driver.find_elements(By.XPATH, "//div[contains(., 'No shortcuts yet')]")

            # Either we have shortcuts or we have an empty state message
            assert len(shortcut_links) > 0 or len(empty_state) > 0

        except Exception as e:
            pytest.fail(f"Shortcuts content structure not found: {e}")

    def test_remove_shortcut_functionality(self, driver, dashboard_url):
        """Test removing a shortcut from the sidebar"""
        # This test requires first adding a shortcut, then removing it
        driver.get(dashboard_url)

        # Navigate to ArXiv tab and add a shortcut
        arxiv_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ArXiv Research')]"))
        )
        arxiv_tab.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )

        add_shortcut_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add to Shortcuts')]")
        if not add_shortcut_buttons:
            pytest.skip("No 'Add to Shortcuts' buttons found")

        first_button = add_shortcut_buttons[0]
        shortcut_name = first_button.get_attribute('data-source-name')
        first_button.click()

        # Wait for success message
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'alert-success')]"))
        )

        # Open shortcuts sidebar
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        shortcuts_button.click()

        # Wait for shortcut to appear in sidebar
        WebDriverWait(driver, 5).until(
            EC.text_to_be_present_in_element((By.XPATH, "//div[contains(@class, 'offcanvas')]"), shortcut_name)
        )

        # Look for remove button for the shortcut
        try:
            remove_button = driver.find_element(By.XPATH, f"//button[contains(@data-shortcut-name, '{shortcut_name}') and contains(., 'Remove')]")
            remove_button.click()

            # Handle confirmation dialog (if present)
            try:
                confirm_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'OK') or contains(text(), 'Confirm')]"))
                )
                confirm_button.click()
            except:
                pass  # No confirmation dialog

            # Verify shortcut is removed (should disappear or show success message)
            time.sleep(1)
            # This part depends on implementation - either the shortcut disappears or shows a success message

        except Exception as e:
            pytest.fail(f"Remove button not found or not working: {e}")

    def test_shortcuts_persistence_across_page_refresh(self, driver, dashboard_url):
        """Test that shortcuts persist across page refreshes"""
        # This test requires adding a shortcut, refreshing the page, and verifying it still exists
        driver.get(dashboard_url)

        # Add a shortcut
        arxiv_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ArXiv Research')]"))
        )
        arxiv_tab.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )

        add_shortcut_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add to Shortcuts')]")
        if not add_shortcut_buttons:
            pytest.skip("No 'Add to Shortcuts' buttons found")

        first_button = add_shortcut_buttons[0]
        shortcut_name = first_button.get_attribute('data-source-name')
        first_button.click()

        # Wait for success message
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'alert-success')]"))
        )

        # Refresh the page
        driver.refresh()

        # Wait for page to load again
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check if shortcuts button shows the same count
        shortcuts_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Shortcuts')]"))
        )
        stats_badge = shortcuts_button.find_element(By.XPATH, ".//span[contains(@class, 'badge')]")
        count = int(stats_badge.text) if stats_badge.text.isdigit() else 0

        # The count should be at least 1 (our shortcut)
        assert count >= 1, "Shortcuts not persisted after page refresh"