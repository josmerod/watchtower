"""Advanced cookie management for Udemy Universal miner.

This module provides comprehensive cookie extraction from multiple browsers
with fallback mechanisms and robust error handling.
"""

import json
import os
import platform
import shutil
import sqlite3
import tempfile
from datetime import datetime
from typing import Any

try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    import browser_cookie3

    BROWSER_COOKIE3_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE3_AVAILABLE = False

try:
    import browserforge

    BROWSERFORGE_AVAILABLE = True
except ImportError:
    BROWSERFORGE_AVAILABLE = False

from logger import get_logger

logger = get_logger(__name__)


class BrowserType:
    """Browser type constants."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"
    OPERA = "opera"
    BRAVE = "brave"
    CHROMIUM = "chromium"


class CookieManager:
    """Advanced cookie management for multiple browsers."""

    def __init__(self, preferred_browser: str = None):
        """Initialize the cookie manager.

        Args:
            preferred_browser: Preferred browser to try first
        """
        self.preferred_browser = preferred_browser or BrowserType.CHROME
        self.logger = logger
        self.system = platform.system().lower()
        self.domain = "udemy.com"

        # Browser detection cache
        self._browser_cache = {}

        # Required cookies for Udemy
        self.required_cookies = ["client_id", "access_token", "csrftoken"]

        # Browser paths for different operating systems
        self.browser_paths = self._get_browser_paths()

    def _get_browser_paths(self) -> dict[str, dict[str, str]]:
        """Get browser paths for different operating systems.

        Returns:
            Dictionary of browser paths by OS and browser
        """
        if self.system == "windows":
            return {
                BrowserType.CHROME: {
                    "cookies": os.path.expandvars(
                        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies"
                    ),
                    "profile": os.path.expandvars(
                        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default"
                    ),
                },
                BrowserType.FIREFOX: {
                    "cookies": os.path.expandvars(
                        r"%APPDATA%\Mozilla\Firefox\Profiles"
                    ),
                    "profile": os.path.expandvars(
                        r"%APPDATA%\Mozilla\Firefox\Profiles"
                    ),
                },
                BrowserType.EDGE: {
                    "cookies": os.path.expandvars(
                        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cookies"
                    ),
                    "profile": os.path.expandvars(
                        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default"
                    ),
                },
                BrowserType.BRAVE: {
                    "cookies": os.path.expandvars(
                        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Cookies"
                    ),
                    "profile": os.path.expandvars(
                        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default"
                    ),
                },
                BrowserType.OPERA: {
                    "cookies": os.path.expandvars(
                        r"%APPDATA%\Opera Software\Opera Stable\Cookies"
                    ),
                    "profile": os.path.expandvars(
                        r"%APPDATA%\Opera Software\Opera Stable"
                    ),
                },
            }
        elif self.system == "darwin":  # macOS
            return {
                BrowserType.CHROME: {
                    "cookies": os.path.expanduser(
                        "~/Library/Application Support/Google/Chrome/Default/Cookies"
                    ),
                    "profile": os.path.expanduser(
                        "~/Library/Application Support/Google/Chrome/Default"
                    ),
                },
                BrowserType.FIREFOX: {
                    "cookies": os.path.expanduser(
                        "~/Library/Application Support/Firefox/Profiles"
                    ),
                    "profile": os.path.expanduser(
                        "~/Library/Application Support/Firefox/Profiles"
                    ),
                },
                BrowserType.SAFARI: {
                    "cookies": os.path.expanduser(
                        "~/Library/Cookies/Cookies.binarycookies"
                    ),
                    "profile": os.path.expanduser("~/Library/Safari"),
                },
                BrowserType.EDGE: {
                    "cookies": os.path.expanduser(
                        "~/Library/Application Support/Microsoft Edge/Default/Cookies"
                    ),
                    "profile": os.path.expanduser(
                        "~/Library/Application Support/Microsoft Edge/Default"
                    ),
                },
                BrowserType.BRAVE: {
                    "cookies": os.path.expanduser(
                        "~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies"
                    ),
                    "profile": os.path.expanduser(
                        "~/Library/Application Support/BraveSoftware/Brave-Browser/Default"
                    ),
                },
            }
        else:  # Linux
            return {
                BrowserType.CHROME: {
                    "cookies": os.path.expanduser(
                        "~/.config/google-chrome/Default/Cookies"
                    ),
                    "profile": os.path.expanduser("~/.config/google-chrome/Default"),
                },
                BrowserType.FIREFOX: {
                    "cookies": os.path.expanduser("~/.mozilla/firefox"),
                    "profile": os.path.expanduser("~/.mozilla/firefox"),
                },
                BrowserType.CHROMIUM: {
                    "cookies": os.path.expanduser("~/.config/chromium/Default/Cookies"),
                    "profile": os.path.expanduser("~/.config/chromium/Default"),
                },
                BrowserType.BRAVE: {
                    "cookies": os.path.expanduser(
                        "~/.config/BraveSoftware/Brave-Browser/Default/Cookies"
                    ),
                    "profile": os.path.expanduser(
                        "~/.config/BraveSoftware/Brave-Browser/Default"
                    ),
                },
            }

    def detect_installed_browsers(self) -> list[str]:
        """Detect installed browsers on the system.

        Returns:
            List of detected browser names
        """
        if hasattr(self, "_cached_browsers"):
            return self._cached_browsers

        detected = []

        for browser, paths in self.browser_paths.items():
            if self._is_browser_installed(browser, paths):
                detected.append(browser)

        self._cached_browsers = detected
        self.logger.info(f"Detected browsers: {detected}")
        return detected

    def _is_browser_installed(self, browser: str, paths: dict[str, str]) -> bool:
        """Check if a browser is installed.

        Args:
            browser: Browser name
            paths: Browser paths dictionary

        Returns:
            True if browser is installed
        """
        # Check if cookie file or profile directory exists
        for path_type, path in paths.items():
            if path_type == "cookies":
                if os.path.exists(path):
                    return True

                # For Firefox, check profiles directory
                if browser == BrowserType.FIREFOX and os.path.exists(path):
                    try:
                        profiles = [
                            d
                            for d in os.listdir(path)
                            if d.endswith(".default") or d.endswith(".default-release")
                        ]
                        return len(profiles) > 0
                    except (OSError, PermissionError):
                        # Failed to list directory, browser not accessible
                        pass

        return False

    def get_cookies_browser_cookie3(self, browser: str = None) -> dict[str, str] | None:
        """Get cookies using browser_cookie3 library.

        Args:
            browser: Browser to extract from

        Returns:
            Dictionary of cookies or None if failed
        """
        if not BROWSER_COOKIE3_AVAILABLE:
            self.logger.warning("browser_cookie3 not available")
            return None

        browser = browser or self.preferred_browser

        try:
            if browser == BrowserType.CHROME:
                cj = browser_cookie3.chrome(domain_name=self.domain)
            elif browser == BrowserType.FIREFOX:
                cj = browser_cookie3.firefox(domain_name=self.domain)
            elif browser == BrowserType.EDGE:
                cj = browser_cookie3.edge(domain_name=self.domain)
            elif browser == BrowserType.SAFARI:
                cj = browser_cookie3.safari(domain_name=self.domain)
            elif browser == BrowserType.OPERA:
                cj = browser_cookie3.opera(domain_name=self.domain)
            else:
                self.logger.warning(
                    f"Unsupported browser for browser_cookie3: {browser}"
                )
                return None

            cookies = {}
            for cookie in cj:
                if cookie.domain == self.domain or cookie.domain == f".{self.domain}":
                    cookies[cookie.name] = cookie.value

            # Check if we have required cookies
            if self._validate_cookies(cookies):
                self.logger.info(
                    f"Successfully extracted cookies from {browser} using browser_cookie3"
                )
                return cookies
            else:
                self.logger.warning(f"Required cookies not found in {browser}")
                return None

        except Exception as e:
            self.logger.warning(
                f"Failed to extract cookies from {browser} using browser_cookie3: {e}"
            )
            return None

    def get_cookies_sqlite(self, browser: str = None) -> dict[str, str] | None:
        """Get cookies by directly reading SQLite database.

        Args:
            browser: Browser to extract from

        Returns:
            Dictionary of cookies or None if failed
        """
        browser = browser or self.preferred_browser

        if browser not in self.browser_paths:
            self.logger.warning(f"Unsupported browser: {browser}")
            return None

        cookie_path = self.browser_paths[browser]["cookies"]

        try:
            return self._extract_cookies_from_sqlite(cookie_path, browser)
        except Exception as e:
            self.logger.warning(f"Failed to extract cookies from {browser} SQLite: {e}")
            return None

    def _extract_cookies_from_sqlite(
        self, cookie_path: str, browser: str
    ) -> dict[str, str] | None:
        """Extract cookies from SQLite database.

        Args:
            cookie_path: Path to cookie database
            browser: Browser name

        Returns:
            Dictionary of cookies or None if failed
        """
        if browser == BrowserType.FIREFOX:
            return self._extract_firefox_cookies(cookie_path)
        else:
            return self._extract_chromium_cookies(cookie_path)

    def _extract_chromium_cookies(self, cookie_path: str) -> dict[str, str] | None:
        """Extract cookies from Chromium-based browsers.

        Args:
            cookie_path: Path to cookie database

        Returns:
            Dictionary of cookies or None if failed
        """
        if not os.path.exists(cookie_path):
            return None

        # Create temporary copy to avoid locking issues
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
                temp_path = temp_file.name

            shutil.copy2(cookie_path, temp_path)

            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()

            # Try different table schemas
            queries = [
                "SELECT name, value FROM cookies WHERE host_key = ? OR host_key = ?",
                "SELECT name, value FROM cookies WHERE host_key LIKE ?",
                "SELECT name, value FROM cookies WHERE host_key = ? OR host_key = ?",
            ]

            cookies = {}
            for query in queries:
                try:
                    if "LIKE" in query:
                        cursor.execute(query, (f"%{self.domain}%",))
                    else:
                        cursor.execute(query, (self.domain, f".{self.domain}"))

                    results = cursor.fetchall()
                    for name, value in results:
                        # Handle encrypted cookies (basic attempt)
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8")
                            except (UnicodeDecodeError, LookupError):
                                # Skip encrypted or non-UTF8 cookies
                                continue
                        cookies[name] = value

                    if cookies:
                        break
                except sqlite3.Error:
                    continue

            conn.close()

            return cookies if self._validate_cookies(cookies) else None

        except Exception as e:
            self.logger.warning(f"Error extracting Chromium cookies: {e}")
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except (OSError, PermissionError):
                    # Failed to clean up temp file
                    pass

    def _extract_firefox_cookies(self, profile_path: str) -> dict[str, str] | None:
        """Extract cookies from Firefox.

        Args:
            profile_path: Path to Firefox profiles directory

        Returns:
            Dictionary of cookies or None if failed
        """
        if not os.path.exists(profile_path):
            return None

        # Find profile directories
        try:
            profiles = [
                d
                for d in os.listdir(profile_path)
                if d.endswith(".default") or d.endswith(".default-release")
            ]
            if not profiles:
                return None

            # Use the first profile found
            profile_dir = os.path.join(profile_path, profiles[0])
            cookie_file = os.path.join(profile_dir, "cookies.sqlite")

            if not os.path.exists(cookie_file):
                return None

            # Create temporary copy
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".db"
                ) as temp_file:
                    temp_path = temp_file.name

                shutil.copy2(cookie_file, temp_path)

                conn = sqlite3.connect(temp_path)
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT name, value FROM moz_cookies WHERE host = ? OR host = ?",
                    (self.domain, f".{self.domain}"),
                )

                cookies = {}
                for name, value in cursor.fetchall():
                    cookies[name] = value

                conn.close()

                return cookies if self._validate_cookies(cookies) else None

            except Exception as e:
                self.logger.warning(f"Error extracting Firefox cookies: {e}")
                return None
            finally:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except (OSError, PermissionError):
                        # Failed to clean up temp file
                        pass

        except Exception as e:
            self.logger.warning(f"Error finding Firefox profiles: {e}")
            return None

    def _validate_cookies(self, cookies: dict[str, str]) -> bool:
        """Validate that required cookies are present.

        Args:
            cookies: Dictionary of cookies

        Returns:
            True if all required cookies are present
        """
        if not cookies:
            return False

        missing_cookies = []
        for required in self.required_cookies:
            if required not in cookies or not cookies[required]:
                missing_cookies.append(required)

        if missing_cookies:
            self.logger.warning(f"Missing required cookies: {missing_cookies}")
            return False

        return True

    def get_cookies_with_fallback(self, browser: str = None) -> dict[str, str] | None:
        """Get cookies with multiple fallback methods.

        Args:
            browser: Browser to extract from

        Returns:
            Dictionary of cookies or None if all methods failed
        """
        browser = browser or self.preferred_browser

        # Method 1: Try browser_cookie3 first
        cookies = self.get_cookies_browser_cookie3(browser)
        if cookies:
            return cookies

        # Method 2: Try direct SQLite extraction
        cookies = self.get_cookies_sqlite(browser)
        if cookies:
            return cookies

        # Method 3: Try other browsers if primary failed
        detected_browsers = self.detect_installed_browsers()
        for alt_browser in detected_browsers:
            if alt_browser == browser:
                continue

            self.logger.info(f"Trying fallback browser: {alt_browser}")

            cookies = self.get_cookies_browser_cookie3(alt_browser)
            if cookies:
                return cookies

            cookies = self.get_cookies_sqlite(alt_browser)
            if cookies:
                return cookies

        return None

    def save_cookies(
        self, cookies: dict[str, str], filename: str = "udemy_cookies.json"
    ):
        """Save cookies to file for later use.

        Args:
            cookies: Dictionary of cookies
            filename: Output filename
        """
        try:
            cookie_data = {
                "cookies": cookies,
                "domain": self.domain,
                "timestamp": datetime.now().isoformat(),
                "browser": self.preferred_browser,
            }

            with open(filename, "w") as f:
                json.dump(cookie_data, f, indent=2)

            self.logger.info(f"Cookies saved to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")

    def load_cookies(
        self, filename: str = "udemy_cookies.json"
    ) -> dict[str, str] | None:
        """Load cookies from file.

        Args:
            filename: Input filename

        Returns:
            Dictionary of cookies or None if failed
        """
        try:
            if not os.path.exists(filename):
                return None

            with open(filename) as f:
                cookie_data = json.load(f)

            cookies = cookie_data.get("cookies", {})

            # Validate cookies
            if self._validate_cookies(cookies):
                self.logger.info(f"Cookies loaded from {filename}")
                return cookies
            else:
                self.logger.warning(f"Invalid cookies in {filename}")
                return None

        except Exception as e:
            self.logger.warning(f"Failed to load cookies from {filename}: {e}")
            return None

    def get_browser_info(self) -> dict[str, Any]:
        """Get information about detected browsers.

        Returns:
            Dictionary containing browser information
        """
        detected = self.detect_installed_browsers()

        info = {
            "detected_browsers": detected,
            "preferred_browser": self.preferred_browser,
            "system": self.system,
            "browser_cookie3_available": BROWSER_COOKIE3_AVAILABLE,
            "keyring_available": KEYRING_AVAILABLE,
            "browser_paths": self.browser_paths,
        }

        return info

    def test_cookie_extraction(self) -> dict[str, Any]:
        """Test cookie extraction from all available browsers.

        Returns:
            Dictionary containing test results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "browsers": {},
            "summary": {"total_tested": 0, "successful": 0, "failed": 0},
        }

        detected_browsers = self.detect_installed_browsers()

        for browser in detected_browsers:
            results["browsers"][browser] = {}
            results["summary"]["total_tested"] += 1

            # Test browser_cookie3
            cookies_bc3 = self.get_cookies_browser_cookie3(browser)
            results["browsers"][browser]["browser_cookie3"] = {
                "success": cookies_bc3 is not None,
                "cookie_count": len(cookies_bc3) if cookies_bc3 else 0,
                "has_required": (
                    self._validate_cookies(cookies_bc3) if cookies_bc3 else False
                ),
            }

            # Test SQLite extraction
            cookies_sqlite = self.get_cookies_sqlite(browser)
            results["browsers"][browser]["sqlite"] = {
                "success": cookies_sqlite is not None,
                "cookie_count": len(cookies_sqlite) if cookies_sqlite else 0,
                "has_required": (
                    self._validate_cookies(cookies_sqlite) if cookies_sqlite else False
                ),
            }

            # Overall success for this browser
            browser_success = (cookies_bc3 is not None) or (cookies_sqlite is not None)
            results["browsers"][browser]["overall_success"] = browser_success

            if browser_success:
                results["summary"]["successful"] += 1
            else:
                results["summary"]["failed"] += 1

        return results


