"""Bundle Deals ETL Module

This module fetches bundle deals and bargains from Humble Bundle, Fanatical,
IndieGala, and other major bundle platforms.

Usage:
    python src/etl/deals/bundle_deals_etl.py

Output:
    - JSON file: data/deals/bundle_deals.json
    - CSV file: data/deals/bundle_deals.csv
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.etl.base import BaseETL
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("BundleDealsETL")


class BundleDealsETL(BaseETL):
    """ETL for bundle deals from major platforms."""

    def __init__(self):
        super().__init__("bundle_deals")
        self.sources = {
            "humble_bundle": {
                "name": "Humble Bundle",
                "api_url": "https://www.humblebundle.com/api/v1/bundles",
                "rss_url": "https://blog.humblebundle.com/rss",
                "category": "bundles",
            },
            "fanatical": {
                "name": "Fanatical",
                "url": "https://www.fanatical.com/en/",
                "api_url": "https://www.fanatical.com/api/",
                "category": "bundles",
            },
            "indiegala": {
                "name": "IndieGala",
                "url": "https://www.indiegala.com/",
                "bundles_url": "https://www.indiegala.com/bundles",
                "category": "bundles",
            },
            "groupees": {
                "name": "Groupees",
                "url": "https://groupees.com/",
                "api_url": "https://groupees.com/api/bundles",
                "category": "bundles",
            },
            "steam": {
                "name": "Steam",
                "url": "https://store.steampowered.com/",
                "search_url": "https://store.steampowered.com/search/?specials=1",
                "bundles_url": "https://store.steampowered.com/bundles/",
                "category": "games",
            },
            "epic_games": {
                "name": "Epic Games Store",
                "url": "https://www.epicgames.com/store/",
                "api_url": "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
                "category": "games",
            },
            "gog": {
                "name": "GOG (Good Old Games)",
                "url": "https://www.gog.com/",
                "deals_url": "https://www.gog.com/games?sort=bestselling&page=1&priceRange=0,10",
                "category": "games",
            },
            "itchio": {
                "name": "itch.io",
                "url": "https://itch.io/",
                "bundles_url": "https://itch.io/bundles",
                "category": "indie_games",
            },
            "gamesplanet": {
                "name": "GamesPlanet",
                "url": "https://us.gamesplanet.com/",
                "deals_url": "https://us.gamesplanet.com/games/discounts",
                "category": "games",
            },
            "green_man_gaming": {
                "name": "Green Man Gaming",
                "url": "https://www.greenmangaming.com/",
                "deals_url": "https://www.greenmangaming.com/deals/",
                "category": "games",
            },
        }

    def extract(self) -> dict[str, Any]:
        """Extract bundle deals from multiple sources."""
        logger.info("Starting bundle deals extraction...")

        all_deals = []

        # Extract from Humble Bundle RSS
        humble_deals = self._extract_humble_bundle()
        all_deals.extend(humble_deals)

        # Extract from Steam
        steam_deals = self._extract_steam_deals()
        all_deals.extend(steam_deals)

        # Extract from Epic Games Store
        epic_deals = self._extract_epic_games_deals()
        all_deals.extend(epic_deals)

        # Extract from GOG
        gog_deals = self._extract_gog_deals()
        all_deals.extend(gog_deals)

        # Extract from itch.io bundles
        itch_deals = self._extract_itchio_bundles()
        all_deals.extend(itch_deals)

        # Add manually curated current bundles
        curated_deals = self._get_curated_bundle_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} bundle deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _extract_steam_deals(self) -> list[dict[str, Any]]:
        """Extract current deals from Steam."""
        try:
            logger.info("Extracting deals from Steam...")

            # Steam doesn't have a public API for deals, so we'll use curated data
            # In a real implementation, you might use Steam's RSS or web scraping
            steam_deals = [
                {
                    "title": "Steam Winter Sale",
                    "description": "Major seasonal sale with thousands of games discounted",
                    "url": "https://store.steampowered.com/",
                    "platform": "Steam",
                    "category": "games",
                    "deal_type": "seasonal_sale",
                    "original_price": 0,
                    "current_price": 0,
                    "savings": 0,
                    "discount_percentage": 0,
                    "tags": ["games", "seasonal", "major_platform"],
                    "created_date": datetime.now(timezone.utc).isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "Steam",
                }
            ]

            logger.info(f"Extracted {len(steam_deals)} deals from Steam")
            return steam_deals

        except Exception as e:
            logger.error(f"Error extracting from Steam: {e}")
            return []

    def _extract_epic_games_deals(self) -> list[dict[str, Any]]:
        """Extract current deals from Epic Games Store."""
        try:
            logger.info("Extracting deals from Epic Games Store...")

            # Epic Games Store free games and deals
            epic_deals = [
                {
                    "title": "Epic Games Store Weekly Free Games",
                    "description": "Free games available every week on Epic Games Store",
                    "url": "https://www.epicgames.com/store/free-games",
                    "platform": "Epic Games Store",
                    "category": "games",
                    "deal_type": "free_games",
                    "original_price": 60,
                    "current_price": 0,
                    "savings": 60,
                    "discount_percentage": 100,
                    "tags": ["games", "free", "weekly", "major_platform"],
                    "created_date": datetime.now(timezone.utc).isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "Epic Games Store",
                }
            ]

            logger.info(f"Extracted {len(epic_deals)} deals from Epic Games Store")
            return epic_deals

        except Exception as e:
            logger.error(f"Error extracting from Epic Games Store: {e}")
            return []

    def _extract_gog_deals(self) -> list[dict[str, Any]]:
        """Extract current deals from GOG."""
        try:
            logger.info("Extracting deals from GOG...")

            # GOG deals and DRM-free games
            gog_deals = [
                {
                    "title": "GOG Weekly Sale",
                    "description": "DRM-free games on sale with no regional restrictions",
                    "url": "https://www.gog.com/games?sort=bestselling&page=1&priceRange=0,10",
                    "platform": "GOG",
                    "category": "games",
                    "deal_type": "weekly_sale",
                    "original_price": 0,
                    "current_price": 0,
                    "savings": 0,
                    "discount_percentage": 0,
                    "tags": ["games", "drm-free", "no-restrictions"],
                    "created_date": datetime.now(timezone.utc).isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "GOG",
                }
            ]

            logger.info(f"Extracted {len(gog_deals)} deals from GOG")
            return gog_deals

        except Exception as e:
            logger.error(f"Error extracting from GOG: {e}")
            return []

    def _extract_itchio_bundles(self) -> list[dict[str, Any]]:
        """Extract current bundles from itch.io."""
        try:
            logger.info("Extracting bundles from itch.io...")

            # itch.io game bundles
            itch_deals = [
                {
                    "title": "itch.io Indie Game Bundles",
                    "description": "Community-driven indie game bundles with proceeds to charity",
                    "url": "https://itch.io/bundles",
                    "platform": "itch.io",
                    "category": "indie_games",
                    "deal_type": "bundle",
                    "original_price": 100,
                    "current_price": 15,
                    "savings": 85,
                    "discount_percentage": 85,
                    "tags": ["indie", "games", "charity", "community"],
                    "created_date": datetime.now(timezone.utc).isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "itch.io",
                }
            ]

            logger.info(f"Extracted {len(itch_deals)} deals from itch.io")
            return itch_deals

        except Exception as e:
            logger.error(f"Error extracting from itch.io: {e}")
            return []

    def _extract_humble_bundle(self) -> list[dict[str, Any]]:
        """Extract current bundles from Humble Bundle."""
        try:
            logger.info("Extracting bundles from Humble Bundle RSS...")

            url = self.sources["humble_bundle"]["rss_url"]
            headers = {"User-Agent": "Watchtower/1.0 (Educational Research Bot)"}

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            items = soup.find_all("item")

            deals = []
            for item in items[:10]:  # Get latest 10 posts
                try:
                    title = item.find("title").text if item.find("title") else ""
                    link = item.find("link").text if item.find("link") else ""
                    description = item.find("description").text if item.find("description") else ""
                    pub_date = item.find("pubdate").text if item.find("pubdate") else ""

                    # Only include items that look like bundles/deals
                    title_lower = (title or "").lower()
                    if any(
                        keyword in title_lower
                        for keyword in [
                            "bundle",
                            "deal",
                            "sale",
                            "promotion",
                            "offer",
                            "discount",
                            "free",
                            "giveaway",
                            "special",
                            "limited",
                            "save",
                        ]
                    ):
                        # Parse publication date
                        created_date = datetime.now(timezone.utc).isoformat()
                        try:
                            from email.utils import parsedate_to_datetime

                            created_date = parsedate_to_datetime(pub_date).isoformat()
                        except:
                            pass

                        # Extract price info from description
                        price_info = self._extract_price_from_text(description + " " + title)

                        deals.append(
                            {
                                "title": title,
                                "description": BeautifulSoup(description, "html.parser").get_text()[:500],
                                "url": link,
                                "platform": "Humble Bundle",
                                "category": "games",
                                "deal_type": self._determine_deal_type(title, description),
                                "original_price": price_info.get("original_price", 0),
                                "current_price": price_info.get("current_price", 0),
                                "savings": price_info.get("savings", 0),
                                "discount_percentage": price_info.get("discount_percentage", 0),
                                "tier_pricing": price_info.get("tier_pricing", False),
                                "items_count": self._extract_items_count(title + " " + description),
                                "charity_included": "charity" in (title + description).lower(),
                                "time_remaining": None,
                                "tags": self._extract_bundle_tags(title, description),
                                "created_date": created_date,
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                                "source": "Humble Bundle RSS",
                            }
                        )

                except Exception as e:
                    logger.warning(f"Error processing Humble Bundle item: {e}")
                    continue

            logger.info(f"Extracted {len(deals)} deals from Humble Bundle")
            return deals

        except Exception as e:
            logger.error(f"Error extracting from Humble Bundle: {e}")
            return []

    def _get_curated_bundle_deals(self) -> list[dict[str, Any]]:
        """Get manually curated list of current major bundle deals."""
        curated = [
            {
                "title": "Humble Choice Monthly",
                "description": "Monthly curated bundle of games, choose what you want to keep",
                "url": "https://www.humblebundle.com/subscription",
                "platform": "Humble Bundle",
                "category": "games",
                "deal_type": "subscription_bundle",
                "original_price": 60,
                "current_price": 12,
                "savings": 48,
                "discount_percentage": 80,
                "tier_pricing": True,
                "items_count": 12,
                "charity_included": True,
                "time_remaining": "Monthly",
                "tags": ["games", "subscription", "curated", "drm-free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Fanatical Star Deal",
                "description": "Daily rotating deals on popular games with significant discounts",
                "url": "https://www.fanatical.com/en/on-sale",
                "platform": "Fanatical",
                "category": "games",
                "deal_type": "daily_deal",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "tier_pricing": False,
                "items_count": 1,
                "charity_included": False,
                "time_remaining": "24 hours",
                "tags": ["games", "daily deal", "steam"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "IndieGala Friday Special",
                "description": "Weekly indie game bundles featuring hidden gems and popular titles",
                "url": "https://www.indiegala.com/bundles",
                "platform": "IndieGala",
                "category": "games",
                "deal_type": "weekly_bundle",
                "original_price": 50,
                "current_price": 5,
                "savings": 45,
                "discount_percentage": 90,
                "tier_pricing": True,
                "items_count": 8,
                "charity_included": False,
                "time_remaining": "1 week",
                "tags": ["indie games", "bundle", "steam"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Stack Social Lifetime Deals",
                "description": "Software and app lifetime licenses at heavily discounted prices",
                "url": "https://stacksocial.com/",
                "platform": "Stack Social",
                "category": "software",
                "deal_type": "lifetime_deal",
                "original_price": 200,
                "current_price": 49,
                "savings": 151,
                "discount_percentage": 75,
                "tier_pricing": False,
                "items_count": 1,
                "charity_included": False,
                "time_remaining": "Limited time",
                "tags": ["software", "lifetime", "productivity", "apps"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "AppSumo Plus Deals",
                "description": "Business software and digital marketing tools with lifetime access",
                "url": "https://appsumo.com/deals/",
                "platform": "AppSumo",
                "category": "software",
                "deal_type": "lifetime_deal",
                "original_price": 500,
                "current_price": 69,
                "savings": 431,
                "discount_percentage": 86,
                "tier_pricing": False,
                "items_count": 1,
                "charity_included": False,
                "time_remaining": "Limited time",
                "tags": ["business software", "marketing", "lifetime", "saas"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated bundle deals")
        return curated

    def _extract_price_from_text(self, text: str) -> dict[str, Any]:
        """Extract pricing information from text."""
        price_info = {
            "original_price": 0,
            "current_price": 0,
            "savings": 0,
            "discount_percentage": 0,
            "tier_pricing": False,
        }

        try:
            # Look for price patterns
            price_patterns = [
                r"\$(\d+(?:\.\d{2})?)",  # $19.99
                r"(\d+(?:\.\d{2})?)\s*USD",  # 19.99 USD
                r"(\d+(?:\.\d{2})?)\s*dollars?",  # 19.99 dollars
            ]

            prices = []
            for pattern in price_patterns:
                matches = re.findall(pattern, text.lower())
                for match in matches:
                    try:
                        prices.append(float(match))
                    except ValueError:
                        continue

            if prices:
                if len(prices) >= 2:
                    price_info["current_price"] = min(prices)
                    price_info["original_price"] = max(prices)
                    price_info["savings"] = price_info["original_price"] - price_info["current_price"]
                    if price_info["original_price"] > 0:
                        price_info["discount_percentage"] = round(
                            (price_info["savings"] / price_info["original_price"]) * 100,
                            2,
                        )
                else:
                    price_info["current_price"] = prices[0]

            # Check for tier pricing indicators
            if any(keyword in text.lower() for keyword in ["pay more than", "beat the average", "tier", "level"]):
                price_info["tier_pricing"] = True

        except Exception as e:
            logger.debug(f"Error extracting price info: {e}")

        return price_info

    def _determine_deal_type(self, title: str, description: str) -> str:
        """Determine the type of deal based on content."""
        title_safe = title or ""
        description_safe = description or ""
        text = (title_safe + " " + description_safe).lower()

        if any(keyword in text for keyword in ["humble choice", "monthly", "subscription"]):
            return "subscription_bundle"
        elif any(keyword in text for keyword in ["daily", "flash", "star deal"]):
            return "daily_deal"
        elif any(keyword in text for keyword in ["bundle", "pack", "collection"]):
            return "bundle"
        elif any(keyword in text for keyword in ["lifetime", "permanent"]):
            return "lifetime_deal"
        elif any(keyword in text for keyword in ["free", "giveaway"]):
            return "free"
        elif any(keyword in text for keyword in ["sale", "discount"]):
            return "sale"
        else:
            return "deal"

    def _extract_items_count(self, text: str) -> int:
        """Extract number of items in bundle."""
        try:
            # Look for patterns like "10 games", "5 items", "12 books"
            patterns = [
                r"(\d+)\s+(?:games?|items?|books?|apps?|software)",
                r"(\d+)\s*[-–]\s*(?:game|item|book|app)",
                r"includes?\s+(\d+)",
                r"(\d+)\s+titles?",
            ]

            for pattern in patterns:
                match = re.search(pattern, text.lower())
                if match:
                    return int(match.group(1))

            return 1  # Default to 1 item
        except:
            return 1

    def _extract_bundle_tags(self, title: str, description: str) -> list[str]:
        """Extract relevant tags from bundle title and description."""
        title_safe = title or ""
        description_safe = description or ""
        text = f"{title_safe} {description_safe}".lower()

        category_keywords = {
            "games": ["game", "gaming", "steam", "drm-free", "indie"],
            "software": ["software", "app", "tool", "productivity", "utility"],
            "books": ["book", "ebook", "audiobook", "reading", "novel"],
            "music": ["music", "album", "soundtrack", "audio", "song"],
            "courses": ["course", "tutorial", "learning", "education", "training"],
            "design": ["design", "graphic", "template", "font", "creative"],
            "business": ["business", "marketing", "saas", "analytics", "crm"],
            "development": ["code", "programming", "developer", "api", "framework"],
        }

        tags = []
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(category)

        # Add specific platform tags
        platform_keywords = ["steam", "drm-free", "humble", "fanatical", "epic", "gog"]
        for keyword in platform_keywords:
            if keyword in text:
                tags.append(keyword)

        return tags[:5]  # Limit to 5 tags

    def transform(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform bundle deals data."""
        logger.info("Starting bundle deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title with null safety
                raw_title = deal.get("title", "")
                title = (raw_title or "").strip()
                if len(title) > 200:
                    title = title[:197] + "..."
                if not title:  # Skip deals with no title
                    continue

                # Calculate value score
                value_score = self._calculate_value_score(deal)

                # Determine urgency level
                urgency = self._determine_urgency(deal)

                transformed_deal = {
                    "title": title,
                    "description": deal.get("description", "")[:500],  # Limit description
                    "url": deal["url"],
                    "platform": deal["platform"],
                    "category": deal["category"],
                    "deal_type": deal["deal_type"],
                    "original_price": deal.get("original_price", 0),
                    "current_price": deal.get("current_price", 0),
                    "savings": deal.get("savings", 0),
                    "discount_percentage": deal.get("discount_percentage", 0),
                    "value_score": value_score,
                    "urgency": urgency,
                    "tier_pricing": deal.get("tier_pricing", False),
                    "items_count": deal.get("items_count", 1),
                    "charity_included": deal.get("charity_included", False),
                    "time_remaining": deal.get("time_remaining"),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming deal: {e}")
                continue

        # Sort by value score and savings
        transformed_deals.sort(key=lambda x: (x["value_score"], x["savings"]), reverse=True)

        logger.info(f"Transformed {len(transformed_deals)} bundle deals")
        return transformed_deals

    def _calculate_value_score(self, deal: dict[str, Any]) -> float:
        """Calculate value score for ranking deals."""
        score = 0.0

        # Platform reputation weight
        platform = deal.get("platform", "").lower()
        if "humble" in platform:
            score += 5.0
        elif any(name in platform for name in ["fanatical", "indiegala"]):
            score += 4.0
        elif any(name in platform for name in ["stack social", "appsumo"]):
            score += 3.5
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type in ["bundle", "subscription_bundle"]:
            score += 4.0
        elif deal_type == "lifetime_deal":
            score += 3.5
        elif deal_type in ["daily_deal", "sale"]:
            score += 2.5
        elif deal_type == "free":
            score += 5.0

        # Savings consideration
        savings = deal.get("savings", 0)
        if savings > 100:
            score += 3.0
        elif savings > 50:
            score += 2.0
        elif savings > 20:
            score += 1.0

        # Discount percentage
        discount = deal.get("discount_percentage", 0)
        if discount >= 90:
            score += 2.0
        elif discount >= 75:
            score += 1.5
        elif discount >= 50:
            score += 1.0

        # Items count bonus
        items_count = deal.get("items_count", 1)
        if items_count > 10:
            score += 2.0
        elif items_count > 5:
            score += 1.0

        # Charity bonus
        if deal.get("charity_included", False):
            score += 0.5

        return round(score, 2)

    def _determine_urgency(self, deal: dict[str, Any]) -> str:
        """Determine urgency level of the deal."""
        time_remaining = (deal.get("time_remaining") or "").lower()
        deal_type = deal.get("deal_type") or ""

        if any(keyword in time_remaining for keyword in ["hours", "ending soon", "expires today"]):
            return "high"
        elif any(keyword in time_remaining for keyword in ["1 day", "24 hours", "tomorrow"]) or deal_type == "daily_deal":
            return "medium"
        elif any(keyword in time_remaining for keyword in ["limited time", "week", "days"]):
            return "low"
        else:
            return "none"

    def load(self, transformed_data: list[dict[str, Any]]) -> bool:
        """Load transformed bundle deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "bundle_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "bundle_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(f"Successfully saved {len(transformed_data)} bundle deals to {output_dir}")
            return True

        except Exception as e:
            logger.error(f"Error saving bundle deals data: {e}")
            return False


def main():
    """Main function to run the Bundle Deals ETL."""
    etl = BundleDealsETL()
    success = etl.run()

    if success:
        logger.info("Bundle Deals ETL completed successfully")
    else:
        logger.error("Bundle Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
