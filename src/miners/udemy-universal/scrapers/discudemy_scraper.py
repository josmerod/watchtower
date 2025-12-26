"""Discudemy.com scraper implementation.

Implements scraping logic for Discudemy.com, one of the primary
sources for free Udemy course coupons.
"""

from typing import Any

from .base import BaseScraper
from ..services.link_cleaner import LinkCleaner
from ..utils.http import fetch_page_content
from ..utils.html_parser import parse_html


class DiscudemyScraper(BaseScraper):
    """Scraper for Discudemy.com.

    Scrapes course listings from Discudemy, visits intermediate 'go' pages
    to extract the final Udemy course links.

    Usage:
        scraper = DiscudemyScraper(debug=True)
        result = scraper.scrape()
        for course in result.courses:
            print(f"{course.title} - {course.url}")
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the Discudemy scraper.

        Args:
            *args: Arguments passed to BaseScraper
            **kwargs: Keyword arguments passed to BaseScraper
        """
        super().__init__(site_code="du", site_name="Discudemy", *args, **kwargs)

        # Initialize link cleaner
        self.link_cleaner = LinkCleaner(debug=self.debug)

        # Discudemy-specific configuration
        self.base_url = "https://www.discudemy.com"
        self.pages_to_scrape = range(1, 6)  # Pages 1-5

    def scrape(self) -> Any:
        """Execute the Discudemy scraping process.

        Returns:
            ScraperResult containing found courses

        Workflow:
            1. Fetch listing pages for each page number
            2. Extract course cards from each page
            3. Visit intermediate 'go' pages to find Udemy links
            4. Clean and normalize URLs
            5. Return list of Course entities
        """
        import time
        from ..domain.models import ScraperResult

        result = ScraperResult(source=self.site_name)
        start_time = time.time()

        try:
            # Step 1: Fetch all course listings
            all_items = self._fetch_all_listings()
            result.total_found = len(all_items)

            self.log_debug(f"Found {result.total_found} courses")

            # Step 2: Process each course
            for index, item in enumerate(all_items):
                result.processed = index + 1

                title = self._extract_title(item)
                if not title:
                    continue

                # Step 3: Extract intermediate URL
                intermediate_url = item.get("href", "")
                if not intermediate_url:
                    continue

                # Step 4: Build 'go' page URL
                go_url = self._build_go_url(intermediate_url)
                if not go_url:
                    continue

                self.log_debug(f"Processing {result.processed}/{result.total_found}: {title}")

                # Step 5: Fetch 'go' page and extract Udemy link
                udemy_link = self._fetch_udemy_link(go_url)

                if udemy_link:
                    course = self.create_course(title, udemy_link)
                    result.courses.append(course)
                    self.log_debug(f"✓ Found: {title}")
                else:
                    self.log_debug(f"✗ Skipped: {title}")

        except Exception as e:
            self.log_error(f"Scraping failed: {e}")

        # Calculate duration
        result.duration = time.time() - start_time

        return result

    def _fetch_all_listings(self) -> list[Any]:
        """Fetch course listings from all pages.

        Returns:
            List of BeautifulSoup elements representing course cards
        """
        all_items = []

        for page_num in self.pages_to_scrape:
            url = f"{self.base_url}/all/{page_num}"
            self.log_debug(f"Fetching page {page_num}: {url}")

            content = self.fetch_page(url)
            if not content:
                continue

            soup = self.parse_html(content)
            page_items = soup.find_all("a", {"class": "card-header"})
            all_items.extend(page_items)

        return all_items

    def _extract_title(self, item: Any) -> str | None:
        """Extract course title from card element.

        Args:
            item: BeautifulSoup element

        Returns:
            Course title or None
        """
        if item.string:
            return item.string.strip()
        return None

    def _build_go_url(self, intermediate_url: str) -> str | None:
        """Build the 'go' page URL from intermediate URL.

        Args:
            intermediate_url: Intermediate course page URL

        Returns:
            'go' page URL or None
        """
        # Extract identifier from URL like:
        # https://www.discudemy.com/category/103/Business -> category/103/Business
        # https://www.discudemy.com/English/2 -> English/2
        url_parts = intermediate_url.split("/")
        if len(url_parts) >= 2:
            identifier = "/".join(url_parts[-2:])  # Take last two parts
            return f"{self.base_url}/go/{identifier}"

        return None

    def _fetch_udemy_link(self, go_url: str) -> str | None:
        """Fetch the Udemy course link from 'go' page.

        Args:
            go_url: URL of the 'go' intermediate page

        Returns:
            Cleaned Udemy course URL or None
        """
        content = self.fetch_page(go_url)
        if not content:
            return None

        soup = self.parse_html(content)

        # Try to find link in primary location
        link_div = soup.find("div", {"class": "ui segment"})
        if link_div and link_div.a:
            raw_link = link_div.a.get("href")
        else:
            # Fallback: try finding button with common classes
            link_tag = soup.find("a", class_=lambda x: x and any(keyword in x for keyword in ["btn", "button"]), href=True)
            if link_tag:
                raw_link = link_tag.get("href")
            else:
                return None

        # Clean the link using link cleaner service
        return self.link_cleaner.clean_link(raw_link) if raw_link else None


# Register the scraper with the factory
from .base import ScraperFactory

ScraperFactory.register("du", DiscudemyScraper)
