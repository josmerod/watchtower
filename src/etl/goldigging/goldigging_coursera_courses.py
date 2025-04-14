import json
import os
import sys
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import asyncio

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

# Import utilities
from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("coursera_scraper")
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Constants
BASE_OUTPUT_DIR = "data/coursera"
MAX_PAGES_FIRST_RUN = 150
MAX_PAGES_SUBSEQUENT_RUN = 10
DEBUG_DIR = os.path.join(BASE_OUTPUT_DIR, "debug")

class CourseraScraper:
    """Scraper for retrieving Coursera courses from mooc-list.com.
    
    This class uses direct HTTP requests to retrieve courses from mooc-list.com
    and save them in JSON and CSV formats for further analysis.
    """
    
    BASE_URL = "https://www.mooc-list.com/initiative/coursera"
    
    def __init__(self, max_pages: Optional[int] = None) -> None:
        """Initialize the CourseraScraper.
        
        Args:
            max_pages: Maximum number of pages to scrape. If None, determined automatically
                       based on whether this is first run (150 pages) or subsequent run (10 pages).
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
                logger.info(f"First run detected, will scrape {MAX_PAGES_FIRST_RUN} pages")
                self.max_pages = MAX_PAGES_FIRST_RUN
            else:
                logger.info(f"Not first run, using default of {MAX_PAGES_SUBSEQUENT_RUN} pages")
                self.max_pages = MAX_PAGES_SUBSEQUENT_RUN
    
    async def scrape_courses(self) -> List[Dict[str, Any]]:
        """Scrape courses from mooc-list.com.
        
        Returns:
            List of dictionaries containing course information.
        """
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup
        
        all_courses = []
        page_num = 0
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
                )
                page = await context.new_page()
                
                # Visit the main site first to establish cookies
                logger.info("Visiting main site to establish cookies")
                await page.goto("https://www.mooc-list.com/", timeout=60000)
                await page.wait_for_timeout(3000)
                
                while page_num < self.max_pages:
                    url = f"{self.BASE_URL}?page={page_num}"
                    logger.info(f"Fetching page {page_num}: {url}")
                    
                    try:
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(5000)  # Wait for page to load
                    
                        # Save debug info for the first page
                        if page_num == 0:
                            debug_file = os.path.join(self.debug_dir, f"page_{page_num}.html")
                            debug_screenshot = os.path.join(self.debug_dir, f"page_{page_num}.png")
                            content = await page.content()
                            with open(debug_file, "w", encoding="utf-8") as f:
                                f.write(content)
                            await page.screenshot(path=debug_screenshot)
                            logger.info(f"Saved debug info to {debug_file} and {debug_screenshot}")
                        
                        # Extract course elements
                        content = await page.content()
                        soup = BeautifulSoup(content, "html.parser")
                        
                        # First try to find course elements in the view
                        course_elements = soup.find_all("div", class_="views-row")
                        
                        if not course_elements:
                            # Try alternative selectors
                            course_elements = soup.find_all("div", class_="node-course")
                        
                        if not course_elements:
                            # Try one more selector from the debug HTML
                            container = soup.find("div", class_="view-content")
                            if container:
                                course_elements = container.find_all("div", recursive=False)
                        
                        if not course_elements:
                            # Save debug info
                            debug_file = os.path.join(self.debug_dir, f"page_{page_num}_failed.html")
                            debug_screenshot = os.path.join(self.debug_dir, f"page_{page_num}_failed.png")
                            with open(debug_file, "w", encoding="utf-8") as f:
                                f.write(content)
                            await page.screenshot(path=debug_screenshot)
                            logger.error(f"No courses found on page {page_num}, saved debug info")
                            
                            # Check for pagination
                            next_button = soup.find("li", class_="pager-next")
                            if not next_button:
                                logger.info("No next page button found, stopping")
                                break
                            
                            try:
                                await page.click("li.pager-next a")
                                await page.wait_for_timeout(3000)
                                page_num += 1
                                continue
                            except Exception as e:
                                logger.error(f"Error clicking next page: {e}")
                                break
                        
                        logger.info(f"Found {len(course_elements)} course elements on page {page_num}")
                        
                        # Process courses
                        for element in course_elements:
                            course_data = self.extract_course_info(element, soup)
                            if course_data:
                                all_courses.append(course_data)
                        
                        # Check for next page
                        next_button = soup.find("li", class_="pager-next")
                        if not next_button:
                            logger.info("No next page button found, stopping")
                            break
                        
                        try:
                            await page.click("li.pager-next a")
                            await page.wait_for_timeout(3000)
                        except Exception as e:
                            logger.error(f"Error clicking next page: {e}")
                            break
                        
                        page_num += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing page {page_num}: {e}")
                        break
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Error in scrape_courses: {e}")
            
        logger.info(f"Scraped {len(all_courses)} courses in total")
        return all_courses
    
    def extract_course_info(self, course_element, soup) -> Dict[str, Any]:
        """Extract course information from a course element.
        
        Args:
            course_element: BeautifulSoup element containing course information.
            soup: The complete BeautifulSoup object for context
            
        Returns:
            Dictionary with extracted course information.
        """
        course_data = {}
        
        try:
            # Extract title and URL - try different selectors based on the HTML structure
            title_element = course_element.find("h2", class_="views-field-title") or course_element.find("h2", class_="node-title")
            
            if title_element and title_element.a:
                course_data["title"] = title_element.a.text.strip()
                course_data["url"] = title_element.a.get("href", "")
                if course_data["url"] and not course_data["url"].startswith("http"):
                    course_data["url"] = f"https://www.mooc-list.com{course_data['url']}"
            else:
                # Try direct title div field
                title_div = course_element.find("div", class_="views-field-title")
                if title_div and title_div.a:
                    course_data["title"] = title_div.a.text.strip()
                    course_data["url"] = title_div.a.get("href", "")
                    if course_data["url"] and not course_data["url"].startswith("http"):
                        course_data["url"] = f"https://www.mooc-list.com{course_data['url']}"
                        
            if not course_data.get("title"):
                return None
            
            # Helper function to extract field data
            def extract_field(field_class: str, prefix: str = "") -> Optional[str]:
                element = course_element.find("div", class_=field_class)
                if element:
                    text = element.get_text(strip=True)
                    if prefix and text.startswith(prefix):
                        return text[len(prefix):].strip()
                    return text
                return None
            
            # Helper function for views fields
            def extract_views_field(field_class: str, prefix: str = "") -> Optional[str]:
                element = course_element.find("div", class_=field_class)
                if element:
                    content = element.find("div", class_="field-content")
                    if content:
                        text = content.get_text(strip=True)
                        if prefix and text.startswith(prefix):
                            return text[len(prefix):].strip()
                        return text
                return None
            
            # Try to extract data from various field classes
            # Initiative/Provider
            provider = (
                extract_field("field-name-field-initiative", "Initiative: ") or 
                extract_views_field("views-field-field-initiative") or 
                "Coursera"
            )
            course_data["provider"] = provider
            
            # University/Institution
            institution = (
                extract_field("field-name-field-university", "University/Institution: ") or
                extract_views_field("views-field-field-university")
            )
            course_data["institution"] = institution
            
            # Subject
            subject = (
                extract_field("field-name-field-subject", "Subject: ") or
                extract_views_field("views-field-field-subject")
            )
            course_data["subject"] = subject
            
            # Cost
            cost = (
                extract_field("field-name-field-fee", "Course Fee: ") or
                extract_views_field("views-field-field-fee")
            )
            course_data["cost"] = cost if cost else "Free"
            
            # Language
            language = (
                extract_field("field-name-field-language", "Language: ") or
                extract_views_field("views-field-field-language")
            )
            course_data["language"] = language
            
            # Duration
            duration = (
                extract_field("field-name-field-duration", "Duration: ") or
                extract_views_field("views-field-field-duration")
            )
            course_data["duration"] = duration
            
            # Certificate information
            certificate_text = (
                extract_field("field-name-field-certificate") or
                extract_views_field("views-field-field-certificate")
            )
            course_data["certificate_offered"] = "Yes" in certificate_text if certificate_text else False
                
            # Description
            description_element = (
                course_element.find("div", class_="field-name-body") or
                course_element.find("div", class_="views-field-body")
            )
            if description_element:
                course_data["description"] = description_element.get_text(strip=True)
            
            # Get the URL directly from the href if title exists
            if "title" in course_data and not course_data.get("url"):
                url_link = soup.find("a", text=course_data["title"])
                if url_link:
                    course_data["url"] = url_link.get("href", "")
                    if course_data["url"] and not course_data["url"].startswith("http"):
                        course_data["url"] = f"https://www.mooc-list.com{course_data['url']}"
                
            # Add metadata
            course_data["scraped_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Error extracting course info: {e}")
            return None
            
        return course_data
        
    def save_courses(self, courses: List[Dict[str, Any]]) -> None:
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
                logger.warning(f"Found only {len(courses)} courses, which is suspiciously low. Check scraping.")

            # If the file already exists, we don't delete it, we update the contents
            if os.path.exists(self.courses_file):
                with open(self.courses_file, "r", encoding="utf-8") as f:
                    existing_courses = json.load(f)
                    existing_courses.extend(courses)
                    courses = existing_courses            
            # Save courses as JSON
            with open(self.courses_file, "w", encoding="utf-8") as f:
                json.dump(courses, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(courses)} courses to {self.courses_file}")
                
            # Update last run information
            last_run_info = {
                "timestamp": datetime.now().isoformat(),
                "courses_count": len(courses)
            }
            
            with open(self.last_run_file, "w", encoding="utf-8") as f:
                json.dump(last_run_info, f, ensure_ascii=False, indent=2)
            
            # Save as CSV for easier viewing (similar to YouTube posts)
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
        logger.info("Starting Coursera course scraper")
        courses = await self.scrape_courses()
        self.save_courses(courses)
        logger.info("Coursera course scraping completed")

async def main_async(max_pages: Optional[int] = None) -> None:
    """Asynchronous main entry point for the script.
    
    Args:
        max_pages: Optional override for the number of pages to scrape.
    """
    logger.info("Starting Coursera course scraping process")
    
    try:
        scraper = CourseraScraper(max_pages=max_pages)
        await scraper.run()
        logger.info("Coursera course scraping completed successfully")
    except Exception as e:
        logger.error(f"Error during Coursera course scraping: {str(e)}", exc_info=True)

def main(max_pages: Optional[int] = None) -> None:
    """Synchronous main entry point for the script.
    
    This function sets up the event loop and runs the async main function.
    
    Args:
        max_pages: Optional override for the number of pages to scrape.
    """
    try:
        # On Windows, use the ProactorEventLoop policy
        if sys.platform == 'win32':
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
    
    parser = argparse.ArgumentParser(description="Scrape Coursera courses from mooc-list.com")
    parser.add_argument("--max-pages", type=int, help="Maximum number of pages to scrape")
    args = parser.parse_args()
    
    main(max_pages=args.max_pages)
    logger.info("Script completed")
