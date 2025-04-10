import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Remove httpx, import playwright
# import httpx 
from playwright.async_api import async_playwright, Page, Browser, Playwright, Error as PlaywrightError
import polars as pl
from bs4 import BeautifulSoup, Tag # Keep BeautifulSoup for parsing flexibility

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.coursera.org/courses?sortBy=NEW&page={page_num}"
OUTPUT_DIR = Path("data/raw/coursera")
OUTPUT_FILE = OUTPUT_DIR / "coursera_courses.parquet"
MAX_PAGES_UPDATE = 5  # Number of pages to check during an update
# REQUEST_TIMEOUT = 30  # Playwright uses different timeout mechanisms
PAGE_LOAD_TIMEOUT = 60 * 1000 # Milliseconds for page load
CONCURRENT_PAGES = 5 # Limit concurrent browser pages/tabs


async def fetch_page(page: Page, page_num: int) -> Optional[str]:
    """
    Fetches the HTML content of a single Coursera search results page using Playwright.

    Args:
        page: A Playwright Page object.
        page_num: The page number to fetch.

    Returns:
        The HTML content as a string, or None if an error occurred.
    """
    url = BASE_URL.format(page_num=page_num)
    try:
        logger.info(f"Navigating to page {page_num}: {url}")
        await page.goto(url, timeout=PAGE_LOAD_TIMEOUT, wait_until='domcontentloaded') 
        # Optional: Wait for a specific selector that indicates courses are loaded
        # await page.wait_for_selector('[data-e2e="search-result-card"]', timeout=30000) 
        content = await page.content()
        logger.info(f"Successfully fetched content for page {page_num}")
        return content
    except PlaywrightError as e:
        logger.error(f"Playwright error fetching page {page_num} ({url}): {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching page {page_num} ({url}): {e}")
    return None


