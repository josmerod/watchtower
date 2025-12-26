#!/usr/bin/env python3
"""E2E Test Runner for Watchtower Recommendations

This script runs Playwright E2E tests for the recommendations functionality.
It handles setup, test execution, and reporting.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_dashboard_running(url: str = "http://localhost:7777") -> bool:
    """Check if the dashboard is running and accessible."""
    try:
        import requests

        response = requests.get(url, timeout=5)
        return response.status_code < 500
    except Exception:
        return False


def setup_test_environment():
    """Set up the test environment."""
    print("Setting up test environment...")

    # Create test directories
    test_results_dir = project_root / "test-results"
    test_results_dir.mkdir(exist_ok=True)
    (test_results_dir / "videos").mkdir(exist_ok=True)
    (test_results_dir / "screenshots").mkdir(exist_ok=True)
    (test_results_dir / "html-report").mkdir(exist_ok=True)

    # Set environment variables
    os.environ["TEST_ENV"] = "e2e"
    os.environ["DASHBOARD_URL"] = "http://localhost:7777"

    print(f"Test results will be saved to: {test_results_dir}")


def start_dashboard_if_needed():
    """Start the dashboard if it's not already running."""
    if check_dashboard_running():
        print("✓ Dashboard is already running")
        return None

    print("Dashboard not running, attempting to start...")
    try:
        # Try to start the dashboard
        cmd = [sys.executable, "run_watchtower_dashboard.py"]
        process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for dashboard to start
        max_wait = 30  # 30 seconds
        wait_interval = 2
        waited = 0

        while waited < max_wait:
            if check_dashboard_running():
                print(f"✓ Dashboard started successfully (waited {waited}s)")
                return process
            time.sleep(wait_interval)
            waited += wait_interval

        print("✗ Failed to start dashboard within timeout")
        process.terminate()
        return None

    except Exception as e:
        print(f"✗ Error starting dashboard: {e}")
        return None


def run_playwright_tests(
    test_pattern: str = "Tests/e2e/test_recommendations_e2e.py",
    headed: bool = False,
    slowmo: int = 0,
    browser: str = "chromium",
    retries: int = 2,
) -> bool:
    """Run the Playwright E2E tests."""
    print(f"Running Playwright tests: {test_pattern}")

    # Prepare pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_pattern,
        "-v",
        f"--browser={browser}",
        f"--retries={retries}",
        "--timeout=30000",
    ]

    if headed:
        cmd.append("--headed")
    else:
        cmd.append("--headless")

    if slowmo > 0:
        cmd.append(f"--slowmo={slowmo}")

    # Add output options
    cmd.extend(
        [
            "--html=test-results/html-report/index.html",
            "--self-contained-html",
            "--screenshot=only-on-failure",
            "--video=retain-on-failure",
            "--tracing=retain-on-failure",
        ]
    )

    # Set environment for Playwright
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(project_root / ".playwright-browsers")

    print(f"Command: {' '.join(cmd)}")

    try:
        # Run tests
        result = subprocess.run(cmd, cwd=project_root, env=env)
        return result.returncode == 0

    except Exception as e:
        print(f"✗ Error running tests: {e}")
        return False


def run_smoke_tests() -> bool:
    """Run a quick smoke test to verify basic functionality."""
    print("Running smoke tests...")

    smoke_test_files = [
        "Tests/e2e/test_recommendations_e2e.py::TestRecommendationsE2E::test_recommendations_tab_loads",
        "Tests/e2e/test_recommendations_e2e.py::TestRecommendationsE2E::test_recommendations_display_with_data",
        "Tests/e2e/test_recommendations_e2e.py::TestRecommendationsE2E::test_recommendation_feedback_mechanism",
    ]

    return run_playwright_tests(
        test_pattern=" ".join(smoke_test_files),
        slowmo=500,  # Slower for visibility
        retries=1,
    )


def run_full_test_suite() -> bool:
    """Run the full test suite."""
    print("Running full test suite...")

    return run_playwright_tests(
        test_pattern="Tests/e2e/test_recommendations_e2e.py",
        slowmo=100,
        retries=2,
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run E2E tests for Watchtower recommendations")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run only smoke tests",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run tests in headed mode",
    )
    parser.add_argument(
        "--slowmo",
        type=int,
        default=0,
        help="Slow down operations by specified milliseconds",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser to run tests on",
    )
    parser.add_argument(
        "--skip-dashboard-start",
        action="store_true",
        help="Skip automatic dashboard start",
    )
    parser.add_argument(
        "--dashboard-url",
        default="http://localhost:7777",
        help="Dashboard URL",
    )

    args = parser.parse_args()

    print("🎭 Watchtower E2E Test Runner")
    print("=" * 50)

    # Set up environment
    setup_test_environment()
    os.environ["DASHBOARD_URL"] = args.dashboard_url

    # Start dashboard if needed
    dashboard_process = None
    if not args.skip_dashboard_start:
        dashboard_process = start_dashboard_if_needed()
        if not dashboard_process and not check_dashboard_running(args.dashboard_url):
            print("✗ Cannot proceed without running dashboard")
            return 1

    try:
        # Run tests
        success = True

        if args.smoke:
            success = run_smoke_tests()
        else:
            success = run_full_test_suite()

        if success:
            print("\n✓ All E2E tests passed!")
            print(f"📊 HTML report available at: {project_root}/test-results/html-report/index.html")
        else:
            print("\n✗ Some E2E tests failed!")
            print(f"📊 Check the report for details: {project_root}/test-results/html-report/index.html")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1

    finally:
        # Clean up dashboard process
        if dashboard_process:
            try:
                dashboard_process.terminate()
                dashboard_process.wait(timeout=5)
                print("✓ Dashboard stopped")
            except subprocess.TimeoutExpired:
                dashboard_process.kill()
                print("✓ Dashboard force-stopped")
            except Exception as e:
                print(f"⚠️  Error stopping dashboard: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
