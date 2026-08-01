#!/usr/bin/env python3
"""🏯 Watchtower Dashboard - Unified Installer Script
📡 Real-time Intelligence & Monitoring Platform

This script automatically detects your operating system and runs the appropriate
deployment script with proper timeout handling to avoid hanging.
"""

import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path


def print_banner():
    """Print the Watchtower banner"""
    print("=" * 64)
    print("  🏯 Watchtower Dashboard - Unified Installer")
    print("  📡 Real-time Intelligence & Monitoring Platform")
    print("=" * 64)
    print()


def timeout_handler(signum, frame):
    """Handle timeout signal"""
    print("\n[ERROR] Installation process timed out!")
    print("[INFO] Please check your network connection and try again.")
    sys.exit(1)


def run_with_timeout(command, timeout_seconds=300):
    """Run a command with timeout handling"""
    print(f"[INFO] Running: {command}")
    print(f"[INFO] Timeout set to {timeout_seconds} seconds")

    try:
        # Set up signal handler for timeout (Unix-like systems)
        if platform.system() != "Windows":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

        # Run the command
        result = subprocess.run(
            command,
            capture_output=False,
            text=True,
            timeout=timeout_seconds,
        )

        # Cancel the alarm (Unix-like systems)
        if platform.system() != "Windows":
            signal.alarm(0)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"\n[ERROR] Command timed out after {timeout_seconds} seconds!")
        print("[INFO] Please check your network connection and try again.")
        return False
    except KeyboardInterrupt:
        print("\n[INFO] Installation cancelled by user.")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False


def detect_os():
    """Detect the operating system"""
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        return "unknown"


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"[ERROR] Python 3.10+ required. Current version: {version.major}.{version.minor}")
        print("[INFO] Please upgrade Python and try again.")
        return False

    print(f"[PASS] Python version: {version.major}.{version.minor}")
    return True


def main():
    """Main installer function"""
    print_banner()

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("[ERROR] pyproject.toml not found. Please run this script from the project root.")
        print(f"[ERROR] Current directory: {os.getcwd()}")
        sys.exit(1)

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Detect operating system
    os_type = detect_os()
    print(f"[INFO] Detected OS: {os_type}")
    print()

    # Select appropriate deployment script
    if os_type == "windows":
        script_name = "deploy_windows.bat"
        command = [script_name]
    elif os_type == "macos":
        script_name = "deploy_mac.sh"
        command = ["bash", script_name]
    elif os_type == "linux":
        script_name = "deploy_linux.sh"
        command = ["bash", script_name]
    else:
        print(f"[ERROR] Unsupported operating system: {platform.system()}")
        print("[INFO] Please run the appropriate deployment script manually:")
        print("  Windows: deploy_windows.bat")
        print("  macOS:   bash deploy_mac.sh")
        print("  Linux:   bash deploy_linux.sh")
        sys.exit(1)

    # Check if deployment script exists
    if not Path(script_name).exists():
        print(f"[ERROR] Deployment script not found: {script_name}")
        print("[INFO] Please ensure all deployment scripts are present in the project root.")
        sys.exit(1)

    # Make script executable on Unix-like systems
    if os_type in ["macos", "linux"]:
        try:
            os.chmod(script_name, 0o755)
            print(f"[INFO] Made {script_name} executable")
        except Exception as e:
            print(f"[WARNING] Could not make script executable: {e}")

    print(f"[INFO] Running deployment script: {script_name}")
    print(f"[INFO] Command: {command}")
    print()

    # Run the deployment script with timeout
    start_time = time.time()
    success = run_with_timeout(command, timeout_seconds=600)  # 10 minute timeout
    end_time = time.time()

    print()
    print("=" * 64)

    if success:
        print("  ✅ Watchtower Installation Complete!")
        print("=" * 64)
        print()
        print("[SUCCESS] Watchtower is now installed and ready to use!")
        print(f"[INFO] Installation took {end_time - start_time:.1f} seconds")
        print()
        print("🚀 Quick Start Commands:")
        if os_type == "windows":
            print("  Main Dashboard:    run_watchtower_dashboard.bat")
            print("  Legacy Dashboard:  run_watchtower.bat")
            print("  Run ETL Processes: run_all_etl.bat")
            print("  Complete System:   run_all_etl_and_dashboard.bat")
        else:
            print("  Main Dashboard:    ./run_watchtower_dashboard.sh")
            print("  Legacy Dashboard:  ./run_streamlit.sh")
            print("  Run ETL Processes: ./run_all_etl.sh")
            print("  Complete System:   ./run_all_etl_and_dashboard.sh")
        print()
        print("🌐 Dashboard URLs:")
        print("  Main Dashboard:    http://localhost:7777")
        print("  Legacy Dashboard:  http://localhost:8501")
        print()
        print("📖 Documentation:")
        print("  Setup Guide:       docs/setup-guide.md")
        print("  Dashboard Guide:   docs/dashboard_guide.md")
        print("  Development Setup: DEVELOPMENT_SETUP.md")
    else:
        print("  ❌ Installation Failed!")
        print("=" * 64)
        print()
        print("[ERROR] Installation was not successful.")
        print("[INFO] Please check the error messages above and try again.")
        print()
        print("💡 Troubleshooting:")
        print("  1. Check your network connection")
        print("  2. Ensure Python 3.10+ is installed")
        print("  3. Run the deployment script manually:")
        print(f"     {command}")
        print("  4. Check the documentation for manual setup instructions")

        sys.exit(1)

    print("=" * 64)
    print()


if __name__ == "__main__":
    main()
