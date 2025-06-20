import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime
from typing import Any

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# Import utilities
from utils.course_deduplication import deduplicate_courses
from utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("deeplearningai_scraper")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Constants
BASE_OUTPUT_DIR = "data/deeplearningai"
MAX_PAGES_FIRST_RUN = 50
MAX_PAGES_SUBSEQUENT_RUN = 10
DEBUG_DIR = os.path.join(BASE_OUTPUT_DIR, "debug")


class DeepLearningAIScraper:
    """Scraper for retrieving courses from DeepLearning.AI.

    This class uses Playwright to scrape the DeepLearning.AI courses page
    and saves the course data in JSON and CSV formats for further analysis.
    """

    BASE_URL = "https://www.deeplearning.ai/courses/"

    def __init__(self, max_pages: int | None = None) -> None:
        """Initialize the DeepLearningAIScraper.

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
        self.courses_file = os.path.join(self.output_dir, "deeplearningai_courses.json")
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
        """Scrape courses from DeepLearning.AI."""
        from bs4 import BeautifulSoup
        from playwright.async_api import async_playwright

        all_courses: list[dict[str, Any]] = []
        page_num = 1

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                )
                # Stealth: mask automation to bypass detection
                await context.add_init_script(
                    "() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }"
                )
                page = await context.new_page()

                # Visit the main site first to establish cookies
                logger.info("Visiting main site to establish cookies")
                await page.goto("https://www.deeplearning.ai/", timeout=60000)
                await page.wait_for_timeout(3000)

                while page_num <= self.max_pages:
                    url = f"{self.BASE_URL}?courses_date_desc[page]={page_num}"
                    logger.info(f"Fetching page {page_num}: {url}")

                    try:
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(
                            random.randint(3000, 6000)
                        )  # Wait with random delay to avoid detection

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

                        # Extract page content
                        content = await page.content()
                        soup = BeautifulSoup(content, "html.parser")

                        # Find course cards - try multiple selectors
                        course_elements = soup.find_all("div", class_="course-card")
                        
                        if not course_elements:
                            # Try alternative selectors
                            course_elements = soup.find_all("article", class_="course")
                        
                        if not course_elements:
                            # Try more generic selectors
                            course_elements = soup.find_all("div", attrs={"data-course": True})
                        
                        if not course_elements:
                            # Try searching for links to courses
                            course_links = soup.find_all("a", href=lambda x: x and "/courses/" in x)
                            if course_links:
                                # Extract unique course links
                                unique_courses = set()
                                for link in course_links:
                                    href = link.get("href", "")
                                    if "/courses/" in href and href not in unique_courses:
                                        unique_courses.add(href)
                                        course_data = self.extract_course_from_link(link, soup)
                                        if course_data:
                                            all_courses.append(course_data)
                                
                                if unique_courses:
                                    logger.info(f"Found {len(unique_courses)} course links on page {page_num}")
                                    page_num += 1
                                    continue

                        if not course_elements:
                            # Save debug info for failed page
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
                            
                            # Check if there's pagination or we've reached the end
                            pagination = soup.find("nav", class_="pagination") or soup.find("div", class_="pagination")
                            next_button = soup.find("a", string=lambda x: x and "next" in x.lower())
                            
                            if not pagination and not next_button:
                                logger.info("No pagination found, likely reached end")
                                break
                            
                            # Try next page anyway in case this was a temporary issue
                            page_num += 1
                            if page_num > 3:  # Don't try too many empty pages
                                break
                            continue

                        logger.info(
                            f"Found {len(course_elements)} course elements on page {page_num}"
                        )

                        # Process courses
                        for course_element in course_elements:
                            course_data = self.extract_course_info(course_element, soup)
                            if course_data:
                                all_courses.append(course_data)

                        page_num += 1

                    except Exception as e:
                        logger.error(f"Error processing page {page_num}: {e}")
                        break

                await browser.close()

        except Exception as e:
            logger.error(f"Error in scrape_courses: {e}")

        logger.info(f"Scraped {len(all_courses)} courses in total")
        return all_courses

    def extract_course_from_link(self, link_element, soup) -> dict[str, Any]:
        """Extract course information from a course link."""
        course_data: dict[str, Any] = {}

        try:
            # Extract course title
            title_text = link_element.get_text(strip=True)
            if title_text:
                course_data["title"] = title_text

            # Extract URL
            href = link_element.get("href", "")
            if href:
                if href.startswith("/"):
                    course_data["url"] = f"https://www.deeplearning.ai{href}"
                else:
                    course_data["url"] = href

            # Set provider
            course_data["provider"] = "DeepLearning.AI"
            course_data["institution"] = "DeepLearning.AI"
            
            # Try to extract additional info from parent elements
            parent = link_element.parent
            if parent:
                # Look for course description
                desc_elem = parent.find("p") or parent.find("div", class_="description")
                if desc_elem:
                    course_data["description"] = desc_elem.get_text(strip=True)

            course_data["scraped_at"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Error extracting course from link: {e}")
            return None

        return course_data

    def extract_course_info(self, course_element, soup) -> dict[str, Any]:
        """Extract course information from a DeepLearning.AI course element."""
        course_data: dict[str, Any] = {}

        try:
            # Extract course title - try multiple selectors
            title_element = (
                course_element.find("h1") or
                course_element.find("h2") or
                course_element.find("h3") or
                course_element.find("h4") or
                course_element.find(class_="title") or
                course_element.find(class_="course-title") or
                course_element.find("a")
            )
            
            if title_element:
                course_data["title"] = title_element.get_text(strip=True)

            # Extract course URL
            link_element = course_element.find("a", href=True)
            if link_element:
                href = link_element.get("href", "")
                if href.startswith("/"):
                    course_data["url"] = f"https://www.deeplearning.ai{href}"
                else:
                    course_data["url"] = href

            # Extract description
            desc_element = (
                course_element.find("p") or
                course_element.find(class_="description") or
                course_element.find(class_="excerpt")
            )
            if desc_element:
                course_data["description"] = desc_element.get_text(strip=True)

            # Extract instructor information
            instructor_element = (
                course_element.find(class_="instructor") or
                course_element.find(class_="author") or
                course_element.find("span", string=lambda x: x and ("instructor" in x.lower() or "taught by" in x.lower()))
            )
            if instructor_element:
                course_data["instructor"] = instructor_element.get_text(strip=True)

            # Extract difficulty level
            level_element = (
                course_element.find(class_="level") or
                course_element.find(class_="difficulty") or
                course_element.find("span", string=lambda x: x and ("beginner" in x.lower() or "intermediate" in x.lower() or "advanced" in x.lower()))
            )
            if level_element:
                course_data["level"] = level_element.get_text(strip=True)

            # Extract duration
            duration_element = (
                course_element.find(class_="duration") or
                course_element.find("span", string=lambda x: x and ("hour" in x.lower() or "minute" in x.lower() or "week" in x.lower()))
            )
            if duration_element:
                course_data["duration"] = duration_element.get_text(strip=True)

            # Set provider and default values
            course_data["provider"] = "DeepLearning.AI"
            course_data["institution"] = "DeepLearning.AI"
            course_data["is_free"] = True  # Most DeepLearning.AI courses are free
            course_data["language"] = "English"
            course_data["certificate_offered"] = True

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
            if len(courses) < 1:
                logger.warning(
                    f"Found only {len(courses)} courses, which might be low. Check scraping."
                )

            # If the file already exists, we don't delete it, we update the contents
            all_courses = courses
            if os.path.exists(self.courses_file):
                try:
                    with open(self.courses_file, encoding="utf-8") as f:
                        existing_courses = json.load(f)
                        all_courses = existing_courses + courses
                        logger.info(
                            f"Combined {len(courses)} new courses with {len(existing_courses)} existing courses"
                        )
                except json.JSONDecodeError:
                    logger.warning(
                        "Error reading existing courses file. Starting fresh."
                    )

            # Deduplicate courses before saving
            deduplicated_courses, removed_count = deduplicate_courses(
                all_courses, key_field="url", prefer_newer=True
            )
            if removed_count > 0:
                logger.info(f"Removed {removed_count} duplicate courses")

            # Save courses as JSON
            with open(self.courses_file, "w", encoding="utf-8") as f:
                json.dump(deduplicated_courses, f, ensure_ascii=False, indent=2)
            logger.info(
                f"Saved {len(deduplicated_courses)} unique courses to {self.courses_file}"
            )

            # Update last run information
            last_run_info = {
                "timestamp": datetime.now().isoformat(),
                "courses_count": len(deduplicated_courses),
                "new_courses_added": len(courses),
                "duplicates_removed": removed_count,
            }

            with open(self.last_run_file, "w", encoding="utf-8") as f:
                json.dump(last_run_info, f, ensure_ascii=False, indent=2)

            # Save as CSV for easier viewing
            try:
                import pandas as pd

                csv_file = os.path.join(self.output_dir, "deeplearningai_courses.csv")
                # Convert to DataFrame
                df = pd.DataFrame(deduplicated_courses)
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
        logger.info("Starting DeepLearning.AI course scraper")
        courses = await self.scrape_courses()
        self.save_courses(courses)
        logger.info("DeepLearning.AI course scraping completed")


async def main_async(max_pages: int | None = None) -> None:
    """Asynchronous main entry point for the script.

    Args:
        max_pages: Optional override for the number of pages to scrape.
    """
    logger.info("Starting DeepLearning.AI course scraping process")

    try:
        scraper = DeepLearningAIScraper(max_pages=max_pages)
        await scraper.run()
        logger.info("DeepLearning.AI course scraping completed successfully")
    except Exception as e:
        logger.error(f"Error during DeepLearning.AI course scraping: {e!s}", exc_info=True)


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
        description="Scrape courses from DeepLearning.AI website"
    )
    parser.add_argument(
        "--max-pages", type=int, help="Maximum number of pages to scrape", default=10
    )
    args = parser.parse_args()

    main(max_pages=args.max_pages)
    logger.info("DeepLearning.AI scraper script completed")
