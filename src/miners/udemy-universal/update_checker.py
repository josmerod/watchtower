"""Update checker for the Udemy Universal miner.

This module provides functionality to check for updates from the original
repository and notify users about new versions available.
"""

import json
import re
from datetime import datetime, timedelta

import requests
from logger import get_logger
from packaging import version

logger = get_logger(__name__)

# Repository information
GITHUB_REPO = "techtanic/Discounted-Udemy-Course-Enroller"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
CURRENT_VERSION = "2.5.1"  # Should match VERSION in base.py

# Update checking settings
UPDATE_CHECK_INTERVAL = timedelta(days=1)  # Check for updates daily
UPDATE_CHECK_FILE = "last_update_check.json"


class UpdateChecker:
    """Handles checking for updates from the original repository."""

    def __init__(self, current_version: str = CURRENT_VERSION):
        """Initialize the update checker.

        Args:
            current_version: The current version of the application
        """
        self.current_version = current_version
        self.logger = logger

    def get_latest_version(self) -> dict | None:
        """Get the latest version information from GitHub.

        Returns:
            Dictionary containing version information or None if failed
        """
        try:
            response = requests.get(GITHUB_API_URL, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "version": data["tag_name"].lstrip("v"),
                "name": data["name"],
                "body": data["body"],
                "published_at": data["published_at"],
                "download_url": data["html_url"],
                "assets": data["assets"],
            }
        except requests.RequestException as e:
            self.logger.warning(f"Failed to check for updates: {e}")
            return None
        except (KeyError, ValueError) as e:
            self.logger.warning(f"Invalid response format from GitHub API: {e}")
            return None

    def compare_versions(self, current: str, latest: str) -> int:
        """Compare two version strings.

        Args:
            current: Current version string
            latest: Latest version string

        Returns:
            -1 if current < latest, 0 if equal, 1 if current > latest
        """
        try:
            current_version = version.parse(current)
            latest_version = version.parse(latest)

            if current_version < latest_version:
                return -1
            elif current_version > latest_version:
                return 1
            else:
                return 0
        except version.InvalidVersion:
            # Fallback to string comparison
            if current < latest:
                return -1
            elif current > latest:
                return 1
            else:
                return 0

    def should_check_for_updates(self) -> bool:
        """Check if it's time to check for updates based on the interval.

        Returns:
            True if update check should be performed
        """
        try:
            with open(UPDATE_CHECK_FILE) as f:
                data = json.load(f)
                last_check = datetime.fromisoformat(data["last_check"])
                return datetime.now() - last_check > UPDATE_CHECK_INTERVAL
        except (FileNotFoundError, KeyError, ValueError):
            return True

    def update_check_timestamp(self):
        """Update the last update check timestamp."""
        try:
            data = {
                "last_check": datetime.now().isoformat(),
                "version": self.current_version,
            }
            with open(UPDATE_CHECK_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to update check timestamp: {e}")

    def check_for_updates(self, force: bool = False) -> tuple[str, str]:
        """Check for updates and return status messages.

        Args:
            force: Force check even if interval hasn't passed

        Returns:
            Tuple of (login_title, main_title) for display
        """
        if not force and not self.should_check_for_updates():
            return "Up-to-date", f"DUCE v{self.current_version}"

        self.update_check_timestamp()

        latest_info = self.get_latest_version()
        if not latest_info:
            return "Update Check Failed", f"DUCE v{self.current_version}"

        latest_version = latest_info["version"]
        comparison = self.compare_versions(self.current_version, latest_version)

        if comparison < 0:
            # New version available
            self.logger.info(f"New version available: {latest_version}")
            return (
                f"Update Available: v{latest_version}",
                f"DUCE v{self.current_version} → v{latest_version}",
            )
        elif comparison > 0:
            # Current version is newer (development version)
            return ("Development Version", f"DUCE v{self.current_version} (dev)")
        else:
            # Versions are equal
            return "Up-to-date", f"DUCE v{self.current_version}"

    def get_update_info(self) -> dict | None:
        """Get detailed update information if available.

        Returns:
            Dictionary with update details or None
        """
        latest_info = self.get_latest_version()
        if not latest_info:
            return None

        latest_version = latest_info["version"]
        comparison = self.compare_versions(self.current_version, latest_version)

        if comparison < 0:
            # Parse changelog/release notes
            changelog = self.parse_changelog(latest_info["body"])

            return {
                "available": True,
                "current_version": self.current_version,
                "latest_version": latest_version,
                "release_name": latest_info["name"],
                "published_at": latest_info["published_at"],
                "download_url": latest_info["download_url"],
                "changelog": changelog,
                "assets": latest_info["assets"],
            }

        return {
            "available": False,
            "current_version": self.current_version,
            "latest_version": latest_version,
        }

    def parse_changelog(self, release_body: str) -> list:
        """Parse changelog from release body.

        Args:
            release_body: The release body text

        Returns:
            List of changelog items
        """
        if not release_body:
            return []

        # Common changelog patterns
        patterns = [
            r"^\s*[-*+]\s+(.+)$",  # Bullet points
            r"^\s*\d+\.\s+(.+)$",  # Numbered lists
            r"^\s*•\s+(.+)$",  # Bullet character
        ]

        changelog = []
        lines = release_body.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    changelog.append(match.group(1))
                    break

        return changelog

    def display_update_notification(self, update_info: dict):
        """Display a formatted update notification.

        Args:
            update_info: Update information dictionary
        """
        if not update_info["available"]:
            self.logger.info(f"You are using the latest version: v{update_info['current_version']}")
            return

        self.logger.info("=" * 60)
        self.logger.info("🆕 UPDATE AVAILABLE")
        self.logger.info("=" * 60)
        self.logger.info(f"Current Version: v{update_info['current_version']}")
        self.logger.info(f"Latest Version:  v{update_info['latest_version']}")
        self.logger.info(f"Release Name:    {update_info['release_name']}")
        self.logger.info(f"Published:       {update_info['published_at']}")
        self.logger.info(f"Download:        {update_info['download_url']}")

        if update_info["changelog"]:
            self.logger.info("\nWhat's New:")
            for item in update_info["changelog"][:5]:  # Show first 5 items
                self.logger.info(f"  • {item}")
            if len(update_info["changelog"]) > 5:
                self.logger.info(f"  ... and {len(update_info['changelog']) - 5} more changes")

        self.logger.info("\nTo update, visit: " + GITHUB_RELEASES_URL)
        self.logger.info("=" * 60)

    def auto_update(self) -> bool:
        """Attempt to auto-update the application (if supported).

        Returns:
            True if update was successful, False otherwise
        """
        # This is a placeholder for auto-update functionality
        # In a real implementation, this would download and install the update
        self.logger.warning("Auto-update is not implemented yet")
        return False


def check_for_updates(current_version: str = CURRENT_VERSION, force: bool = False) -> tuple[str, str]:
    """Convenience function to check for updates.

    Args:
        current_version: Current version of the application
        force: Force check even if interval hasn't passed

    Returns:
        Tuple of (login_title, main_title) for display
    """
    checker = UpdateChecker(current_version)
    return checker.check_for_updates(force)


def get_update_info(current_version: str = CURRENT_VERSION) -> dict | None:
    """Convenience function to get update information.

    Args:
        current_version: Current version of the application

    Returns:
        Dictionary with update details or None
    """
    checker = UpdateChecker(current_version)
    return checker.get_update_info()


def display_update_notification(current_version: str = CURRENT_VERSION):
    """Convenience function to display update notification.

    Args:
        current_version: Current version of the application
    """
    checker = UpdateChecker(current_version)
    update_info = checker.get_update_info()
    if update_info:
        checker.display_update_notification(update_info)


if __name__ == "__main__":
    # Test the update checker
    checker = UpdateChecker()

    print("Testing update checker...")
    login_title, main_title = checker.check_for_updates(force=True)
    print(f"Login Title: {login_title}")
    print(f"Main Title: {main_title}")

    update_info = checker.get_update_info()
    if update_info:
        checker.display_update_notification(update_info)
