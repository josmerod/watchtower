"""Course enrollment service.

Orchestrates the course enrollment process, including filtering,
price checking, and enrollment logic.
"""

from datetime import datetime
from typing import Any

from ..domain.models import Course, EnrollmentResult
from ..infrastructure.udemy_client import UdemyClient


class EnrollmentService:
    """Service for enrolling in Udemy courses.

    Coordinates the enrollment workflow:
    1. Validate course against filters
    2. Check course price with coupon
    3. Enroll in free courses directly
    4. Enroll in discounted courses via checkout

    Attributes:
        client: Udemy API client
        filter_settings: Course filtering settings
    """

    def __init__(
        self,
        client: UdemyClient,
        filter_settings: Any,
        debug: bool = False,
    ):
        """Initialize the enrollment service.

        Args:
            client: Authenticated Udemy client
            filter_settings: Filter settings for course exclusion
            debug: Enable debug logging
        """
        self.client = client
        self.filter_settings = filter_settings
        self.debug = debug

    def enroll_in_course(self, course: Course) -> EnrollmentResult:
        """Enroll in a single course.

        Args:
            course: Course to enroll in

        Returns:
            EnrollmentResult with success status and details
        """
        # Get course ID first
        course_info = self.client.get_course_id(course.url)

        if course_info.get("is_invalid"):
            return EnrollmentResult(
                course_id=course.course_id or "unknown",
                success=False,
                error=course_info.get("msg", "Invalid course"),
            )

        course_id = course_info.get("course_id")
        if not course_id:
            return EnrollmentResult(
                course_id="unknown",
                success=False,
                error="Could not extract course ID",
            )

        # Check if course is excluded by filters
        if course_info.get("is_excluded"):
            return EnrollmentResult(
                course_id=course_id,
                success=False,
                error="Course excluded by filters",
            )

        # Check price with coupon
        coupon_code = course.coupon_code
        price, coupon_valid = self.client.check_course_price(course_id, coupon_code)

        # Enroll based on price
        if price == 0.0:
            return self._enroll_free(course_id)
        elif price > 0 and coupon_valid:
            return self._enroll_discounted(course_id, coupon_code, price)
        else:
            return EnrollmentResult(
                course_id=course_id,
                success=False,
                error=f"Course not free (price: ${price:.2f})",
            )

    def _enroll_free(self, course_id: str) -> EnrollmentResult:
        """Enroll in a free course.

        Args:
            course_id: Course ID

        Returns:
            EnrollmentResult
        """
        try:
            result = self.client.enroll_free_course(course_id)

            if "error" in result:
                return EnrollmentResult(
                    course_id=course_id,
                    success=False,
                    error=result["error"],
                )

            return EnrollmentResult(
                course_id=course_id,
                success=True,
                price=0.0,
            )

        except Exception as e:
            return EnrollmentResult(
                course_id=course_id,
                success=False,
                error=str(e),
            )

    def _enroll_discounted(
        self, course_id: str, coupon_code: str, price: float
    ) -> EnrollmentResult:
        """Enroll in a discounted course.

        Args:
            course_id: Course ID
            coupon_code: Coupon code to apply
            price: Discounted price

        Returns:
            EnrollmentResult
        """
        try:
            result = self.client.enroll_discounted_course(course_id, coupon_code)

            if "error" in result:
                return EnrollmentResult(
                    course_id=course_id,
                    success=False,
                    error=result["error"],
                )

            return EnrollmentResult(
                course_id=course_id,
                success=True,
                price=price,
                coupon_used=coupon_code,
            )

        except Exception as e:
            return EnrollmentResult(
                course_id=course_id,
                success=False,
                error=str(e),
            )

    def enroll_in_courses(
        self, courses: list[Course]
    ) -> list[EnrollmentResult]:
        """Enroll in multiple courses.

        Args:
            courses: List of courses to enroll in

        Returns:
            List of enrollment results
        """
        results = []

        for course in courses:
            result = self.enroll_in_course(course)
            results.append(result)

            if self.debug:
                print(result)

        return results


class CourseFilter:
    """Service for filtering courses based on criteria."""

    def __init__(self, filter_settings: Any, debug: bool = False):
        """Initialize the course filter.

        Args:
            filter_settings: Filter configuration
            debug: Enable debug logging
        """
        self.settings = filter_settings
        self.debug = debug

    def is_keyword_excluded(self, title: str) -> bool:
        """Check if course title contains excluded keywords.

        Args:
            title: Course title

        Returns:
            True if course should be excluded
        """
        title_words = title.casefold().split()

        for word in title_words:
            if word in self.settings.title_exclude:
                if self.debug:
                    print(f"Keyword excluded: {word}")
                return True

        return False

    def is_instructor_excluded(self, instructors: list[str]) -> bool:
        """Check if instructor is in exclusion list.

        Args:
            instructors: List of instructor URLs

        Returns:
            True if any instructor is excluded
        """
        for instructor in instructors:
            if instructor in self.settings.instructor_exclude:
                if self.debug:
                    print(f"Instructor excluded: {instructor}")
                return True

        return False

    def is_course_updated(self, last_update: str | None) -> bool:
        """Check if course has been updated recently enough.

        Args:
            last_update: Last update date (YYYY-MM-DD format)

        Returns:
            True if course is recent enough
        """
        if not last_update:
            return True

        try:
            from datetime import datetime

            current_date = datetime.now()
            last_update_date = datetime.strptime(last_update, "%Y-%m-%d")

            # Calculate month difference
            years = current_date.year - last_update_date.year
            months = current_date.month - last_update_date.month

            if months < 0:
                years -= 1
                months += 12

            month_diff = years * 12 + months

            return month_diff < self.settings.course_update_threshold_months

        except ValueError:
            return True  # If we can't parse the date, accept it

    def should_exclude_course(self, dma: dict[str, Any]) -> bool:
        """Check if course should be excluded based on all filters.

        Args:
            dma: Course data from data-module-args

        Returns:
            True if course should be excluded
        """
        # Extract instructors
        instructors = [
            i["absolute_url"].split("/")[-2]
            for i in dma["serverSideProps"]["course"]["instructors"]["instructors_info"]
            if i.get("absolute_url")
        ]

        # Extract course attributes
        language = dma["serverSideProps"]["course"]["localeSimpleEnglishTitle"]
        category = dma["serverSideProps"]["topicMenu"]["breadcrumbs"][0]["title"]
        rating = dma["serverSideProps"]["course"]["rating"]
        last_update = dma["serverSideProps"]["course"]["lastUpdateDate"]

        # Check each filter
        if not self.is_course_updated(last_update):
            if self.debug:
                print(f"Course excluded: Last updated {last_update}")
            return True

        if self.is_instructor_excluded(instructors):
            return True

        if category not in self.settings.categories:
            if self.debug:
                print(f"Category excluded: {category}")
            return True

        if language not in self.settings.languages:
            if self.debug:
                print(f"Language excluded: {language}")
            return True

        if rating < self.settings.min_rating:
            if self.debug:
                print(f"Low rating: {rating}")
            return True

        return False
