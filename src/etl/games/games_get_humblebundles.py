"""ETL module for scraping and processing Humble Bundle data.

This module uses Playwright to scrape active game, book, and software
bundles from the Humble Bundle website. The scraped data is then
processed and saved into JSON and CSV files.

Each listing page embeds an object per bundle (title, URL, end date, item count, the first item titles). The
ETL reads those; reading the tiles alone gave a title and "Pay what you want", and nothing else.
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT

# Ensure project root is on path
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("HumbleBundleETL")

# Constants
DEBUG_DIR = "data/games/debug"
BUNDLE_TYPES = ("games", "books", "software")
HUMBLE = "https://www.humblebundle.com"

# Next.js ships the page's data as self.__next_f.push([1, "<escaped text>"]); the capture is the JS string's content
_FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')


def _objects_holding(text: str, key: str) -> list[dict[str, Any]]:
    """Every JSON object of *text* that holds *key*, as Python data, in document order.

    One pass keeps the open brackets on a stack and skips whatever lies inside strings, so a brace inside a
    title misleads nothing: at ``"key"`` the innermost open object is the one wanted, and it is read out when
    it closes. One that is not complete JSON is dropped: a bundle is missed, never malformed.
    """
    wanted = f'"{key}"'
    objects: list[dict[str, Any]] = []
    stack: list[list] = []  # [bracket, where it opened, holds the key]
    quoted = escaped = False
    for index, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            if text.startswith(wanted, index):
                for bracket in reversed(stack):
                    if bracket[0] == "{":
                        bracket[2] = True
                        break
            quoted = True
        elif char in "{[":
            stack.append([char, index, False])
        elif char in "}]" and stack:
            bracket = stack.pop()
            if bracket[0] == "{" and bracket[2]:
                try:
                    objects.append(json.loads(text[bracket[1] : index + 1]))
                except ValueError:
                    pass
    return objects


def _iso_utc(value: Any) -> str | None:
    """A date the page states, as ISO in UTC; ``None`` when it states none or in a form not understood."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def _count(value: Any) -> int | None:
    """A whole number the page states (as text or as a number); ``None`` for anything else."""
    return int(value) if isinstance(value, int) or (isinstance(value, str) and value.isdigit()) else None


def embedded_bundles(content: str) -> list[dict[str, Any]]:
    """The records for the bundles a listing page embeds for its tiles, one per URL, in page order."""
    chunks = []
    for chunk in _FLIGHT_CHUNK.findall(content):
        try:
            chunks.append(json.loads(f'"{chunk}"'))
        except ValueError:
            continue
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for obj in _objects_holding("".join(chunks), "productType"):
        if not isinstance(obj, dict) or obj.get("productType") != "humble-bundle":
            continue
        url, titles = obj.get("url"), obj.get("includedItemTitles")
        if not isinstance(url, str) or not url.startswith("/") or not isinstance(titles, list):
            continue
        link = HUMBLE + url
        if link in seen:
            continue
        seen.add(link)
        category = obj.get("category")
        stated = obj.get("title")
        title = stated.strip() if isinstance(stated, str) else ""
        records.append(
            {
                "title": title or urlparse(url).path.strip("/").rsplit("/", 1)[-1].replace("-", " ").title(),
                "link": link,
                # The date the page states, or none. It used to be "now + 14 days" for every bundle.
                "end_date": _iso_utc(obj.get("endDate")),
                "price": "Pay what you want",  # how every tile opens
                # The page lists the first items only (eleven at most); the count is the bundle's own
                "games": [t.strip() for t in titles if isinstance(t, str) and t.strip()],
                "items_count": _count(obj.get("itemsCount")),
                "type": category if category in BUNDLE_TYPES else _type_of(link),
            }
        )
    return records


def _type_of(link: str) -> str:
    """The bundle type a Humble URL names."""
    for bundle_type in BUNDLE_TYPES:
        if f"/{bundle_type}/" in link:
            return bundle_type
    return "unknown"


