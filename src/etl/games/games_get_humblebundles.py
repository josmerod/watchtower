# src/etl/games/games_get_humblebundles.py
import os
import sys
import json
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("HumbleBundleETL")

# Constants
DEBUG_DIR = "data/games/debug"


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
    
    async def scrape_bundles(self) -> List[Dict[str, Any]]:
        """Scrape active bundles from Humble Bundle website using Playwright.
        
        Returns:
            List of bundle metadata dictionaries.
        """
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup
        
        all_bundles = []
        bundle_urls = [
            ("https://www.humblebundle.com/games", "games"),
            ("https://www.humblebundle.com/books", "books"),
            ("https://www.humblebundle.com/software", "software"),
            ("https://www.humblebundle.com/bundles", "all")
        ]
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
                )
                
                # Stealth: mask automation to bypass detection
                await context.add_init_script(
                    "() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }"
                )
                
                page = await context.new_page()
                
                # Visit the main site first to establish cookies
                logger.info("Visiting main Humble Bundle site to establish cookies")
                await page.goto("https://www.humblebundle.com/", timeout=60000)
                await page.wait_for_timeout(3000)
                
                for url, bundle_type in bundle_urls:
                    try:
                        logger.info(f"Scraping {bundle_type} bundles from {url}")
                        
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(8000)  # Wait longer for JS to load
                        
                        # Save page content and screenshot for debugging
                        content = await page.content()
                        debug_html_path = os.path.join(self.debug_dir, f"humble_{bundle_type}_page.html")
                        debug_screenshot_path = os.path.join(self.debug_dir, f"humble_{bundle_type}_page.png")
                        
                        with open(debug_html_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        await page.screenshot(path=debug_screenshot_path)
                        logger.info(f"Saved debug info to {debug_html_path} and {debug_screenshot_path}")
                        
                        # Parse with BeautifulSoup
                        soup = BeautifulSoup(content, "html.parser")
                        
                        # Extract bundle data from HTML
                        # Updated selectors based on actual page structure
                        bundle_elements = []
                        selectors = [
                            "div.tile, div.mosaic-tile",
                            "a[href*='/games/'], a[href*='/books/'], a[href*='/software/']",
                            "article.bundle, div.bundle-info",
                            ".bundle-card, .bundle-container",
                            "[data-product-type='bundle']"
                        ]
                        
                        for selector in selectors:
                            elements = soup.select(selector)
                            if elements:
                                logger.info(f"Found {len(elements)} bundle elements with selector '{selector}'")
                                bundle_elements.extend(elements)
                        
                        # Extract links specifically for bundles if no elements found
                        if not bundle_elements:
                            logger.info(f"No bundle elements found with selectors for {bundle_type}, trying direct link detection")
                            link_patterns = [
                                f"a[href*='/{bundle_type}/']", 
                                "a[href*='/bundle/']"
                            ]
                            
                            for pattern in link_patterns:
                                link_elements = soup.select(pattern)
                                filtered_links = []
                                
                                # Filter out non-bundle links
                                for link in link_elements:
                                    href = link.get("href", "")
                                    # Only include if link has the right structure and isn't a navigation/header link
                                    if href and not any(x in href for x in ["/store/", "/choice/", "/membership/", "/blog/", "#", "?"]):
                                        # Check if link text contains anything useful
                                        text = link.text.strip()
                                        if text and len(text) > 3 and not text.lower() in ["bundles", "games", "books", "software"]:
                                            filtered_links.append(link)
                                
                                if filtered_links:
                                    logger.info(f"Found {len(filtered_links)} potential bundle links with pattern {pattern}")
                                    bundle_elements.extend(filtered_links)
                        
                        # Extract data from bundle elements
                        bundles_found = 0
                        
                        for element in bundle_elements:
                            bundle_info = self._extract_bundle_info(element, bundle_type)
                            if bundle_info and not any(b["link"] == bundle_info["link"] for b in all_bundles):
                                all_bundles.append(bundle_info)
                                bundles_found += 1
                        
                        logger.info(f"Extracted {bundles_found} bundle(s) from {bundle_type} page")
                        
                        # Use JavaScript to find bundle data embedded in the page
                        if bundles_found == 0 or bundle_type == "all":
                            logger.info("Attempting to extract bundle data from JavaScript")
                            
                            # Evaluate script to find bundle objects via global JavaScript variables
                            js_bundles = await page.evaluate(r'''
                                () => {
                                    try {
                                        // Collect all potentially relevant variables
                                        const results = [];
                                        
                                        // Look for bundles in window.__INITIAL_STATE__
                                        if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.bundles) {
                                            results.push({
                                                source: 'INITIAL_STATE',
                                                data: window.__INITIAL_STATE__.bundles
                                            });
                                        }
                                        
                                        // Look for direct mosaic tiles
                                        if (window.mosaic && window.mosaic.tiles) {
                                            results.push({
                                                source: 'mosaic.tiles',
                                                data: window.mosaic.tiles
                                            });
                                        }
                                        
                                        // Look for product data
                                        if (window.productData) {
                                            results.push({
                                                source: 'productData',
                                                data: window.productData
                                            });
                                        }
                                        
                                        // Look for data in window.products
                                        if (window.products) {
                                            results.push({
                                                source: 'products',
                                                data: window.products
                                            });
                                        }
                                        
                                        // Create an array to hold filtered bundle URLs
                                        const bundleUrls = [];
                                        
                                        // Get all bundle links from the page
                                        const links = document.querySelectorAll('a[href*="/games/"], a[href*="/books/"], a[href*="/software/"], a[href*="/bundle/"]');
                                        links.forEach(link => {
                                            const href = link.getAttribute('href');
                                            if (href && !href.includes('/store/') && !href.includes('/choice/') && 
                                                !href.includes('#') && !href.includes('?sort=')) {
                                                
                                                // Extract title from link text or closest heading
                                                let title = link.textContent.trim();
                                                if (!title || title.length < 5) {
                                                    const heading = link.closest('div').querySelector('h1, h2, h3, h4, .title');
                                                    if (heading) {
                                                        title = heading.textContent.trim();
                                                    }
                                                }
                                                
                                                // If still no good title, try to extract from URL
                                                if (!title || title.length < 5) {
                                                    const parts = href.split('/');
                                                    if (parts.length > 1) {
                                                        const slug = parts[parts.length - 1];
                                                        title = slug.replace(/-/g, ' ').replace(/(\w)(\w*)/g, 
                                                            (g0,g1,g2) => g1.toUpperCase() + g2);
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
                                        
                                        // Add bundle URLs to results
                                        if (bundleUrls.length > 0) {
                                            results.push({
                                                source: 'bundleUrls',
                                                data: bundleUrls
                                            });
                                        }
                                        
                                        return results;
                                    } catch (e) {
                                        return [{error: e.toString()}];
                                    }
                                }
                            ''')
                            
                            if js_bundles:
                                # Save the JavaScript data for debugging
                                debug_js_path = os.path.join(self.debug_dir, f"humble_{bundle_type}_js_data.json")
                                with open(debug_js_path, "w", encoding="utf-8") as f:
                                    json.dump(js_bundles, f, indent=2)
                                
                                for result in js_bundles:
                                    source = result.get("source", "unknown")
                                    data = result.get("data", [])
                                    
                                    if source == "bundleUrls" and isinstance(data, list):
                                        for bundle_url in data:
                                            if not isinstance(bundle_url, dict):
                                                continue
                                            
                                            url = bundle_url.get("url", "")
                                            title = bundle_url.get("title", "")
                                            price = bundle_url.get("price", "Pay what you want")
                                            
                                            if url and title and not any(b["link"] == url for b in all_bundles):
                                                # Determine the correct bundle type from URL
                                                detected_type = self._determine_bundle_type(url)
                                                
                                                # Extract a better title from the URL if needed
                                                if title == "Pay What You Want" or len(title) < 5:
                                                    title = self._extract_title_from_url(url)
                                                
                                                all_bundles.append({
                                                    "title": title,
                                                    "link": url,
                                                    "end_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
                                                    "price": price,
                                                    "games": [],
                                                    "type": detected_type
                                                })
                                    
                                    elif isinstance(data, list):
                                        for bundle in data:
                                            if not isinstance(bundle, dict):
                                                continue
                                            
                                            bundle_info = self._extract_bundle_from_js_object(bundle, bundle_type)
                                            if bundle_info and not any(b["link"] == bundle_info["link"] for b in all_bundles):
                                                all_bundles.append(bundle_info)
                                    
                                    elif isinstance(data, dict) and "bundles" in data and isinstance(data["bundles"], list):
                                        for bundle in data["bundles"]:
                                            if not isinstance(bundle, dict):
                                                continue
                                            
                                            bundle_info = self._extract_bundle_from_js_object(bundle, bundle_type)
                                            if bundle_info and not any(b["link"] == bundle_info["link"] for b in all_bundles):
                                                all_bundles.append(bundle_info)
                    
                    except Exception as e:
                        logger.error(f"Error scraping {bundle_type} bundles: {e}")
                
                # Post-process all bundles to fix titles and types
                self._post_process_bundles(all_bundles)
                
                await browser.close()
        
        except Exception as e:
            logger.error(f"Error in scrape_bundles: {str(e)}")
        
        # If no bundles were found with any method, create a placeholder entry
        if not all_bundles:
            logger.warning("All scraping methods failed. Creating placeholder bundle.")
            all_bundles = [{
                "title": "Humble Bundle Scraping Failed",
                "link": "https://www.humblebundle.com/",
                "end_date": datetime.now(timezone.utc).isoformat(),
                "price": "Unknown",
                "games": ["Scraping Failed - Check https://www.humblebundle.com/ directly"],
                "type": "error",
                "note": "Automatic scraping failed. Please visit the Humble Bundle website to see current bundles."
            }]
        
        logger.info(f"Retrieved a total of {len(all_bundles)} bundles")
        return all_bundles
    
    def _post_process_bundles(self, bundles: List[Dict[str, Any]]) -> None:
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
        path = parsed_url.path.strip('/')
        
        # Split the path into components
        path_parts = path.split('/')
        
        # Get the last part (usually the bundle slug)
        if len(path_parts) >= 2:
            slug = path_parts[-1]
            
            # Remove query parameters if present
            if '?' in slug:
                slug = slug.split('?')[0]
            
            # Clean and format the slug as a title
            if slug:
                # Replace hyphens with spaces and capitalize words
                title = slug.replace('-', ' ').title()
                
                # Clean up bundle-specific words that are redundant
                title = re.sub(r'\bBundle\b', '', title).strip()
                
                return title
        
        # Fallback: try to extract from URL query parameters
        query_params = parse_qs(parsed_url.query)
        for param_name in ['c', 'hmb_campaign']:
            if param_name in query_params:
                param_value = query_params[param_name][0]
                # Look for patterns in campaign parameters
                match = re.search(r'c_([a-zA-Z0-9_]+)_bundle', param_value)
                if match:
                    # Extract and clean up the bundle name
                    bundle_name = match.group(1)
                    bundle_name = bundle_name.replace('_', ' ').title()
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
    
    def _extract_bundle_info(self, element, bundle_type: str) -> Optional[Dict[str, Any]]:
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
                    if href.startswith('/'):
                        link = f"https://www.humblebundle.com{href}"
                    else:
                        link = href
            else:
                link_elem = element.select_one("a")
                if link_elem and link_elem.get("href"):
                    href = link_elem.get("href")
                    if href.startswith('/'):
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
                ".product-title"
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
                    title = title.split('\n')[0].strip()
            
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
            
            # End date is rarely available in HTML
            # Use a default end date 2 weeks from now
            end_date = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
            
            # We'd need to visit individual bundle pages for the game list
            # which is resource-intensive
            games = []
            
            return {
                "title": title,
                "link": link,
                "end_date": end_date,
                "price": price,
                "games": games,
                "type": actual_type
            }
        
        except Exception as e:
            logger.debug(f"Failed to extract bundle info: {str(e)}")
            return None
    
    def _extract_bundle_from_js_object(self, bundle: Dict[str, Any], bundle_type: str) -> Optional[Dict[str, Any]]:
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
                "product_human_name", "fullName", "display_name", "human_name", 
                "title", "name", "heading"
            ]
            for key in title_keys:
                if key in bundle and bundle[key] and isinstance(bundle[key], str):
                    title = bundle[key].strip()
                    break
            
            # If no title found or title looks like a machine name, try to extract from URL/machine_name
            if not title or (title and (len(title) < 5 or '_' in title or title.islower())):
                # Try to get a better title from the machine_name or URL
                machine_name = None
                for key in ["machine_name", "url", "urlName", "slug"]:
                    if key in bundle and bundle[key]:
                        machine_name = bundle[key]
                        break
                        
                if machine_name:
                    # Convert machine_name to a more readable format
                    title = machine_name.replace('_', ' ').replace('-', ' ').title()
                    # Remove common suffixes
                    title = re.sub(r'\s+Bundle$', '', title, flags=re.IGNORECASE)
            
            if not title:
                return None
            
            # Extract URL
            link = None
            url_keys = ["url", "machine_name", "urlName", "human_url", "url_path"]
            
            for key in url_keys:
                if key in bundle and bundle[key]:
                    url_val = bundle[key]
                    if isinstance(url_val, str):
                        if url_val.startswith('/'):
                            link = f"https://www.humblebundle.com{url_val}"
                        elif url_val.startswith('http'):
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
                if key in bundle and bundle[key]:
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
            
            if not end_date:
                end_date = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
            
            # Extract price
            price = "Pay what you want"
            price_keys = ["human_price", "price", "starting_price", "displayPrice"]
            for key in price_keys:
                if key in bundle and bundle[key]:
                    price_val = bundle[key]
                    if isinstance(price_val, str):
                        price = price_val
                    else:
                        price = f"${price_val}"
                    break
            
            # Extract games/content items
            games = []
            
            # Look in various places for content items
            content_paths = [
                "items",
                "contents",
                "tier_items",
                "products"
            ]
            
            for path in content_paths:
                if path in bundle and isinstance(bundle[path], list):
                    for item in bundle[path]:
                        if isinstance(item, dict):
                            for name_key in ["human_name", "name", "title", "display_name"]:
                                if name_key in item and item[name_key]:
                                    games.append(item[name_key])
                                    break
            
            # Check for tiers with games
            if "tiers" in bundle and isinstance(bundle["tiers"], list):
                for tier in bundle["tiers"]:
                    if isinstance(tier, dict) and "items" in tier and isinstance(tier["items"], list):
                        for item in tier["items"]:
                            if isinstance(item, dict):
                                for name_key in ["human_name", "name", "title", "display_name"]:
                                    if name_key in item and item[name_key]:
                                        games.append(item[name_key])
                                        break
            
            return {
                "title": title,
                "link": link,
                "end_date": end_date,
                "price": price,
                "games": games,
                "type": actual_type
            }
        
        except Exception as e:
            logger.debug(f"Failed to extract bundle from JS object: {str(e)}")
            return None


