#!/usr/bin/env python3
"""Development installation script for Watchtower using UV.

This script installs the Watchtower package in development mode using UV,
the extremely fast Python package manager written in Rust.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path


def check_uv_installed() -> bool:
    """Check if UV is installed and available."""
    return shutil.which("uv") is not None


def install_uv() -> bool:
    """Install UV using the official installer."""
    print("[INFO] UV not found. Installing UV...")
    
    try:
        if sys.platform.startswith('win'):
            # Windows installation
            cmd = [
                "powershell", "-ExecutionPolicy", "ByPass", "-c",
                "irm https://astral.sh/uv/install.ps1 | iex"
            ]
        else:
            # Unix/Linux/macOS installation
            cmd = [
                "sh", "-c",
                "curl -LsSf https://astral.sh/uv/install.sh | sh"
            ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[PASS] UV installed successfully")
        
        # Add UV to PATH for current session (Unix-like systems)
        if not sys.platform.startswith('win'):
            uv_bin_path = Path.home() / ".cargo" / "bin"
            if str(uv_bin_path) not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{uv_bin_path}:{os.environ.get('PATH', '')}"
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Failed to install UV: {e}")
        print("Please install UV manually from https://github.com/astral-sh/uv")
        return False


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
    print("[INFO] Watchtower Development Setup with UV")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("[FAIL] Error: pyproject.toml not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Check if UV is installed
    if not check_uv_installed():
        if not install_uv():
            sys.exit(1)
        
        # Re-check after installation
        if not check_uv_installed():
            print("[FAIL] UV installation failed. Please install manually.")
            sys.exit(1)
    
    print("[PASS] UV is available")
    
    # Install package in development mode using UV
    commands = [
        # Sync dependencies and install in development mode
        (["uv", "sync", "--all-extras"], 
         "Syncing dependencies with UV"),
        
        # Install Playwright browsers
        (["uv", "run", "playwright", "install"], 
         "Installing Playwright browsers"),
        
        # Verify installation
        (["uv", "run", "python", "-c", "from src.config.settings import get_settings; print('[PASS] Package setup successfully')"], 
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
    print("[PASS] Development setup completed successfully with UV!")
    print("\nNext steps:")
    print("1. Run 'uv run streamlit run src/web/fullstreamlit/app.py' to start the dashboard")
    print("2. Use 'uv run python <script>' to run Python scripts")
    print("3. Use 'uv run pytest' to run tests")
    print("4. Use 'uv add <package>' to add new dependencies")
    print("5. Use 'uv remove <package>' to remove dependencies")
    print("\nUV Commands Reference:")
    print("- uv sync: Install/update dependencies from pyproject.toml")
    print("- uv add: Add a new dependency")
    print("- uv remove: Remove a dependency")
    print("- uv run: Run a command in the project environment")
    print("- uv lock: Update the lockfile")
    print("- uv tree: Show dependency tree")


if __name__ == "__main__":
    main() 