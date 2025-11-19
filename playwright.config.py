"""Playwright configuration for Watchtower E2E tests."""

import os
from pathlib import Path

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent

# Project configuration
PROJECT_ROOT = get_project_root()
BASE_URL = os.getenv("DASHBOARD_URL", "http://localhost:7777")

def pytest_configure():
    """Configure pytest with custom markers."""
    pass

# Test configuration
config = {
    # Browser settings
    "browser": "chromium",  # chromium, firefox, webkit
    "headless": True,  # Set to False for debugging
    "slowMo": 100,  # Slow down operations by specified milliseconds

    # Test execution
    "timeout": 30000,  # 30 seconds timeout
    "retries": 2,  # Number of retries for failed tests

    # Output
    "outputDir": PROJECT_ROOT / "test-results",
    "videoDir": PROJECT_ROOT / "test-results" / "videos",
    "screenshotDir": PROJECT_ROOT / "test-results" / "screenshots",
    "traceDir": PROJECT_ROOT / "test-results" / "traces",

    # Reporting
    "htmlReport": True,
    "reportDir": PROJECT_ROOT / "test-results" / "html-report",

    # Test configuration
    "testIgnore": [
        "**/node_modules/**",
        "**/dist/**",
        "**/.git/**",
        "**/.venv/**",
        "**/__pycache__/**",
    ],

    # Environment
    "env": {
        "DASHBOARD_URL": BASE_URL,
        "TEST_ENV": "e2e",
    },

    # Test files
    "testMatch": [
        "Tests/e2e/**/test_*.py",
    ],

    # Global setup and teardown
    "globalSetup": PROJECT_ROOT / "Tests" / "e2e" / "conftest.py",
    "globalTeardown": PROJECT_ROOT / "Tests" / "e2e" / "conftest.py",

    # Viewport sizes for responsive testing
    "viewport": {
        "width": 1280,
        "height": 720,
    },

    # Device emulation
    "devices": [
        "Desktop Chrome",
        "Desktop Firefox",
        "iPhone 13",
        "iPad",
    ],

    # Network conditions
    "networkConditions": {
        "offline": False,
        "downloadThroughput": None,
        "uploadThroughput": None,
        "latency": None,
    },

    # Geolocation
    "geolocation": None,

    # Permissions
    "permissions": [
        "geolocation",
        "notifications",
    ],

    # Color scheme
    "colorScheme": "light",  # light, dark, no-preference

    # Locale
    "locale": "en-US",

    # Timezone
    "timezoneId": "America/New_York",

    # User agent
    "userAgent": None,

    # HTTP headers
    "extraHTTPHeaders": {
        "Accept-Language": "en-US,en;q=0.9",
    },

    # Ignore HTTPS errors
    "ignoreHTTPSErrors": False,

    # Bypass CSP
    "bypassCSP": False,

    # Service workers
    "serviceWorkers": "allow",

    # Coverage
    "collectCoverage": False,
    "coverageDir": PROJECT_ROOT / "test-results" / "coverage",

    # Har capture
    "harDir": PROJECT_ROOT / "test-results" / "har",

    # Development tools
    "devtools": False,

    # Extensions
    "extensions": [],

    # Downloads
    "downloadsDir": PROJECT_ROOT / "test-results" / "downloads",

    # Application data
    "userDataDir": None,

    # Chrome-specific options
    "chromiumOptions": {
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
        ],
    },

    # Firefox-specific options
    "firefoxOptions": {
        "args": [],
    },

    # WebKit-specific options
    "webkitOptions": {
        "args": [],
    },
}

# Export configuration
playwright_config = config