#!/usr/bin/env python3
"""
Cross-platform service manager for Watchtower platform.

Supports:
- systemd (Linux)
- launchd (macOS)
- Windows services
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


class ServiceManager:
    """Cross-platform service manager."""

    def __init__(self):
        self.system = platform.system().lower()
        self.services_dir = Path(__file__).parent
        self.project_root = self.services_dir.parent

    def detect_service_manager(self):
        """Detect available service manager."""
        if self.system == "linux":
            # Check for systemd
            try:
                subprocess.run(["systemctl", "--version"], capture_output=True, check=True)
                return "systemd"
            except (subprocess.CalledProcessError, FileNotFoundError):
                return "manual"

        elif self.system == "darwin":
            # Check for launchd
            return "launchd"

        elif self.system == "windows":
            # Check for NSSM or use sc.exe
            nssm_path = r"C:\Program Files\nssm\win64\nssm.exe"
            if os.path.exists(nssm_path):
                return "nssm"
            return "sc"

        return "manual"

    def install_service(self):
        """Install the service."""
        manager = self.detect_service_manager()

        if manager == "systemd":
            self._install_systemd()
        elif manager == "launchd":
            self._install_launchd()
        elif manager == "nssm":
            self._install_nssm()
        elif manager == "sc":
            self._install_sc()
        else:
            print("ERROR No supported service manager found.")
            print("Please install manually or use Podman Compose.")
            sys.exit(1)

    def _install_systemd(self):
        """Install systemd service."""
        service_file = self.services_dir / "watchtower.service"
        target_file = Path("/etc/systemd/system/watchtower.service")

        print("INFO Installing systemd service...")

        # Copy service file
        try:
            import shutil
            shutil.copy2(service_file, target_file)

            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)

            # Enable service
            subprocess.run(["systemctl", "enable", "watchtower"], check=True)

            print("SUCCESS Systemd service installed successfully!")
            print("🚀 Start with: sudo systemctl start watchtower")
            print("STATUS Check status: sudo systemctl status watchtower")

        except PermissionError:
            print("ERROR Permission denied. Please run with sudo.")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to install systemd service: {e}")
            sys.exit(1)

    def _install_launchd(self):
        """Install launchd service on macOS."""
        plist_file = self.services_dir / "com.watchtower.platform.plist"
        target_dir = Path.home() / "Library" / "LaunchAgents"
        target_file = target_dir / "com.watchtower.platform.plist"

        print("INFO Installing launchd service...")

        try:
            # Create LaunchAgents directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)

            # Copy plist file
            import shutil
            shutil.copy2(plist_file, target_file)

            # Load the service
            subprocess.run(["launchctl", "load", str(target_file)], check=True)

            print("SUCCESS Launchd service installed successfully!")
            print("🚀 Start with: launchctl start com.watchtower.platform")
            print("STATUS Check status: launchctl list | grep watchtower")

        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to install launchd service: {e}")
            sys.exit(1)

    def _install_nssm(self):
        """Install Windows service with NSSM."""
        print("INFO Installing Windows service with NSSM...")

        script_path = self.project_root / "src" / "launcher" / "main.py"
        nssm_path = r"C:\Program Files\nssm\win64\nssm.exe"

        try:
            # Install service
            cmd = [
                nssm_path, "install", "WatchtowerPlatform",
                "uv", "run", "python", str(script_path), "--mode", "production"
            ]

            subprocess.run(cmd, check=True, cwd=self.project_root)

            # Set service properties
            subprocess.run([nssm_path, "set", "WatchtowerPlatform", "DisplayName",
                          "Watchtower Intelligence Platform"], check=True)
            subprocess.run([nssm_path, "set", "WatchtowerPlatform", "Description",
                          "Watchtower Intelligence Platform - Real-time data collection and monitoring"], check=True)

            print("SUCCESS NSSM service installed successfully!")
            print("🚀 Start with: net start WatchtowerPlatform")
            print("STATUS Check status: sc query WatchtowerPlatform")

        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to install NSSM service: {e}")
            sys.exit(1)

    def _install_sc(self):
        """Install Windows service with sc.exe (basic)."""
        print("INFO Installing Windows service with sc.exe...")
        print("WARNING  For better service management, consider installing NSSM from https://nssm.cc/")

        script_path = self.project_root / "src" / "launcher" / "main.py"
        wrapper_script = self.services_dir / "watchtower_service.bat"

        # Create wrapper script
        wrapper_content = f'''@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
uv run python "{script_path}" --mode production

endlocal
'''

        with open(wrapper_script, 'w') as f:
            f.write(wrapper_content)

        try:
            # Create service
            cmd = [
                "sc", "create", "WatchtowerPlatform", "binPath=",
                f"\"{wrapper_script}\"", "start=", "auto",
                "DisplayName=", "Watchtower Intelligence Platform"
            ]

            subprocess.run(cmd, check=True, shell=True)

            print("SUCCESS Windows service installed successfully!")
            print("🚀 Start with: net start WatchtowerPlatform")

        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to install Windows service: {e}")
            sys.exit(1)

    def uninstall_service(self):
        """Uninstall the service."""
        manager = self.detect_service_manager()

        if manager == "systemd":
            self._uninstall_systemd()
        elif manager == "launchd":
            self._uninstall_launchd()
        elif manager in ["nssm", "sc"]:
            self._uninstall_windows()
        else:
            print("ERROR No supported service manager found.")
            sys.exit(1)

    def _uninstall_systemd(self):
        """Uninstall systemd service."""
        print("🗑️  Uninstalling systemd service...")

        try:
            # Stop and disable service
            subprocess.run(["systemctl", "stop", "watchtower"], check=True)
            subprocess.run(["systemctl", "disable", "watchtower"], check=True)

            # Remove service file
            service_file = Path("/etc/systemd/system/watchtower.service")
            if service_file.exists():
                service_file.unlink()

            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)

            print("SUCCESS Systemd service uninstalled successfully!")

        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to uninstall systemd service: {e}")
            sys.exit(1)

    def _uninstall_launchd(self):
        """Uninstall launchd service on macOS."""
        print("🗑️  Uninstalling launchd service...")

        try:
            # Unload service
            subprocess.run(["launchctl", "unload", "~/Library/LaunchAgents/com.watchtower.platform.plist"], check=True)

            # Remove plist file
            plist_file = Path.home() / "Library" / "LaunchAgents" / "com.watchtower.platform.plist"
            if plist_file.exists():
                plist_file.unlink()

            print("SUCCESS Launchd service uninstalled successfully!")

        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to uninstall launchd service: {e}")
            sys.exit(1)

    def _uninstall_windows(self):
        """Uninstall Windows service."""
        print("🗑️  Uninstalling Windows service...")

        try:
            # Stop service
            subprocess.run(["net", "stop", "WatchtowerPlatform"], check=True)

            # Delete service
            subprocess.run(["sc", "delete", "WatchtowerPlatform"], check=True)

            print("SUCCESS Windows service uninstalled successfully!")

        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to uninstall Windows service: {e}")
            sys.exit(1)

    def start_service(self):
        """Start the service."""
        manager = self.detect_service_manager()

        if manager == "systemd":
            subprocess.run(["sudo", "systemctl", "start", "watchtower"], check=True)
        elif manager == "launchd":
            subprocess.run(["launchctl", "start", "com.watchtower.platform"], check=True)
        elif manager in ["nssm", "sc"]:
            subprocess.run(["net", "start", "WatchtowerPlatform"], check=True)

        print("🚀 Service started!")

    def stop_service(self):
        """Stop the service."""
        manager = self.detect_service_manager()

        if manager == "systemd":
            subprocess.run(["sudo", "systemctl", "stop", "watchtower"], check=True)
        elif manager == "launchd":
            subprocess.run(["launchctl", "stop", "com.watchtower.platform"], check=True)
        elif manager in ["nssm", "sc"]:
            subprocess.run(["net", "stop", "WatchtowerPlatform"], check=True)

        print("STOPPED  Service stopped!")

    def status_service(self):
        """Check service status."""
        manager = self.detect_service_manager()

        if manager == "systemd":
            result = subprocess.run(["systemctl", "status", "watchtower", "--no-pager"],
                                  capture_output=True, text=True)
            print(result.stdout)
        elif manager == "launchd":
            result = subprocess.run(["launchctl", "list", "|", "grep", "watchtower"],
                                  capture_output=True, text=True, shell=True)
            print(result.stdout)
        elif manager in ["nssm", "sc"]:
            result = subprocess.run(["sc", "query", "WatchtowerPlatform"],
                                  capture_output=True, text=True)
            print(result.stdout)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Watchtower Service Manager")
    parser.add_argument("action", choices=["install", "uninstall", "start", "stop", "status"],
                       help="Action to perform")
    parser.add_argument("--platform", help="Force platform (linux, darwin, windows)")

    args = parser.parse_args()

    if args.platform:
        # Override platform detection for testing
        import sys
        sys.modules[__name__].platform.system = lambda: args.platform

    manager = ServiceManager()

    print(f"TOOLS Watchtower Service Manager - Detected: {manager.detect_service_manager()}")

    if args.action == "install":
        manager.install_service()
    elif args.action == "uninstall":
        manager.uninstall_service()
    elif args.action == "start":
        manager.start_service()
    elif args.action == "stop":
        manager.stop_service()
    elif args.action == "status":
        manager.status_service()


if __name__ == "__main__":
    main()
