import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# Import utilities
from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("classcentral_scraper")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Constants
BASE_OUTPUT_DIR = "data/classcentral"
MAX_PAGES_FIRST_RUN = 50
MAX_PAGES_SUBSEQUENT_RUN = 10
DEBUG_DIR = os.path.join(BASE_OUTPUT_DIR, "debug")


class ClassCentralScraper:
    """Scraper for retrieving Coursera courses from classcentral.com.

    This class uses direct HTTP requests to retrieve courses from classcentral.com
    and save them in JSON and CSV formats for further analysis.
    """

    BASE_URL = "https://www.classcentral.com/provider/coursera"

    def __init__(self, max_pages: int | None = None) -> None:
        """Initialize the ClassCentralScraper.

        Args:
            max_pages: Maximum number of pages to scrape. If None, determined automatically
                       based on whether this is first run (50 pages) or subsequent run (10 pages).
        """
        # Ensure base output directory exists
        project_root = get_project_root()
        self.output_dir = os.path.join(project_root, BASE_OUTPUT_DIR)
        ensure_directories([BASE_OUTPUT_DIR])

        # Ensure debug directory exists
        self.debug_dir = os.path.join(self.output_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)

        # Define output files
        self.courses_file = os.path.join(self.output_dir, "coursera_courses.json")
        self.last_run_file = os.path.join(self.output_dir, "last_run_info.json")

        # Configuration
        self.max_pages = max_pages

        # Determine if this is first run
        self.is_first_run = not os.path.exists(self.last_run_file)

        # Set max pages based on whether this is first run
        if self.max_pages is None:
            if self.is_first_run:
                logger.info(
                    f"First run detected, will scrape {MAX_PAGES_FIRST_RUN} pages"
                )
                self.max_pages = MAX_PAGES_FIRST_RUN
            else:
                logger.info(
                    f"Not first run, using default of {MAX_PAGES_SUBSEQUENT_RUN} pages"
                )
                self.max_pages = MAX_PAGES_SUBSEQUENT_RUN

    async def scrape_courses(self) -> list[dict[str, Any]]:
        """Scrape courses from classcentral.com.

        Returns:
            List of dictionaries containing course information.
        """
        from bs4 import BeautifulSoup
        from playwright.async_api import async_playwright

        all_courses = []
        page_num = 1

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                # Visit the main site first to establish cookies
                logger.info("Visiting main site to establish cookies")
                await page.goto("https://www.classcentral.com/", timeout=60000)
                await page.wait_for_timeout(3000)

                while page_num <= self.max_pages:
                    url = f"{self.BASE_URL}?sort=created-up&page={page_num}"
                    logger.info(f"Fetching page {page_num}: {url}")

                    try:
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(5000)  # Wait for page to load

                        # Save debug info for the first page
                        if page_num == 1:
                            debug_file = os.path.join(
                                self.debug_dir, f"page_{page_num}.html"
                            )
                            debug_screenshot = os.path.join(
                                self.debug_dir, f"page_{page_num}.png"
                            )
                            content = await page.content()
                            with open(debug_file, "w", encoding="utf-8") as f:
                                f.write(content)
                            await page.screenshot(path=debug_screenshot)
                            logger.info(
                                f"Saved debug info to {debug_file} and {debug_screenshot}"
                            )

                        # Extract course elements
                        content = await page.content()
                        soup = BeautifulSoup(content, "html.parser")

                        # Find all course listings - they're in a list structure
                        course_elements = soup.find_all(
                            "li", class_="course-list-course"
                        )

                        if not course_elements:
                            # Try alternative selector
                            course_elements = soup.select(
                                "div.catalog-grid__results li"
                            )

                        if not course_elements:
                            # Save debug info
                            debug_file = os.path.join(
                                self.debug_dir, f"page_{page_num}_failed.html"
                            )
                            debug_screenshot = os.path.join(
                                self.debug_dir, f"page_{page_num}_failed.png"
                            )
                            with open(debug_file, "w", encoding="utf-8") as f:
                                f.write(content)
                            await page.screenshot(path=debug_screenshot)
                            logger.error(
                                f"No courses found on page {page_num}, saved debug info"
                            )

                            # Check if we've reached the end (no next page link)
                            next_link = soup.find("link", attrs={"rel": "next"})
                            if not next_link:
                                logger.info("No next page link found, stopping")
                                break

                            page_num += 1
                            continue

                        logger.info(
                            f"Found {len(course_elements)} course elements on page {page_num}"
                        )

                        # Process courses
                        for course_element in course_elements:
                            course_data = self.extract_course_info(course_element, soup)
                            if course_data:
                                all_courses.append(course_data)

                        # Check for next page
                        next_link = soup.find("link", attrs={"rel": "next"})
                        if not next_link:
                            logger.info("No next page link found, stopping")
                            break

                        # Next page exists, move to next page
                        page_num += 1

                    except Exception as e:
                        logger.error(f"Error processing page {page_num}: {e}")
                        break

                await browser.close()

        except Exception as e:
            logger.error(f"Error in scrape_courses: {e}")

        logger.info(f"Scraped {len(all_courses)} courses in total")
        return all_courses

    def extract_course_info(self, course_element, soup) -> dict[str, Any]:
        """Extract course information from a course element.

        Args:
            course_element: BeautifulSoup element containing course information.
            soup: The complete BeautifulSoup object for context

        Returns:
            Dictionary with extracted course information.
        """
        course_data = {}

        try:
            # Extract course title and URL
            course_name_element = course_element.find("h2", class_="text-1")
            if course_name_element:
                course_data["title"] = course_name_element.text.strip()

                # Get course URL from the nearest a tag
                a_tag = course_name_element.find_parent("a")
                if a_tag:
                    relative_url = a_tag.get("href", "")
                    course_data["url"] = f"https://www.classcentral.com{relative_url}"

            # Extract institution
            institution_element = course_element.find(
                "a", href=lambda x: x and "/institution/" in x
            )
            if institution_element:
                course_data["institution"] = institution_element.text.strip()

            # Extract description
            desc_element = course_element.find("p", class_="text-2")
            if desc_element and desc_element.a:
                course_data["description"] = desc_element.a.text.strip()

            # Extract details from the list items
            details_list = course_element.find("ul")
            if details_list:
                list_items = details_list.find_all("li")

                for item in list_items:
                    icon = item.find("i")
                    if not icon:
                        continue

                    icon_class = icon.get("class", [])
                    text_content = item.get_text(strip=True)

                    # Provider
                    if "icon-provider-charcoal" in icon_class:
                        course_data["provider"] = "Coursera"

                    # Duration
                    elif "icon-clock-charcoal" in icon_class:
                        course_data["duration"] = text_content

                    # Start date
                    elif "icon-calendar-charcoal" in icon_class:
                        course_data["start_date"] = text_content

                    # Cost/Pricing
                    elif (
                        "icon-tag-red" in icon_class
                        or "icon-tag-charcoal" in icon_class
                    ):
                        course_data["cost"] = text_content
                        course_data["is_free"] = "Free" in text_content

            # Extract rating if available
            rating_element = course_element.find("span", class_="cmpt-rating-medium")
            if rating_element:
                filled_stars = rating_element.find_all(
                    "i", class_=lambda c: c and "icon-star-" in c and "empty" not in c
                )
                course_data["rating"] = len(filled_stars) if filled_stars else 0

            # Extract subject/category if available
            track_props = course_element.find(attrs={"data-track-props": True})
            if track_props:
                try:
                    props = json.loads(track_props["data-track-props"])
                    if "course_subject" in props:
                        course_data["subject"] = props["course_subject"]
                    if "course_language" in props:
                        course_data["language"] = props["course_language"]
                    if "course_certificate" in props:
                        course_data["certificate_offered"] = props["course_certificate"]
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Error extracting track props: {e}")

            # Add metadata
            course_data["scraped_at"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Error extracting course info: {e}")
            return None

        return course_data

    def save_courses(self, courses: list[dict[str, Any]]) -> None:
        """Save scraped courses to JSON and CSV files.

        Args:
            courses: List of course dictionaries to save.
        """
        if not courses:
            logger.warning("No courses to save")
            return

        try:
            # Ensure we have at least some data before saving
            if len(courses) < 3:
                logger.warning(
                    f"Found only {len(courses)} courses, which is suspiciously low. Check scraping."
                )

            # Save courses as JSON
            with open(self.courses_file, "w", encoding="utf-8") as f:
                json.dump(courses, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(courses)} courses to {self.courses_file}")

            # Update last run information
            last_run_info = {
                "timestamp": datetime.now().isoformat(),
                "courses_count": len(courses),
            }

            with open(self.last_run_file, "w", encoding="utf-8") as f:
                json.dump(last_run_info, f, ensure_ascii=False, indent=2)

            # Save as CSV for easier viewing
            try:
                import pandas as pd

                csv_file = os.path.join(self.output_dir, "coursera_courses.csv")
                # Convert to DataFrame
                df = pd.DataFrame(courses)
                # Drop description to avoid CSV formatting issues
                if "description" in df.columns:
                    df = df.drop(columns=["description"])
                df.to_csv(csv_file, index=False)
                logger.info(f"Also saved courses to CSV: {csv_file}")
            except Exception as e:
                logger.warning(f"Could not save courses to CSV: {e}")

        except Exception as e:
            logger.error(f"Error saving courses: {e}")

    async def run(self) -> None:
        """Run the scraper asynchronously."""
        logger.info("Starting Class Central Coursera course scraper")
        courses = await self.scrape_courses()
        self.save_courses(courses)
        logger.info("Class Central Coursera course scraping completed")


async def main_async(max_pages: int | None = None) -> None:
    """Asynchronous main entry point for the script.

    Args:
        max_pages: Optional override for the number of pages to scrape.
    """
    logger.info("Starting Class Central Coursera course scraping process")

    try:
        scraper = ClassCentralScraper(max_pages=max_pages)
        await scraper.run()
        logger.info("Class Central Coursera course scraping completed successfully")
    except Exception as e:
        logger.error(
            f"Error during Class Central Coursera course scraping: {e!s}",
            exc_info=True,
        )


def main(max_pages: int | None = None) -> None:
    """Synchronous main entry point for the script.

    This function sets up the event loop and runs the async main function.

    Args:
        max_pages: Optional override for the number of pages to scrape.
    """
    try:
        # On Windows, use the ProactorEventLoop policy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(main_async(max_pages=max_pages))
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Coursera courses from classcentral.com"
    )
    parser.add_argument(
        "--max-pages", type=int, help="Maximum number of pages to scrape"
    )
    args = parser.parse_args()

    main(max_pages=args.max_pages)
    logger.info("Script completed")
