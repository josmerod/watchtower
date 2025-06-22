"""AllKeyShop Games ETL for scraping game deals from AllKeyShop.com.

This ETL scrapes game deals from AllKeyShop with different sorting criteria:
- Deal score (best deals first)
- Default sorting (newest deals)
- Price (lowest price first with quality filter)

Extracts comprehensive game deal information including prices, discounts, 
store ratings, and deal scores.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import pandas as pd

from etl.base import BaseETL
from models.games import AllKeyShopGameModel, GamePlatform
from utils.logging import get_logger


class AllKeyShopETL(BaseETL):
    """ETL for scraping AllKeyShop game deals."""
    
    def __init__(self, max_pages: int = 10, **kwargs):
        """Initialize AllKeyShop ETL.
        
        Args:
            max_pages: Maximum pages to scrape per sorting criteria
        """
        super().__init__(
            name="allkeyshop_games",
            description="AllKeyShop game deals scraper with multiple sorting criteria",
            **kwargs
        )
        self.logger = get_logger("ETL.AllKeyShop")
        self.max_pages = max_pages
        
        # Base URLs for different sorting criteria
        self.base_urls = {
            'deal_score': 'https://www.allkeyshop.com/blog/products/?sort_field=deal_score&sort_order=desc&type=game&operating_systems=pc',
            'default': 'https://www.allkeyshop.com/blog/products/?type=game&operating_systems=pc',
            'price_asc': 'https://www.allkeyshop.com/blog/products/?sort_field=price&sort_order=asc&type=game&operating_systems=pc&price_min=1&rating_min=80'
        }
        
        # Request headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Delay between requests to be respectful
        self.request_delay = 2
        
    def extract(self) -> List[Dict[str, Any]]:
        """Extract game deals from AllKeyShop with different sorting criteria."""
        self.logger.info("Starting AllKeyShop game deals extraction 🎮")
        all_games = []
        
        for sort_criteria, base_url in self.base_urls.items():
            self.logger.info(f"Extracting games with sorting: {sort_criteria}")
            
            try:
                games_for_criteria = self._extract_games_for_criteria(
                    sort_criteria, base_url
                )
                all_games.extend(games_for_criteria)
                self.metrics.records_extracted += len(games_for_criteria)
                
                # Respect rate limits
                time.sleep(self.request_delay)
                
            except Exception as e:
                self.logger.error(f"Failed to extract games for {sort_criteria}: {e}")
                self.metrics.records_failed += 1
                continue
        
        self.logger.info(f"Total games extracted: {len(all_games)}")
        return all_games
    
    def _extract_games_for_criteria(self, sort_criteria: str, base_url: str) -> List[Dict[str, Any]]:
        """Extract games for a specific sorting criteria."""
        games = []
        
        for page_num in range(1, self.max_pages + 1):
            try:
                # Construct page URL
                page_url = f"{base_url}&pagenum={page_num}"
                self.logger.debug(f"Scraping page {page_num} for {sort_criteria}: {page_url}")
                
                # Make request
                response = requests.get(page_url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract games from this page
                page_games = self._parse_games_from_page(soup, sort_criteria, page_num)
                
                if not page_games:
                    self.logger.info(f"No games found on page {page_num} for {sort_criteria}, stopping")
                    break
                
                games.extend(page_games)
                self.logger.debug(f"Extracted {len(page_games)} games from page {page_num}")
                
                # Respect rate limits
                time.sleep(self.request_delay)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed for page {page_num} of {sort_criteria}: {e}")
                break
            except Exception as e:
                self.logger.error(f"Error processing page {page_num} of {sort_criteria}: {e}")
                continue
        
        return games
    
    def _parse_games_from_page(self, soup: BeautifulSoup, sort_criteria: str, page_num: int) -> List[Dict[str, Any]]:
        """Parse games from a single page."""
        games = []
        
        # AllKeyShop uses different selectors, we need to find the game containers
        # These selectors may need adjustment based on the actual HTML structure
        game_containers = soup.find_all('div', class_=['product-item', 'game-item', 'deal-item'])
        
        # If the above doesn't work, try alternative selectors
        if not game_containers:
            game_containers = soup.find_all('article', class_=['product', 'game'])
        
        # Fallback to more generic selectors
        if not game_containers:
            game_containers = soup.find_all('div', attrs={'data-product-id': True})
        
        # Last resort - look for any div with game-related content
        if not game_containers:
            game_containers = soup.find_all('div', string=re.compile(r'game|deal|price', re.I))
            
        self.logger.debug(f"Found {len(game_containers)} potential game containers")
        
        for container in game_containers:
            try:
                game_data = self._extract_game_from_container(container, sort_criteria, page_num)
                if game_data:
                    games.append(game_data)
            except Exception as e:
                self.logger.debug(f"Error parsing game container: {e}")
                continue
        
        # If we still don't have games, try a different approach
        if not games:
            games = self._fallback_game_extraction(soup, sort_criteria, page_num)
        
        return games
    
    def _extract_game_from_container(self, container: BeautifulSoup, sort_criteria: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Extract game data from a container element."""
        game_data = {
            'sort_criteria': sort_criteria,
            'page_number': page_num,
            'extracted_at': datetime.utcnow().isoformat()
        }
        
        # Extract title
        title_elem = container.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'title|name|product', re.I))
        if not title_elem:
            title_elem = container.find(['a', 'span'], class_=re.compile(r'title|name', re.I))
        
        if title_elem:
            game_data['title'] = title_elem.get_text(strip=True)
        else:
            # Skip if no title found
            return None
        
        # Extract URL
        url_elem = container.find('a', href=True)
        if url_elem:
            href = url_elem['href']
            if href.startswith('/'):
                game_data['url'] = urljoin('https://www.allkeyshop.com', href)
            else:
                game_data['url'] = href
        
        # Extract image URL
        img_elem = container.find('img', src=True)
        if img_elem:
            src = img_elem['src']
            if src.startswith('/'):
                game_data['image_url'] = urljoin('https://www.allkeyshop.com', src)
            else:
                game_data['image_url'] = src
        
        # Extract prices
        self._extract_price_info(container, game_data)
        
        # Extract deal score
        score_elem = container.find(string=re.compile(r'\d+%|\d+/100', re.I))
        if score_elem:
            score_match = re.search(r'(\d+)', score_elem)
            if score_match:
                game_data['deal_score'] = int(score_match.group(1))
        
        # Extract store information
        store_elem = container.find(string=re.compile(r'store|shop', re.I))
        if store_elem:
            game_data['store_name'] = store_elem.strip()
        
        # Extract rating if available
        rating_elem = container.find(string=re.compile(r'\d+\.\d+|\d+/10', re.I))
        if rating_elem:
            rating_match = re.search(r'(\d+\.?\d*)', rating_elem)
            if rating_match:
                game_data['rating'] = float(rating_match.group(1))
        
        return game_data
    
    def _extract_price_info(self, container: BeautifulSoup, game_data: Dict[str, Any]) -> None:
        """Extract price information from container."""
        # First, look for explicit attributes that often store numeric price values
        prices = []

        # 1) Data attributes commonly used by AllKeyShop (e.g., data-price-final)
        for attr in [
            "data-price", "data-price-final", "data-price-discount", "data-price-amount"
        ]:
            attr_val = container.get(attr)
            if attr_val:
                match = re.search(r"(\d+\.?\d*)", str(attr_val))
                if match:
                    prices.append(float(match.group(1)))

        # 2) Text inside elements that contain price symbols (€, $, £)
        price_elements = container.find_all(string=re.compile(r"[€$£]\s?\d+|\d+\.?\d*\s?[€$£]", re.I))
        for price_elem in price_elements:
            price_match = re.search(r"(\d+\.?\d*)", str(price_elem))
            if price_match:
                prices.append(float(price_match.group(1)))

        # Deduplicate and sort prices to make stable assignments
        if prices:
            prices = sorted(set(prices))

            # Assume the lowest price is the current price (best offer)
            game_data['current_price'] = prices[0]

            # If there is a higher price, treat it as the original list price
            if len(prices) > 1:
                game_data['original_price'] = prices[-1]
        
        # Extract discount percentage (e.g., "-75%" or "75% off")
        discount_elem = container.find(string=re.compile(r"-\s?\d+%|\d+%\s?off", re.I))
        if discount_elem:
            discount_match = re.search(r"(\d+)", discount_elem)
            if discount_match:
                game_data['discount_percentage'] = int(discount_match.group(1))
    
    def _fallback_game_extraction(self, soup: BeautifulSoup, sort_criteria: str, page_num: int) -> List[Dict[str, Any]]:
        """Fallback method to extract games when standard selectors fail."""
        games = []
        
        # Look for any links that might be game URLs
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Skip if it's not a game-related link
            if not any(keyword in href.lower() for keyword in ['game', 'deal', 'product']):
                continue
            
            if len(text) < 3:  # Skip very short texts
                continue
            
            game_data = {
                'title': text,
                'url': urljoin('https://www.allkeyshop.com', href) if href.startswith('/') else href,
                'sort_criteria': sort_criteria,
                'page_number': page_num,
                'extracted_at': datetime.utcnow().isoformat()
            }
            
            games.append(game_data)
            
            # Limit fallback results
            if len(games) >= 20:
                break
        
        return games
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw game data into structured format."""
        self.logger.info(f"Transforming {len(data)} game records 🔧")
        transformed_games = []
        
        for game_data in data:
            try:
                # Clean and validate data
                cleaned_data = self._clean_game_data(game_data)
                
                # Skip if essential data is missing
                if (
                    not cleaned_data.get('title') or not cleaned_data.get('url') or
                    (
                        cleaned_data.get('current_price') is None and
                        cleaned_data.get('discount_percentage') is None
                    )
                ):
                    self.metrics.records_failed += 1
                    continue
                
                # Add calculated fields
                self._add_calculated_fields(cleaned_data)
                
                transformed_games.append(cleaned_data)
                self.metrics.records_transformed += 1
                
            except Exception as e:
                self.logger.error(f"Failed to transform game record: {e}")
                self.metrics.records_failed += 1
                continue
        
        return transformed_games
    
    def _clean_game_data(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize game data."""
        cleaned = game_data.copy()
        
        # Clean title
        if 'title' in cleaned:
            cleaned['title'] = re.sub(r'\s+', ' ', cleaned['title']).strip()
        
        # Ensure prices are numeric
        for price_field in ['current_price', 'original_price']:
            if price_field in cleaned and cleaned[price_field]:
                try:
                    cleaned[price_field] = float(cleaned[price_field])
                except (ValueError, TypeError):
                    cleaned[price_field] = None
        
        # Ensure integers are integers
        for int_field in ['deal_score', 'discount_percentage', 'metacritic_score']:
            if int_field in cleaned and cleaned[int_field]:
                try:
                    cleaned[int_field] = int(cleaned[int_field])
                except (ValueError, TypeError):
                    cleaned[int_field] = None
        
        # Set platform
        cleaned['platform'] = GamePlatform.PC.value
        
        # Detect DLC
        title_lower = cleaned.get('title', '').lower()
        cleaned['is_dlc'] = any(keyword in title_lower for keyword in ['dlc', 'expansion', 'season pass'])
        
        return cleaned
    
    def _add_calculated_fields(self, game_data: Dict[str, Any]) -> None:
        """Add calculated fields to game data."""
        # Calculate discount percentage if not provided
        if (not game_data.get('discount_percentage') and 
            game_data.get('original_price') and 
            game_data.get('current_price')):
            
            original = game_data['original_price']
            current = game_data['current_price']
            if original > current:
                discount = int(((original - current) / original) * 100)
                game_data['discount_percentage'] = discount
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Load game deals data to storage."""
        self.logger.info(f"Loading {len(data)} AllKeyShop game deals 💾")
        
        # Save complete data
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f"allkeyshop_games_{timestamp}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Save latest data
            latest_file = self.output_dir / "latest_allkeyshop_games.json"
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Create CSV export
            if data:
                df = pd.DataFrame(data)
                csv_file = self.output_dir / f"allkeyshop_games_{timestamp}.csv"
                df.to_csv(csv_file, index=False, encoding='utf-8')
            
            # Create filtered datasets
            self._create_filtered_datasets(data)
            
            self.logger.info(f"AllKeyShop games data saved to {output_file}")
            self.metrics.records_loaded = len(data)
            
            # Log useful stats
            self._log_extraction_stats(data)
            
        except Exception as e:
            self.logger.error(f"Failed to save AllKeyShop games data: {e}")
            raise
    
    def _create_filtered_datasets(self, data: List[Dict[str, Any]]) -> None:
        """Create filtered datasets for specific use cases."""
        # Best deals (high discount or deal score)
        best_deals = [
            game for game in data 
            if (game.get('discount_percentage', 0) >= 50 or 
                game.get('deal_score', 0) >= 80)
        ]
        
        # Budget games (under €10)
        budget_games = [
            game for game in data 
            if game.get('current_price', float('inf')) <= 10
        ]
        
        # Premium games (over €30)
        premium_games = [
            game for game in data 
            if game.get('current_price', 0) >= 30
        ]
        
        # Free games
        free_games = [
            game for game in data 
            if game.get('current_price', 1) == 0
        ]
        
        # Save filtered datasets
        filters = {
            'best_deals.json': best_deals,
            'budget_games.json': budget_games,
            'premium_games.json': premium_games,
            'free_games.json': free_games
        }
        
        for filename, filtered_data in filters.items():
            if filtered_data:
                with open(self.output_dir / filename, 'w', encoding='utf-8') as f:
                    json.dump(filtered_data, f, indent=2, default=str)
    
    def _log_extraction_stats(self, data: List[Dict[str, Any]]) -> None:
        """Log extraction statistics."""
        if not data:
            return
        
        # Group by sort criteria
        by_criteria = {}
        for game in data:
            criteria = game.get('sort_criteria', 'unknown')
            by_criteria[criteria] = by_criteria.get(criteria, 0) + 1
        
        # Price statistics
        prices = [game.get('current_price') for game in data if game.get('current_price')]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
        else:
            avg_price = min_price = max_price = 0
        
        # Discount statistics
        discounts = [game.get('discount_percentage') for game in data if game.get('discount_percentage')]
        avg_discount = sum(discounts) / len(discounts) if discounts else 0
        
        self.logger.info(f"Extraction summary:")
        self.logger.info(f"  - Total games: {len(data)}")
        self.logger.info(f"  - By criteria: {by_criteria}")
        self.logger.info(f"  - Price range: €{min_price:.2f} - €{max_price:.2f} (avg: €{avg_price:.2f})")
        self.logger.info(f"  - Average discount: {avg_discount:.1f}%")
        self.logger.info(f"  - Games with discounts: {len(discounts)}")


def get_allkeyshop():
    """Run the AllKeyShop ETL process."""
    etl = AllKeyShopETL(max_pages=10)
    metrics = etl.run()
    return metrics


if __name__ == "__main__":
    get_allkeyshop() 