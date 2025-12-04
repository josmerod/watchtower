"""Visual tests for AI Research Dashboard Tab."""

import os
import subprocess
import sys
import time

import pytest
import requests
from playwright.sync_api import Page, expect

# Constants
DASHBOARD_URL = "http://localhost:7778"
DASHBOARD_SCRIPT = "run_watchtower_dashboard.py"


@pytest.fixture(scope="module")
def dashboard_process():
    """Start the dashboard process for testing."""
    # Start the dashboard
    process = subprocess.Popen(
        [sys.executable, DASHBOARD_SCRIPT],
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to start
    max_retries = 60
    for i in range(max_retries):
        try:
            response = requests.get(f"{DASHBOARD_URL}/health")
            if response.status_code == 200:
                break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        process.terminate()
        stdout, stderr = process.communicate()
        raise RuntimeError(f"Dashboard failed to start.\nStdout: {stdout}\nStderr: {stderr}")

    yield process

    # Cleanup
    process.terminate()
    process.wait()


def test_ai_research_tab_visual(page: Page, dashboard_process):
    """Test that the AI Research tab renders correctly."""
    # Navigate to dashboard
    page.goto(DASHBOARD_URL)

    # Wait for title
    expect(page.get_by_role("heading", name="Watchtower Dashboard")).to_be_visible()

    # Click on AI Research Intelligence tab
    # Note: The tab label might be truncated or hidden in mobile view, but we assume desktop for this test
    # We look for the tab with the specific text
    tab_locator = page.get_by_text("AI Research Intelligence")

    # If tab is not visible (e.g. in overflow), we might need to handle that,
    # but for now assuming it's visible or we can force click
    tab_locator.click()

    # Verify Tab Content
    expect(page.get_by_role("heading", name="AI Research Intelligence")).to_be_visible()

    # Verify Summary Cards
    expect(page.get_by_text("Total Papers")).to_be_visible()
    expect(page.get_by_text("High Trend")).to_be_visible()
    expect(page.get_by_text("Easy Implementation")).to_be_visible()

    # Verify Charts
    expect(page.locator(".js-plotly-plot").first).to_be_visible()

    # Verify Table
    # Check for the mock paper title we inserted
    expect(page.get_by_text("Attention Is All You Need")).to_be_visible()

    # Take a screenshot for visual verification artifact
    os.makedirs("artifacts", exist_ok=True)
    page.screenshot(path="artifacts/ai_research_tab.png", full_page=True)
