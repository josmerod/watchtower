"""Domain models for Udemy course mining.

This module defines the core domain entities used throughout the
udemy-universal module, following DDD (Domain-Driven Design) principles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Instructor:
    """Udemy course instructor.

    Attributes:
        name: Instructor's display name
        title: Instructor's job title
        url: URL to instructor's profile
        image: URL to instructor's profile image
    """

    name: str
    url: str | None = None
    title: str | None = None
    image: str | None = None

    def __str__(self) -> str:
        return self.name


@dataclass
class Course:
    """Udemy course entity.

    Represents a course discovered through scraping, with metadata
    for filtering and enrollment purposes.

    Attributes:
        title: Course title
        url: Direct URL to the course on Udemy
        course_id: Udemy course ID (extracted from URL)
        coupon_code: Optional coupon code for free/discounted access
        instructors: List of course instructors
        category: Course category
        language: Course language
        rating: Course rating (0-5)
        num_students: Number of enrolled students
        last_update_date: Last course update date (YYYY-MM)
        is_free: Whether the course is currently free
        is_excluded: Whether the course is excluded by filters
        source: Source where the course was found (e.g., 'discudemy', 'udemyfreebies')
    """

    title: str
    url: str
    source: str
    course_id: str | None = None
    coupon_code: str | None = None
    instructors: list[Instructor] = field(default_factory=list)
    category: str | None = None
    language: str | None = None
    rating: float | None = None
    num_students: int | None = None
    last_update_date: str | None = None
    is_free: bool | None = None
    is_excluded: bool = False
    exclusion_reason: str | None = None

    def __str__(self) -> str:
        return f"{self.title} ({self.url})"

    def __hash__(self) -> int:
        # Hash based on normalized URL for deduplication
        return hash(self._normalize_url(self.url))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Course):
            return False
        return self._normalize_url(self.url) == self._normalize_url(other.url)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for comparison by removing trailing slashes and query params."""
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        # Ensure path ends with /
        path = parsed.path if parsed.path.endswith("/") else parsed.path + "/"
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


@dataclass
class CourseDetails:
    """Detailed information about a course scraped from Udemy.

    Contains extended course metadata beyond the basic Course entity,
    typically fetched from Udemy's API or by scraping the course page.

    Attributes:
        course_id: Udemy course ID
        title: Course title
        headline: Course subtitle/headline
        description: Full course description
        url: Course URL
        instructors: List of instructor details
        language: Course language
        rating: Course rating (0-5)
        num_students: Number of enrolled students
        last_update_date: Last course update date (YYYY-MM-DD)
        curriculum_sections: List of course sections with lectures
        error: Error message if scraping failed
    """

    course_id: str
    title: str | None = None
    headline: str | None = None
    description: str | None = None
    url: str | None = None
    instructors: list[dict[str, Any]] = field(default_factory=list)
    language: str | None = None
    rating: float | None = None
    num_students: int | None = None
    last_update_date: str | None = None
    curriculum_sections: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        """Check if the course details are valid (have at least a title)."""
        return bool(self.title)


@dataclass
class EnrollmentResult:
    """Result of a course enrollment attempt.

    Attributes:
        course_id: The course ID
        success: Whether enrollment was successful
        price: Final price paid (0.0 for free courses)
        coupon_used: Coupon code used for enrollment
        error: Error message if enrollment failed
        timestamp: When the enrollment was attempted
    """

    course_id: str
    success: bool
    price: float = 0.0
    coupon_used: str | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        if self.success:
            return f"✓ Enrolled in {self.course_id} (Price: ${self.price:.2f})"
        else:
            return f"✗ Failed to enroll in {self.course_id}: {self.error}"


@dataclass
class ScraperResult:
    """Result from a scraper execution.

    Attributes:
        source: Source name (e.g., 'discudemy', 'udemyfreebies')
        courses: List of courses found
        total_found: Total items found on the site
        processed: Number of items processed
        errors: List of error messages encountered
        duration: Time taken to scrape (seconds)
    """

    source: str
    courses: list[Course] = field(default_factory=list)
    total_found: int = 0
    processed: int = 0
    errors: list[str] = field(default_factory=list)
    duration: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (courses_found / total_found)."""
        if self.total_found == 0:
            return 0.0
        return len(self.courses) / self.total_found

    def __str__(self) -> str:
        return f"{self.source}: {len(self.courses)} courses ({self.processed}/{self.total_found} processed)"
