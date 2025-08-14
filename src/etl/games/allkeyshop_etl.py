"""AllKeyShop ETL Module

This module fetches and processes game data from AllKeyShop using Playwright.
It retrieves both new releases and game offers under 10 EUR from AllKeyShop.

Usage:
    python src/etl/games/allkeyshop_etl.py

Output:
    - JSON file: data/games/allkeyshop.json
    - CSV file: data/games/allkeyshop.csv
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright

# Add the project root to the path to ensure imports work correctly
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("AllKeyShopETL")

# AllKeyShop URLs - Updated to use the actual game listing pages
NEW_RELEASES_URL = "https://www.allkeyshop.com/blog/catalogue/category-action/?condition=new&sort_by=price&way=asc"
OFFERS_URL = "https://www.allkeyshop.com/blog/catalogue/category-action/?sort_by=price&way=asc&price_from=0&price_to=10"


def parse_price(price_text: str) -> float:
    """Parse price text and extract numeric value."""
    if not price_text:
        return 0.0

    # Remove currency symbols and clean up
    price_text = re.sub(r"[€$£¥₹]", "", price_text)
    price_text = re.sub(r"[^\\d.,]", "", price_text)

    # Handle different decimal separators
    if "," in price_text and "." in price_text:
        # Format like 1,234.56
        price_text = price_text.replace(",", "")
    elif "," in price_text:
        # Check if it's a decimal separator or thousands separator
        parts = price_text.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Decimal separator
            price_text = price_text.replace(",", ".")
        else:
            # Thousands separator
            price_text = price_text.replace(",", "")

    try:
        return float(price_text)
    except ValueError:
        return 0.0


def parse_discount_percentage(discount_text: str) -> Optional[float]:
    """Parse discount percentage from text."""
    if not discount_text:
        return None

    # Extract percentage numbers
    match = re.search(r"(\d+)%", discount_text)
    if match:
        return float(match.group(1))

    return None


def scrape_new_releases(page) -> List[Dict[str, Any]]:
    """Scrape new game releases from AllKeyShop."""
    logger.info("Scraping new releases from AllKeyShop...")

    try:
        page.goto(NEW_RELEASES_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for page to fully load
        page.wait_for_timeout(5000)

        # Try to wait for specific AllKeyShop content to load
        try:
            # Wait for potential game containers or lists
            page.wait_for_selector("div, .container, main, article", timeout=10000)
            logger.info("Basic content loaded")

            # Additional wait for JavaScript to execute
            page.wait_for_timeout(5000)

        except Exception as e:
            logger.info(f"Timeout waiting for content: {e}")

        # Debug: Log page content summary and look for actual game content
        try:
            all_links = page.query_selector_all("a")
            logger.info(f"Total links found on page: {len(all_links)}")

            # Look for specific AllKeyShop game patterns
            game_patterns = [
                'a[href*="/blog/buy-"]',
                'a[href*="cd-key"]',
                'a[href*="compare-prices"]',
                ".game-item a",
                ".product-item a",
                ".search-result a",
            ]

            for pattern in game_patterns:
                matches = page.query_selector_all(pattern)
                logger.info(f"Pattern '{pattern}': {len(matches)} matches")

                # Log first few matches for debugging
                for i, match in enumerate(matches[:3]):
                    try:
                        href = match.get_attribute("href")
                        text = match.inner_text().strip()[:50]
                        logger.info(f"  {pattern} match {i+1}: {text} -> {href}")
                    except:
                        pass

            # Sample some link hrefs for debugging
            sample_links = all_links[:10]
            for i, link in enumerate(sample_links):
                try:
                    href = link.get_attribute("href")
                    text = link.inner_text().strip()[:50]
                    logger.debug(f"Sample link {i+1}: {text} -> {href}")
                except:
                    pass

            # Check for JavaScript-driven content
            scripts = page.query_selector_all("script")
            logger.info(
                f"Found {len(scripts)} script tags - this is likely a dynamic site"
            )

        except Exception as e:
            logger.debug(f"Debug logging failed: {e}")

        # Try to scroll down to trigger lazy loading and look for "show more" buttons
        try:
            # Scroll down gradually to trigger any lazy loading
            for i in range(3):
                page.evaluate(
                    f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})"
                )
                page.wait_for_timeout(2000)

            # Look for and click "show more" or "load more" buttons
            show_more_selectors = [
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                'button:has-text("See more")',
                'a:has-text("Show more")',
                'a:has-text("Load more")',
                'a:has-text("See more")',
                ".show-more",
                ".load-more",
                ".see-more",
                '[data-action="load-more"]',
                '[data-action="show-more"]',
                'button[class*="more"]',
                'a[class*="more"]',
            ]

            clicked_buttons = 0
            max_clicks = 5  # Limit to prevent infinite loops

            for _ in range(max_clicks):
                button_clicked = False
                for selector in show_more_selectors:
                    try:
                        button = page.query_selector(selector)
                        if button and button.is_visible():
                            logger.info(
                                f"Found and clicking show more button: {selector}"
                            )
                            button.click()
                            page.wait_for_timeout(3000)  # Wait for content to load
                            clicked_buttons += 1
                            button_clicked = True
                            break
                    except Exception as e:
                        logger.debug(f"Error clicking button {selector}: {e}")
                        continue

                if not button_clicked:
                    break

                # Scroll to bottom again after clicking
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            logger.info(f"Clicked {clicked_buttons} show more buttons")

            # Look for pagination - "Next" buttons or page numbers
            pagination_selectors = [
                'a:has-text("Next")',
                'button:has-text("Next")',
                'a:has-text(">")',
                'button:has-text(">")',
                ".pagination a[href]:last-child",
                ".next-page",
                "[data-page]",
                'a[aria-label="Next page"]',
                'button[aria-label="Next page"]',
            ]

            clicked_pagination = 0
            max_pages = 3  # Limit pagination clicks

            for page_num in range(max_pages):
                pagination_clicked = False
                for selector in pagination_selectors:
                    try:
                        next_button = page.query_selector(selector)
                        if next_button and next_button.is_visible():
                            logger.info(
                                f"Found and clicking pagination button: {selector}"
                            )
                            next_button.click()
                            page.wait_for_timeout(4000)  # Wait for page to load
                            clicked_pagination += 1
                            pagination_clicked = True

                            # After clicking pagination, scroll and check for more "show more" buttons
                            page.evaluate(
                                "window.scrollTo(0, document.body.scrollHeight)"
                            )
                            page.wait_for_timeout(2000)

                            # Try clicking show more buttons again on new page
                            for show_selector in show_more_selectors:
                                try:
                                    show_button = page.query_selector(show_selector)
                                    if show_button and show_button.is_visible():
                                        logger.info(
                                            f"Found show more on new page: {show_selector}"
                                        )
                                        show_button.click()
                                        page.wait_for_timeout(3000)
                                        break
                                except:
                                    continue
                            break
                    except Exception as e:
                        logger.debug(f"Error clicking pagination {selector}: {e}")
                        continue

                if not pagination_clicked:
                    break

            logger.info(f"Clicked {clicked_pagination} pagination buttons")

            # Check for infinite scroll pattern
            initial_height = page.evaluate("document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 5

            while scroll_attempts < max_scroll_attempts:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)

                new_height = page.evaluate("document.body.scrollHeight")
                if new_height > initial_height:
                    logger.info(
                        f"Infinite scroll detected, new content loaded (height: {initial_height} -> {new_height})"
                    )
                    initial_height = new_height
                    scroll_attempts += 1
                else:
                    break

            logger.info(f"Completed {scroll_attempts} infinite scroll cycles")

            # Final scroll to top
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)
        except Exception as e:
            logger.debug(f"Error during scrolling/button clicking: {e}")

        # Log the page title for debugging
        try:
            page_title = page.title()
            logger.info(f"Page title: {page_title}")
        except:
            pass

        # Wait for the main content area to load
        try:
            page.wait_for_selector("body", timeout=10000)

            # Close any cookie banners or popups
            try:
                popup_selectors = [
                    ".cookie-banner button",
                    ".cookie-consent button",
                    ".modal-close",
                ]
                for popup_selector in popup_selectors:
                    try:
                        popup_element = page.query_selector(popup_selector)
                        if popup_element:
                            popup_element.click()
                            page.wait_for_timeout(1000)
                    except:
                        continue
            except:
                pass

            # Look for the actual game table/list structure from the screenshot
            games = []

            # Try to find the game table or list that shows TITLE, STORE, PRICE, TYPE, FETCHED columns
            table_selectors = [
                "table",
                ".table",
                ".game-table",
                ".product-table",
                ".listing-table",
                ".data-table",
                'table[class*="game"]',
                'table[class*="product"]',
            ]

            # Look for table rows that contain game data
            for table_selector in table_selectors:
                try:
                    table = page.query_selector(table_selector)
                    if table:
                        rows = table.query_selector_all("tr")
                        logger.info(
                            f"Found table with {len(rows)} rows using selector: {table_selector}"
                        )

                        for row in rows[1:]:  # Skip header row
                            try:
                                cells = row.query_selector_all("td")
                                if (
                                    len(cells) >= 2
                                ):  # Need at least title and one other column
                                    title_cell = cells[0]
                                    title_link = title_cell.query_selector("a")

                                    if title_link:
                                        title = title_link.inner_text().strip()
                                        url = title_link.get_attribute("href")

                                        if title and url and is_valid_game_title(title):
                                            game_data = {
                                                "title": title,
                                                "url": (
                                                    url
                                                    if url.startswith("http")
                                                    else f"https://www.allkeyshop.com{url}"
                                                ),
                                                "current_price": 0.0,
                                                "original_price": None,
                                                "discount_percentage": None,
                                                "store_name": None,
                                                "deal_score": None,
                                                "game_type": "new_release",
                                                "is_dlc": False,
                                                "fetched_at": datetime.now(
                                                    timezone.utc
                                                ).isoformat(),
                                                "source": "AllKeyShop",
                                            }

                                            # Try to extract price from other columns
                                            if len(cells) >= 3:
                                                price_text = (
                                                    cells[2].inner_text().strip()
                                                )
                                                game_data["current_price"] = (
                                                    parse_price(price_text)
                                                )

                                            games.append(game_data)
                                            logger.debug(
                                                f"Extracted game from table: {title}"
                                            )
                            except:
                                continue

                        if games:
                            logger.info(
                                f"Successfully extracted {len(games)} games from table"
                            )
                            return games

                except Exception as e:
                    logger.debug(f"Table selector {table_selector} failed: {e}")
                    continue

            # If no table found, try the alternative extraction method
            logger.warning("No game table found, trying alternative extraction")
            games = extract_games_alternative(page, "new_release")

            logger.info(f"Successfully scraped {len(games)} new releases")
            return games

        except Exception as e:
            logger.error(f"Error waiting for page elements: {e}")
            return []

    except Exception as e:
        logger.error(f"Error scraping new releases: {e}")
        return []


def scrape_offers(page) -> List[Dict[str, Any]]:
    """Scrape game offers under 10 EUR from AllKeyShop."""
    logger.info("Scraping game offers from AllKeyShop...")

    try:
        page.goto(OFFERS_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for page to fully load and check for dynamic content
        page.wait_for_timeout(10000)

        # Try to wait for specific AllKeyShop content to load
        try:
            # Wait for potential game containers or lists
            page.wait_for_selector("div, .container, main, article", timeout=10000)
            logger.info("Basic content loaded")

            # Additional wait for JavaScript to execute
            page.wait_for_timeout(5000)

        except Exception as e:
            logger.info(f"Timeout waiting for content: {e}")

        # Debug: Log page content summary and look for actual game content
        try:
            all_links = page.query_selector_all("a")
            logger.info(f"Total links found on page: {len(all_links)}")

            # Look for specific AllKeyShop game patterns
            game_patterns = [
                'a[href*="/blog/buy-"]',
                'a[href*="cd-key"]',
                'a[href*="compare-prices"]',
                ".game-item a",
                ".product-item a",
                ".search-result a",
            ]

            for pattern in game_patterns:
                matches = page.query_selector_all(pattern)
                logger.info(f"Pattern '{pattern}': {len(matches)} matches")

                # Log first few matches for debugging
                for i, match in enumerate(matches[:3]):
                    try:
                        href = match.get_attribute("href")
                        text = match.inner_text().strip()[:50]
                        logger.info(f"  {pattern} match {i+1}: {text} -> {href}")
                    except:
                        pass

            # Sample some link hrefs for debugging
            sample_links = all_links[:10]
            for i, link in enumerate(sample_links):
                try:
                    href = link.get_attribute("href")
                    text = link.inner_text().strip()[:50]
                    logger.debug(f"Sample link {i+1}: {text} -> {href}")
                except:
                    pass

            # Check for JavaScript-driven content
            scripts = page.query_selector_all("script")
            logger.info(
                f"Found {len(scripts)} script tags - this is likely a dynamic site"
            )

        except Exception as e:
            logger.debug(f"Debug logging failed: {e}")

        # Try to scroll down to trigger lazy loading and look for "show more" buttons
        try:
            # Scroll down gradually to trigger any lazy loading
            for i in range(3):
                page.evaluate(
                    f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})"
                )
                page.wait_for_timeout(2000)

            # Look for and click "show more" or "load more" buttons
            show_more_selectors = [
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                'button:has-text("See more")',
                'a:has-text("Show more")',
                'a:has-text("Load more")',
                'a:has-text("See more")',
                ".show-more",
                ".load-more",
                ".see-more",
                '[data-action="load-more"]',
                '[data-action="show-more"]',
                'button[class*="more"]',
                'a[class*="more"]',
            ]

            clicked_buttons = 0
            max_clicks = 5  # Limit to prevent infinite loops

            for _ in range(max_clicks):
                button_clicked = False
                for selector in show_more_selectors:
                    try:
                        button = page.query_selector(selector)
                        if button and button.is_visible():
                            logger.info(
                                f"Found and clicking show more button: {selector}"
                            )
                            button.click()
                            page.wait_for_timeout(3000)  # Wait for content to load
                            clicked_buttons += 1
                            button_clicked = True
                            break
                    except Exception as e:
                        logger.debug(f"Error clicking button {selector}: {e}")
                        continue

                if not button_clicked:
                    break

                # Scroll to bottom again after clicking
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            logger.info(f"Clicked {clicked_buttons} show more buttons")

            # Look for pagination - "Next" buttons or page numbers
            pagination_selectors = [
                'a:has-text("Next")',
                'button:has-text("Next")',
                'a:has-text(">")',
                'button:has-text(">")',
                ".pagination a[href]:last-child",
                ".next-page",
                "[data-page]",
                'a[aria-label="Next page"]',
                'button[aria-label="Next page"]',
            ]

            clicked_pagination = 0
            max_pages = 3  # Limit pagination clicks

            for page_num in range(max_pages):
                pagination_clicked = False
                for selector in pagination_selectors:
                    try:
                        next_button = page.query_selector(selector)
                        if next_button and next_button.is_visible():
                            logger.info(
                                f"Found and clicking pagination button: {selector}"
                            )
                            next_button.click()
                            page.wait_for_timeout(4000)  # Wait for page to load
                            clicked_pagination += 1
                            pagination_clicked = True

                            # After clicking pagination, scroll and check for more "show more" buttons
                            page.evaluate(
                                "window.scrollTo(0, document.body.scrollHeight)"
                            )
                            page.wait_for_timeout(2000)

                            # Try clicking show more buttons again on new page
                            for show_selector in show_more_selectors:
                                try:
                                    show_button = page.query_selector(show_selector)
                                    if show_button and show_button.is_visible():
                                        logger.info(
                                            f"Found show more on new page: {show_selector}"
                                        )
                                        show_button.click()
                                        page.wait_for_timeout(3000)
                                        break
                                except:
                                    continue
                            break
                    except Exception as e:
                        logger.debug(f"Error clicking pagination {selector}: {e}")
                        continue

                if not pagination_clicked:
                    break

            logger.info(f"Clicked {clicked_pagination} pagination buttons")

            # Check for infinite scroll pattern
            initial_height = page.evaluate("document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 5

            while scroll_attempts < max_scroll_attempts:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)

                new_height = page.evaluate("document.body.scrollHeight")
                if new_height > initial_height:
                    logger.info(
                        f"Infinite scroll detected, new content loaded (height: {initial_height} -> {new_height})"
                    )
                    initial_height = new_height
                    scroll_attempts += 1
                else:
                    break

            logger.info(f"Completed {scroll_attempts} infinite scroll cycles")

            # Final scroll to top
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)
        except Exception as e:
            logger.debug(f"Error during scrolling/button clicking: {e}")

        # Log the page title for debugging
        try:
            page_title = page.title()
            logger.info(f"Page title: {page_title}")
        except:
            pass

        # Wait for the main content area to load
        try:
            page.wait_for_selector("body", timeout=10000)

            # Close any cookie banners or popups
            try:
                popup_selectors = [
                    ".cookie-banner button",
                    ".cookie-consent button",
                    ".modal-close",
                ]
                for popup_selector in popup_selectors:
                    try:
                        popup_element = page.query_selector(popup_selector)
                        if popup_element:
                            popup_element.click()
                            page.wait_for_timeout(1000)
                    except:
                        continue
            except:
                pass

            # Look for the actual game table/list structure from the screenshot
            games = []

            # Try to find the game table or list that shows TITLE, STORE, PRICE, TYPE, FETCHED columns
            table_selectors = [
                "table",
                ".table",
                ".game-table",
                ".product-table",
                ".listing-table",
                ".data-table",
                'table[class*="game"]',
                'table[class*="product"]',
            ]

            # Look for table rows that contain game data
            for table_selector in table_selectors:
                try:
                    table = page.query_selector(table_selector)
                    if table:
                        rows = table.query_selector_all("tr")
                        logger.info(
                            f"Found table with {len(rows)} rows using selector: {table_selector}"
                        )

                        for row in rows[1:]:  # Skip header row
                            try:
                                cells = row.query_selector_all("td")
                                if (
                                    len(cells) >= 2
                                ):  # Need at least title and one other column
                                    title_cell = cells[0]
                                    title_link = title_cell.query_selector("a")

                                    if title_link:
                                        title = title_link.inner_text().strip()
                                        url = title_link.get_attribute("href")

                                        if title and url and is_valid_game_title(title):
                                            game_data = {
                                                "title": title,
                                                "url": (
                                                    url
                                                    if url.startswith("http")
                                                    else f"https://www.allkeyshop.com{url}"
                                                ),
                                                "current_price": 0.0,
                                                "original_price": None,
                                                "discount_percentage": None,
                                                "store_name": None,
                                                "deal_score": None,
                                                "game_type": "offer",
                                                "is_dlc": False,
                                                "fetched_at": datetime.now(
                                                    timezone.utc
                                                ).isoformat(),
                                                "source": "AllKeyShop",
                                            }

                                            # Try to extract price from other columns
                                            if len(cells) >= 3:
                                                price_text = (
                                                    cells[2].inner_text().strip()
                                                )
                                                game_data["current_price"] = (
                                                    parse_price(price_text)
                                                )

                                            games.append(game_data)
                                            logger.debug(
                                                f"Extracted offer from table: {title}"
                                            )
                            except:
                                continue

                        if games:
                            logger.info(
                                f"Successfully extracted {len(games)} offers from table"
                            )
                            return games

                except Exception as e:
                    logger.debug(f"Table selector {table_selector} failed: {e}")
                    continue

            # If no table found, try the alternative extraction method
            logger.warning("No game table found, trying alternative extraction")
            games = extract_games_alternative(page, "offer")

            logger.info(f"Successfully scraped {len(games)} offers")
            return games

        except Exception as e:
            logger.error(f"Error waiting for page elements: {e}")
            return []

    except Exception as e:
        logger.error(f"Error scraping offers: {e}")
        return []


def extract_game_data(game_element, game_type: str) -> Optional[Dict[str, Any]]:
    """Extract game data from a game element."""
    try:
        # Extract title
        title_selectors = [
            ".game-title",
            ".product-title",
            ".title",
            "h3",
            "h4",
            ".name",
            ".game-name",
        ]

        title = None
        for selector in title_selectors:
            try:
                title_element = game_element.query_selector(selector)
                if title_element:
                    title = title_element.inner_text().strip()
                    break
            except:
                continue

        if not title:
            return None

        # Extract URL
        url = None
        try:
            link_element = game_element.query_selector("a")
            if link_element:
                url = link_element.get_attribute("href")
                if url and not url.startswith("http"):
                    url = f"https://www.allkeyshop.com{url}"
        except:
            pass

        # Extract current price
        price_selectors = [
            ".price",
            ".current-price",
            ".best-price",
            ".price-current",
            ".price-value",
        ]

        current_price = 0.0
        price_text = None
        for selector in price_selectors:
            try:
                price_element = game_element.query_selector(selector)
                if price_element:
                    price_text = price_element.inner_text().strip()
                    current_price = parse_price(price_text)
                    break
            except:
                continue

        # Extract original price
        original_price = None
        original_price_selectors = [
            ".original-price",
            ".old-price",
            ".price-original",
            ".price-old",
        ]

        for selector in original_price_selectors:
            try:
                original_price_element = game_element.query_selector(selector)
                if original_price_element:
                    original_price_text = original_price_element.inner_text().strip()
                    original_price = parse_price(original_price_text)
                    break
            except:
                continue

        # Extract discount percentage
        discount_percentage = None
        discount_selectors = [
            ".discount",
            ".discount-percentage",
            ".sale-percentage",
            ".off-percentage",
        ]

        for selector in discount_selectors:
            try:
                discount_element = game_element.query_selector(selector)
                if discount_element:
                    discount_text = discount_element.inner_text().strip()
                    discount_percentage = parse_discount_percentage(discount_text)
                    break
            except:
                continue

        # Extract store name
        store_name = None
        store_selectors = [".store-name", ".shop-name", ".retailer", ".store"]

        for selector in store_selectors:
            try:
                store_element = game_element.query_selector(selector)
                if store_element:
                    store_name = store_element.inner_text().strip()
                    break
            except:
                continue

        # Extract deal score if available
        deal_score = None
        score_selectors = [".deal-score", ".score", ".rating-score"]

        for selector in score_selectors:
            try:
                score_element = game_element.query_selector(selector)
                if score_element:
                    score_text = score_element.inner_text().strip()
                    score_match = re.search(r"(\d+)", score_text)
                    if score_match:
                        deal_score = int(score_match.group(1))
                    break
            except:
                continue

        # Calculate discount percentage if not found but have both prices
        if (
            not discount_percentage
            and original_price
            and current_price
            and original_price > current_price
        ):
            discount_percentage = (
                (original_price - current_price) / original_price
            ) * 100

        return {
            "title": title,
            "url": url,
            "current_price": current_price,
            "original_price": original_price,
            "discount_percentage": discount_percentage,
            "store_name": store_name,
            "deal_score": deal_score,
            "game_type": game_type,
            "is_dlc": "DLC" in title.upper() or "EXPANSION" in title.upper(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "AllKeyShop",
        }

    except Exception as e:
        logger.error(f"Error extracting game data: {e}")
        return None


def extract_game_data_improved(element, game_type: str) -> Optional[Dict[str, Any]]:
    """Extract game data from an element with improved approach."""
    try:
        # Get all text content from the element
        text_content = element.inner_text().strip()

        # Skip if element is too small or contains only whitespace
        if len(text_content) < 10:
            return None

        # Skip navigation and promotional elements - expanded
        skip_patterns = [
            "newsletter",
            "subscribe",
            "categories",
            "partnership",
            "about us",
            "need help",
            "buyer protection",
            "market best prices",
            "feeling lucky",
            "reward program",
            "reviews",
            "spin the wheel",
            "link your steam",
            "gift cards",
            "discord",
            "twitch",
            "kick",
            "allkeyshop",
            "best deals",
            "coupons",
            "twitchkick",
            "join our",
            "win points",
            "turn the wheel",
            "get the best deals",
            "free game and coupons",
            "official and keysellers",
            "best new game releases",
            "average price",
            "free games",
            "dlc/expansions",
        ]

        text_lower = text_content.lower()
        for pattern in skip_patterns:
            if pattern in text_lower:
                return None

        # Skip if element contains too many promotional keywords
        promotional_word_count = 0
        promotional_words = [
            "subscribe",
            "newsletter",
            "reward",
            "program",
            "lucky",
            "wheel",
            "gift",
            "discord",
            "twitch",
            "partnership",
            "protection",
            "best",
            "deals",
            "coupons",
            "official",
            "keysellers",
            "reviews",
            "allkeyshop",
            "join",
            "win",
            "points",
            "turn",
            "free",
            "average",
            "price",
        ]

        for word in promotional_words:
            if word in text_lower:
                promotional_word_count += 1

        if promotional_word_count > 2:  # Too many promotional words
            return None

        # Try to extract title - look for text that could be a game title
        title = None

        # First try to find a title in nested elements
        title_selectors = [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            ".title",
            ".name",
            ".game-title",
            ".product-name",
            ".game-name",
            ".product-title",
            'a[href*="game"]',
            'a[href*="product"]',
            "strong",
            "b",
        ]

        for selector in title_selectors:
            try:
                title_element = element.query_selector(selector)
                if title_element:
                    potential_title = title_element.inner_text().strip()
                    if is_valid_game_title(potential_title):
                        title = potential_title
                        break
            except:
                continue

        # If no title found in nested elements, try to extract from text
        if not title:
            lines = text_content.split("\n")
            for line in lines:
                line = line.strip()
                if is_valid_game_title(line):
                    title = line
                    break

        if not title:
            return None

        # Extract URL
        url = None
        try:
            link_element = element.query_selector('a[href*="game"], a[href*="product"]')
            if link_element:
                url = link_element.get_attribute("href")
                if url and not url.startswith("http"):
                    url = f"https://www.allkeyshop.com{url}"
        except:
            pass

        # Extract price information
        current_price = 0.0
        original_price = None
        discount_percentage = None

        # Look for price elements first
        price_selectors = [
            ".price",
            ".current-price",
            ".best-price",
            ".price-current",
            ".price-value",
            ".amount",
            ".cost",
            ".euro",
            ".dollar",
        ]

        for selector in price_selectors:
            try:
                price_element = element.query_selector(selector)
                if price_element:
                    price_text = price_element.inner_text().strip()
                    parsed_price = parse_price(price_text)
                    if parsed_price > 0:
                        current_price = parsed_price
                        break
            except:
                continue

        # If no price found in specific elements, look for price patterns in text
        if current_price == 0.0:
            price_patterns = [
                r"€\s*(\d+[.,]\d+)",
                r"(\d+[.,]\d+)\s*€",
                r"\$\s*(\d+[.,]\d+)",
                r"(\d+[.,]\d+)\s*\$",
            ]

            for pattern in price_patterns:
                matches = re.findall(pattern, text_content)
                if matches:
                    try:
                        current_price = parse_price(matches[0])
                        break
                    except:
                        continue

        # Look for discount patterns
        discount_match = re.search(r"(\d+)%", text_content)
        if discount_match:
            discount_percentage = float(discount_match.group(1))

        # Extract store name
        store_name = None
        store_selectors = [
            ".store-name",
            ".shop-name",
            ".retailer",
            ".store",
            ".merchant",
            ".vendor",
            ".platform",
        ]

        for selector in store_selectors:
            try:
                store_element = element.query_selector(selector)
                if store_element:
                    store_name = store_element.inner_text().strip()
                    break
            except:
                continue

        # If no store found in specific elements, look for common store indicators
        if not store_name:
            store_indicators = [
                "Steam",
                "Epic",
                "GOG",
                "Humble",
                "Green Man Gaming",
                "Fanatical",
                "GamersGate",
                "Origin",
                "Uplay",
                "Battle.net",
            ]
            for indicator in store_indicators:
                if indicator.lower() in text_content.lower():
                    store_name = indicator
                    break

        return {
            "title": title,
            "url": url,
            "current_price": current_price,
            "original_price": original_price,
            "discount_percentage": discount_percentage,
            "store_name": store_name,
            "deal_score": None,
            "game_type": game_type,
            "is_dlc": (
                "DLC" in title.upper() or "EXPANSION" in title.upper()
                if title
                else False
            ),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "AllKeyShop",
        }

    except Exception as e:
        logger.debug(f"Error in improved extraction: {e}")
        return None


def is_valid_game_title(title: str) -> bool:
    """Check if a title looks like a valid game title."""
    if not title or len(title) < 3 or len(title) > 150:
        return False

    # Skip common non-game elements - expanded list
    invalid_patterns = [
        r"^\d+$",  # Just numbers
        r"^\d+[.,]\d+$",  # Just prices
        r"^\d+%$",  # Just percentages
        r"^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",  # Dates
        r"^historical low",
        r"^subscribe",
        r"^newsletter",
        r"^categories",
        r"^partnership",
        r"^about us",
        r"^need help",
        r"^buyer protection",
        r"^market best prices",
        r"^official and",
        r"^feeling lucky",
        r"reward program",
        r"^\d+\s+reviews",
        r"^reviews$",
        r"^spin the wheel",
        r"^link your steam",
        r"^gift cards",
        r"^discord",
        r"^twitch",
        r"^kick",
        r"^xbox$",  # Just platform names
        r"^playstation$",
        r"^nintendo$",
        r"^steam$",
        r"^epic$",
        r"^free$",
        r"^n/a$",
        r"^\.\.\.$",
        r"^more$",
        r"^next$",
        r"^previous$",
        r"^page \d+",
        r"^\d+ \d+ \d+",
        r"^or win points",
        r"^join our",
        r"^how does it work",
        r"^\d+\s*€",  # Prices starting with numbers
        r"^€\s*\d+",  # Prices starting with currency
        r"^\$\s*\d+",  # Dollar prices
        # New patterns based on screenshot and improved filtering
        r"^best new game releases$",
        r"^allkeyshop",
        r"^twitchkick$",
        r"^\d+ reviews$",
        r"^join our reward program$",
        r"feeling lucky.*win.*gift cards",
        r"or win points to turn the wheel",
        r"get the best deals",
        r"free game and coupons",
        r"^official and keysellers",
        r"^new releases$",
        r"^offers$",
        r"^average price$",
        r"^free games$",
        r"^dlc/expansions$",
        # Currency and navigation
        r"^eur €$",
        r"^usd \$$",
        r"^gbp £$",
        r"^cards$",
        r"^vouchers$",
        r"^coins$",
        # Subscription services (not actual games)
        r"^playstation plus",
        r"^xbox game pass",
        r"^nintendo online",
        r"^all subscription cards$",
        # Remove gift cards from exclusions - they're valid gaming products
        # r'^nintendo eshop cards$',  # These are legitimate gaming products
        # r'^apex coins$',
        # r'^fc \d+ points$',
        # r'^fortnite v-bucks$',
        # r'^robux$',
        # r'multibucks$',
        # Generic categories
        r"^games like & franchises$",
        r"^e-sports.*tournaments$",
        r"etour de france",
        r"european slamfest",
    ]

    for pattern in invalid_patterns:
        if re.match(pattern, title.lower()):
            return False

    # Must contain at least one letter
    if not re.search(r"[a-zA-Z]", title):
        return False

    # Enhanced promotional keyword filtering - exclude actual gaming products
    promotional_keywords = [
        "newsletter",
        "subscribe",
        "reward",
        "program",
        "lucky",
        "wheel",
        "discord",
        "twitch",
        "partnership",
        "protection",
        "best prices",
        "official",
        "keysellers",
        "reviews",
        "allkeyshop",
        "best deals",
        "coupons",
        "new releases",
        "offers",
        "average price",
        "categories",
        "about us",
        "need help",
        "buyer protection",
        "market best",
        "win points",
        "turn the wheel",
        "join our",
        "feeling lucky",
        "twitchkick",
        "etour de france",
        "european slamfest",
        "tournaments",
        "vouchers",
        # Removed gaming products: 'gift card', 'eshop cards', 'game pass', 'v-bucks', 'robux', etc.
    ]

    title_lower = title.lower()
    for keyword in promotional_keywords:
        if keyword in title_lower:
            # Be more strict with promotional content
            if len(title_lower) < 100 or title_lower.count(" ") > 8:
                return False

    # Reject titles that are too generic or clearly not games
    generic_patterns = [
        r"^(game|games|product|item|store|shop|deal|offer|sale)s?$",
        r"^(pc|xbox|playstation|nintendo|steam|epic|gog)$",
        r"^(new|best|top|free|cheap)$",
        r"^\d+.*reviews?$",
        r"^reviews?\s*\d*$",
        r"partnership|protection|program|newsletter|subscribe",
    ]

    for pattern in generic_patterns:
        if re.match(pattern, title_lower):
            return False

    return True


def is_valid_game_data(game_data: Dict[str, Any]) -> bool:
    """Check if game data looks valid."""
    if not game_data or not game_data.get("title"):
        return False

    title = game_data["title"]

    # Use the title validation function
    if not is_valid_game_title(title):
        return False

    # Additional validation for game data
    # Skip if title is too generic or common
    generic_titles = [
        "free",
        "sale",
        "deal",
        "offer",
        "discount",
        "price",
        "store",
        "game",
        "product",
        "item",
        "card",
        "box",
        "container",
    ]

    if title.lower() in generic_titles:
        return False

    return True


def extract_games_alternative(page, game_type: str) -> List[Dict[str, Any]]:
    """Alternative extraction method for games."""
    try:
        logger.info("Trying alternative extraction method...")
        games = []

        # Look for links that go to actual game pages - focus on actual game/product links
        game_url_patterns = [
            'a[href*="/blog/buy-"]',  # AllKeyShop's main product links
            'a[href*="cd-key"]',
            'a[href*="compare-prices"]',
            'a[href*="/blog/game/"]',
            'a[href*="/game/"]',
            'a[href*="/product/"]',
            'a[href*="buy-cd-key"]',
            'a[href*="compare-and-buy"]',
        ]

        # Also try to find ANY links that might contain game titles
        all_page_links = page.query_selector_all("a")
        logger.info(f"Total links on page: {len(all_page_links)}")

        # Filter links that might be games based on text content
        potential_game_links = []
        for link in all_page_links:
            try:
                text = link.inner_text().strip()
                href = link.get_attribute("href")

                # Skip if no text or href
                if not text or not href:
                    continue

                # Skip obvious navigation/promotional links
                if any(
                    skip in text.lower()
                    for skip in [
                        "newsletter",
                        "subscribe",
                        "about",
                        "help",
                        "contact",
                        "privacy",
                        "terms",
                        "categories",
                        "partnership",
                        "protection",
                        "rewards",
                        "gift card",
                        "discord",
                        "twitch",
                    ]
                ):
                    continue

                # Look for links that might be games (have reasonable length title)
                if 5 <= len(text) <= 100 and is_valid_game_title(text):
                    potential_game_links.append(link)

            except:
                continue

        logger.info(
            f"Found {len(potential_game_links)} potential game links based on text analysis"
        )

        all_links = potential_game_links  # Start with text-based filtered links

        # Add pattern-based links
        for pattern in game_url_patterns:
            links = page.query_selector_all(pattern)
            all_links.extend(links)
            logger.info(f"Found {len(links)} links with pattern: {pattern}")

        # Remove duplicates
        unique_links = []
        seen_urls = set()
        for link in all_links:
            try:
                url = link.get_attribute("href")
                if url and url not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(url)
            except:
                continue

        logger.info(f"Processing {len(unique_links)} unique potential game links")

        for link in unique_links[:50]:  # Increased limit to capture more deals
            try:
                # Get link text as potential title
                title = link.inner_text().strip()
                url = link.get_attribute("href")

                if not url:
                    continue

                if not url.startswith("http"):
                    url = f"https://www.allkeyshop.com{url}"

                # Validate title
                if not title or not is_valid_game_title(title):
                    continue

                # Additional URL-based filtering
                if url:
                    # Skip URLs that are clearly not games
                    skip_url_patterns = [
                        "category-giftcards",
                        "category-subscriptions",
                        "category-gamecards",
                        "compare-prices",
                        "buying-guide",
                        "vouchers",
                        "blog/en-us",
                        "blog/en-gb",
                        "#",
                        "allkeyshop.com/blog/$",
                        "blog/category",
                    ]
                    if any(pattern in url for pattern in skip_url_patterns):
                        continue

                # Look for price information in nearby elements
                current_price = 0.0
                try:
                    # Check parent containers for price
                    parent = link.locator(
                        'xpath=ancestor::div[contains(@class, "price") or contains(@class, "game") or contains(@class, "product")][1]'
                    )
                    if parent:
                        price_text = parent.inner_text()
                        price_match = re.search(r"€\s*(\d+[.,]\d+)", price_text)
                        if price_match:
                            current_price = parse_price(price_match.group(1))
                except:
                    pass

                game_data = {
                    "title": title,
                    "url": url,
                    "current_price": current_price,
                    "original_price": None,
                    "discount_percentage": None,
                    "store_name": None,
                    "deal_score": None,
                    "game_type": game_type,
                    "is_dlc": "DLC" in title.upper() or "EXPANSION" in title.upper(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "AllKeyShop",
                }

                if is_valid_game_data(game_data):
                    games.append(game_data)
                    logger.debug(f"Added game: {title}")

            except Exception as e:
                logger.debug(f"Error processing link: {e}")
                continue

        logger.info(f"Alternative extraction found {len(games)} valid games")
        return games

    except Exception as e:
        logger.error(f"Error in alternative extraction: {e}")
        return []


def extract_games_from_content(page, game_type: str) -> List[Dict[str, Any]]:
    """Extract games from page content using text analysis."""
    try:
        # Get all text content from the page
        page_content = page.content()

        # Look for patterns that might indicate games
        games = []

        # Try to find game titles in the HTML
        # Look for patterns like game names followed by prices
        game_patterns = [
            r"<[^>]*>([^<]{10,80})</[^>]*>.*?€\s*(\d+[.,]\d+)",
            r'<a[^>]*href="[^"]*game[^"]*"[^>]*>([^<]{5,80})</a>',
            r'<[^>]*class="[^"]*title[^"]*"[^>]*>([^<]{5,80})</[^>]*>',
        ]

        for pattern in game_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches[:10]:  # Limit to 10 matches
                if isinstance(match, tuple):
                    title = match[0].strip()
                    price = parse_price(match[1]) if len(match) > 1 else 0.0
                else:
                    title = match.strip()
                    price = 0.0

                if title and len(title) > 3:
                    games.append(
                        {
                            "title": title,
                            "url": None,
                            "current_price": price,
                            "original_price": None,
                            "discount_percentage": None,
                            "store_name": None,
                            "deal_score": None,
                            "game_type": game_type,
                            "is_dlc": "DLC" in title.upper()
                            or "EXPANSION" in title.upper(),
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                            "source": "AllKeyShop",
                        }
                    )

        return games

    except Exception as e:
        logger.error(f"Error in content-based extraction: {e}")
        return []


def get_allkeyshop_data(max_retries: int = 3) -> List[Dict[str, Any]]:
    """Main function to fetch AllKeyShop data using Playwright."""
    logger.info("Starting AllKeyShop data fetch...")

    all_games = []

    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                # Launch browser with stealth settings
                browser = p.chromium.launch(
                    headless=True,  # Headless for production
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ],
                )

                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="Europe/Madrid",
                )

                # Add common headers
                context.set_extra_http_headers(
                    {
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                    }
                )

                page = context.new_page()

                # Scrape new releases
                new_releases = scrape_new_releases(page)
                all_games.extend(new_releases)

                # Wait between requests
                time.sleep(5)

                # Scrape offers
                offers = scrape_offers(page)
                all_games.extend(offers)

                browser.close()

                logger.info(
                    f"Successfully fetched {len(all_games)} games from AllKeyShop"
                )
                return all_games

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("All retry attempts failed")
                return []

    return all_games


def save_data(data: List[Dict[str, Any]]) -> None:
    """Save the fetched data to JSON and CSV files."""
    if not data:
        logger.warning("No data to save")
        return

    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "games")
        ensure_directories(["data/games"])

        # Save to JSON
        json_path = os.path.join(output_dir, "allkeyshop.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Data saved to {json_path}")

        # Save to CSV
        csv_path = os.path.join(output_dir, "allkeyshop.csv")
        if data:
            import pandas as pd

            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False, encoding="utf-8")
            logger.info(f"Data saved to {csv_path}")

    except Exception as e:
        logger.error(f"Error saving data: {e}")


def main():
    """Main function to run the AllKeyShop ETL process."""
    logger.info("Starting AllKeyShop ETL process...")

    try:
        # Fetch data
        data = get_allkeyshop_data()

        if data:
            # Save data
            save_data(data)
            logger.info(
                f"AllKeyShop ETL completed successfully. Processed {len(data)} games."
            )
        else:
            logger.warning("No data retrieved from AllKeyShop")

    except Exception as e:
        logger.error(f"AllKeyShop ETL failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
