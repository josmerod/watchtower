#!/usr/bin/env python3
"""Udemy Course Scraper Setup and Runner.
=====================================

This script helps set up dependencies and run the Udemy course scraper CLI.
It checks for required dependencies, provides installation guidance, and
offers options to fix common issues.

Usage:
    python setup_and_run.py [--setup-only] [--run-only]

Options:
    --setup-only    Only check and setup dependencies, don't run the scraper
    --run-only      Skip dependency checks and run the scraper directly
    --help          Show this help message
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def print_header():
    """Print a nice header for the script."""
    print("=" * 60)
    print("    Udemy Course Scraper - Setup and Runner")
    print("=" * 60)
    print()


def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(
            f"❌ Python {version.major}.{version.minor} detected. Python 3.8+ required."
        )
        print("   Please upgrade Python and try again.")
        return False
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")

    missing_deps = []
    optional_missing = []

    # Required dependencies
    required_deps = [
        "requests",
        "beautifulsoup4",
        "tqdm",
    ]

    # Optional dependencies
    optional_deps = [
        "playwright",
        "cloudscraper",
    ]

    for dep in required_deps:
        try:
            __import__(dep.replace("-", "_"))
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} (required)")
            missing_deps.append(dep)

    for dep in optional_deps:
        try:
            __import__(dep.replace("-", "_"))
            print(f"✅ {dep} (optional)")
        except ImportError:
            print(f"⚠️  {dep} (optional - some scrapers may not work)")
            optional_missing.append(dep)

    return missing_deps, optional_missing


def check_playwright_browsers():
    """Check if Playwright browsers are installed."""
    print("\n🌐 Checking Playwright browsers...")

    try:
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            print("✅ Playwright browsers are installed and working")
            return True
        except Exception as e:
            print(f"❌ Playwright browsers not installed or not working: {e}")
            print(
                "   This will affect Real Discount, Udemy Freebies, and Udemy Free Courses scrapers"
            )
            return False
    except ImportError:
        print("⚠️  Playwright not installed - browser check skipped")
        return None


def install_dependencies(deps, optional=False):
    """Install missing dependencies."""
    if not deps:
        return True

    dep_type = "optional" if optional else "required"
    print(f"\n📥 Installing {dep_type} dependencies: {', '.join(deps)}")

    try:
        cmd = [sys.executable, "-m", "pip", "install", *deps]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Successfully installed {dep_type} dependencies")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {dep_type} dependencies:")
        print(f"   Error: {e.stderr}")
        print(f"   Try running manually: pip install {' '.join(deps)}")
        return False


def install_playwright_browsers():
    """Install Playwright browsers."""
    print("\n🌐 Installing Playwright browsers...")

    try:
        cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Successfully installed Playwright browsers")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Failed to install Playwright browsers:")
        print(f"   Error: {e.stderr}")
        print("   Try running manually: playwright install")
        return False


def setup_dependencies():
    """Set up all dependencies."""
    print_header()

    # Check Python version
    if not check_python_version():
        return False

    # Check dependencies
    missing_deps, optional_missing = check_dependencies()

    # Install missing required dependencies
    if missing_deps and not install_dependencies(missing_deps, optional=False):
        return False

    # Offer to install optional dependencies
    if optional_missing:
        response = input(
            f"\nInstall optional dependencies ({', '.join(optional_missing)})? [Y/n]: "
        )
        if response.lower() in ["", "y", "yes"]:
            install_dependencies(optional_missing, optional=True)

    # Check Playwright browsers if Playwright is available
    browser_status = check_playwright_browsers()
    if browser_status is False:
        response = input("\nInstall Playwright browsers? [Y/n]: ")
        if response.lower() in ["", "y", "yes"]:
            install_playwright_browsers()

    print("\n✅ Setup complete!")
    return True


def run_scraper():
    """Run the scraper CLI."""
    print("\n🚀 Starting Udemy Course Scraper...")
    print("-" * 40)

    try:
        # Import and run the CLI
        from cli import main_extract

        main_extract()
    except ImportError as e:
        print(f"❌ Failed to import CLI module: {e}")
        print("   Make sure you're running this script from the correct directory")
        return False
    except KeyboardInterrupt:
        print("\n\n⏹️  Scraper stopped by user")
        return True
    except Exception as e:
        print(f"\n❌ Unexpected error while running scraper: {e}")
        print("   Check the logs for more details")
        return False

    print("\n✅ Scraper finished!")
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Setup and run the Udemy Course Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--setup-only", action="store_true", help="Only check and setup dependencies"
    )
    parser.add_argument(
        "--run-only",
        action="store_true",
        help="Skip dependency checks and run directly",
    )

    args = parser.parse_args()

    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    success = True

    if args.run_only:
        # Run directly without setup
        success = run_scraper()
    elif args.setup_only:
        # Setup only
        success = setup_dependencies()
    else:
        # Full setup and run
        if setup_dependencies():
            print("\n" + "=" * 60)
            response = input("Setup complete! Run the scraper now? [Y/n]: ")
            if response.lower() in ["", "y", "yes"]:
                success = run_scraper()
        else:
            print("\n❌ Setup failed. Please fix the issues above and try again.")
            success = False

    if success:
        print("\n🎉 All done!")
    else:
        print("\n💔 Something went wrong. Check the messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
