"""Pytest configuration for Playwright E2E tests."""

import os
import sys
import tempfile
import time
from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import Page

# Add src to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Environment configuration
BASE_URL = os.getenv("DASHBOARD_URL", "http://localhost:7777")
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Configure browser context arguments."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "record_video_dir": None,  # Will be set per test
        "locale": "en-US",
        "timezone_id": "America/New_York",
    }


@pytest.fixture()
def page(page: Page) -> Generator[Page, None, None]:
    """Configure page with custom settings."""
    # Set default timeout
    page.set_default_timeout(30000)

    # Configure console logging
    def handle_console(msg):
        if msg.type == "error":
            print(f"Console Error: {msg.text}")
        elif msg.type == "warning":
            print(f"Console Warning: {msg.text}")

    page.on("console", handle_console)

    yield page

    # Cleanup after test
    page.close()


@pytest.fixture(scope="session", autouse=True)
def before_all() -> None:
    """Setup before all tests."""
    print("Setting up E2E test environment...")

    # Create necessary directories
    test_results_dir = project_root / "test-results"
    test_results_dir.mkdir(exist_ok=True)
    (test_results_dir / "videos").mkdir(exist_ok=True)
    (test_results_dir / "screenshots").mkdir(exist_ok=True)
    (test_results_dir / "traces").mkdir(exist_ok=True)

    # Set up environment variables
    os.environ["TEST_ENV"] = "e2e"
    os.environ["PYTEST_CURRENT_TEST"] = "e2e"


@pytest.fixture(scope="session", autouse=True)
def after_all() -> None:
    """Cleanup after all tests."""
    print("Cleaning up E2E test environment...")


@pytest.fixture(scope="function", autouse=True)
def before_each(page: Page) -> None:
    """Setup before each test."""
    # Clear any existing state
    page.evaluate("() => localStorage.clear()")
    page.evaluate("() => sessionStorage.clear()")

    # Set up test user session if needed
    page.context.add_cookies(
        [
            {
                "name": "test_user_id",
                "value": "e2e_test_user",
                "domain": "localhost",
                "path": "/",
            }
        ]
    )


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """Provide an authenticated page for tests."""
    # Mock authentication if your app requires it
    page.goto(f"{BASE_URL}/login")

    # Fill in login credentials (adjust based on your app)
    # page.fill("#username", "test_user")
    # page.fill("#password", "test_password")
    # page.click("#login-button")

    # Wait for authentication to complete
    # page.wait_for_url(f"{BASE_URL}/dashboard")

    return page


@pytest.fixture()
def dashboard_page(page: Page) -> Page:
    """Navigate to the dashboard page."""
    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # Wait for main dashboard container to be visible
        page.wait_for_selector(
            "[data-testid='dashboard-container'], .dashboard-container, .container",
            timeout=10000,
        )

    except Exception as e:
        print(f"Failed to load dashboard: {e}")
        # Take screenshot for debugging
        page.screenshot(path=f"test-results/screenshots/dashboard-load-error-{int(time.time())}.png")
        raise

    return page


@pytest.fixture()
def recommendations_page(page: Page) -> Page:
    """Navigate directly to the recommendations tab."""
    # First load the dashboard
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # Look for recommendations tab and click it
    tab_selectors = [
        "[data-testid='recommendations-tab']",
        "#recommendations-tab",
        ".nav-link:has-text('Recommendations')",
        "a[href*='recommendations']",
    ]

    tab_clicked = False
    for selector in tab_selectors:
        tab = page.locator(selector)
        if tab.count() > 0:
            tab.first.click()
            tab_clicked = True
            break

    if not tab_clicked:
        print("Could not find recommendations tab, trying direct navigation")
        page.goto(f"{BASE_URL}/recommendations")

    # Wait for recommendations content to load
    page.wait_for_timeout(2000)

    return page


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--dashboard-url",
        action="store",
        default=BASE_URL,
        help=f"URL of the dashboard (default: {BASE_URL})",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        help="Run tests in headed mode",
    )
    parser.addoption(
        "--slowmo",
        action="store",
        type=int,
        default=0,
        help="Slow down operations by specified milliseconds",
    )


def pytest_configure(config):
    """Configure pytest with custom options."""
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running",
    )
    config.addinivalue_line(
        "markers",
        "smoke: mark test as smoke test",
    )


@pytest.fixture(scope="session")
def get_dashboard_url(pytestconfig):
    """Get dashboard URL from command line or environment."""
    return pytestconfig.getoption("--dashboard_url") or BASE_URL


@pytest.fixture()
def video_enabled(pytestconfig):
    """Determine if video recording should be enabled."""
    return not pytestconfig.getoption("--headed")


# Custom markers
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow
pytest.mark.smoke = pytest.mark.smoke
