#!/usr/bin/env python3
"""Development installation script for Watchtower.

This script installs the Watchtower package in development mode,
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"[INFO] {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"[PASS] {description} completed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {description} failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        return False


def main():
    """Main installation function."""
    print("[INFO] Watchtower Development Setup")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("[FAIL] Error: pyproject.toml not found. Please run this script from the project root.")
        sys.exit(1)

    # Install package in development mode
    commands = [
        # Install in development mode with all extras
        ([sys.executable, "-m", "pip", "install", "-e", ".[dev,ml,web,all]"],
         "Installing Watchtower in development mode"),

        # Verify installation
        ([sys.executable, "-c", "from config.settings import get_settings; print('[PASS] Package installed successfully')"],
         "Verifying installation"),
    ]

    success_count = 0
    for command, description in commands:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"\n[FAIL] Setup failed at step: {description}")
            print("Please check the error messages above and try again.")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("[PASS] Development setup completed successfully!")
    print("\nNext steps:")
    print("2. Use normal imports like: from config.settings import get_settings")
    print("3. Run 'python -m pytest' to run tests")
    print("4. Run 'streamlit run src/web/fullstreamlit/app.py' to start the dashboard")
    print("\nNote: If you add new dependencies, run 'pip install -e .[dev,ml,web,all]' again")


if __name__ == "__main__":
    main()
