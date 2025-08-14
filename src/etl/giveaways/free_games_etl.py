"""Free Games ETL Module

This module tracks free games from Epic Games Store, GOG, Steam, and other platforms.

Usage:
    python src/etl/giveaways/free_games_etl.py

Output:
    - JSON file: data/giveaways/free_games.json
    - CSV file: data/giveaways/free_games.csv
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
import requests
from bs4 import BeautifulSoup

# Add the project root to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.etl.base import BaseETL
from src.models.giveaways import UnifiedGiveawayModel

# Initialize logger
logger = get_logger("FreeGamesETL")


class FreeGamesETL(BaseETL):
    """ETL for free games from multiple platforms."""

    def __init__(self):
        super().__init__("giveaways/free_games")
        self.sources = {
            "epic_games": {
                "name": "Epic Games Store",
                "url": "https://store.epicgames.com/en-US/free-games",
                "api_url": "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
                "category": "games",
            },
            "gog": {
                "name": "GOG.com",
                "url": "https://www.gog.com/games?price=free&sort=popularity&page=1",
                "category": "games",
            },
            "steam": {
                "name": "Steam",
                "url": "https://store.steampowered.com/search/?maxprice=free&specials=1",
                "category": "games",
            },
        }

    def extract(self) -> Dict[str, Any]:
        """Extract free games from multiple sources."""
        logger.info("Starting free games extraction...")

        all_games = []

        # Extract from Epic Games Store
        epic_games = self._extract_epic_games()
        all_games.extend(epic_games)

        # Extract from other sources with web scraping
        # gog_games = self._extract_gog_games()
        # all_games.extend(gog_games)

        logger.info(f"Total extracted {len(all_games)} free games")
        return {"games": all_games, "total_count": len(all_games)}

    def _extract_epic_games(self) -> List[Dict[str, Any]]:
        """Extract free games from Epic Games Store API."""
        try:
            logger.info("Extracting free games from Epic Games Store...")

            url = self.sources["epic_games"]["api_url"]
            headers = {"User-Agent": "Watchtower/1.0 (Educational Research Bot)"}

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            games = []

            promotions = (
                data.get("data", {})
                .get("Catalog", {})
                .get("searchStore", {})
                .get("elements", [])
            )

            for game in promotions:
                try:
                    # Check if game is currently free
                    price_info = game.get("price", {})
                    total_price = price_info.get("totalPrice", {})
                    original_price = total_price.get("originalPrice", 0)
                    discount_price = total_price.get("discountPrice", 0)

                    # Check for promotions
                    promotions_data = game.get("promotions")
                    is_free = False
                    promotion_end = None

                    if promotions_data:
                        promotional_offers = promotions_data.get(
                            "promotionalOffers", []
                        )
                        upcoming_offers = promotions_data.get(
                            "upcomingPromotionalOffers", []
                        )

                        # Check current promotional offers
                        for offer_set in promotional_offers:
                            for offer in offer_set.get("promotionalOffers", []):
                                if (
                                    offer.get("discountSetting", {}).get(
                                        "discountPercentage"
                                    )
                                    == 0
                                ):
                                    is_free = True
                                    promotion_end = offer.get("endDate")
                                    break

                        # Check upcoming offers
                        if not is_free:
                            for offer_set in upcoming_offers:
                                for offer in offer_set.get("promotionalOffers", []):
                                    if (
                                        offer.get("discountSetting", {}).get(
                                            "discountPercentage"
                                        )
                                        == 0
                                    ):
                                        # This will be free in the future
                                        promotion_start = offer.get("startDate")
                                        promotion_end = offer.get("endDate")
                                        games.append(
                                            {
                                                "title": game.get("title", "Unknown"),
                                                "description": game.get(
                                                    "description", ""
                                                ),
                                                "url": f"https://store.epicgames.com/en-US/p/{game.get('catalogNs', {}).get('mappings', [{}])[0].get('pageSlug', '')}",
                                                "image_url": self._get_game_image(game),
                                                "original_price": (
                                                    original_price / 100
                                                    if original_price
                                                    else 0
                                                ),
                                                "current_price": 0,
                                                "discount_percentage": 100,
                                                "platform": "Epic Games Store",
                                                "category": "games",
                                                "giveaway_type": "upcoming_free",
                                                "promotion_start": promotion_start,
                                                "promotion_end": promotion_end,
                                                "is_active": False,
                                                "tags": self._extract_tags(game),
                                                "developer": game.get("developer", ""),
                                                "publisher": game.get("publisher", ""),
                                                "fetched_at": datetime.now(
                                                    timezone.utc
                                                ).isoformat(),
                                                "source": "Epic Games Store API",
                                            }
                                        )

                    # If currently free or permanently free
                    if is_free or (discount_price == 0 and original_price > 0):
                        games.append(
                            {
                                "title": game.get("title", "Unknown"),
                                "description": game.get("description", ""),
                                "url": f"https://store.epicgames.com/en-US/p/{game.get('catalogNs', {}).get('mappings', [{}])[0].get('pageSlug', '')}",
                                "image_url": self._get_game_image(game),
                                "original_price": (
                                    original_price / 100 if original_price else 0
                                ),
                                "current_price": (
                                    discount_price / 100 if discount_price else 0
                                ),
                                "discount_percentage": (
                                    100 if discount_price == 0 else 0
                                ),
                                "platform": "Epic Games Store",
                                "category": "games",
                                "giveaway_type": "free_game",
                                "promotion_start": None,
                                "promotion_end": promotion_end,
                                "is_active": True,
                                "tags": self._extract_tags(game),
                                "developer": game.get("developer", ""),
                                "publisher": game.get("publisher", ""),
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                                "source": "Epic Games Store API",
                            }
                        )

                except Exception as e:
                    logger.warning(f"Error processing Epic game: {e}")
                    continue

            logger.info(f"Extracted {len(games)} games from Epic Games Store")
            return games

        except Exception as e:
            logger.error(f"Error extracting from Epic Games Store: {e}")
            return []

    def _get_game_image(self, game: Dict[str, Any]) -> str:
        """Extract game image URL."""
        try:
            key_images = game.get("keyImages", [])
            for image in key_images:
                if image.get("type") in ["DieselStoreFrontWide", "OfferImageWide"]:
                    return image.get("url", "")
            return ""
        except:
            return ""

    def _extract_tags(self, game: Dict[str, Any]) -> List[str]:
        """Extract game tags/genres."""
        try:
            tags = []
            categories = game.get("categories", [])
            for category in categories:
                path = category.get("path", "")
                if path:
                    tags.append(path.replace("games/", "").replace("/", " > "))
            return tags[:5]  # Limit to 5 tags
        except:
            return []

    def transform(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform free games data."""
        logger.info("Starting free games transformation...")

        games = raw_data.get("games", [])
        transformed_games: List[Dict[str, Any]] = []

        for game in games:
            try:
                # Clean up title
                title = game["title"].strip()
                if len(title) > 100:
                    title = title[:97] + "..."

                # Calculate relevance score
                relevance_score = self._calculate_game_relevance_score(game)

                # Determine availability status
                availability = self._determine_availability(game)

                transformed_game = {
                    "title": title,
                    "description": game.get("description", "")[
                        :300
                    ],  # Limit description
                    "url": game["url"],
                    "image_url": game.get("image_url", ""),
                    "original_price": game.get("original_price", 0),
                    "current_price": game.get("current_price", 0),
                    "discount_percentage": game.get("discount_percentage", 0),
                    "platform": game["platform"],
                    "category": game["category"],
                    "giveaway_type": game["giveaway_type"],
                    "availability": availability,
                    "relevance_score": relevance_score,
                    "promotion_end": game.get("promotion_end"),
                    "is_active": game.get("is_active", True),
                    "tags": game.get("tags", []),
                    "developer": game.get("developer", ""),
                    "publisher": game.get("publisher", ""),
                    "fetched_at": game["fetched_at"],
                    "source": game["source"],
                }

                # Validate against canonical contract (as a soft contract)
                try:
                    _ = UnifiedGiveawayModel(
                        title=transformed_game["title"],
                        url=transformed_game["url"],
                        platform=transformed_game["platform"],
                        category=transformed_game["category"],
                        availability=transformed_game["availability"],
                        promotion_end=transformed_game["promotion_end"],
                        is_active=transformed_game["is_active"],
                        fetched_at=transformed_game["fetched_at"],
                        source=transformed_game["source"],
                    )
                except Exception as e:
                    logger.warning(f"Validation failed for giveaway '{title}': {e}")
                    # Continue but mark inactive and basic defaults
                    transformed_game["is_active"] = False

                transformed_games.append(transformed_game)

            except Exception as e:
                logger.warning(f"Error transforming game: {e}")
                continue

        # Sort by relevance score and active status
        transformed_games.sort(
            key=lambda x: (x["is_active"], x["relevance_score"]), reverse=True
        )

        logger.info(f"Transformed {len(transformed_games)} free games")
        return transformed_games

    def _calculate_game_relevance_score(self, game: Dict[str, Any]) -> float:
        """Calculate relevance score for ranking games."""
        score = 0.0

        # Platform weight
        if game["platform"] == "Epic Games Store":
            score += 3.0
        elif game["platform"] == "Steam":
            score += 2.5
        elif game["platform"] == "GOG.com":
            score += 2.0

        # Giveaway type weight
        if game["giveaway_type"] == "free_game":
            score += 5.0
        elif game["giveaway_type"] == "upcoming_free":
            score += 3.0

        # Price consideration (higher original price = better deal)
        original_price = game.get("original_price", 0)
        if original_price > 50:
            score += 3.0
        elif original_price > 20:
            score += 2.0
        elif original_price > 5:
            score += 1.0

        # Recency bonus
        if game.get("is_active", False):
            score += 2.0

        return round(score, 2)

    def _determine_availability(self, game: Dict[str, Any]) -> str:
        """Determine game availability status."""
        if not game.get("is_active", True):
            return "upcoming"

        promotion_end = game.get("promotion_end")
        if promotion_end:
            try:
                end_date = datetime.fromisoformat(promotion_end.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if end_date > now:
                    days_left = (end_date - now).days
                    if days_left == 0:
                        return "ends_today"
                    elif days_left <= 2:
                        return "ends_soon"
                    else:
                        return "limited_time"
                else:
                    return "expired"
            except:
                return "active"

        return "permanent"

    def load(self, transformed_data: List[Dict[str, Any]]) -> bool:
        """Load transformed free games data to files."""
        try:
            # Ensure output directory exists
            import os
            from pathlib import Path

            output_dir = Path(get_project_root()) / "data" / "giveaways"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save as JSON
            json_path = output_dir / "free_games.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)
            # Also save latest alias
            latest_path = output_dir / "free_games_latest.json"
            with open(latest_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = output_dir / "free_games.csv"
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(
                f"Successfully saved {len(transformed_data)} free games to {output_dir}"
            )
            self._last_load_count = len(transformed_data)
            return True

        except Exception as e:
            logger.error(f"Error saving free games data: {e}")
            return False


def main():
    """Main function to run the Free Games ETL."""
    etl = FreeGamesETL()
    success = etl.run()

    if success:
        logger.info("Free Games ETL completed successfully")
    else:
        logger.error("Free Games ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