# Global instance
cookie_manager = CookieManager()


def get_cookies(browser: str = None) -> dict[str, str] | None:
    """Convenience function to get cookies.

    Args:
        browser: Browser to extract from

    Returns:
        Dictionary of cookies or None if failed
    """
    return cookie_manager.get_cookies_with_fallback(browser)


def detect_browsers() -> list[str]:
    """Convenience function to detect browsers.

    Returns:
        List of detected browser names
    """
    return cookie_manager.detect_installed_browsers()


def test_cookie_extraction() -> dict[str, Any]:
    """Convenience function to test cookie extraction.

    Returns:
        Test results dictionary
    """
    return cookie_manager.test_cookie_extraction()


if __name__ == "__main__":
    # Test the cookie manager
    print("Testing cookie manager...")

    # Test browser detection
    browsers = detect_browsers()
    print(f"Detected browsers: {browsers}")

    # Test cookie extraction
    if browsers:
        cookies = get_cookies(browsers[0])
        if cookies:
            print(f"Successfully extracted {len(cookies)} cookies")
            print(
                f"Required cookies present: {cookie_manager._validate_cookies(cookies)}"
            )
        else:
            print("Failed to extract cookies")

    # Full test
    test_results = test_cookie_extraction()
    print(f"Test results: {test_results}")
