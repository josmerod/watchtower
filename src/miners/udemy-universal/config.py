"""Configuration for udemy-universal module.

Centralizes all configuration values, constants, and settings
previously scattered throughout the monolithic base.py file.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# Version Information
# =============================================================================
VERSION = "jmmr.2.5.1"  # Updated with reliability improvements


# =============================================================================
# Scraper Configuration
# =============================================================================
SCRAPER_TIMEOUT_SECONDS: int = 30  # HTTP request timeout
SCRAPER_MAX_RETRIES: int = 5  # Number of retries for failed requests
SCRAPER_PAGE_RANGES: dict[str, range] = {
    "discudemy": range(1, 6),
    "udemyfreebies": range(1, 4),
    "tutorialbar": range(1, 8),
    "real.discount": range(1, 2),  # Playwright-based
    "coursevania": range(1, 2),
    "idownloadcoupon": range(1, 6),
    "e-next": range(1, 10),
    "coursejoiner": range(1, 4),
    "cursosdev": range(1, 10),
    "udemyfreecourses": range(1, 5),
}


# =============================================================================
# Scraper Registry
# =============================================================================
# Maps human-readable names to internal scraper codes
SCRAPER_DICT: dict[str, str] = {
    "Udemy Freebies": "uf",
    "Tutorial Bar": "tb",
    "Real Discount": "rd",
    "Course Vania": "cv",
    "IDownloadCoupons": "idc",
    "E-next": "en",
    "Discudemy": "du",
    "Course Joiner": "cj",
    "Cursos Dev": "cd",
    "Udemy Free Courses": "ufc",
}

# Maps scraper codes to human-readable names
SCRAPER_NAMES: dict[str, str] = {v: k for k, v in SCRAPER_DICT.items()}


# =============================================================================
# External Links
# =============================================================================
EXTERNAL_LINKS: dict[str, str] = {
    "github": "https://github.com/techtanic/Discounted-Udemy-Course-Enroller",
    "support": "https://techtanic.github.io/duce/support",
    "discord": "https://discord.gg/wFsfhJh4Rh",
}


# =============================================================================
# HTTP Headers
# =============================================================================
DEFAULT_HEADERS: dict[str, str] = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,"
    "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
}

UDEMY_API_HEADERS: dict[str, str] = {
    "User-Agent": "okhttp/4.9.2 UdemyAndroid 8.9.2(499) (phone)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.5",
    "Referer": "https://www.udemy.com/",
    "X-Requested-With": "XMLHttpRequest",
    "DNT": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


# =============================================================================
# Redirect Handlers Configuration
# =============================================================================
# Known redirector domains and their handler names
REDIRECTOR_DOMAINS: dict[str, str] = {
    "click.linksynergy.com": "linksynergy",
    "fast.linksly.co": "generic",
    "click.linksynergy.art": "linksynergy",
    "udemy.cc": "generic",
    "ad.admitad.com": "generic",
    "www.kqzyfj.com": "generic",
    "t.grtyi.com": "generic",
    "linkjust.com": "generic",
    "gotocourse.com": "generic",
    "anrdoezrs.net": "generic",
    "dpbolvw.net": "generic",
    "aff.reideenroll.com": "generic",
    "tracking.eljojomkt.com": "generic",
    "clk.srv.linksynergy.com": "linksynergy",
}

# LinkSynergy-specific parameters to check for redirect URLs
LINKSYNERGY_PARAMS: list[str] = ["RD_PARM1", "murl", "u1", "url", "SREF"]


# =============================================================================
# Playwright Configuration
# =============================================================================
PLAYWRIGHT_ARGS: list[str] = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]

PLAYWRIGHT_VIEWPORT: dict[str, int] = {"width": 1280, "height": 720}


# =============================================================================
# Default Filter Settings
# =============================================================================
@dataclass
class FilterSettings:
    """Course filtering settings.

    Attributes:
        sites: Enabled scrapers (scraper_code -> bool)
        categories: Enabled categories (category_name -> bool)
        languages: Enabled languages (language_name -> bool)
        instructor_exclude: List of instructor URLs to exclude
        title_exclude: List of keywords that exclude courses if in title
        min_rating: Minimum course rating (0-5)
        course_update_threshold_months: Maximum months since last update
    """

    sites: dict[str, bool] = field(default_factory=lambda: {
        "uf": True,
        "tb": True,
        "rd": True,
        "cv": True,
        "idc": True,
        "en": True,
        "du": True,
        "cj": True,
        "cd": False,  # Disabled by default
        "ufc": False,  # Disabled by default
    })
    categories: dict[str, bool] = field(default_factory=dict)
    languages: dict[str, bool] = field(default_factory=lambda: {"English": True})
    instructor_exclude: list[str] = field(default_factory=list)
    title_exclude: list[str] = field(default_factory=list)
    min_rating: float = 0.0
    course_update_threshold_months: int = 24  # Exclude courses not updated in 24 months

    def is_valid(self) -> bool:
        """Check if settings are valid (at least one site, category, and language enabled)."""
        return all([bool(self.sites), bool(self.categories), bool(self.languages)])


# =============================================================================
# Udemy Client Configuration
# =============================================================================
@dataclass
class UdemyClientConfig:
    """Configuration for Udemy API client.

    Attributes:
        domain: Udemy domain (e.g., 'www.udemy.com')
        cookie_file: Path to stored cookies
        enable_cloudscraper: Whether to use cloudscraper for requests
        verify_ssl: Whether to verify SSL certificates
    """

    domain: str = "www.udemy.com"
    cookie_file: Path | None = None
    enable_cloudscraper: bool = True
    verify_ssl: bool = True

    @property
    def base_url(self) -> str:
        """Get the base URL for Udemy API."""
        return f"https://{self.domain}"

    @property
    def api_base(self) -> str:
        """Get the base URL for Udemy API."""
        return f"https://{self.domain}/api-2.0"


# =============================================================================
# Enrollment Configuration
# =============================================================================
@dataclass
class EnrollmentConfig:
    """Configuration for course enrollment process.

    Attributes:
        max_concurrent_enrollments: Maximum concurrent enrollment threads
        enrollment_timeout: Timeout for enrollment requests (seconds)
        retry_failed_enrollments: Whether to retry failed enrollments
        max_retries: Maximum number of retries per course
        save_txt: Whether to save enrolled courses to text file
        txt_file_path: Path to text file for saving enrolled courses
    """

    max_concurrent_enrollments: int = 5
    enrollment_timeout: int = 30
    retry_failed_enrollments: bool = True
    max_retries: int = 3
    save_txt: bool = True
    txt_file_path: Path | None = None


# =============================================================================
# Logging Configuration
# =============================================================================
@dataclass
class LoggingConfig:
    """Configuration for logging.

    Attributes:
        enabled: Whether logging is enabled
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (None for stdout only)
        include_timestamp: Whether to include timestamps in logs
    """

    enabled: bool = True
    level: str = "INFO"
    log_file: Path | None = None
    include_timestamp: bool = True


# =============================================================================
# Complete Configuration
# =============================================================================
@dataclass
class Config:
    """Complete configuration for udemy-universal module.

    This is the main configuration object that should be passed to
    services and clients during initialization.

    Attributes:
        filter_settings: Course filtering settings
        udemy_client: Udemy API client configuration
        enrollment: Enrollment process configuration
        logging: Logging configuration
        debug: Enable debug mode (verbose output, error details)
    """

    filter_settings: FilterSettings = field(default_factory=FilterSettings)
    udemy_client: UdemyClientConfig = field(default_factory=UdemyClientConfig)
    enrollment: EnrollmentConfig = field(default_factory=EnrollmentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    debug: bool = False

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        # Validate filter settings
        if not self.filter_settings.is_valid():
            errors.append(
                "Invalid filter settings: At least one site, category, and language must be enabled"
            )

        # Validate rating range
        if not (0 <= self.filter_settings.min_rating <= 5):
            errors.append("min_rating must be between 0 and 5")

        # Validate update threshold
        if self.filter_settings.course_update_threshold_months < 0:
            errors.append("course_update_threshold_months must be non-negative")

        # Validate enrollment config
        if self.enrollment.max_concurrent_enrollments < 1:
            errors.append("max_concurrent_enrollments must be at least 1")

        if self.enrollment.enrollment_timeout < 1:
            errors.append("enrollment_timeout must be at least 1 second")

        return errors
