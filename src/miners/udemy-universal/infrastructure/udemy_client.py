"""Udemy API client for course enrollment and management.

Provides a clean interface for interacting with Udemy's API,
including authentication, course details fetching, and enrollment.
"""

import json
from pathlib import Path
from typing import Any

import cloudscraper
import requests
from bs4 import BeautifulSoup

from ..config import UdemyClientConfig, UDEMY_API_HEADERS


class LoginError(Exception):
    """Login failed exception."""

    pass


class UdemyClient:
    """Client for Udemy API operations.

    Handles authentication, course details retrieval, and enrollment
    through Udemy's public API.

    Attributes:
        config: Client configuration
        client: HTTP session for API requests
        cookie_dict: Stored cookies for authentication
        display_name: User's display name
        currency: User's currency code
    """

    def __init__(self, config: UdemyClientConfig):
        """Initialize the Udemy client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.client = self._create_session()
        self.cookie_dict: dict[str, str] = {}
        self.display_name: str | None = None
        self.currency: str | None = None

    def _create_session(self) -> requests.Session:
        """Create HTTP session.

        Returns:
            Configured session object
        """
        if self.config.enable_cloudscraper:
            session = cloudscraper.create_scraper()
        else:
            session = requests.Session()

        session.headers.update(UDEMY_API_HEADERS)
        session.keep_alive = False

        return self.client

    def authenticate(self, email: str, password: str) -> None:
        """Authenticate with email and password.

        Args:
            email: Udemy account email
            password: Udemy account password

        Raises:
            LoginError: If authentication fails
        """
        # Get CSRF token
        csrf_url = f"{self.config.base_url}/join/signup-popup/?locale=en_US&response_type=html&next={self.config.base_url}/logout/"
        response = self.client.get(csrf_url)

        try:
            csrf_token = response.cookies["csrftoken"]
        except KeyError as e:
            raise LoginError("Could not get CSRF token") from e

        # Perform login
        login_data = {
            "csrfmiddlewaretoken": csrf_token,
            "locale": "en_US",
            "email": email,
            "password": password,
        }

        self.client.cookies.update(response.cookies)

        login_url = f"{self.config.base_url}/join/login-popup/?passwordredirect=True&response_type=json"
        response = self.client.post(login_url, data=login_data, allow_redirects=False)

        if "returnUrl" not in response.text:
            # Login failed
            try:
                error_data = response.json()
                login_error = error_data["error"]["data"]["formErrors"][0]
                if login_error[0] == "Y":
                    raise LoginError("Too many login attempts - try again later")
                elif login_error[0] == "T":
                    raise LoginError("Email or password incorrect")
                else:
                    raise LoginError(login_error)
            except (json.JSONDecodeError, KeyError) as e:
                raise LoginError(f"Login failed: {response.text}") from e

        # Extract tokens from cookies
        self._make_cookies(
            response.cookies["client_id"],
            response.cookies["access_token"],
            csrf_token,
        )

        # Verify login and get user info
        self._verify_session()

    def _make_cookies(self, client_id: str, access_token: str, csrf_token: str) -> None:
        """Create cookie dictionary from tokens.

        Args:
            client_id: Client ID token
            access_token: Access token
            csrf_token: CSRF token
        """
        self.cookie_dict = {
            "client_id": client_id,
            "access_token": access_token,
            "csrftoken": csrf_token,
        }

    def _verify_session(self) -> None:
        """Verify login session and fetch user info.

        Raises:
            LoginError: If session verification fails
        """
        # Get user context
        context_url = f"{self.config.api_base}/contexts/me/?header=True"
        response = self.client.get(context_url, cookies=self.cookie_dict)
        data = response.json()

        if not data["header"]["isLoggedIn"]:
            raise LoginError("Login verification failed")

        self.display_name = data["header"]["user"]["display_name"]

        # Get currency info
        cart_url = f"{self.config.api_base}/shopping-carts/me/"
        response = self.client.get(cart_url, cookies=self.cookie_dict)
        data = response.json()
        self.currency = data["user"]["credit"]["currency_code"]

    def get_course_id(self, url: str) -> dict[str, Any]:
        """Extract course ID from URL.

        Args:
            url: Course URL

        Returns:
            Dictionary with course_id and metadata
        """
        import re
        from urllib.parse import unquote

        course = {
            "course_id": None,
            "url": url,
            "is_invalid": False,
            "is_free": None,
            "is_excluded": None,
            "retry": None,
            "msg": "Report to developer",
        }

        url = re.sub(r"\W+$", "", unquote(url))

        try:
            response = self.client.get(url)
        except requests.exceptions.ConnectionError:
            course["retry"] = True
            return course

        course["url"] = response.url

        # Parse HTML to extract course ID
        soup = BeautifulSoup(response.content, "html5lib")
        course_id = soup.find("body").get("data-clp-course-id", "invalid")

        if course_id == "invalid":
            course["is_invalid"] = True
            course["msg"] = "Course ID not found"
            return course

        course["course_id"] = course_id

        # Parse data-module-args for course details
        dma_str = soup.find("body").get("data-module-args")
        if dma_str:
            dma = json.loads(dma_str)

            # Check for restrictions
            if dma.get("view_restriction"):
                course["is_invalid"] = True
                course["msg"] = dma["serverSideProps"]["limitedAccess"]["errorMessage"]["title"]
                return course

            course["is_free"] = not dma["serverSideProps"]["course"].get("isPaid", True)

        return course

    def check_course_price(self, course_id: str, coupon_code: str | None = None) -> tuple[float, bool]:
        """Check course price with optional coupon code.

        Args:
            course_id: Course ID
            coupon_code: Optional coupon code

        Returns:
            Tuple of (price, coupon_valid)
        """
        url = f"{self.config.api_base}/course-landing-components/{course_id}/me/?components=price_text"

        if coupon_code:
            url += f"&couponCode={coupon_code}"

        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            price_info = data.get("price_text", {}).get("data", {})
            amount_str = price_info.get("list_price", {}).get("price_string")

            if amount_str:
                # Extract numeric price
                import re

                match = re.search(r"([\d,]+\.?\d*)", amount_str.replace(",", ""))
                if match:
                    price = float(match.group(1))
                    return price, True

            return -1.0, False

        except requests.RequestException:
            return -1.0, False

    def enroll_free_course(self, course_id: str) -> dict[str, Any]:
        """Enroll in a free course.

        Args:
            course_id: Course ID

        Returns:
            Enrollment result dictionary
        """
        url = f"{self.config.api_base}/users/me/subscribed-courses/"
        data = {"course_id": course_id, "buyable": {"type": "course"}}

        try:
            response = self.client.post(url, json=data, cookies=self.cookie_dict)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def enroll_discounted_course(self, course_id: str, coupon_code: str) -> dict[str, Any]:
        """Enroll in a discounted course using coupon code.

        Args:
            course_id: Course ID
            coupon_code: Coupon code to apply

        Returns:
            Enrollment result dictionary
        """
        # Add to cart
        cart_url = f"{self.config.api_base}/users/me/shopping-carts/items/"
        cart_data = {
            "buyable": {"type": "course", "id": course_id},
            "coupon_code": coupon_code,
        }

        try:
            response = self.client.post(cart_url, json=cart_data, cookies=self.cookie_dict)
            response.raise_for_status()
            cart_data = response.json()

            # Checkout
            checkout_url = f"{self.config.api_base}/shopping-carts/me/checkout/"
            checkout_data = {
                "items": [cart_data],
                "payment_method": "free",
            }

            response = self.client.post(checkout_url, json=checkout_data, cookies=self.cookie_dict)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            return {"error": str(e)}
