"""ETL pipeline for scraping LinkedIn Learning courses from Class Central.

Uses Playwright with stealth settings to bypass Cloudflare protection on
classcentral.com. Follows the same approach as the Coursera scraper, targeting
the LinkedIn Learning provider page.
"""

import asyncio
import json
import random
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from src.etl.base import BaseETL
from src.models.course import LinkedInLearningCourseModel

# Class Central provider page for LinkedIn Learning
BASE_URL = "https://www.classcentral.com/provider/linkedin-learning"
# Subject pages — soft skills + tech focus
SUBJECT_PAGES = {
    "software-development": "https://www.classcentral.com/subject/software-development",
    "data-science": "https://www.classcentral.com/subject/data-science",
    "business": "https://www.classcentral.com/subject/business",
    "leadership-management": "https://www.classcentral.com/subject/leadership-management",
    "communication": "https://www.classcentral.com/subject/communication",
}
MAX_PAGES_FIRST_RUN = 50
MAX_PAGES_SUBSEQUENT = 5
STEALTH_JS = "() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class LinkedInLearningETL(BaseETL[dict[str, Any], LinkedInLearningCourseModel]):
    """Scrape LinkedIn Learning courses from Class Central.

    Uses Playwright to navigate the provider page with pagination,
    extracting course metadata via BeautifulSoup. Falls back to
    cloudscraper if Cloudflare challenge is detected.
    """

    def __init__(self, max_pages: int | None = None, **kwargs: Any) -> None:
        """Initialize the ETL.

        Args:
            max_pages: Override for max pages to scrape. Auto-determined if None.
            **kwargs: Forwarded to BaseETL.
        """
        super().__init__(
            name="linkedin_learning",
            description="Scrape LinkedIn Learning courses from Class Central",
            **kwargs,
        )
        self.base_url = BASE_URL
        self.max_pages = max_pages
        self._determine_max_pages()
        assert self.max_pages is not None  # set by _determine_max_pages

    def _determine_max_pages(self) -> None:
        """Set max_pages based on whether this is the first run."""
        last_run_file = self.data_dir / "last_run_info.json"
        if self.max_pages is None:
            if not last_run_file.exists():
                self.logger.info("First run detected — will scrape up to %d pages", MAX_PAGES_FIRST_RUN)
                self.max_pages = MAX_PAGES_FIRST_RUN
            else:
                self.logger.info("Subsequent run — using %d pages", MAX_PAGES_SUBSEQUENT)
                self.max_pages = MAX_PAGES_SUBSEQUENT

    # ------------------------------------------------------------------
    # BaseETL contract
    # ------------------------------------------------------------------

    def extract(self) -> list[dict[str, Any]]:
        """Run the async Playwright scraper and return raw course dicts."""
        return asyncio.run(self._extract_async())

    def transform(self, data: list[dict[str, Any]]) -> list[LinkedInLearningCourseModel]:
        """Validate raw course dicts into LinkedInLearningCourseModel."""
        transformed: list[LinkedInLearningCourseModel] = []

        for item in data:
            if not item.get("title") or not item.get("url"):
                continue
            try:
                # Ensure URL has protocol
                if not item["url"].startswith(("http://", "https://")):
                    item["url"] = f"https://{item['url']}"

                course = LinkedInLearningCourseModel(**item)
                transformed.append(course)
            except Exception as e:
                self.logger.warning("Error transforming '%s': %s", item.get("title", "?"), e)
                self.metrics.records_failed += 1

        self.logger.info("Transformed %d valid courses", len(transformed))
        return transformed

    def load(self, data: list[LinkedInLearningCourseModel]) -> None:
        """Save to data/linkedin_learning/linkedin_learning_courses.json."""
        if not data:
            self.logger.warning("No courses to save")
            return

        courses_data = [course.model_dump() for course in data]

        # Load existing
        output_file = self.data_dir / "linkedin_learning_courses.json"
        existing: list[dict[str, Any]] = []
        if output_file.exists():
            try:
                existing = json.loads(output_file.read_text(encoding="utf-8"))
                self.logger.info("Loaded %d existing courses", len(existing))
            except (OSError, json.JSONDecodeError) as e:
                self.logger.warning("Could not load existing courses: %s", e)

        # Merge + dedupe by URL (keep newer scraped_at)
        all_courses = existing + courses_data
        unique: dict[str, dict[str, Any]] = {}
        for course in all_courses:
            url = course.get("url")
            if url and (url not in unique or str(course.get("scraped_at", "")) > str(unique[url].get("scraped_at", ""))):
                unique[url] = course

        final_courses = sorted(
            unique.values(),
            key=lambda x: str(x.get("scraped_at", "")),
            reverse=True,
        )

        # Save JSON
        output_file.write_text(
            json.dumps(final_courses, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        self.logger.info("Saved %d unique courses to %s", len(final_courses), output_file)

        # Last run info
        last_run = {
            "timestamp": datetime.utcnow().isoformat(),
            "courses_count": len(final_courses),
            "new_courses_added": len(courses_data),
            "duplicates_removed": len(all_courses) - len(final_courses),
        }
        (self.data_dir / "last_run_info.json").write_text(
            json.dumps(last_run, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # CSV export
        try:
            import pandas as pd

            csv_file = self.data_dir / "linkedin_learning_courses.csv"
            df = pd.DataFrame(final_courses)
            if "description" in df.columns:
                df = df.drop(columns=["description"])
            df.to_csv(csv_file, index=False)
        except Exception as e:
            self.logger.debug("CSV export skipped: %s", e)

    # ------------------------------------------------------------------
    # Async scraping
    # ------------------------------------------------------------------

    async def _extract_async(self) -> list[dict[str, Any]]:
        """Launch Playwright and scrape all pages."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.error("Playwright not installed. Run: uv add playwright")
            raise

        all_courses: list[dict[str, Any]] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=USER_AGENT,
                )
                await context.add_init_script(STEALTH_JS)
                page = await context.new_page()

                # Visit main site first to establish cookies
                self.logger.info("Visiting classcentral.com to establish cookies")
                await page.goto("https://www.classcentral.com/", timeout=60000)
                await page.wait_for_timeout(3000)

                # Scrape the LinkedIn Learning provider page
                for page_num in range(1, self.max_pages + 1):
                    url = f"{self.base_url}?sort=created-down&page={page_num}"
                    self.logger.info("Fetching page %d: %s", page_num, url)

                    try:
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(random.randint(4000, 7000))

                        # Debug save on first page
                        if page_num == 1:
                            debug_file = self.output_dir / "debug_page_1.html"
                            debug_file.write_text(await page.content(), encoding="utf-8")
                            self.logger.info("Saved debug HTML to %s", debug_file)

                        content = await page.content()
                        page_courses = self._parse_provider_page(content, page_num)
                        all_courses.extend(page_courses)

                        # Stop early if no courses found (end of data)
                        if not page_courses:
                            self.logger.info("No courses found on page %d — stopping pagination", page_num)
                            break

                    except Exception as e:
                        self.logger.error("Error on page %d: %s", page_num, e)
                        break

                await browser.close()

        except Exception as e:
            self.logger.error("Error in async extraction: %s", e)

        self.logger.info("Extracted %d courses total", len(all_courses))
        return all_courses

    def _parse_provider_page(self, content: str, page_num: int) -> list[dict[str, Any]]:
        """Parse a Class Central provider page HTML into course dicts."""
        soup = BeautifulSoup(content, "html.parser")
        courses: list[dict[str, Any]] = []

        # Class Central course listings are <li> with class "course-list-course"
        course_elements = soup.find_all("li", class_="course-list-course")
        if not course_elements:
            course_elements = soup.select("div.catalog-grid__results li")

        if not course_elements:
            self.logger.warning("No course elements found on page %d", page_num)
            return []

        self.logger.info("Found %d course elements on page %d", len(course_elements), page_num)

        for element in course_elements:
            course_data = self._extract_course_info(element)
            if course_data:
                courses.append(course_data)

        return courses

    def _extract_course_info(self, element: Any) -> dict[str, Any] | None:
        """Extract structured data from a single Class Central course element."""
        course_data: dict[str, Any] = {}

        try:
            # Title + URL
            title_el = element.find("h2", class_="text-1")
            if title_el:
                course_data["title"] = title_el.get_text(strip=True)
                a_tag = title_el.find_parent("a")
                if a_tag:
                    href = a_tag.get("href", "")
                    course_data["url"] = f"https://www.classcentral.com{href}"

            if not course_data.get("title"):
                return None

            # Institution
            inst_el = element.find("a", href=lambda x: x and "/institution/" in x)
            if inst_el:
                course_data["institution"] = inst_el.get_text(strip=True)

            # Description
            desc_el = element.find("p", class_="text-2")
            if desc_el:
                course_data["description"] = desc_el.get_text(strip=True)

            # Details list (duration, start date, cost)
            details_list = element.find("ul")
            if details_list:
                for item in details_list.find_all("li"):
                    icon = item.find("i")
                    if not icon:
                        continue
                    icon_class = icon.get("class", [])
                    text_content = item.get_text(strip=True)

                    if "icon-clock-charcoal" in icon_class:
                        course_data["duration"] = text_content
                    elif "icon-calendar-charcoal" in icon_class:
                        # Only set as published_date if it looks like a date.
                        # Class Central shows "Self-Paced" or "No Longer Offered"
                        # for courses without a concrete start date.
                        if text_content and not any(text_content.lower().startswith(w) for w in ("self", "no longer", "on", "ongoing", "flexible")):
                            course_data["published_date"] = text_content
                    elif "icon-tag-red" in icon_class or "icon-tag-charcoal" in icon_class:
                        course_data["is_free"] = "Free" in text_content

            # Rating
            rating_el = element.find("span", class_="cmpt-rating-medium")
            if rating_el:
                filled = rating_el.find_all("i", class_=lambda c: c and "icon-star-" in c and "empty" not in c)
                course_data["rating"] = len(filled) if filled else None

            # Track props (subject, language, certificate)
            track_el = element.find(attrs={"data-track-props": True})
            if track_el:
                try:
                    props = json.loads(track_el["data-track-props"])
                    course_data["subject"] = props.get("course_subject", "")
                    course_data["language"] = props.get("course_language", "")
                except (json.JSONDecodeError, KeyError):
                    pass

            # Provider — always LinkedIn Learning for this ETL
            course_data["provider"] = "LinkedIn Learning"
            course_data["scraped_at"] = datetime.utcnow().isoformat()

        except Exception as e:
            self.logger.error("Error extracting course info: %s", e)
            return None

        return course_data


if __name__ == "__main__":
    etl = LinkedInLearningETL()
    etl.run()
