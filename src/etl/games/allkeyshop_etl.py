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
    price_text = re.sub(r'[^\\d.,]', '', price_text)
    
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
        
        # Wait for page to fully load
        page.wait_for_timeout(5000)
        
        # Log the page title for debugging
        try:
            page_title = page.title()
            logger.info(f"Page title: {page_title}")
        except:
            pass
        
        # Wait for the main content area to load
        try:
            page.wait_for_selector('body', timeout=10000)
            
            # First, let's check if we need to handle any popups or overlays
            try:
                # Close any cookie banners or popups
                popup_selectors = [
                    '.cookie-banner button',
                    '.cookie-consent button',
                    '.modal-close',
                    '.popup-close',
                    '[aria-label="Close"]'
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
            
            # Look for the actual game listing container
            # AllKeyShop typically uses a results container
            games = []
            
            # More specific selectors for AllKeyShop game listings
            game_container_selectors = [
                '#results',
                '.results',
                '.game-list',
                '.products-list',
                '.search-results',
                '.listing-results',
                'main .container',
                '.content-wrapper',
                '.main-content'
            ]
            
            game_item_selectors = [
                '.game-item',
                '.product-item', 
                '.listing-item',
                '.search-item',
                '.result-item',
                '.game-card',
                '.product-card',
                '.item-container',
                'article[class*="game"]',
                'article[class*="product"]',
                'div[class*="game-"]',
                'div[class*="product-"]',
                '.col-md-4',
                '.col-lg-3',
                '.col-sm-6'
            ]
            
            # Try to find the main container first
            main_container = None
            for container_selector in game_container_selectors:
                try:
                    container = page.query_selector(container_selector)
                    if container:
                        main_container = container
                        logger.info(f"Found main container with selector: {container_selector}")
                        break
                except:
                    continue
            
            # If no specific container found, use the body
            if not main_container:
                main_container = page.query_selector('body')
            
            # Now look for game items within the container
            if main_container:
                for item_selector in game_item_selectors:
                    try:
                        elements = main_container.query_selector_all(item_selector)
                        if elements and len(elements) > 2:  # Need at least 3 elements
                            logger.info(f"Found {len(elements)} potential game elements with selector: {item_selector}")
                            
                            # Filter out navigation and other non-game elements
                            valid_games = []
                            
                            for idx, element in enumerate(elements[:30]):  # Limit to first 30
                                try:
                                    game_data = extract_game_data_improved(element, "new_release")
                                    if game_data and is_valid_game_data(game_data):
                                        valid_games.append(game_data)
                                        logger.debug(f"Extracted valid game {idx + 1}: {game_data.get('title', 'Unknown')}")
                                except Exception as e:
                                    logger.debug(f"Error extracting from element {idx + 1}: {e}")
                                    continue
                            
                            if valid_games:
                                logger.info(f"Successfully scraped {len(valid_games)} new releases using selector: {item_selector}")
                                return valid_games
                                
                    except Exception as e:
                        logger.debug(f"Selector {item_selector} failed: {e}")
                        continue
            
            # If no games found with structured selectors, try alternative approach
            if not games:
                logger.warning("No games found with structured selectors, trying alternative extraction")
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
        
        # Wait for page to fully load
        page.wait_for_timeout(5000)
        
        # Log the page title for debugging
        try:
            page_title = page.title()
            logger.info(f"Page title: {page_title}")
        except:
            pass
        
        # Wait for the main content area to load
        try:
            page.wait_for_selector('body', timeout=10000)
            
            # Handle any popups or overlays
            try:
                popup_selectors = [
                    '.cookie-banner button',
                    '.cookie-consent button',
                    '.modal-close',
                    '.popup-close',
                    '[aria-label="Close"]'
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
            
            # Look for the actual game listing container
            games = []
            
            # More specific selectors for AllKeyShop game listings
            game_container_selectors = [
                '#results',
                '.results',
                '.game-list',
                '.products-list',
                '.search-results',
                '.listing-results',
                'main .container',
                '.content-wrapper',
                '.main-content'
            ]
            
            game_item_selectors = [
                '.game-item',
                '.product-item', 
                '.listing-item',
                '.search-item',
                '.result-item',
                '.game-card',
                '.product-card',
                '.item-container',
                'article[class*="game"]',
                'article[class*="product"]',
                'div[class*="game-"]',
                'div[class*="product-"]',
                '.col-md-4',
                '.col-lg-3',
                '.col-sm-6'
            ]
            
            # Try to find the main container first
            main_container = None
            for container_selector in game_container_selectors:
                try:
                    container = page.query_selector(container_selector)
                    if container:
                        main_container = container
                        logger.info(f"Found main container with selector: {container_selector}")
                        break
                except:
                    continue
            
            # If no specific container found, use the body
            if not main_container:
                main_container = page.query_selector('body')
            
            # Now look for game items within the container
            if main_container:
                for item_selector in game_item_selectors:
                    try:
                        elements = main_container.query_selector_all(item_selector)
                        if elements and len(elements) > 2:  # Need at least 3 elements
                            logger.info(f"Found {len(elements)} potential game elements with selector: {item_selector}")
                            
                            # Filter out navigation and other non-game elements
                            valid_games = []
                            
                            for idx, element in enumerate(elements[:30]):  # Limit to first 30
                                try:
                                    game_data = extract_game_data_improved(element, "offer")
                                    if game_data and is_valid_game_data(game_data):
                                        valid_games.append(game_data)
                                        logger.debug(f"Extracted valid offer {idx + 1}: {game_data.get('title', 'Unknown')}")
                                except Exception as e:
                                    logger.debug(f"Error extracting from element {idx + 1}: {e}")
                                    continue
                            
                            if valid_games:
                                logger.info(f"Successfully scraped {len(valid_games)} offers using selector: {item_selector}")
                                return valid_games
                                
                    except Exception as e:
                        logger.debug(f"Selector {item_selector} failed: {e}")
                        continue
            
            # If no games found with structured selectors, try alternative approach
            if not games:
                logger.warning("No games found with structured selectors, trying alternative extraction")
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


def extract_game_data_improved(element, game_type: str) -> Optional[Dict[str, Any]]:
    """Extract game data from an element with improved approach."""
    try:
        # Get all text content from the element
        text_content = element.inner_text().strip()
        
        # Skip if element is too small or contains only whitespace
        if len(text_content) < 5:
            return None
        
        # Skip navigation and promotional elements
        skip_patterns = [
            'newsletter',
            'subscribe',
            'categories',
            'partnership',
            'about us',
            'need help',
            'buyer protection',
            'market best prices',
            'feeling lucky',
            'reward program',
            'reviews',
            'spin the wheel',
            'link your steam',
            'gift cards',
            'discord',
            'twitch',
            'kick'
        ]
        
        for pattern in skip_patterns:
            if pattern in text_content.lower():
                return None
        
        # Try to extract title - look for text that could be a game title
        title = None
        
        # First try to find a title in nested elements
        title_selectors = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            '.title', '.name', '.game-title', '.product-name',
            '.game-name', '.product-title',
            'a[href*="game"]', 'a[href*="product"]',
            'strong', 'b'
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
            lines = text_content.split('\n')
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
                url = link_element.get_attribute('href')
                if url and not url.startswith('http'):
                    url = f"https://www.allkeyshop.com{url}"
        except:
            pass
        
        # Extract price information
        current_price = 0.0
        original_price = None
        discount_percentage = None
        
        # Look for price elements first
        price_selectors = [
            '.price', '.current-price', '.best-price', '.price-current',
            '.price-value', '.amount', '.cost', '.euro', '.dollar'
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
        
        # Extract store name
        store_name = None
        store_selectors = [
            '.store-name', '.shop-name', '.retailer', '.store',
            '.merchant', '.vendor', '.platform'
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
            store_indicators = ['Steam', 'Epic', 'GOG', 'Humble', 'Green Man Gaming', 'Fanatical', 'GamersGate', 'Origin', 'Uplay', 'Battle.net']
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
        logger.debug(f"Error in improved extraction: {e}")
        return None


def is_valid_game_title(title: str) -> bool:
    """Check if a title looks like a valid game title."""
    if not title or len(title) < 3 or len(title) > 150:
        return False
    
    # Skip common non-game elements
    invalid_patterns = [
        r'^\d+$',  # Just numbers
        r'^\d+[.,]\d+$',  # Just prices
        r'^\d+%$',  # Just percentages
        r'^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Dates
        r'^historical low',
        r'^subscribe',
        r'^newsletter',
        r'^categories',
        r'^partnership',
        r'^about us',
        r'^need help',
        r'^buyer protection',
        r'^market best prices',
        r'^official and',
        r'^feeling lucky',
        r'reward program',
        r'^\d+\s+reviews',
        r'^reviews$',
        r'^spin the wheel',
        r'^link your steam',
        r'^gift cards',
        r'^discord',
        r'^twitch',
        r'^kick',
        r'^xbox$',  # Just platform names
        r'^playstation$',
        r'^nintendo$',
        r'^steam$',
        r'^epic$',
        r'^free$',
        r'^n/a$',
        r'^\.\.\.$',
        r'^more$',
        r'^next$',
        r'^previous$',
        r'^page \d+',
        r'^\d+ \d+ \d+',
        r'^or win points',
        r'^join our',
        r'^how does it work',
        r'^\d+\s*€',  # Prices starting with numbers
        r'^€\s*\d+',  # Prices starting with currency
        r'^\$\s*\d+',  # Dollar prices
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, title.lower()):
            return False
    
    # Must contain at least one letter
    if not re.search(r'[a-zA-Z]', title):
        return False
    
    # Additional checks for common promotional text
    promotional_keywords = [
        'newsletter', 'subscribe', 'reward', 'program', 'lucky', 'wheel',
        'gift card', 'discord', 'twitch', 'partnership', 'protection',
        'best prices', 'official', 'keysellers', 'reviews'
    ]
    
    title_lower = title.lower()
    for keyword in promotional_keywords:
        if keyword in title_lower and len(title_lower) < 50:  # Short promotional text
            return False
    
    return True


def is_valid_game_data(game_data: Dict[str, Any]) -> bool:
    """Check if game data looks valid."""
    if not game_data or not game_data.get('title'):
        return False
    
    title = game_data['title']
    
    # Use the title validation function
    if not is_valid_game_title(title):
        return False
    
    # Additional validation for game data
    # Skip if title is too generic or common
    generic_titles = [
        'free', 'sale', 'deal', 'offer', 'discount', 'price', 'store',
        'game', 'product', 'item', 'card', 'box', 'container'
    ]
    
    if title.lower() in generic_titles:
        return False
    
    return True


def extract_games_alternative(page, game_type: str) -> List[Dict[str, Any]]:
    """Alternative extraction method for games."""
    try:
        # Try to find games by looking for specific patterns in the page
        games = []
        
        # Get page content
        content = page.content()
        
        # Look for game-related links
        game_links = page.query_selector_all('a[href*="game"], a[href*="product"]')
        
        for link in game_links[:20]:  # Limit to first 20 links
            try:
                # Get the parent container
                parent = link.locator('xpath=ancestor::div[1]')
                if parent:
                    game_data = extract_game_data_improved(parent, game_type)
                    if game_data and is_valid_game_data(game_data):
                        games.append(game_data)
            except:
                continue
        
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