def save_humblebundle_bundles(bundles: List[Dict[str, Any]]) -> None:
    """
    Saves Humble Bundle data to JSON and CSV in the data/games directory.

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

    import pandas as pd  # type: ignore
    df = pd.DataFrame(bundles)
    df.to_csv(csv_path, index=False)

    logger.info(f"Saved Humble Bundle data to {json_path} and {csv_path}")


async def get_humblebundle_data_async() -> List[Dict[str, Any]]:
    """
    Asynchronously fetches active bundles from Humble Bundle via web scraping.
    
    Returns:
        List of bundle metadata dictionaries.
    """
    scraper = HumbleBundleScraper()
    return await scraper.scrape_bundles()


def get_humblebundle_data() -> List[Dict[str, Any]]:
    """
    Fetches active bundles from Humble Bundle via web scraping.
    
    Returns:
        List of bundle metadata dictionaries.
    """
    try:
        # On Windows, use the ProactorEventLoop policy
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        return asyncio.run(get_humblebundle_data_async())
    except Exception as e:
        logger.error(f"Error in get_humblebundle_data: {str(e)}")
        
        # Return placeholder bundle data in case of failure
        return [{
            "title": "Humble Bundle Scraping Failed",
            "link": "https://www.humblebundle.com/",
            "end_date": datetime.now(timezone.utc).isoformat(),
            "price": "Unknown",
            "games": ["Scraping Failed - Check https://www.humblebundle.com/ directly"],
            "type": "error",
            "note": "Automatic scraping failed. Please visit the Humble Bundle website to see current bundles."
        }]


async def main_async() -> None:
    """Asynchronous main entry point for the script."""
    logger.info("Starting Humble Bundle ETL process")
    
    try:
        bundles = await get_humblebundle_data_async()
        save_humblebundle_bundles(bundles)
        logger.info("Humble Bundle ETL process completed successfully")
    except Exception as e:
        logger.error(f"Error during Humble Bundle ETL process: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the Humble Bundle ETL process."""
    logger.info("Starting Humble Bundle ETL process")
    
    try:
        # On Windows, use the ProactorEventLoop policy
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 