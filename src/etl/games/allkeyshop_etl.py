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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("AllKeyShopETL")

# AllKeyShop URLs
NEW_RELEASES_URL = "https://www.allkeyshop.com/blog/games/new-releases/?operating_systems=pc"
OFFERS_URL = "https://www.allkeyshop.com/blog/games/under-10-eur/?operating_systems=pc"


def parse_price(price_text: str) -> float:
    """Parse price text and extract numeric value."""
    if not price_text:
        return 0.0
    
    # Remove currency symbols and clean up
    price_text = re.sub(r'[€$£¥₹]', '', price_text)
    price_text = re.sub(r'[^\d.,]', '', price_text)
    
    # Handle different decimal separators
    if ',' in price_text and '.' in price_text:
        # Format like 1,234.56
        price_text = price_text.replace(',', '')
    elif ',' in price_text:
        # Check if it's a decimal separator or thousands separator
        parts = price_text.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Decimal separator
            price_text = price_text.replace(',', '.')
        else:
            # Thousands separator
            price_text = price_text.replace(',', '')
    
    try:
        return float(price_text)
    except ValueError:
        return 0.0


def parse_discount_percentage(discount_text: str) -> Optional[float]:
    """Parse discount percentage from text."""
    if not discount_text:
        return None
    
    # Extract percentage numbers
    match = re.search(r'(\d+)%', discount_text)
    if match:
        return float(match.group(1))
    
    return None


