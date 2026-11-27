import gzip
import json
import logging
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from src.constants.etl import SCRAPER_BRANDED_USER_AGENT
from src.etl.base import BaseETL
from src.models.course import AwsSkillBuilderModel

logger = logging.getLogger(__name__)

BASE_URL = "https://www.classcentral.com"
PROVIDER_PATH = "/provider/aws-skill-builder"
# Class Central answers HTTP 429 after a handful of quick requests (seen on
# 2026-11-27), so a run stays small and slow: two pages per listing, pauses
# in between.
PAGES_PER_LISTING = 2
REQUEST_DELAY_SECONDS = 5
LANGUAGE_SPANISH, LANGUAGE_ENGLISH = "es", "en"
LANGUAGES = (LANGUAGE_SPANISH, LANGUAGE_ENGLISH)

# (language, Class Central `lang` value, sort). The newest Spanish courses
# are Spanish. The newest courses tagged English are SimuLearn scenarios
# titled in Korean or Japanese, so English is read by rating instead.
LISTINGS = ((LANGUAGE_SPANISH, "spanish", "created-up"), (LANGUAGE_ENGLISH, "english", "rating-up"))

# Markers AWS puts in the title of a course that is not in English. Class
# Central tags some of them "English" all the same, so the title is read too.
LANGUAGE_MARKERS = {
    "es": ("español", "spanish"),
    "fr": ("français", "french"),
    "pt": ("portugu", "portuguese"),
    "it": ("italiano", "italian"),
    "de": ("deutsch", "german"),
    "ja": ("日本語", "japanese"),
    "ko": ("한국", "korean"),
    "zh": ("中文", "chinese"),
    "id": ("indones", "instruktur"),
    "ar": ("العربية", "arabic"),
    "ru": ("русский", "russian"),
    "tr": ("türk", "turkish"),
    "nl": ("nederlands", "dutch"),
    "sv": ("svenska", "swedish"),
}


class ClassCentralRateLimited(RuntimeError):
    """Class Central answered HTTP 429: wait instead of asking again."""


def is_latin_script(title: str) -> bool:
    """Return True when every letter of `title` is Latin script."""
    return all("LATIN" in unicodedata.name(char, "") for char in title if unicodedata.category(char).startswith("L"))


def names_another_language(title: str, language: str) -> bool:
    """Return True when `title` carries the marker of a language other than `language`."""
    lowered = title.lower()
    return any(marker in lowered for code, markers in LANGUAGE_MARKERS.items() if code != language for marker in markers)


def is_in_language(title: str | None, language: str) -> bool:
    """Return True when `title` reads as a course in `language`."""
    if not title or not is_latin_script(title):
        return False
    return not names_another_language(title, language)


def parse_listing(html: str, language: str) -> list[dict[str, Any]]:
    """Return the courses of one Class Central page.

    Each course link carries its facts as JSON in `data-track-props`, which is
    sturdier than reading the spans. A course appears in the page through up
    to three links; the first one wins.
    """
    soup = BeautifulSoup(html, "html.parser")
    courses: dict[Any, dict[str, Any]] = {}
    for item in soup.select("li.course-list-course"):
        for link in item.select("a[data-track-props]"):
            try:
                props = json.loads(str(link["data-track-props"]))
            except (KeyError, TypeError, ValueError):
                continue
            course_id = props.get("course_id")
            if not course_id or course_id in courses:
                continue
            spans = [text for span in item.find_all("span") if (text := span.get_text(strip=True))]
            courses[course_id] = {
                "language": language,
                "title": props.get("course_name"),
                "url": BASE_URL + str(link.get("href") or ""),
                "level": str(props.get("course_level") or "").capitalize() or None,
                "is_free": bool(props.get("course_is_free")),
                "rating": props.get("course_avg_rating"),
                "rating_count": props.get("course_num_rating") or 0,
                "subject": props.get("course_subject"),
                "duration": next((text for text in spans if "hour" in text.lower() or "minute" in text.lower()), None),
                "no_longer_offered": "No Longer Offered" in spans,
            }
            break
    return list(courses.values())


def describe(course: dict[str, Any]) -> str | None:
    """One line with what the listing says about a course, e.g. `Beginner · 1 hour · 4.6/5 (17 ratings) · Free`."""
    parts = [course["level"], course["duration"]]
    if course["rating"] and course["rating_count"]:
        parts.append(f"{course['rating']:.1f}/5 ({course['rating_count']} ratings)")
    elif course["rating_count"]:
        parts.append(f"{course['rating_count']} ratings")
    parts.append("Free" if course["is_free"] else "Paid")
    if course["no_longer_offered"]:
        parts.append("No longer offered")
    return " · ".join(part for part in parts if part) or None


class AwsSkillBuilderETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """AWS Skill Builder courses as Class Central lists them, in Spanish and in English.

    Each run reads the first pages of two listings and keeps what it finds,
    together with the courses of earlier runs, so the file only grows.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.courses_file = Path(self.settings.project_root) / "data" / "courses" / "aws_skill_builder.json"

    def _fetch_page(self, lang: str, sort: str, page: int) -> str:
        """Return the HTML of one page of the provider listing."""
        query = urllib.parse.urlencode({"sort": sort, "lang": lang, "page": page})
        request = urllib.request.Request(f"{BASE_URL}{PROVIDER_PATH}?{query}", headers={"User-Agent": SCRAPER_BRANDED_USER_AGENT, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise ClassCentralRateLimited(f"Class Central rate-limited page {page} of the {lang} listing (HTTP 429).") from e
            logger.error(f"Failed to fetch Class Central page {page} of the {lang} listing: {e}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"Failed to fetch Class Central page {page} of the {lang} listing: {e}")
            raise
        return body.decode("utf-8", "replace")

    def extract(self) -> list[dict[str, Any]]:
        """Read the first pages of each listing; a rate limit ends the walk, but an empty first page is an error."""
        courses: list[dict[str, Any]] = []
        requests_left = len(LISTINGS) * PAGES_PER_LISTING
        for language, lang, sort in LISTINGS:
            for page in range(1, PAGES_PER_LISTING + 1):
                requests_left -= 1
                try:
                    found = parse_listing(self._fetch_page(lang, sort, page), language)
                except ClassCentralRateLimited:
                    if not courses:
                        raise
                    logger.warning("Rate-limited by Class Central: keeping the %d courses read so far.", len(courses))
                    return courses
                if not found:
                    if not courses:
                        raise ValueError("Class Central listed no AWS Skill Builder course: the page layout changed or the request was blocked.")
                    logger.warning("Page %d of the %s listing listed no course: keeping the %d courses read so far.", page, lang, len(courses))
                    return courses
                courses.extend(found)
                if requests_left:
                    time.sleep(REQUEST_DELAY_SECONDS)
        logger.info(f"Read {len(courses)} courses from Class Central.")
        return courses

    def _load_previous_records(self) -> dict[str, dict[str, Any]]:
        """The courses of earlier runs, by URL. Records without a language predate the Spanish/English split and are dropped."""
        if not self.courses_file.exists():
            return {}
        try:
            with open(self.courses_file, encoding="utf-8") as f:
                old_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load existing AWS courses: {e}")
            return {}
        return {course["url"]: course for course in old_data if course.get("url") and course.get("language") in LANGUAGES}

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep the courses in Spanish or English, add them to the ones already known, and keep `first_detected_at` by URL."""
        previous = self._load_previous_records()
        detected_times = {url: course.get("first_detected_at") for url, course in previous.items()}
        now = datetime.now(timezone.utc)
        records: dict[str, dict[str, Any]] = dict(previous)
        dropped = new = 0
        for course in data:
            if not course["url"] or not course["title"] or not is_in_language(course["title"], course["language"]):
                dropped += 1
                continue
            detected_at = detected_times.get(course["url"])
            new += detected_at is None
            model = AwsSkillBuilderModel(
                title=course["title"],
                url=course["url"],
                description=describe(course),
                duration=course["duration"],
                level=course["level"],
                subject=course["subject"],
                rating=course["rating"],
                rating_count=course["rating_count"],
                is_free=course["is_free"],
                language=course["language"],
                first_detected_at=datetime.fromisoformat(detected_at) if detected_at else now,
            )
            records[course["url"]] = model.model_dump(mode="json")

        logger.info(f"{len(data)} courses read, {dropped} not in Spanish or English, {new} new, {len(records)} in the file.")
        return list(records.values())

    def load(self, data: list[dict[str, Any]]) -> None:
        """Save the courses to JSON."""
        self.courses_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.courses_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved {len(data)} AWS Skill Builder courses to {self.courses_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    AwsSkillBuilderETL(name="aws_skill_builder_etl").run()
