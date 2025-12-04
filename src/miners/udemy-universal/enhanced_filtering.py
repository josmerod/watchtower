"""Enhanced filtering system for Udemy courses.

This module provides advanced filtering capabilities for courses based on
various criteria including categories, languages, ratings, instructor,
keywords, and more.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from logger import get_logger

logger = get_logger(__name__)


class FilterAction(Enum):
    """Action to take when a filter matches."""

    INCLUDE = "include"
    EXCLUDE = "exclude"


@dataclass
class FilterRule:
    """A single filter rule."""

    name: str
    field: str
    operator: str  # eq, ne, lt, gt, le, ge, contains, not_contains, regex, in, not_in
    value: Any
    action: FilterAction = FilterAction.INCLUDE
    case_sensitive: bool = False
    priority: int = 0


@dataclass
class CourseData:
    """Course data structure for filtering."""

    title: str = ""
    instructor: str = ""
    category: str = ""
    subcategory: str = ""
    language: str = ""
    rating: float = 0.0
    num_reviews: int = 0
    num_students: int = 0
    price: float = 0.0
    discounted_price: float = 0.0
    duration: float = 0.0  # in hours
    level: str = ""  # beginner, intermediate, advanced
    last_updated: str = ""
    has_certificate: bool = False
    has_captions: bool = False
    keywords: list[str] = None
    url: str = ""
    coupon_code: str = ""

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class EnhancedFilter:
    """Enhanced filtering system for courses."""

    def __init__(self, settings: dict[str, Any] = None):
        """Initialize the enhanced filter.

        Args:
            settings: Filter settings dictionary
        """
        self.settings = settings or {}
        self.logger = logger
        self.rules: list[FilterRule] = []
        self.category_mappings = self._get_category_mappings()
        self.language_mappings = self._get_language_mappings()

        # Load filter rules from settings
        self._load_filter_rules()

    def _get_category_mappings(self) -> dict[str, list[str]]:
        """Get category mappings for normalization.

        Returns:
            Dictionary mapping canonical categories to variations
        """
        return {
            "development": [
                "development",
                "programming",
                "coding",
                "software",
                "web-development",
                "mobile-development",
            ],
            "business": [
                "business",
                "entrepreneurship",
                "marketing",
                "sales",
                "management",
                "finance",
            ],
            "design": [
                "design",
                "graphic-design",
                "ui-ux",
                "web-design",
                "art",
                "photography",
            ],
            "it-software": [
                "it-software",
                "information-technology",
                "networking",
                "cybersecurity",
                "database",
            ],
            "personal-development": [
                "personal-development",
                "productivity",
                "leadership",
                "communication",
            ],
            "music": ["music", "audio", "sound-design", "music-production"],
            "health-fitness": [
                "health-fitness",
                "wellness",
                "nutrition",
                "exercise",
                "yoga",
            ],
            "lifestyle": ["lifestyle", "travel", "cooking", "hobby", "pets"],
            "teaching": ["teaching", "education", "training", "academic"],
            "office-productivity": [
                "office-productivity",
                "microsoft-office",
                "excel",
                "powerpoint",
                "word",
            ],
            "marketing": [
                "marketing",
                "digital-marketing",
                "social-media",
                "advertising",
                "seo",
            ],
            "photography": [
                "photography",
                "photo-editing",
                "videography",
                "visual-arts",
            ],
        }

    def _get_language_mappings(self) -> dict[str, list[str]]:
        """Get language mappings for normalization.

        Returns:
            Dictionary mapping language codes to variations
        """
        return {
            "en": ["en", "english", "eng"],
            "es": ["es", "spanish", "español", "spa"],
            "fr": ["fr", "french", "français", "fre"],
            "de": ["de", "german", "deutsch", "ger"],
            "pt": ["pt", "portuguese", "português", "por"],
            "it": ["it", "italian", "italiano", "ita"],
            "ja": ["ja", "japanese", "日本語", "jpn"],
            "ko": ["ko", "korean", "한국어", "kor"],
            "zh": ["zh", "chinese", "中文", "chi"],
            "ru": ["ru", "russian", "русский", "rus"],
            "ar": ["ar", "arabic", "العربية", "ara"],
            "hi": ["hi", "hindi", "हिन्दी", "hin"],
            "tr": ["tr", "turkish", "türkçe", "tur"],
            "pl": ["pl", "polish", "polski", "pol"],
            "nl": ["nl", "dutch", "nederlands", "dut"],
        }

    def _load_filter_rules(self):
        """Load filter rules from settings."""
        self.rules.clear()

        # Language filters
        if "languages" in self.settings:
            enabled_languages = [lang for lang, enabled in self.settings["languages"].items() if enabled]
            if enabled_languages:
                self.rules.append(
                    FilterRule(
                        name="language_filter",
                        field="language",
                        operator="in",
                        value=enabled_languages,
                        action=FilterAction.INCLUDE,
                        priority=1,
                    )
                )

        # Category filters
        if "categories" in self.settings:
            enabled_categories = [cat for cat, enabled in self.settings["categories"].items() if enabled]
            if enabled_categories:
                self.rules.append(
                    FilterRule(
                        name="category_filter",
                        field="category",
                        operator="in",
                        value=enabled_categories,
                        action=FilterAction.INCLUDE,
                        priority=1,
                    )
                )

        # Rating filter
        if "filters" in self.settings and "min_rating" in self.settings["filters"]:
            min_rating = self.settings["filters"]["min_rating"]
            if min_rating > 0:
                self.rules.append(
                    FilterRule(
                        name="min_rating_filter",
                        field="rating",
                        operator="ge",
                        value=min_rating,
                        action=FilterAction.INCLUDE,
                        priority=2,
                    )
                )

        # Review count filter
        if "filters" in self.settings and "min_reviews" in self.settings["filters"]:
            min_reviews = self.settings["filters"]["min_reviews"]
            if min_reviews > 0:
                self.rules.append(
                    FilterRule(
                        name="min_reviews_filter",
                        field="num_reviews",
                        operator="ge",
                        value=min_reviews,
                        action=FilterAction.INCLUDE,
                        priority=2,
                    )
                )

        # Course update threshold
        if "filters" in self.settings and "course_update_threshold_months" in self.settings["filters"]:
            threshold_months = self.settings["filters"]["course_update_threshold_months"]
            if threshold_months > 0:
                self.rules.append(
                    FilterRule(
                        name="course_update_filter",
                        field="last_updated",
                        operator="custom",
                        value=threshold_months,
                        action=FilterAction.INCLUDE,
                        priority=2,
                    )
                )

        # Title exclusions
        if "exclusions" in self.settings and "title_exclude" in self.settings["exclusions"]:
            title_exclude = self.settings["exclusions"]["title_exclude"]
            if title_exclude:
                self.rules.append(
                    FilterRule(
                        name="title_exclude_filter",
                        field="title",
                        operator="not_contains_any",
                        value=title_exclude,
                        action=FilterAction.EXCLUDE,
                        priority=3,
                    )
                )

        # Instructor exclusions
        if "exclusions" in self.settings and "instructor_exclude" in self.settings["exclusions"]:
            instructor_exclude = self.settings["exclusions"]["instructor_exclude"]
            if instructor_exclude:
                self.rules.append(
                    FilterRule(
                        name="instructor_exclude_filter",
                        field="instructor",
                        operator="not_in",
                        value=instructor_exclude,
                        action=FilterAction.EXCLUDE,
                        priority=3,
                    )
                )

        # Keyword exclusions
        if "exclusions" in self.settings and "keyword_exclude" in self.settings["exclusions"]:
            keyword_exclude = self.settings["exclusions"]["keyword_exclude"]
            if keyword_exclude:
                self.rules.append(
                    FilterRule(
                        name="keyword_exclude_filter",
                        field="keywords",
                        operator="not_contains_any",
                        value=keyword_exclude,
                        action=FilterAction.EXCLUDE,
                        priority=3,
                    )
                )

        # Price filters
        if "filters" in self.settings:
            if self.settings["filters"].get("free_only", False):
                self.rules.append(
                    FilterRule(
                        name="free_only_filter",
                        field="discounted_price",
                        operator="eq",
                        value=0.0,
                        action=FilterAction.INCLUDE,
                        priority=1,
                    )
                )
            elif self.settings["filters"].get("discounted_only", False):
                self.rules.append(
                    FilterRule(
                        name="discounted_only_filter",
                        field="discounted_price",
                        operator="lt",
                        value=lambda course: course.price,
                        action=FilterAction.INCLUDE,
                        priority=1,
                    )
                )

        # Sort rules by priority
        self.rules.sort(key=lambda r: r.priority)

    def normalize_category(self, category: str) -> str:
        """Normalize category name to canonical form.

        Args:
            category: Raw category name

        Returns:
            Normalized category name
        """
        if not category:
            return ""

        category_lower = category.lower().strip()

        for canonical, variations in self.category_mappings.items():
            if category_lower in variations:
                return canonical

        return category_lower

    def normalize_language(self, language: str) -> str:
        """Normalize language code to canonical form.

        Args:
            language: Raw language code or name

        Returns:
            Normalized language code
        """
        if not language:
            return ""

        language_lower = language.lower().strip()

        for canonical, variations in self.language_mappings.items():
            if language_lower in variations:
                return canonical

        return language_lower

    def extract_keywords(self, course: CourseData) -> list[str]:
        """Extract keywords from course data.

        Args:
            course: Course data

        Returns:
            List of extracted keywords
        """
        keywords = []

        # Extract from title
        if course.title:
            title_words = re.findall(r"\b\w+\b", course.title.lower())
            keywords.extend(title_words)

        # Extract from category
        if course.category:
            keywords.append(course.category.lower())

        # Extract from subcategory
        if course.subcategory:
            keywords.append(course.subcategory.lower())

        # Extract from instructor
        if course.instructor:
            instructor_words = re.findall(r"\b\w+\b", course.instructor.lower())
            keywords.extend(instructor_words)

        # Add existing keywords
        if course.keywords:
            keywords.extend([kw.lower() for kw in course.keywords])

        return list(set(keywords))  # Remove duplicates

    def apply_rule(self, course: CourseData, rule: FilterRule) -> tuple[bool, str]:
        """Apply a single filter rule to a course.

        Args:
            course: Course data
            rule: Filter rule to apply

        Returns:
            Tuple of (passes_filter, reason)
        """
        try:
            # Get field value
            field_value = getattr(course, rule.field, None)
            if field_value is None:
                return True, f"Field '{rule.field}' not found"

            # Handle case sensitivity
            if isinstance(field_value, str) and not rule.case_sensitive:
                field_value = field_value.lower()

            rule_value = rule.value
            if isinstance(rule_value, str) and not rule.case_sensitive:
                rule_value = rule_value.lower()
            elif isinstance(rule_value, list):
                rule_value = [v.lower() if isinstance(v, str) and not rule.case_sensitive else v for v in rule_value]

            # Apply operator
            result = self._apply_operator(field_value, rule.operator, rule_value, course)

            # Return result based on action
            if rule.action == FilterAction.INCLUDE:
                return result, f"{'Passed' if result else 'Failed'} {rule.name}"
            else:  # EXCLUDE
                return not result, f"{'Passed' if not result else 'Failed'} {rule.name}"

        except Exception as e:
            self.logger.warning(f"Error applying filter rule '{rule.name}': {e}")
            return True, f"Error in {rule.name}: {e!s}"

    def _apply_operator(self, field_value: Any, operator: str, rule_value: Any, course: CourseData) -> bool:
        """Apply a specific operator.

        Args:
            field_value: Value from the course field
            operator: Operator to apply
            rule_value: Value to compare against
            course: Full course data (for custom operators)

        Returns:
            True if condition is met
        """
        if operator == "eq":
            return field_value == rule_value
        elif operator == "ne":
            return field_value != rule_value
        elif operator == "lt":
            return field_value < (rule_value(course) if callable(rule_value) else rule_value)
        elif operator == "gt":
            return field_value > (rule_value(course) if callable(rule_value) else rule_value)
        elif operator == "le":
            return field_value <= (rule_value(course) if callable(rule_value) else rule_value)
        elif operator == "ge":
            return field_value >= (rule_value(course) if callable(rule_value) else rule_value)
        elif operator == "contains":
            return rule_value in str(field_value)
        elif operator == "not_contains":
            return rule_value not in str(field_value)
        elif operator == "contains_any":
            return any(item in str(field_value) for item in rule_value)
        elif operator == "not_contains_any":
            return not any(item in str(field_value) for item in rule_value)
        elif operator == "regex":
            return bool(re.search(rule_value, str(field_value)))
        elif operator == "in":
            # Handle normalized values
            if field_value in rule_value:
                return True
            # Try normalized versions
            if isinstance(field_value, str):
                normalized = self.normalize_category(field_value) if hasattr(self, "normalize_category") else field_value
                return normalized in rule_value
            return False
        elif operator == "not_in":
            normalized = self.normalize_category(field_value) if hasattr(self, "normalize_category") else field_value
            return normalized not in rule_value
        elif operator == "custom":
            # Custom operators for specific fields
            if hasattr(self, f"_custom_{field_value}"):
                return getattr(self, f"_custom_{field_value}")(field_value, rule_value, course)
            # Default custom handling for course update
            if "last_updated" in str(field_value):
                return self._is_course_updated(field_value, rule_value)
            return True
        else:
            self.logger.warning(f"Unknown operator: {operator}")
            return True

    def _is_course_updated(self, last_updated: str, threshold_months: int) -> bool:
        """Check if course was updated within threshold.

        Args:
            last_updated: Last update date string
            threshold_months: Threshold in months

        Returns:
            True if course is recently updated
        """
        if not last_updated:
            return False

        try:
            # Parse date (handle various formats)
            update_date = None
            for fmt in [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
            ]:
                try:
                    update_date = datetime.strptime(last_updated, fmt)
                    break
                except ValueError:
                    continue

            if not update_date:
                return False

            threshold_date = datetime.now() - timedelta(days=threshold_months * 30)
            return update_date >= threshold_date

        except Exception as e:
            self.logger.warning(f"Error parsing last_updated date '{last_updated}': {e}")
            return False

    def filter_course(self, course: CourseData) -> tuple[bool, list[str]]:
        """Filter a single course through all rules.

        Args:
            course: Course data to filter

        Returns:
            Tuple of (passes_all_filters, reasons)
        """
        reasons = []

        # Normalize course data
        course.category = self.normalize_category(course.category)
        course.language = self.normalize_language(course.language)

        # Extract keywords if not present
        if not course.keywords:
            course.keywords = self.extract_keywords(course)

        # Apply all rules
        for rule in self.rules:
            passes, reason = self.apply_rule(course, rule)
            reasons.append(reason)

            if not passes:
                return False, reasons

        return True, reasons

    def filter_courses(self, courses: list[CourseData]) -> tuple[list[CourseData], dict[str, int]]:
        """Filter a list of courses.

        Args:
            courses: List of courses to filter

        Returns:
            Tuple of (filtered_courses, filter_stats)
        """
        filtered_courses = []
        filter_stats = {
            "total_input": len(courses),
            "total_output": 0,
            "filtered_out": 0,
            "filter_reasons": {},
        }

        for course in courses:
            passes, reasons = self.filter_course(course)

            if passes:
                filtered_courses.append(course)
                filter_stats["total_output"] += 1
            else:
                filter_stats["filtered_out"] += 1
                # Track reasons for filtering out
                for reason in reasons:
                    if "Failed" in reason:
                        filter_name = reason.split("Failed ")[-1]
                        filter_stats["filter_reasons"][filter_name] = filter_stats["filter_reasons"].get(filter_name, 0) + 1

        return filtered_courses, filter_stats

    def get_filter_summary(self) -> dict[str, Any]:
        """Get a summary of active filters.

        Returns:
            Dictionary containing filter summary
        """
        summary = {
            "total_rules": len(self.rules),
            "include_rules": [r.name for r in self.rules if r.action == FilterAction.INCLUDE],
            "exclude_rules": [r.name for r in self.rules if r.action == FilterAction.EXCLUDE],
            "settings": self.settings,
        }

        return summary

    def add_custom_rule(self, rule: FilterRule):
        """Add a custom filter rule.

        Args:
            rule: Custom filter rule to add
        """
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
        self.logger.info(f"Added custom filter rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a filter rule by name.

        Args:
            rule_name: Name of the rule to remove

        Returns:
            True if rule was removed
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        removed = len(self.rules) < original_count

        if removed:
            self.logger.info(f"Removed filter rule: {rule_name}")

        return removed

    def update_settings(self, new_settings: dict[str, Any]):
        """Update filter settings and reload rules.

        Args:
            new_settings: New settings dictionary
        """
        self.settings.update(new_settings)
        self._load_filter_rules()
        self.logger.info("Filter settings updated and rules reloaded")


def create_course_from_dict(data: dict[str, Any]) -> CourseData:
    """Create a CourseData object from a dictionary.

    Args:
        data: Dictionary containing course data

    Returns:
        CourseData object
    """
    return CourseData(
        title=data.get("title", ""),
        instructor=data.get("instructor", ""),
        category=data.get("category", ""),
        subcategory=data.get("subcategory", ""),
        language=data.get("language", ""),
        rating=float(data.get("rating", 0.0)),
        num_reviews=int(data.get("num_reviews", 0)),
        num_students=int(data.get("num_students", 0)),
        price=float(data.get("price", 0.0)),
        discounted_price=float(data.get("discounted_price", 0.0)),
        duration=float(data.get("duration", 0.0)),
        level=data.get("level", ""),
        last_updated=data.get("last_updated", ""),
        has_certificate=bool(data.get("has_certificate", False)),
        has_captions=bool(data.get("has_captions", False)),
        keywords=data.get("keywords", []),
        url=data.get("url", ""),
        coupon_code=data.get("coupon_code", ""),
    )


if __name__ == "__main__":
    # Test the enhanced filter
    print("Testing enhanced filter...")

    # Create test settings
    test_settings = {
        "languages": {"en": True, "es": False},
        "categories": {"development": True, "business": True},
        "filters": {
            "min_rating": 4.0,
            "min_reviews": 10,
            "course_update_threshold_months": 12,
        },
        "exclusions": {
            "title_exclude": ["test", "demo"],
            "instructor_exclude": ["bad-instructor"],
        },
    }

    # Create enhanced filter
    enhanced_filter = EnhancedFilter(test_settings)

    # Create test course
    test_course = CourseData(
        title="Python Programming Course",
        instructor="good-instructor",
        category="development",
        language="en",
        rating=4.5,
        num_reviews=100,
        last_updated="2024-01-01T00:00:00Z",
    )

    # Test filtering
    passes, reasons = enhanced_filter.filter_course(test_course)
    print(f"Course passes filter: {passes}")
    print(f"Reasons: {reasons}")

    # Test filter summary
    summary = enhanced_filter.get_filter_summary()
    print(f"Filter summary: {summary}")