def parse_courses(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses the HTML content of a search results page to extract course data.

    Args:
        html_content: The HTML content of the page.

    Returns:
        A list of dictionaries, where each dictionary represents a course.
    """
    courses_data = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all course card containers. The exact selector might need adjustment.
        # Common patterns involve list items (li) within an ordered/unordered list (ol/ul)
        # Let's assume course cards are `li` elements with a specific data attribute or class.
        # We might need to inspect the actual page source for robust selectors.
        course_cards = soup.find_all('li', class_=lambda x: x and 'cds-9' in x) # Placeholder selector - likely needs refinement

        if not course_cards:
            # Fallback selector based on potential structure
             course_cards = soup.select('[data-e2e="search-result-card"]') # Another guess

        if not course_cards:
             logger.warning("Could not find course card containers using known selectors.")
             return []

        logger.info(f"Found {len(course_cards)} potential course cards on the page.")

        for card in course_cards:
            course_info = {}
            try:
                # --- Extract Course URL and Title --- Usually within an <a> tag
                title_element = card.find('h3') # Often course titles are in h3
                link_element = card.find('a', href=True)
                if link_element:
                    course_info['url'] = f"https://www.coursera.org{link_element['href']}" if link_element['href'].startswith('/') else link_element['href']
                    # Try getting title from link's content or a specific heading tag
                    title_text = title_element.get_text(strip=True) if title_element else link_element.get_text(strip=True)
                    course_info['title'] = title_text
                else:
                    # Skip card if no link/URL found
                    logger.debug("Skipping card, no link element found.")
                    continue

                # --- Extract Educator --- Look for a specific element or class
                # Often near the top, potentially a p or span with specific class
                educator_element = card.find('span', class_=lambda x: x and ('partner-name' in x or 'cds-1' in x)) # Guessing class names
                course_info['educator'] = educator_element.get_text(strip=True) if educator_element else None

                # --- Extract Skills --- Look for text starting with "Skills you'll gain:"
                skills_element = card.find(lambda tag: tag.name == 'p' and tag.find('strong') and "Skills you'll gain:" in tag.find('strong').get_text())
                if not skills_element:
                     # Fallback: find div/p containing the skills text based on structure
                    skills_container = card.find('div', class_=lambda x: x and 'skills' in x.lower())
                    if skills_container:
                        skills_text_raw = skills_container.get_text(separator=' ', strip=True)
                        if skills_text_raw.startswith("Skills you'll gain:"):
                            skills_text = skills_text_raw.replace("Skills you'll gain:", "").strip()
                            course_info['skills'] = [skill.strip() for skill in skills_text.split(',') if skill.strip()]
                        else:
                             course_info['skills'] = None
                    else:
                        course_info['skills'] = None
                else:
                    # Extract text after the strong tag
                    skills_text = ' '.join(sibling.get_text(strip=True) for sibling in skills_element.find('strong').find_next_siblings())
                    if not skills_text: # If skills are directly after strong tag text
                        skills_text = skills_element.get_text(strip=True).replace("Skills you'll gain:", "").strip()

                    course_info['skills'] = [skill.strip() for skill in skills_text.split(',') if skill.strip()]


                # --- Extract Level, Type, Duration --- Often in a shared container
                metadata_element = card.find('div', class_=lambda x: x and ('product-difficulty' in x or 'cds-117' in x )) # Guess
                if metadata_element:
                    metadata_text = metadata_element.get_text(separator='|', strip=True)
                    parts = [part.strip() for part in metadata_text.split('|') if part.strip()]
                    course_info['level'] = parts[0] if len(parts) > 0 else None
                    course_info['type'] = parts[1] if len(parts) > 1 else None # e.g., Course, Specialization
                    course_info['duration'] = parts[2] if len(parts) > 2 else None
                else:
                    # Fallback if specific class not found, look for pattern like "Level · Type · Duration"
                    details_elements = card.find_all('span', limit=3) # Guessing structure
                    details_text = ' · '.join(elem.get_text(strip=True) for elem in details_elements if elem.get_text(strip=True))
                    parts = [part.strip() for part in details_text.split('·') if part.strip()]
                    course_info['level'] = parts[0] if len(parts) > 0 else None
                    course_info['type'] = parts[1] if len(parts) > 1 else None
                    course_info['duration'] = parts[2] if len(parts) > 2 else None

                # Add other fields if needed, e.g., rating, number of reviews

                if course_info.get('title') and course_info.get('url'):
                    courses_data.append(course_info)
                else:
                    logger.debug(f"Skipping card, missing title or URL. Card content: {card.prettify()[:200]}...")

            except Exception as e:
                logger.warning(f"Error parsing a course card: {e}. Card content: {card.prettify()[:200]}...")
                continue # Skip this card on error

    except Exception as e:
        logger.error(f"Error parsing page content: {e}")

    logger.info(f"Successfully parsed {len(courses_data)} courses from the page.")
    return courses_data


def get_total_pages(html_content: str) -> int:
    """
    Parses the HTML content to find the total number of pages.

    Args:
        html_content: The HTML content of the first page.

    Returns:
        The total number of pages, or 0 if not found.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Find pagination controls - selectors might need adjustment based on actual page structure
        # Common patterns include nav elements or divs with 'pagination' in class/id
        # Let's look for buttons with a 'data-page' attribute within a likely pagination container
        pagination_container = soup.find('nav', attrs={'aria-label': lambda x: x and 'pagination' in x.lower()})
        if not pagination_container:
            # Fallback: search for divs that might contain pagination buttons
            pagination_container = soup.find('div', class_=lambda x: x and 'pagination' in x.lower())

        if pagination_container:
            page_buttons = pagination_container.find_all('button', attrs={'data-page': True})
            if page_buttons:
                # Extract page numbers and find the maximum
                page_numbers = [int(btn['data-page']) for btn in page_buttons if btn['data-page'].isdigit()]
                if page_numbers:
                    total_pages = max(page_numbers)
                    logger.info(f"Determined total pages: {total_pages}")
                    return total_pages

        # If the above fails, maybe look for text like "... 84"
        # This requires more specific selectors based on inspection
        logger.warning("Could not find pagination controls or determine total pages from the standard selectors.")
        return 0 # Indicate failure to find total pages

    except Exception as e:
        logger.error(f"Error parsing total pages: {e}")
        return 0


async def scrape_coursera(browser: Browser, num_pages_to_scrape: int) -> List[Dict[str, Any]]:
    """
    Scrapes course data from the specified number of Coursera pages concurrently using Playwright pages.

    Args:
        browser: A Playwright Browser instance.
        num_pages_to_scrape: The number of pages to scrape.

    Returns:
        A list of dictionaries containing scraped course data.
    """
    all_courses_data = []
    tasks = []
    semaphore = asyncio.Semaphore(CONCURRENT_PAGES) # Limit concurrent pages

    async def fetch_and_parse_page(page_num: int) -> List[Dict[str, Any]]:
        async with semaphore:
            page = None
            context = None
            try:
                # Create a new context for isolation, helps with cookies/localStorage if needed
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                page = await context.new_page()
                html_content = await fetch_page(page, page_num)
                if html_content:
                    parsed_data = parse_courses(html_content) # Still use BeautifulSoup parser
                    return parsed_data
                return []
            except Exception as e:
                 logger.error(f"Error in fetch_and_parse_page for page {page_num}: {e}")
                 return [] # Return empty list on error
            finally:
                if page:
                    await page.close()
                if context:
                    await context.close() # Close context to free up resources

    logger.info(f"Starting scrape for {num_pages_to_scrape} pages using Playwright...")
    # Create tasks for each page
    scrape_tasks = [fetch_and_parse_page(page_num) for page_num in range(1, num_pages_to_scrape + 1)]

    # Run tasks concurrently and gather results
    results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

    for i, result in enumerate(results):
        page_num = i + 1
        if isinstance(result, Exception):
            logger.error(f"Task for page {page_num} failed with exception: {result}")
        elif isinstance(result, list):
            if result:
                all_courses_data.extend(result)
                logger.debug(f"Successfully processed page {page_num}, added {len(result)} courses.")
            else:
                # This could be due to parsing errors logged earlier or no courses found
                logger.warning(f"No courses parsed or found for page {page_num}.")
        else:
             logger.error(f"Unexpected result type for page {page_num}: {type(result)}")


    logger.info(f"Playwright scraping finished. Total courses collected: {len(all_courses_data)}")
    return all_courses_data


def save_data(data: List[Dict[str, Any]], file_path: Path) -> None:
    """
    Saves the scraped course data to a Parquet file using Polars.

    Args:
        data: A list of dictionaries containing course data.
        file_path: The Path object representing the output file.
    """
    if not data:
        logger.warning("No data to save.")
        return

    try:
        df = pl.DataFrame(data)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(file_path)
        logger.info(f"Successfully saved {len(df)} courses to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save data to {file_path}: {e}")


async def main() -> None:
    """
    Main function to orchestrate the Coursera course scraping process using Playwright.
    Determines whether to perform a full scrape or an update based on file existence.
    """
    logger.info("Starting Coursera course scraping process with Playwright...")
    output_file_exists = OUTPUT_FILE.exists()
    num_pages_to_scrape = 0 # Default to 0, determine based on logic below

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True) # Use headless mode
            page = await browser.new_page() # Use one page for initial check

            if not output_file_exists:
                logger.info(f"Output file {OUTPUT_FILE} not found. Performing initial full scrape.")
                first_page_html = await fetch_page(page, 1)
                if first_page_html:
                    total_pages = get_total_pages(first_page_html) # Use existing parser
                    if total_pages > 0:
                        num_pages_to_scrape = total_pages
                        logger.info(f"Determined {total_pages} total pages for full scrape.")
                    else:
                        logger.warning("Could not determine total pages from first page. Falling back to update mode (first 5 pages).")
                        num_pages_to_scrape = MAX_PAGES_UPDATE
                else:
                    logger.error("Failed to fetch the first page using Playwright. Aborting scrape.")
                    return # Exit if first page fetch fails
            else:
                logger.info(f"Output file {OUTPUT_FILE} found. Scraping first {MAX_PAGES_UPDATE} pages for updates.")
                num_pages_to_scrape = MAX_PAGES_UPDATE

            await page.close() # Close the initial check page

            if num_pages_to_scrape > 0:
                logger.info(f"Proceeding to scrape {num_pages_to_scrape} pages.")
                # Pass the browser instance to the main scraping function
                scraped_data = await scrape_coursera(browser, num_pages_to_scrape)

                if scraped_data:
                    save_data(scraped_data, OUTPUT_FILE)
                else:
                    logger.warning("No data was scraped.")
            else:
                logger.warning("Number of pages to scrape is zero. No scraping will occur.")

        except PlaywrightError as e:
             logger.error(f"A Playwright error occurred during execution: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred in main: {e}")
        finally:
            if browser:
                await browser.close()
            logger.info("Playwright browser closed.")

    logger.info("Coursera scraping process finished.")


if __name__ == "__main__":
    # Ensure browser binaries are installed: Run `playwright install` in your terminal
    logger.info("Reminder: Ensure Playwright browsers are installed (`playwright install`).")
    asyncio.run(main())