def scrape_new_releases(page) -> List[Dict[str, Any]]:
    """Scrape new game releases from AllKeyShop."""
    logger.info("Scraping new releases from AllKeyShop...")
    
    try:
        page.goto(NEW_RELEASES_URL, wait_until="domcontentloaded", timeout=60000)
        
        # Wait a moment for dynamic content to load
        page.wait_for_timeout(3000)
        
        # Take a screenshot for debugging
        logger.info("Taking screenshot for debugging...")
        
        # Log the page title for debugging
        try:
            page_title = page.title()
            logger.info(f"Page title: {page_title}")
        except:
            pass
        
        # Try to find the page content by waiting for common elements
        try:
            page.wait_for_selector('body', timeout=10000)
            
            # Look for various possible selectors on AllKeyShop
            possible_selectors = [
                '.col-md-3',  # Common grid column class
                '.col-sm-6',  # Common grid column class
                '.col-lg-4',  # Common grid column class
                '.game-card',
                '.product-card',
                '.deal-card',
                'article',
                '.product',
                '.game',
                '.item',
                '.card',
                '.box',
                '.row',
                'div[class*="game"]',
                'div[class*="product"]',
                'div[class*="item"]',
                'div[class*="col-"]',  # Bootstrap columns
                'li',
                'a[href*="game"]',
                'a[href*="product"]'
            ]
            
            games = []
            
            for selector in possible_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements and len(elements) > 3:  # Only consider if we find multiple elements
                        logger.info(f"Found {len(elements)} potential elements with selector: {selector}")
                        
                        # If we found .row elements, look for game items within those rows
                        if selector == '.row':
                            for row_idx, row_element in enumerate(elements):
                                try:
                                    # Look for game items within each row
                                    game_items = row_element.query_selector_all('div, article, .item, .game, .product')
                                    logger.debug(f"Found {len(game_items)} items in row {row_idx + 1}")
                                    
                                    for item_idx, item in enumerate(game_items):
                                        try:
                                            game_data = extract_game_data_flexible(item, "new_release", page)
                                            if game_data and game_data.get('title'):
                                                games.append(game_data)
                                                logger.debug(f"Extracted new release from row {row_idx + 1}, item {item_idx + 1}: {game_data.get('title', 'Unknown')}")
                                        except Exception as e:
                                            logger.debug(f"Error extracting from row {row_idx + 1}, item {item_idx + 1}: {e}")
                                            continue
                                except Exception as e:
                                    logger.debug(f"Error processing row {row_idx + 1}: {e}")
                                    continue
                        else:
                            # Try to extract game data from these elements
                            for idx, element in enumerate(elements[:50]):  # Increased limit to 50
                                try:
                                    game_data = extract_game_data_flexible(element, "new_release", page)
                                    if game_data and game_data.get('title'):
                                        games.append(game_data)
                                        logger.debug(f"Extracted new release {idx + 1}: {game_data.get('title', 'Unknown')}")
                                except Exception as e:
                                    logger.debug(f"Error extracting from element {idx + 1}: {e}")
                                    continue
                        
                        if games:
                            logger.info(f"Successfully scraped {len(games)} new releases using selector: {selector}")
                            return games
                            
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no games found with structured selectors, try to extract from page content
            if not games:
                logger.warning("No games found with structured selectors, trying content-based extraction")
                games = extract_games_from_content(page, "new_release")
            
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
        
        # Wait a moment for dynamic content to load
        page.wait_for_timeout(3000)
        
        # Take a screenshot for debugging
        logger.info("Taking screenshot for debugging...")
        
        # Log the page title for debugging
        try:
            page_title = page.title()
            logger.info(f"Page title: {page_title}")
        except:
            pass
        
        # Try to find the page content by waiting for common elements
        try:
            page.wait_for_selector('body', timeout=10000)
            
            # Look for various possible selectors on AllKeyShop
            possible_selectors = [
                '.col-md-3',  # Common grid column class
                '.col-sm-6',  # Common grid column class
                '.col-lg-4',  # Common grid column class
                '.game-card',
                '.product-card',
                '.deal-card',
                'article',
                '.product',
                '.game',
                '.item',
                '.card',
                '.box',
                '.row',
                'div[class*="game"]',
                'div[class*="product"]',
                'div[class*="item"]',
                'div[class*="col-"]',  # Bootstrap columns
                'li',
                'a[href*="game"]',
                'a[href*="product"]'
            ]
            
            games = []
            
            for selector in possible_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements and len(elements) > 3:  # Only consider if we find multiple elements
                        logger.info(f"Found {len(elements)} potential elements with selector: {selector}")
                        
                        # If we found .row elements, look for game items within those rows
                        if selector == '.row':
                            for row_idx, row_element in enumerate(elements):
                                try:
                                    # Look for game items within each row
                                    game_items = row_element.query_selector_all('div, article, .item, .game, .product')
                                    logger.debug(f"Found {len(game_items)} items in row {row_idx + 1}")
                                    
                                    for item_idx, item in enumerate(game_items):
                                        try:
                                            game_data = extract_game_data_flexible(item, "offer", page)
                                            if game_data and game_data.get('title'):
                                                games.append(game_data)
                                                logger.debug(f"Extracted offer from row {row_idx + 1}, item {item_idx + 1}: {game_data.get('title', 'Unknown')}")
                                        except Exception as e:
                                            logger.debug(f"Error extracting from row {row_idx + 1}, item {item_idx + 1}: {e}")
                                            continue
                                except Exception as e:
                                    logger.debug(f"Error processing row {row_idx + 1}: {e}")
                                    continue
                        else:
                            # Try to extract game data from these elements
                            for idx, element in enumerate(elements[:50]):  # Increased limit to 50
                                try:
                                    game_data = extract_game_data_flexible(element, "offer", page)
                                    if game_data and game_data.get('title'):
                                        games.append(game_data)
                                        logger.debug(f"Extracted offer {idx + 1}: {game_data.get('title', 'Unknown')}")
                                except Exception as e:
                                    logger.debug(f"Error extracting from element {idx + 1}: {e}")
                                    continue
                        
                        if games:
                            logger.info(f"Successfully scraped {len(games)} offers using selector: {selector}")
                            return games
                            
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no games found with structured selectors, try to extract from page content
            if not games:
                logger.warning("No games found with structured selectors, trying content-based extraction")
                games = extract_games_from_content(page, "offer")
            
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
            '.game-title',
            '.product-title',
            '.title',
            'h3',
            'h4',
            '.name',
            '.game-name'
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
            link_element = game_element.query_selector('a')
            if link_element:
                url = link_element.get_attribute('href')
                if url and not url.startswith('http'):
                    url = f"https://www.allkeyshop.com{url}"
        except:
            pass
        
        # Extract current price
        price_selectors = [
            '.price',
            '.current-price',
            '.best-price',
            '.price-current',
            '.price-value'
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
            '.original-price',
            '.old-price',
            '.price-original',
            '.price-old'
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
            '.discount',
            '.discount-percentage',
            '.sale-percentage',
            '.off-percentage'
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
        store_selectors = [
            '.store-name',
            '.shop-name',
            '.retailer',
            '.store'
        ]
        
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
        score_selectors = [
            '.deal-score',
            '.score',
            '.rating-score'
        ]
        
        for selector in score_selectors:
            try:
                score_element = game_element.query_selector(selector)
                if score_element:
                    score_text = score_element.inner_text().strip()
                    score_match = re.search(r'(\d+)', score_text)
                    if score_match:
                        deal_score = int(score_match.group(1))
                    break
            except:
                continue
        
        # Calculate discount percentage if not found but have both prices
        if not discount_percentage and original_price and current_price and original_price > current_price:
            discount_percentage = ((original_price - current_price) / original_price) * 100
        
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
            "source": "AllKeyShop"
        }
        
    except Exception as e:
        logger.error(f"Error extracting game data: {e}")
        return None


