"""ETL for extracting latest courses from Pluralsight."""

import asyncio
import json
import random
import re
from datetime import datetime

from bs4 import BeautifulSoup

from src.etl.base import BaseETL
from src.models.course import PluralsightCourseModel


class PluralsightETL(BaseETL[dict, PluralsightCourseModel]):
    """ETL for extracting latest courses from Pluralsight."""

    def __init__(self, max_pages: int = 5, **kwargs):
        """Initialize the Pluralsight ETL with configuration."""
        super().__init__(
            name="pluralsight_courses",
            description="Extract latest courses from Pluralsight",
            **kwargs,
        )
        self.max_pages = max_pages
        self.base_url = "https://www.pluralsight.com"
        self.browse_url = f"{self.base_url}/browse"

    def extract(self) -> list[dict]:
        """Extract course data from Pluralsight browse pages."""
        # Use asyncio to run the async scraping method
        return asyncio.run(self._extract_async())

    async def _extract_async(self) -> list[dict]:
        """Async extraction using Playwright for JavaScript rendering."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.error("Playwright not installed. Run: pip install playwright")
            raise

        courses = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                for page_num in range(1, self.max_pages + 1):
                    self.logger.info(f"Extracting from page {page_num}")

                    try:
                        page_courses = await self._extract_page_async(page, page_num)
                        courses.extend(page_courses)

                        # Rate limiting
                        await asyncio.sleep(random.uniform(2, 4))

                    except Exception as e:
                        self.logger.error(f"Error extracting page {page_num}: {e}")
                        continue

                await browser.close()

        except Exception as e:
            self.logger.error(f"Error in async extraction: {e}")

        self.logger.info(f"Extracted {len(courses)} courses total")
        return courses

    async def _extract_page_async(self, page, page_num: int) -> list[dict]:
        """Extract courses from a single page using Playwright."""
        url = f"{self.browse_url}?sort=new&page={page_num}"

        try:
            self.logger.info(f"Navigating to: {url}")
            await page.goto(url, timeout=60000)

            # Wait for the page to load and content to be rendered
            await page.wait_for_timeout(5000)

            # Try to wait for course content to load
            try:
                await page.wait_for_selector(
                    'div[data-cy*="course"], a[href*="/courses/"], .course-card, [class*="course"]',
                    timeout=10000,
                )
            except:
                self.logger.warning(f"No course selectors found on page {page_num}, continuing anyway")

            # Debug: Save HTML for inspection on first page
            if page_num == 1:
                debug_file = self.output_dir / f"debug_page_{page_num}_playwright.html"
                content = await page.content()
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info(f"Saved debug HTML to {debug_file}")

            # Get page content and parse with BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            courses = []

            # Look for course cards with better selectors for modern Pluralsight
            course_elements = []

            # Try multiple selectors that might match Pluralsight's structure
            selectors_to_try = [
                'div[data-cy*="course"]',  # Data-cy attributes
                'a[href*="/courses/"]',  # Course URLs
                ".course-card",  # Course card class
                '[class*="course"]',  # Any class containing "course"
                '[data-testid*="course"]',  # Test ID attributes
                ".search-result",  # Search result items
                '[class*="card"]',  # Generic cards
            ]

            for selector in selectors_to_try:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        # Extract data directly from Playwright elements
                        for element in elements[:20]:  # Limit to first 20
                            # Get href and text content directly from Playwright element
                            try:
                                href = await element.get_attribute("href")
                                text_content = await element.text_content()
                                inner_text = await element.inner_text() if hasattr(element, "inner_text") else ""

                                if href and "/courses/" in href:
                                    # Create a simple dict to pass to extraction
                                    element_data = {
                                        "href": href,
                                        "text": text_content or inner_text or "",
                                        "type": "playwright_element",
                                    }
                                    course_elements.append(element_data)
                            except Exception as e:
                                self.logger.debug(f"Error extracting from element: {e}")
                                continue
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue

            # If no elements found with Playwright selectors, fall back to BeautifulSoup parsing
            if not course_elements:
                self.logger.info("No elements found with Playwright selectors, trying BeautifulSoup parsing")
                # Try finding course links in the rendered HTML
                all_links = soup.find_all("a", href=True)
                course_links = [link for link in all_links if "/courses/" in link.get("href", "")]

                if course_links:
                    course_elements = course_links[:20]
                    self.logger.info(f"Found {len(course_elements)} course links via BeautifulSoup")

            self.logger.info(f"Found {len(course_elements)} course elements on page {page_num}")

            # Extract course data from elements
            for i, element in enumerate(course_elements):
                self.logger.debug(f"Processing element {i + 1}/{len(course_elements)}")
                course_data = self._extract_course_from_element(element)
                if course_data:
                    courses.append(course_data)
                    self.logger.info(f"Successfully extracted course: {course_data.get('title', 'No title')}")
                else:
                    self.logger.debug(f"Failed to extract course data from element {i + 1}")

            return courses

        except Exception as e:
            self.logger.error(f"Error extracting page {page_num}: {e}")
            return []

    def _extract_course_from_element(self, element) -> dict | None:
        """Extract course information from a course element."""
        try:
            course_data = {}

            # Handle different element types
            if isinstance(element, dict) and element.get("type") == "playwright_element":
                # Playwright-extracted element
                course_data["url"] = self._build_full_url(element.get("href", ""))
                full_text = element.get("text", "").strip()
                course_data["title"] = full_text

                # Extract instructor from the full text
                if " by " in full_text:
                    parts = full_text.split(" by ")
                    if len(parts) > 1:
                        instructor_part = parts[1].split(" Libraries:")[0] if " Libraries:" in parts[1] else parts[1]
                        instructor_part = instructor_part.split(" Core Tech")[0]  # Remove category info
                        instructor_part = instructor_part.split(" Data ")[0]  # Remove data category
                        course_data["instructor"] = instructor_part.strip()

                self.logger.debug(f"Playwright element: {course_data['url'][:50]}, title: {course_data['title'][:50]}")

            elif hasattr(element, "get") and hasattr(element, "get_text"):
                # This is a BeautifulSoup element
                if element.name == "a" and element.get("href"):
                    # Direct link element
                    course_data["url"] = self._build_full_url(element.get("href"))
                    course_data["title"] = element.get_text(strip=True)
                    self.logger.debug(f"Direct link: {course_data['url'][:50]}, title: {course_data['title'][:50]}")
                else:
                    # Container element - find course link and title
                    link_element = element.find("a", href=lambda x: x and "/courses/" in str(x))
                    if link_element:
                        course_data["url"] = self._build_full_url(link_element.get("href"))

                    # Try to find title in headers or in the link text
                    title_element = element.find(["h1", "h2", "h3", "h4", "h5", "h6"])
                    if title_element:
                        course_data["title"] = title_element.get_text(strip=True)
                    elif link_element:
                        course_data["title"] = link_element.get_text(strip=True)

                # Extract additional metadata for BeautifulSoup elements
                if hasattr(element, "get_text"):
                    all_text = element.get_text()
                    text_parts = [part.strip() for part in all_text.split("\n") if part.strip()]

                    # Look for instructor info
                    for part in text_parts:
                        if any(keyword in part.lower() for keyword in ["by ", "instructor", "author"]):
                            course_data["instructor"] = part.replace("by ", "").replace("By ", "").strip()
                            break

                    # Look for duration
                    for part in text_parts:
                        if re.search(r"\d+h|\d+m|\d+ hours|\d+ minutes", part, re.I):
                            course_data["duration"] = part.strip()
                            break

                    # Look for level
                    for part in text_parts:
                        if any(level in part.lower() for level in ["beginner", "intermediate", "advanced"]):
                            course_data["level"] = part.strip()
                            break

            # Clean up title
            if course_data.get("title"):
                title = course_data["title"]
                # Remove "Course" prefix if present
                if title.startswith("Course "):
                    title = title[7:]

                # Try to extract just the course name (everything before "by" or "Libraries:")
                if " by " in title:
                    title = title.split(" by ")[0]
                elif " Libraries:" in title:
                    title = title.split(" Libraries:")[0]

                # Clean up whitespace
                course_data["title"] = " ".join(title.split()).strip()

            # Basic validation
            if not course_data.get("title") or not course_data.get("url"):
                self.logger.debug(f"Missing title or URL: title={course_data.get('title')}, url={course_data.get('url')}")
                return None

            # Skip if title is too short or seems invalid
            if len(course_data["title"]) < 3:
                self.logger.debug(f"Title too short: '{course_data['title']}'")
                return None

            # Extract course ID from URL
            if course_data.get("url"):
                course_id_match = re.search(r"/courses/([^/?]+)", course_data["url"])
                if course_id_match:
                    course_data["course_id"] = course_id_match.group(1)

            # Set provider and timestamp
            course_data["provider"] = "Pluralsight"
            course_data["scraped_at"] = datetime.utcnow().isoformat()

            return course_data

        except Exception as e:
            self.logger.warning(f"Error extracting course from element: {e}")
            return None

    def _build_full_url(self, relative_url: str) -> str:
        """Build full URL from relative URL."""
        if relative_url.startswith("http"):
            return relative_url
        if relative_url.startswith("/"):
            return f"{self.base_url}{relative_url}"
        return f"{self.base_url}/{relative_url}"

    def transform(self, data: list[dict]) -> list[PluralsightCourseModel]:
        """Transform extracted data into PluralsightCourseModel objects."""
        transformed = []

        for item in data:
            try:
                # Clean and validate data
                if not item.get("title") or not item.get("url"):
                    continue

                # Ensure URL is properly formatted
                if not item["url"].startswith(("http://", "https://")):
                    item["url"] = f"https://{item['url']}"

                # Parse published date if available
                if item.get("published_date"):
                    try:
                        if isinstance(item["published_date"], str):
                            item["published_date"] = datetime.fromisoformat(item["published_date"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        item["published_date"] = None

                # Create model instance
                course = PluralsightCourseModel(**item)
                transformed.append(course)

            except Exception as e:
                self.logger.warning(f"Error transforming course data: {e}")
                self.metrics.records_failed += 1
                continue

        self.logger.info(f"Transformed {len(transformed)} courses")
        return transformed

    def load(self, data: list[PluralsightCourseModel]) -> None:
        """Load transformed data to JSON file."""
        if not data:
            self.logger.warning("No courses to save")
            return

        # Convert to dictionaries for JSON serialization
        courses_data = [course.model_dump() for course in data]

        # Load existing data if available
        output_file = self.output_dir / "pluralsight_courses.json"
        existing_courses = []

        if output_file.exists():
            try:
                with open(output_file, encoding="utf-8") as f:
                    existing_courses = json.load(f)
                self.logger.info(f"Loaded {len(existing_courses)} existing courses")
            except (OSError, json.JSONDecodeError) as e:
                self.logger.warning(f"Could not load existing courses: {e}")

        # Combine and deduplicate by URL
        all_courses = existing_courses + courses_data
        unique_courses = {}

        for course in all_courses:
            url = course.get("url")
            if url and (url not in unique_courses or str(course.get("scraped_at", "")) > str(unique_courses[url].get("scraped_at", ""))):
                unique_courses[url] = course

        final_courses = list(unique_courses.values())

        # Sort by scraped_at descending (newest first)
        # Convert to strings to ensure consistent comparison
        final_courses.sort(key=lambda x: str(x.get("scraped_at", "")), reverse=True)

        # Save to JSON
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(final_courses, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"Saved {len(final_courses)} unique courses to {output_file}")

            # Also save to CSV for easier viewing
            csv_file = self.output_dir / "pluralsight_courses.csv"
            try:
                import pandas as pd

                df = pd.DataFrame(final_courses)
                # Drop description to avoid CSV formatting issues
                if "description" in df.columns:
                    df = df.drop(columns=["description"])
                df.to_csv(csv_file, index=False)
                self.logger.info(f"Also saved courses to CSV: {csv_file}")
            except ImportError:
                self.logger.info("Pandas not available, skipping CSV export")
            except Exception as e:
                self.logger.warning(f"Could not save to CSV: {e}")

        except Exception as e:
            self.logger.error(f"Error saving courses: {e}")
            raise


def main():
    """Main function to run the Pluralsight ETL."""
    etl = PluralsightETL(max_pages=3)  # Start with fewer pages for testing
    metrics = etl.run()

    print(f"ETL completed. Extracted: {metrics.records_extracted}, " f"Transformed: {metrics.records_transformed}, " f"Loaded: {metrics.records_loaded}")


if __name__ == "__main__":
    main()
