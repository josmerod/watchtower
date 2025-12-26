"""URL extraction from OCR text with aggressive error correction."""

import re
from typing import ClassVar


class URLExtractor:
    """Extracts and validates URLs from OCR text with error correction."""

    # Primary URL pattern - comprehensive regex for URL detection
    PRIMARY_URL_PATTERN: ClassVar[re.Pattern] = re.compile(
        r"""
        (?:
            # HTTP/HTTPS protocol
            (?:https?://|www\.)

            # Domain (case-insensitive)
            (?:
                [a-zA-Z0-9-]+\.)+

                # TLD (2-6 letters for standard TLDs, or new longer TLDs)
                [a-zA-Z]{2,6}
            )

            # Optional port
            (?::\d+)?

            # Path (optional)
            (?:
                /
                [^\s\]\[}]{0,300}?

                # Allow certain characters at end without space
                [^\s\]\[},.;!?]?
            )?

            # Query string (optional)
            (?:
                \?
                [^\s\]\[}]{0,200}?

                # Allow certain characters at end without space
                [^\s\]\[},.;!?]?
            )?

            # Fragment (optional)
            (?:
                \#
                [^\s\]\[}]{0,100}?

                # Allow certain characters at end without space
                [^\s\]\[},.;!?]?
            )?
        )
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # Fallback URL patterns for URLs that might have OCR errors
    FALLBACK_PATTERNS: ClassVar[list[str]] = [
        # URLs with common OCR substitutions
        r"(?:https?://)[\w\-]+(?:\.[\w\-]+)+\.[a-zA-Z]{2,6}(?:/[^\s\]\[}]*)?",
        # URLs without protocol
        r"[\w\-]{3,}\.(?:com|org|net|edu|gov|io|co|ai|app|dev)(?:/[^\s\]\[}]*)?",
        # URLs with 'hXXp' or similar obfuscation
        r"h[Xx]{2}p?s?(?:://)?[\w\-]+(?:\.[\w\-]+)+\.[a-zA-Z]{2,6}",
        # URLs with common OCR errors in protocol
        r"(?:htps|htp|https|htts)://[\w\-]+(?:\.[\w\-]+)+\.[a-zA-Z]{2,6}",
    ]

    # OCR error correction patterns
    OCR_CORRECTIONS: ClassVar[dict[str, str]] = {
        r"(\w)0\.": r"\1o.",  # 0 instead of o
        r"(\w)1\.": r"\1i.",  # 1 instead of i
        r"(\w)3\.": r"\1e.",  # 3 instead of e
        r"(\w)5\.": r"\1s.",  # 5 instead of s
        r"(\w)8\.": r"\1b.",  # 8 instead of b
        r"\[": "(",  # [ instead of (
        r"\]": ")",  # ] instead of )
        r"\{": "(",  # { instead of (
        r"\}": ")",  # } instead of )
        r"\|": "/",  # | instead of /
        r"l\/": "lt",  # l/ instead of it
        r"\/l": "tl",  # /l instead of tl
        r":\/\/": "://",  # :// normalization
        r":/\\": "://",  # :/\ instead of ://
        r":\\\\": "://",  # :\\ instead of ://
    }

    # Common domains to prioritize
    COMMON_DOMAINS: ClassVar[set[str]] = {
        "youtube.com",
        "youtu.be",
        "github.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "reddit.com",
        "huggingface.co",
        "openai.com",
        "anthropic.com",
        "google.com",
        "stackoverflow.com",
        "medium.com",
        "dev.to",
        " Udemy.com",
        "coursera.org",
        "khanacademy.org",
    }

    def __init__(self, debug: bool = False):
        """Initialize URL extractor.

        Args:
            debug: Enable debug logging
        """
        self.debug = debug

    def clean_ocr_text_for_urls(self, text: str) -> str:
        """Apply aggressive OCR error correction for URL detection.

        Args:
            text: Raw OCR text

        Returns:
            Text with common OCR errors corrected
        """
        cleaned = text

        # Apply correction patterns
        for pattern, replacement in self.OCR_CORRECTIONS.items():
            cleaned = re.sub(pattern, replacement, cleaned)

        # Remove common OCR noise around URLs
        cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
        cleaned = cleaned.strip()

        return cleaned

    def extract_urls_from_text(self, text: str, confidence: float = 50.0) -> list[str]:
        """Extract URLs from text using multiple patterns.

        Args:
            text: Text to extract URLs from
            confidence: OCR confidence score (0-100)

        Returns:
            List of extracted URLs (deduplicated)
        """
        if not text or len(text) < 8:
            return []

        # Clean text first
        cleaned_text = self.clean_ocr_text_for_urls(text)
        urls = set()

        # Try primary pattern first
        primary_matches = self.PRIMARY_URL_PATTERN.findall(cleaned_text)
        urls.update(primary_matches)

        # If no matches with primary pattern, try fallback patterns
        if not urls:
            for pattern_str in self.FALLBACK_PATTERNS:
                try:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                    matches = pattern.findall(cleaned_text)
                    urls.update(matches)
                except re.error:
                    continue

        # Prioritize common domains
        url_list = list(urls)
        common_domain_urls = []
        other_urls = []

        for url in url_list:
            domain = self._extract_domain(url)
            if domain in self.COMMON_DOMAINS:
                common_domain_urls.append(url)
            else:
                other_urls.append(url)

        # Return common domains first, then others
        return common_domain_urls + other_urls

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url: URL string

        Returns:
            Domain name (e.g., "youtube.com")
        """
        try:
            # Remove protocol
            domain = url
            if "://" in domain:
                domain = domain.split("://")[1]

            # Remove path and query
            domain = domain.split("/")[0]

            # Remove port if present
            domain = domain.split(":")[0]

            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]

            return domain.lower()
        except Exception:
            return ""

    def validate_url(self, url: str) -> bool:
        """Validate if a string is a well-formed URL.

        Args:
            url: String to validate

        Returns:
            True if valid URL, False otherwise
        """
        if not url or len(url) < 8:
            return False

        # Check for protocol
        has_protocol = bool(url.startswith("http://") or url.startswith("https://"))
        has_www = url.startswith("www.")

        if not (has_protocol or has_www):
            return False

        # Check for domain
        if "." not in url:
            return False

        # Check for TLD
        domain_part = url.split("/")[-1] if "/" in url else url
        if "." not in domain_part:
            return False

        tld = domain_part.rsplit(".", 1)[-1]
        if not tld or len(tld) < 2 or len(tld) > 10:
            return False

        return True