def extract_game_data_flexible(element, game_type: str, page) -> Optional[Dict[str, Any]]:
    """Extract game data from an element with flexible approach."""
    try:
        # Get all text content from the element
        text_content = element.inner_text().strip()
        
        # Skip if element is too small or doesn't contain game-like content
        if len(text_content) < 10:
            return None
        
        # Try to extract title - look for text that could be a game title
        title = None
        
        # First try to find a title in nested elements
        title_selectors = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            '.title', '.name', '.game-title', '.product-name',
            'a', 'span', 'div'
        ]
        
        for selector in title_selectors:
            try:
                title_element = element.query_selector(selector)
                if title_element:
                    potential_title = title_element.inner_text().strip()
                    if potential_title and len(potential_title) > 3 and len(potential_title) < 100:
                        title = potential_title
                        break
            except:
                continue
        
        # If no title found in nested elements, use the element's text
        if not title:
            lines = text_content.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 3 and len(line) < 100:
                    # Skip lines that look like prices or dates
                    if not re.match(r'^\d+[.,]\d+|^\d+%|^\d{2}/\d{2}', line):
                        title = line
                        break
        
        if not title:
            return None
        
        # Extract URL
        url = None
        try:
            link_element = element.query_selector('a')
            if link_element:
                url = link_element.get_attribute('href')
                if url and not url.startswith('http'):
                    url = f"https://www.allkeyshop.com{url}"
        except:
            pass
        
        # Extract price information from text
        current_price = 0.0
        original_price = None
        discount_percentage = None
        
        # Look for price patterns in the text
        price_patterns = [
            r'€\s*(\d+[.,]\d+)',
            r'(\d+[.,]\d+)\s*€',
            r'\$\s*(\d+[.,]\d+)',
            r'(\d+[.,]\d+)\s*\$',
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
        discount_match = re.search(r'(\d+)%', text_content)
        if discount_match:
            discount_percentage = float(discount_match.group(1))
        
        # Extract store name - look for common store indicators
        store_name = None
        store_indicators = ['Steam', 'Epic', 'GOG', 'Humble', 'Green Man Gaming', 'Fanatical', 'GamersGate']
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
            "is_dlc": "DLC" in title.upper() or "EXPANSION" in title.upper() if title else False,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "AllKeyShop"
        }
        
    except Exception as e:
        logger.debug(f"Error in flexible extraction: {e}")
        return None


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
            r'<[^>]*>([^<]{10,80})</[^>]*>.*?€\s*(\d+[.,]\d+)',
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
                    games.append({
                        "title": title,
                        "url": None,
                        "current_price": price,
                        "original_price": None,
                        "discount_percentage": None,
                        "store_name": None,
                        "deal_score": None,
                        "game_type": game_type,
                        "is_dlc": "DLC" in title.upper() or "EXPANSION" in title.upper(),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "source": "AllKeyShop"
                    })
        
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
                # Launch browser with stealth settings - try visible first for debugging
                browser = p.chromium.launch(
                    headless=False,  # Make visible for debugging
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="Europe/Madrid"
                )
                
                # Add common headers
                context.set_extra_http_headers({
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
                })
                
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
                
                logger.info(f"Successfully fetched {len(all_games)} games from AllKeyShop")
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
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Data saved to {json_path}")
        
        # Save to CSV
        csv_path = os.path.join(output_dir, "allkeyshop.csv")
        if data:
            import pandas as pd
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False, encoding='utf-8')
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
            logger.info(f"AllKeyShop ETL completed successfully. Processed {len(data)} games.")
        else:
            logger.warning("No data retrieved from AllKeyShop")
            
    except Exception as e:
        logger.error(f"AllKeyShop ETL failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()