class HumbleBundleScraper:
    """Scraper for retrieving bundle data from Humble Bundle."""

    def __init__(self):
        """Initialize the scraper."""
        project_root = get_project_root()
        self.output_dir = os.path.join(project_root, "data/games")
        ensure_directories(["data/games"])

        # Ensure debug directory exists
        self.debug_dir = os.path.join(project_root, DEBUG_DIR)
        ensure_directories([DEBUG_DIR])

    async def _setup_playwright(self, playwright):
        """Sets up the Playwright browser and context."""
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=SCRAPER_DEFAULT_USER_AGENT,
        )
        await context.add_init_script("() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }")
        return browser, context

    async def _navigate_and_debug_page(self, page, url: str, bundle_type: str):
        """Navigates to a URL, waits, and saves debug information."""
        logger.info(f"Scraping {bundle_type} bundles from {url}")
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(8000)  # Wait longer for JS to load

        content = await page.content()
        debug_html_path = os.path.join(self.debug_dir, f"humble_{bundle_type}_page.html")
        debug_screenshot_path = os.path.join(self.debug_dir, f"humble_{bundle_type}_page.png")
        with open(debug_html_path, "w", encoding="utf-8") as f:
            f.write(content)
        await page.screenshot(path=debug_screenshot_path)
        logger.info(f"Saved debug info to {debug_html_path} and {debug_screenshot_path}")
        return content

    def _extract_bundles_with_bs(self, soup, bundle_type: str, all_bundles: list):
        """Extracts bundle elements from HTML content using BeautifulSoup."""
        bundle_elements = []
        selectors = [
            "div.tile, div.mosaic-tile",
            "a[href*='/games/'], a[href*='/books/'], a[href*='/software/']",
            "article.bundle, div.bundle-info",
            ".bundle-card, .bundle-container",
            "[data-product-type='bundle']",
        ]
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Found {len(elements)} bundle elements with selector '{selector}'")
                bundle_elements.extend(elements)

        if not bundle_elements:
            logger.info(f"No bundle elements found with selectors for {bundle_type}, trying direct link detection")
            link_patterns = [f"a[href*='/{bundle_type}/']", "a[href*='/bundle/']"]
            for pattern in link_patterns:
                link_elements = soup.select(pattern)
                filtered_links = []
                for link in link_elements:
                    href = link.get("href", "")
                    if href and not any(
                        x in href
                        for x in [
                            "/store/",
                            "/choice/",
                            "/membership/",
                            "/blog/",
                            "#",
                            "?",
                        ]
                    ):
                        text = link.text.strip()
                        if text and len(text) > 3 and text.lower() not in ["bundles", "games", "books", "software"]:
                            filtered_links.append(link)
                if filtered_links:
                    logger.info(f"Found {len(filtered_links)} potential bundle links with pattern {pattern}")
                    bundle_elements.extend(filtered_links)

        bundles_found_bs = 0
        for element in bundle_elements:
            bundle_info = self._extract_bundle_info(element, bundle_type)
            if bundle_info and not any(b["link"] == bundle_info["link"] for b in all_bundles):
                all_bundles.append(bundle_info)
                bundles_found_bs += 1
        logger.info(f"Extracted {bundles_found_bs} bundle(s) from {bundle_type} page via BeautifulSoup")
        return bundles_found_bs

    async def _extract_bundles_from_js(self, page, bundle_type: str, all_bundles: list):
        """Extracts bundle data embedded in JavaScript variables on the page."""
        logger.info(f"Attempting to extract bundle data from JavaScript for {bundle_type}")
        js_bundles_data = await page.evaluate(r"""
            () => {
                try {
                    const results = [];
                    if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.bundles) {
                        results.push({ source: 'INITIAL_STATE', data: window.__INITIAL_STATE__.bundles });
                    }
                    if (window.mosaic && window.mosaic.tiles) {
                        results.push({ source: 'mosaic.tiles', data: window.mosaic.tiles });
                    }
                    if (window.productData) {
                        results.push({ source: 'productData', data: window.productData });
                    }
                    if (window.products) {
                        results.push({ source: 'products', data: window.products });
                    }
                    const bundleUrls = [];
                    const links = document.querySelectorAll('a[href*="/games/"], a[href*="/books/"], a[href*="/software/"], a[href*="/bundle/"]');
                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href && !href.includes('/store/') && !href.includes('/choice/') &&
                            !href.includes('#') && !href.includes('?sort=')) {
                            let title = link.textContent.trim();
                            if (!title || title.length < 5) {
                                const heading = link.closest('div')?.querySelector('h1, h2, h3, h4, .title');
                                if (heading) title = heading.textContent.trim();
                            }
                            if (!title || title.length < 5) {
                                const parts = href.split('/');
                                if (parts.length > 1) {
                                    const slug = parts[parts.length - 1];
                                    title = slug.replace(/-/g, ' ').replace(/(\w)(\w*)/g, (g0,g1,g2) => g1.toUpperCase() + g2);
                                }
                            }
                            if (title && title.length > 5) {
                                bundleUrls.push({
                                    url: href.startsWith('/') ? 'https://www.humblebundle.com' + href : href,
                                    title: title,
                                    price: 'Pay what you want'
                                });
                            }
                        }
                    });
                    if (bundleUrls.length > 0) results.push({ source: 'bundleUrls', data: bundleUrls });
                    return results;
                } catch (e) { return [{error: e.toString()}]; }
            }
        """)

        if js_bundles_data:
            debug_js_path = os.path.join(self.debug_dir, f"humble_{bundle_type}_js_data.json")
            with open(debug_js_path, "w", encoding="utf-8") as f:
                json.dump(js_bundles_data, f, indent=2)

            for result in js_bundles_data:
                source = result.get("source", "unknown")
                data = result.get("data", [])
                if source == "bundleUrls" and isinstance(data, list):
                    for bundle_url_data in data:
                        if not isinstance(bundle_url_data, dict):
                            continue
                        url, title, price = (
                            bundle_url_data.get("url"),
                            bundle_url_data.get("title"),
                            bundle_url_data.get("price", "Pay what you want"),
                        )
                        if url and title and not any(b["link"] == url for b in all_bundles):
                            detected_type = self._determine_bundle_type(url)
                            if title == "Pay What You Want" or len(title) < 5:
                                title = self._extract_title_from_url(url)
                            all_bundles.append(
                                {
                                    "title": title,
                                    "link": url,
                                    "price": price,
                                    "games": [],
                                    "type": detected_type,
                                    "end_date": None,  # a link states no date
                                }
                            )
                elif isinstance(data, list):
                    for bundle_item in data:
                        if not isinstance(bundle_item, dict):
                            continue
                        bundle_info = self._extract_bundle_from_js_object(bundle_item, bundle_type)
                        if bundle_info and not any(b["link"] == bundle_info["link"] for b in all_bundles):
                            all_bundles.append(bundle_info)
                elif isinstance(data, dict) and "bundles" in data and isinstance(data["bundles"], list):
                    for bundle_item in data["bundles"]:
                        if not isinstance(bundle_item, dict):
                            continue
                        bundle_info = self._extract_bundle_from_js_object(bundle_item, bundle_type)
                        if bundle_info and not any(b["link"] == bundle_info["link"] for b in all_bundles):
                            all_bundles.append(bundle_info)
        logger.info(f"Processed JS data for {bundle_type}, current total bundles: {len(all_bundles)}")

    async def _process_single_bundle_url(self, page, url: str, bundle_type: str, all_bundles: list):
        """Processes a single Humble Bundle URL (games, books, etc.) to find bundles."""
        from bs4 import BeautifulSoup

        try:
            content = await self._navigate_and_debug_page(page, url, bundle_type)
            embedded = [b for b in embedded_bundles(content) if not any(known["link"] == b["link"] for known in all_bundles)]
            all_bundles.extend(embedded)
            if embedded:
                logger.info(f"Read {len(embedded)} new bundle(s) from the data embedded in the {bundle_type} page")
                return

            # No embedded data: the page changed shape. Read its markup instead, which states much less.
            logger.warning(f"The {bundle_type} page embeds no bundle data; falling back to its markup")
            soup = BeautifulSoup(content, "html.parser")

            bundles_found_bs = self._extract_bundles_with_bs(soup, bundle_type, all_bundles)

            if bundles_found_bs == 0 or bundle_type == "all":  # "all" type might have more JS data
                await self._extract_bundles_from_js(page, bundle_type, all_bundles)
        except Exception as e:  # broad by design: Playwright scraping of external site (unpredictable page/DOM failures)
            logger.error(f"Error scraping {bundle_type} bundles from {url}: {e}")

    async def scrape_bundles(self) -> list[dict[str, Any]]:
        """Scrape active bundles from Humble Bundle website using Playwright.

        Returns:
            List of bundle metadata dictionaries.
        """
        from playwright.async_api import async_playwright

        all_bundles: list[dict[str, Any]] = []
        bundle_sources = [
            ("https://www.humblebundle.com/games", "games"),
            ("https://www.humblebundle.com/books", "books"),
            ("https://www.humblebundle.com/software", "software"),
            ("https://www.humblebundle.com/bundles", "all"),  # General bundles page
        ]

        browser = None
        context = None
        page = None

        try:
            async with async_playwright() as p_manager:
                browser, context = await self._setup_playwright(p_manager)
                page = await context.new_page()

                logger.info("Visiting main Humble Bundle site to establish cookies")
                await page.goto("https://www.humblebundle.com/", timeout=60000)
                await page.wait_for_timeout(3000)  # Allow cookies to settle

                for url, bundle_type in bundle_sources:
                    await self._process_single_bundle_url(page, url, bundle_type, all_bundles)

            self._post_process_bundles(all_bundles)

        except Exception as e:  # broad by design: Playwright scraping of external site (unpredictable page/DOM failures)
            logger.error(f"Error in scrape_bundles main try-block: {e!s}", exc_info=True)
        finally:
            if page:
                try:
                    await page.close()
                except Exception:  # broad by design: Playwright best-effort cleanup
                    pass
            if context:
                try:
                    await context.close()
                except Exception:  # broad by design: Playwright best-effort cleanup
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:  # broad by design: Playwright best-effort cleanup
                    pass

        if not all_bundles:
            logger.warning("All scraping methods failed. Creating placeholder bundle.")
            all_bundles = [
                {
                    "title": "Humble Bundle Scraping Failed",
                    "link": "https://www.humblebundle.com/",
                    "end_date": datetime.now(timezone.utc).isoformat(),
                    "price": "Unknown",
                    "games": ["Scraping Failed - Check https://www.humblebundle.com/ directly"],
                    "type": "error",
                    "note": "Automatic scraping failed. Please visit the Humble Bundle website to see current bundles.",
                }
            ]

        logger.info(f"Retrieved a total of {len(all_bundles)} bundles")
        return all_bundles

    def _post_process_bundles(self, bundles: list[dict[str, Any]]) -> None:
        """Post-process bundles to fix issues with titles and types.

        Args:
            bundles: List of bundle dictionaries to process
        """
        for bundle in bundles:
            # Fix the bundle type based on the link if needed
            if "link" in bundle:
                url = bundle["link"]

                # Fix incorrect type assignments
                if "/games/" in url and bundle.get("type") != "games":
                    bundle["type"] = "games"
                elif "/books/" in url and bundle.get("type") != "books":
                    bundle["type"] = "books"
                elif "/software/" in url and bundle.get("type") != "software":
                    bundle["type"] = "software"

                # Fix missing or generic titles
                if bundle.get("title", "") in ["Pay What You Want", ""]:
                    better_title = self._extract_title_from_url(url)
                    if better_title:
                        bundle["title"] = better_title

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from a URL.

        Args:
            url: URL to extract title from

        Returns:
            Extracted title
        """
        # Parse the URL
        parsed_url = urlparse(url)
        path = parsed_url.path.strip("/")

        # Split the path into components
        path_parts = path.split("/")

        # Get the last part (usually the bundle slug)
        if len(path_parts) >= 2:
            slug = path_parts[-1]

            # Remove query parameters if present
            if "?" in slug:
                slug = slug.split("?")[0]

            # Clean and format the slug as a title
            if slug:
                # Replace hyphens with spaces and capitalize words
                title = slug.replace("-", " ").title()

                # Clean up bundle-specific words that are redundant
                title = re.sub(r"\bBundle\b", "", title).strip()

                return title

        # Fallback: try to extract from URL query parameters
        query_params = parse_qs(parsed_url.query)
        for param_name in ["c", "hmb_campaign"]:
            if param_name in query_params:
                param_value = query_params[param_name][0]
                # Look for patterns in campaign parameters
                match = re.search(r"c_([a-zA-Z0-9_]+)_bundle", param_value)
                if match:
                    # Extract and clean up the bundle name
                    bundle_name = match.group(1)
                    bundle_name = bundle_name.replace("_", " ").title()
                    return bundle_name

        # If nothing else worked, return the domain name
        return "Humble Bundle"

    def _determine_bundle_type(self, url: str) -> str:
        """Determine bundle type from URL."""
        if "/games/" in url:
            return "games"
        elif "/books/" in url:
            return "books"
        elif "/software/" in url:
            return "software"
        else:
            return "unknown"

    def _extract_bundle_info(self, element, bundle_type: str) -> dict[str, Any] | None:
        """Extract bundle information from an HTML element.

        Args:
            element: BeautifulSoup element containing bundle info
            bundle_type: Type of bundle (games, books, software)

        Returns:
            Bundle metadata dictionary or None if extraction failed
        """
        try:
            # Extract link first (we need it for title fallback)
            link = None
            if element.name == "a":
                href = element.get("href", "")
                if href:
                    if href.startswith("/"):
                        link = f"https://www.humblebundle.com{href}"
                    else:
                        link = href
            else:
                link_elem = element.select_one("a")
                if link_elem and link_elem.get("href"):
                    href = link_elem.get("href")
                    if href.startswith("/"):
                        link = f"https://www.humblebundle.com{href}"
                    else:
                        link = href

            if not link:
                return None

            # Determine actual bundle type from the URL
            actual_type = self._determine_bundle_type(link)
            if actual_type == "unknown":
                # Only keep bundles with known types
                if bundle_type != "all":
                    actual_type = bundle_type
                else:
                    return None

            # Ensure link is related to bundles
            if not any(x in link for x in ["/games/", "/books/", "/software/", "/bundle/"]):
                return None

            # Avoid store and homepage links
            if any(x in link for x in ["/store/", "/choice/", "/membership/", "/blog/"]):
                return None

            # Extract title with multiple selectors and priority
            title = None

            # Try more specific title selectors first
            for selector in [
                ".header-title",
                ".bundle-title",
                ".heading-title",
                "h1.title",
                "h2.title",
                ".mosaic-title",
                ".product-title",
            ]:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.text.strip()
                    break

            # If not found, try broader selectors
            if not title:
                title_elem = element.select_one("h1, h2, h3, h4, .title, .heading, strong")
                if title_elem:
                    title = title_elem.text.strip()

            # If element is an anchor and no specific title found, use text content
            if not title and element.name == "a":
                title = element.text.strip()
                if title:
                    # Clean up title if needed
                    title = title.split("\n")[0].strip()

            # If title contains price-like text, it's probably not the real title
            if not title or len(title) < 3 or title.lower() in ["pay what you want", "from", "bundle"]:
                # Extract title from URL as fallback
                title = self._extract_title_from_url(link)

            if not title or len(title) < 3:  # Skip very short titles
                return None

            # Extract price
            price = "Pay what you want"
            price_elem = element.select_one(".price, .pricing, [class*='price']")
            if price_elem:
                price_text = price_elem.text.strip()
                if price_text:
                    price = price_text

            # The tile states no end date. It used to be set to two weeks ahead for every bundle; a date the
            # page did not give stays empty.
            end_date = None

            # We'd need to visit individual bundle pages for the game list
            # which is resource-intensive
            games: list[str] = []

            return {
                "title": title,
                "link": link,
                "end_date": end_date,
                "price": price,
                "games": games,
                "type": actual_type,
            }

        except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
            logger.debug(f"Failed to extract bundle info: {e!s}")
            return None

    def _extract_bundle_from_js_object(self, bundle: dict[str, Any], bundle_type: str) -> dict[str, Any] | None:
        """Extract bundle information from a JavaScript object.

        Args:
            bundle: Bundle data from JS object
            bundle_type: Type of bundle (games, books, software)

        Returns:
            Bundle metadata dictionary or None if extraction failed
        """
        try:
            # Extract title with higher priority for descriptive fields
            title = None
            title_keys = [
                "product_human_name",
                "fullName",
                "display_name",
                "human_name",
                "title",
                "name",
                "heading",
            ]
            for key in title_keys:
                if key in bundle and bundle[key] and isinstance(bundle[key], str):
                    title = bundle[key].strip()
                    break

            # If no title found or title looks like a machine name, try to extract from URL/machine_name
            if not title or (title and (len(title) < 5 or "_" in title or title.islower())):
                # Try to get a better title from the machine_name or URL
                machine_name = None
                for key in ["machine_name", "url", "urlName", "slug"]:
                    if bundle.get(key):
                        machine_name = bundle[key]
                        break

                if machine_name:
                    # Convert machine_name to a more readable format
                    title = machine_name.replace("_", " ").replace("-", " ").title()
                    # Remove common suffixes
                    title = re.sub(r"\s+Bundle$", "", title, flags=re.IGNORECASE)

            if not title:
                return None

            # Extract URL
            link = None
            url_keys = ["url", "machine_name", "urlName", "human_url", "url_path"]

            for key in url_keys:
                if bundle.get(key):
                    url_val = bundle[key]
                    if isinstance(url_val, str):
                        if url_val.startswith("/"):
                            link = f"https://www.humblebundle.com{url_val}"
                        elif url_val.startswith("http"):
                            link = url_val
                        else:
                            # Default to the bundle type we're currently processing
                            actual_type = bundle_type
                            if bundle_type == "all":
                                # Try to determine bundle type from object
                                if "product_machine_name" in bundle:
                                    product_name = bundle["product_machine_name"]
                                    if "book" in product_name:
                                        actual_type = "books"
                                    elif "software" in product_name:
                                        actual_type = "software"
                                    else:
                                        actual_type = "games"

                            link = f"https://www.humblebundle.com/{actual_type}/{url_val}"
                        break

            if not link:
                return None

            # Determine the actual bundle type from the URL
            actual_type = self._determine_bundle_type(link)
            if actual_type == "unknown" and bundle_type != "all":
                actual_type = bundle_type

            # Extract end date
            end_date = None
            date_keys = ["end_date", "endDate", "expiry_date", "expiresAt"]
            for key in date_keys:
                if bundle.get(key):
                    try:
                        # Handle different date formats
                        date_val = bundle[key]
                        if isinstance(date_val, int) or (isinstance(date_val, str) and date_val.isdigit()):
                            # Unix timestamp
                            end_ts = int(date_val)
                            end_date = datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()
                        elif isinstance(date_val, str):
                            # ISO format string
                            end_date = datetime.fromisoformat(date_val).isoformat()
                        break
                    except (ValueError, TypeError):
                        pass

            # Extract price
            price = "Pay what you want"
            price_keys = ["human_price", "price", "starting_price", "displayPrice"]
            for key in price_keys:
                if bundle.get(key):
                    price_val = bundle[key]
                    if isinstance(price_val, str):
                        price = price_val
                    else:
                        price = f"${price_val}"
                    break

            # Extract games/content items
            games = []

            # Look in various places for content items
            content_paths = ["items", "contents", "tier_items", "products"]

            for path in content_paths:
                if path in bundle and isinstance(bundle[path], list):
                    for item in bundle[path]:
                        if isinstance(item, dict):
                            for name_key in [
                                "human_name",
                                "name",
                                "title",
                                "display_name",
                            ]:
                                if item.get(name_key):
                                    games.append(item[name_key])
                                    break

            # Check for tiers with games
            if "tiers" in bundle and isinstance(bundle["tiers"], list):
                for tier in bundle["tiers"]:
                    if isinstance(tier, dict) and "items" in tier and isinstance(tier["items"], list):
                        for item in tier["items"]:
                            if isinstance(item, dict):
                                for name_key in [
                                    "human_name",
                                    "name",
                                    "title",
                                    "display_name",
                                ]:
                                    if item.get(name_key):
                                        games.append(item[name_key])
                                        break

            return {
                "title": title,
                "link": link,
                "end_date": end_date,
                "price": price,
                "games": games,
                "type": actual_type,
            }

        except Exception as e:  # broad by design: JS-object bundle extraction from scraped page
            logger.debug(f"Failed to extract bundle from JS object: {e!s}")
            return None


def save_humblebundle_bundles(bundles: list[dict[str, Any]]) -> None:
    """Saves Humble Bundle data to JSON and CSV in the data/games directory.

    Args:
        bundles: List of bundle metadata dictionaries.
    """
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/games")
    ensure_directories(["data/games"])

    json_path = os.path.join(output_dir, "humblebundles.json")
    csv_path = os.path.join(output_dir, "humblebundles.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(bundles, f, indent=2)

    import pandas as pd

    df = pd.DataFrame(bundles)
    df.to_csv(csv_path, index=False)

    logger.info(f"Saved Humble Bundle data to {json_path} and {csv_path}")


async def get_humblebundle_data_async() -> list[dict[str, Any]]:
    """Asynchronously fetches active bundles from Humble Bundle via web scraping.

    Returns:
        List of bundle metadata dictionaries.
    """
    scraper = HumbleBundleScraper()
    return await scraper.scrape_bundles()


def get_humblebundle_data() -> list[dict[str, Any]]:
    """Fetches active bundles from Humble Bundle via web scraping.

    Returns:
        List of bundle metadata dictionaries.
    """
    try:
        # On Windows, use the ProactorEventLoop policy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        return asyncio.run(get_humblebundle_data_async())
    except Exception as e:  # broad by design: asyncio entry point incl. event-loop policy setup
        logger.error(f"Error in get_humblebundle_data: {e!s}")

        # Return placeholder bundle data in case of failure
        return [
            {
                "title": "Humble Bundle Scraping Failed",
                "link": "https://www.humblebundle.com/",
                "end_date": datetime.now(timezone.utc).isoformat(),
                "price": "Unknown",
                "games": ["Scraping Failed - Check https://www.humblebundle.com/ directly"],
                "type": "error",
                "note": "Automatic scraping failed. Please visit the Humble Bundle website to see current bundles.",
            }
        ]


async def main_async() -> None:
    """Asynchronous main entry point for the script."""
    logger.info("Starting Humble Bundle ETL process")

    try:
        bundles = await get_humblebundle_data_async()
        save_humblebundle_bundles(bundles)
        logger.info("Humble Bundle ETL process completed successfully")
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Error during Humble Bundle ETL process: {e!s}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the Humble Bundle ETL process."""
    logger.info("Starting Humble Bundle ETL process")

    try:
        # On Windows, use the ProactorEventLoop policy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:  # broad by design: script entry point
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
