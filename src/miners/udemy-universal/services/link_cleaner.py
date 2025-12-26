"""URL cleanup and redirect handling service.

Provides centralized logic for cleaning Udemy course URLs and
handling various redirector services.
"""

import re
from urllib.parse import parse_qs, unquote, urlparse

from .utils.http import follow_redirect


class LinkCleaner:
    """Service for cleaning and normalizing course URLs.

    Handles various redirector services (LinkSynergy, generic redirectors)
    and extracts final Udemy course URLs.
    """

    # Known redirector domains and their handler methods
    REDIRECTOR_HANDLERS = {
        "click.linksynergy.com": "_handle_linksynergy",
        "fast.linksly.co": "_handle_generic_redirector",
        "click.linksynergy.art": "_handle_linksynergy",
        "udemy.cc": "_handle_generic_redirector",
        "ad.admitad.com": "_handle_generic_redirector",
        "www.kqzyfj.com": "_handle_generic_redirector",
        "t.grtyi.com": "_handle_generic_redirector",
        "linkjust.com": "_handle_generic_redirector",
        "gotocourse.com": "_handle_generic_redirector",
        "anrdoezrs.net": "_handle_generic_redirector",
        "dpbolvw.net": "_handle_generic_redirector",
        "aff.reideenroll.com": "_handle_generic_redirector",
        "tracking.eljojomkt.com": "_handle_generic_redirector",
        "clk.srv.linksynergy.com": "_handle_linksynergy",
    }

    # LinkSynergy parameters to check for redirect URLs
    LINKSYNERGY_PARAMS = ["RD_PARM1", "murl", "u1", "url", "SREF"]

    # Udemy URL pattern
    UDEMY_PATTERN = re.compile(
        r"https?://(?:www\.)?udemy\.com/course/[^/\s]+/?(?:\?(?:couponCode=[^&\s]+)?)?"
    )

    def __init__(self, debug: bool = False):
        """Initialize the link cleaner.

        Args:
            debug: Enable debug logging
        """
        self.debug = debug

    def clean_link(self, link: str) -> str:
        """Clean and normalize a course link.

        Handles:
        - Direct Udemy links (normalizes them)
        - Redirector links (follows and extracts Udemy URL)
        - Generic links (searches for embedded Udemy URLs)

        Args:
            link: URL to clean

        Returns:
            Cleaned Udemy course URL, or empty string if not a valid course link
        """
        if not link:
            return ""

        try:
            # Check if it's already a clean Udemy link
            if self._is_direct_udemy_link(link):
                return self._normalize_udemy_link(link)

            # Parse the URL
            parsed_url = urlparse(link)
            netloc = parsed_url.netloc.lower()

            # Check if it's a known redirector
            handler_name = self.REDIRECTOR_HANDLERS.get(netloc)
            if handler_name:
                handler = getattr(self, handler_name, None)
                if handler:
                    return handler(parsed_url, link)

            # Check if the link contains "udemy.com" anywhere
            if "udemy.com" in link:
                match = self.UDEMY_PATTERN.search(link)
                if match:
                    return self._normalize_udemy_link(match.group(0))

            # Not recognized as Udemy or known redirector
            if self.debug:
                print(f"Link not recognized: {link}")
            return ""

        except Exception as e:
            if self.debug:
                print(f"Error cleaning link {link}: {e}")
            return ""

    def _is_direct_udemy_link(self, link: str) -> bool:
        """Check if link is a direct Udemy course link.

        Args:
            link: URL to check

        Returns:
            True if it's a direct Udemy course link
        """
        return bool(self.UDEMY_PATTERN.match(link))

    def _normalize_udemy_link(self, link: str) -> str:
        """Normalize a Udemy course link.

        Removes trailing slashes and query parameters except couponCode.

        Args:
            link: Udemy course URL

        Returns:
            Normalized URL
        """
        parsed = urlparse(link)

        # Keep couponCode if present
        coupon_code = ""
        if "couponCode" in parsed.query:
            params = parse_qs(parsed.query)
            coupon_code = f"?couponCode={params['couponCode'][0]}"

        # Normalize path (ensure no trailing slash)
        path = parsed.path.rstrip("/")

        return f"{parsed.scheme}://{parsed.netloc}{path}/{coupon_code}"

    def _handle_linksynergy(self, parsed_url, link: str) -> str:
        """Handle LinkSynergy redirector links.

        Args:
            parsed_url: Parsed URL object
            link: Original link string

        Returns:
            Cleaned Udemy URL or empty string
        """
        query_params = parse_qs(parsed_url.query)

        # Check for common redirect parameters
        for param in self.LINKSYNERGY_PARAMS:
            if param in query_params:
                udemy_link = unquote(query_params[param][0])
                return self.clean_link(udemy_link)

        return ""

    def _handle_generic_redirector(self, parsed_url, link: str) -> str:
        """Handle generic redirectors by following redirects.

        Args:
            parsed_url: Parsed URL object
            link: Original link string

        Returns:
            Cleaned Udemy URL or empty string
        """
        try:
            final_url = follow_redirect(link)
            if final_url and "udemy.com" in final_url:
                return self.clean_link(final_url)
        except Exception as e:
            if self.debug:
                print(f"Error following redirect for {link}: {e}")

        return ""
