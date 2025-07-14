"""Bargain Hunter ETL Module

This module aggregates deals and bargains from major deal hunting sites like
IsThereAnyDeal, CheapShark, Slickdeals, DealNews, and more.

Usage:
    python src/etl/deals/bargain_hunter_etl.py

Output:
    - JSON file: data/deals/bargain_deals.json
    - CSV file: data/deals/bargain_deals.csv
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests
from bs4 import BeautifulSoup
import re

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.etl.base import BaseETL

# Initialize logger
logger = get_logger("BargainHunterETL")

class BargainHunterETL(BaseETL):
    """ETL for bargain hunting and deal aggregation."""
    
    def __init__(self):
        super().__init__("bargain_deals")
        self.sources = {
            "isthereanydeal": {
                "name": "IsThereAnyDeal",
                "api_url": "https://api.isthereanydeal.com/v02/",
                "deals_url": "https://isthereanydeal.com/specials/",
                "category": "games"
            },
            "cheapshark": {
                "name": "CheapShark", 
                "api_url": "https://www.cheapshark.com/api/1.0/deals",
                "category": "games"
            },
            "gg_deals": {
                "name": "GG.deals",
                "url": "https://gg.deals/",
                "api_url": "https://gg.deals/api/",
                "category": "games"
            },
            "slickdeals": {
                "name": "Slickdeals",
                "rss_url": "https://slickdeals.net/newsearch.php?mode=popdeals&searcharea=deals&searchin=first&rss=1",
                "category": "general"
            },
            "dealnews": {
                "name": "DealNews",
                "rss_url": "https://www.dealnews.com/rss/all-deals.xml",
                "category": "general"
            }
        }

    def extract(self) -> Dict[str, Any]:
        """Extract bargain deals from multiple sources."""
        logger.info("Starting bargain hunter extraction...")
        
        all_deals = []
        
        # Extract from CheapShark API
        cheapshark_deals = self._extract_cheapshark_deals()
        all_deals.extend(cheapshark_deals)
        
        # Add curated deal sites and sources
        curated_deals = self._get_curated_bargain_sources()
        all_deals.extend(curated_deals)
        
        logger.info(f"Total extracted {len(all_deals)} bargain deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _extract_cheapshark_deals(self) -> List[Dict[str, Any]]:
        """Extract current deals from CheapShark API."""
        try:
            logger.info("Extracting deals from CheapShark API...")
            
            url = self.sources["cheapshark"]["api_url"]
            params = {
                'storeID': '1,7,11,13,15,21,24,25',  # Major stores
                'upperPrice': '50',  # Under $50
                'metacritic': '70',  # Good reviews
                'pageSize': '20'
            }
            
            headers = {
                'User-Agent': 'Watchtower/1.0 (Educational Research Bot)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            deals_data = response.json()
            
            deals = []
            for deal in deals_data:
                try:
                    # Calculate savings
                    normal_price = float(deal.get('normalPrice', 0))
                    sale_price = float(deal.get('salePrice', 0))
                    savings = normal_price - sale_price
                    discount_percent = 0
                    if normal_price > 0:
                        discount_percent = round((savings / normal_price) * 100, 2)
                    
                    # Get store info
                    store_id = deal.get('storeID', '')
                    store_name = self._get_store_name(store_id)
                    
                    # Determine deal urgency
                    deal_rating = float(deal.get('dealRating', 0))
                    
                    deals.append({
                        'title': deal.get('title', 'Unknown Game'),
                        'description': f"Game deal with {discount_percent}% off. Metacritic score: {deal.get('metacriticScore', 'N/A')}",
                        'url': f"https://www.cheapshark.com/redirect?dealID={deal.get('dealID', '')}",
                        'platform': 'CheapShark',
                        'category': 'games',
                        'deal_type': 'price_drop',
                        'original_price': normal_price,
                        'current_price': sale_price,
                        'savings': savings,
                        'discount_percentage': discount_percent,
                        'store_name': store_name,
                        'deal_rating': deal_rating,
                        'metacritic_score': deal.get('metacriticScore'),
                        'steam_rating': deal.get('steamRatingPercent'),
                        'release_date': deal.get('releaseDate'),
                        'last_change': deal.get('lastChange'),
                        'tags': self._extract_game_tags(deal),
                        'created_date': datetime.now(timezone.utc).isoformat(),
                        'fetched_at': datetime.now(timezone.utc).isoformat(),
                        'source': 'CheapShark API'
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing CheapShark deal: {e}")
                    continue
            
            logger.info(f"Extracted {len(deals)} deals from CheapShark")
            return deals
            
        except Exception as e:
            logger.error(f"Error extracting from CheapShark: {e}")
            return []

    def _get_store_name(self, store_id: str) -> str:
        """Get store name from store ID."""
        store_map = {
            '1': 'Steam',
            '2': 'GamersGate',
            '3': 'GreenManGaming',
            '7': 'GOG',
            '8': 'Origin',
            '11': 'Humble Store',
            '13': 'Uplay',
            '15': 'Fanatical',
            '21': 'WinGameStore',
            '24': 'Epic Games Store',
            '25': 'Microsoft Store'
        }
        return store_map.get(store_id, f'Store {store_id}')

    def _extract_game_tags(self, deal: Dict[str, Any]) -> List[str]:
        """Extract tags for game deals."""
        tags = []
        
        # Add platform tag
        title = deal.get('title', '').lower()
        if 'steam' in title:
            tags.append('steam')
        
        # Add rating tags
        metacritic = deal.get('metacriticScore')
        if metacritic:
            try:
                score = int(metacritic)
                if score >= 90:
                    tags.append('highly rated')
                elif score >= 75:
                    tags.append('well rated')
            except:
                pass
        
        # Add discount tier tags
        deal_rating = float(deal.get('dealRating', 0))
        if deal_rating >= 8:
            tags.append('hot deal')
        elif deal_rating >= 6:
            tags.append('good deal')
        
        return tags

    def _get_curated_bargain_sources(self) -> List[Dict[str, Any]]:
        """Get manually curated list of bargain hunting sources."""
        curated = [
            {
                'title': 'IsThereAnyDeal - Game Price Tracker',
                'description': 'Comprehensive game price tracking across 60+ stores with historical data',
                'url': 'https://isthereanydeal.com/',
                'platform': 'IsThereAnyDeal',
                'category': 'games',
                'deal_type': 'price_tracking',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Multiple',
                'features': ['price alerts', 'historical data', 'wishlist sync'],
                'stores_covered': 60,
                'tags': ['price tracking', 'historical data', 'alerts'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'Slickdeals Community',
                'description': 'Community-driven deal sharing platform with user voting and verification',
                'url': 'https://slickdeals.net/',
                'platform': 'Slickdeals',
                'category': 'general',
                'deal_type': 'community_deals',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Various',
                'features': ['community voting', 'deal alerts', 'cashback'],
                'tags': ['community driven', 'verified deals', 'all categories'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'DealNews Daily Deals',
                'description': 'Hand-picked deals across electronics, clothing, home goods, and more',
                'url': 'https://www.dealnews.com/',
                'platform': 'DealNews',
                'category': 'general',
                'deal_type': 'curated_deals',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Various',
                'features': ['editor curated', 'price history', 'deal alerts'],
                'tags': ['curated', 'electronics', 'home goods'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'Woot! Daily Deals',
                'description': 'Amazon-owned daily deals site with limited quantities and flash sales',
                'url': 'https://www.woot.com/',
                'platform': 'Woot!',
                'category': 'electronics',
                'deal_type': 'daily_deals',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Woot!',
                'features': ['daily rotation', 'limited quantities', 'flash sales'],
                'tags': ['daily deals', 'electronics', 'amazon'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'RetailMeNot Coupons & Cashback',
                'description': 'Coupon codes, cashback offers, and promotional deals across major retailers',
                'url': 'https://www.retailmenot.com/',
                'platform': 'RetailMeNot',
                'category': 'coupons',
                'deal_type': 'coupons_cashback',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Various',
                'features': ['coupon codes', 'cashback', 'browser extension'],
                'tags': ['coupons', 'cashback', 'browser extension'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'Honey Browser Extension',
                'description': 'Automatic coupon code testing and price tracking across thousands of sites',
                'url': 'https://www.joinhoney.com/',
                'platform': 'Honey',
                'category': 'shopping_tools',
                'deal_type': 'automated_savings',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Browser Extension',
                'features': ['auto coupon testing', 'price tracking', 'droplist'],
                'tags': ['browser extension', 'automated', 'price tracking'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'Rakuten Cashback',
                'description': 'Earn cashback on purchases from 3,500+ stores with additional coupon codes',
                'url': 'https://www.rakuten.com/',
                'platform': 'Rakuten',
                'category': 'cashback',
                'deal_type': 'cashback_rewards',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Rakuten Portal',
                'features': ['cashback rewards', 'coupon stacking', 'price alerts'],
                'tags': ['cashback', 'rewards', 'coupon stacking'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'GG.deals Game Price Comparison',
                'description': 'Game price comparison across authorized resellers with key shops warnings',
                'url': 'https://gg.deals/',
                'platform': 'GG.deals',
                'category': 'games',
                'deal_type': 'price_comparison',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Multiple',
                'features': ['authorized sellers only', 'price history', 'wishlist alerts'],
                'tags': ['authorized sellers', 'price comparison', 'game deals'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            },
            {
                'title': 'Amazon Lightning Deals',
                'description': 'Time-limited deals with significant discounts on popular Amazon products',
                'url': 'https://www.amazon.com/gp/goldbox',
                'platform': 'Amazon',
                'category': 'general',
                'deal_type': 'lightning_deals',
                'original_price': 0,
                'current_price': 0,
                'savings': 0,
                'discount_percentage': 0,
                'store_name': 'Amazon',
                'features': ['time limited', 'quantity limited', 'prime benefits'],
                'tags': ['lightning deals', 'amazon', 'time limited'],
                'created_date': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'source': 'Curated'
            }
        ]
        
        logger.info(f"Added {len(curated)} curated bargain sources")
        return curated

    def transform(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform bargain deals data."""
        logger.info("Starting bargain deals transformation...")
        
        deals = raw_data.get("deals", [])
        transformed_deals = []
        
        for deal in deals:
            try:
                # Clean up title
                title = deal['title'].strip()
                if len(title) > 200:
                    title = title[:197] + "..."
                
                # Calculate bargain score
                bargain_score = self._calculate_bargain_score(deal)
                
                # Determine deal urgency
                urgency = self._determine_deal_urgency(deal)
                
                transformed_deal = {
                    'title': title,
                    'description': deal.get('description', '')[:500],
                    'url': deal['url'],
                    'platform': deal['platform'],
                    'category': deal['category'],
                    'deal_type': deal['deal_type'],
                    'original_price': deal.get('original_price', 0),
                    'current_price': deal.get('current_price', 0),
                    'savings': deal.get('savings', 0),
                    'discount_percentage': deal.get('discount_percentage', 0),
                    'bargain_score': bargain_score,
                    'urgency': urgency,
                    'store_name': deal.get('store_name', 'Unknown'),
                    'deal_rating': deal.get('deal_rating'),
                    'metacritic_score': deal.get('metacritic_score'),
                    'features': deal.get('features', []),
                    'tags': deal.get('tags', []),
                    'created_date': deal.get('created_date'),
                    'fetched_at': deal['fetched_at'],
                    'source': deal['source']
                }
                
                transformed_deals.append(transformed_deal)
                
            except Exception as e:
                logger.warning(f"Error transforming bargain deal: {e}")
                continue
        
        # Sort by bargain score and savings
        transformed_deals.sort(key=lambda x: (x['bargain_score'], x['savings']), reverse=True)
        
        logger.info(f"Transformed {len(transformed_deals)} bargain deals")
        return transformed_deals

    def _calculate_bargain_score(self, deal: Dict[str, Any]) -> float:
        """Calculate bargain score for ranking deals."""
        score = 0.0
        
        # Platform reliability weight
        platform = deal.get('platform', '').lower()
        if any(name in platform for name in ['cheapshark', 'isthereanydeal']):
            score += 5.0
        elif any(name in platform for name in ['slickdeals', 'dealnews']):
            score += 4.5
        elif any(name in platform for name in ['amazon', 'woot']):
            score += 4.0
        else:
            score += 2.0
        
        # Deal type weight
        deal_type = deal.get('deal_type', '')
        if deal_type == 'price_drop':
            score += 4.0
        elif deal_type in ['lightning_deals', 'daily_deals']:
            score += 3.5
        elif deal_type in ['community_deals', 'curated_deals']:
            score += 3.0
        elif deal_type in ['price_tracking', 'price_comparison']:
            score += 2.5
        
        # Savings consideration
        savings = deal.get('savings', 0)
        discount_percent = deal.get('discount_percentage', 0)
        
        if savings > 50 or discount_percent > 70:
            score += 3.0
        elif savings > 25 or discount_percent > 50:
            score += 2.0
        elif savings > 10 or discount_percent > 30:
            score += 1.0
        
        # Quality indicators (for games)
        metacritic = deal.get('metacritic_score')
        if metacritic:
            try:
                score_val = int(metacritic)
                if score_val >= 90:
                    score += 2.0
                elif score_val >= 75:
                    score += 1.0
            except:
                pass
        
        # Deal rating (for CheapShark)
        deal_rating = deal.get('deal_rating')
        if deal_rating:
            try:
                rating = float(deal_rating)
                if rating >= 8:
                    score += 2.0
                elif rating >= 6:
                    score += 1.0
            except:
                pass
        
        return round(score, 2)

    def _determine_deal_urgency(self, deal: Dict[str, Any]) -> str:
        """Determine urgency level of the deal."""
        deal_type = deal.get('deal_type', '')
        platform = deal.get('platform', '').lower()
        
        if deal_type in ['lightning_deals', 'flash_sales']:
            return 'high'
        elif deal_type == 'daily_deals' or 'woot' in platform:
            return 'medium'
        elif deal_type in ['price_drop', 'community_deals']:
            return 'low'
        else:
            return 'none'

    def load(self, transformed_data: List[Dict[str, Any]]) -> bool:
        """Load transformed bargain deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])
            
            # Save as JSON
            json_path = os.path.join(output_dir, "bargain_deals.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)
            
            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "bargain_deals.csv")
                import pandas as pd
                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding='utf-8')
            
            logger.info(f"Successfully saved {len(transformed_data)} bargain deals to {output_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving bargain deals data: {e}")
            return False


def main():
    """Main function to run the Bargain Hunter ETL."""
    etl = BargainHunterETL()
    success = etl.run()
    
    if success:
        logger.info("Bargain Hunter ETL completed successfully")
    else:
        logger.error("Bargain Hunter ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()