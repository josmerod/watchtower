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
from typing import Any

import pandas as pd
import requests

from etl.base import BaseETL
from models.games import GamePlatform
from utils.logging import get_logger


class AllKeyShopETL(BaseETL):
    """ETL for scraping AllKeyShop game deals."""

    def __init__(self, max_pages: int = 10, **kwargs):
        """Initialize AllKeyShop ETL.

        Args:
            max_pages: Maximum pages to scrape per sorting criteria
        """
        super().__init__(
            name="AllKeyShop",
            description="Extract game deals from AllKeyShop API",
            **kwargs,
        )
        self.logger = get_logger("ETL.AllKeyShop")
        self.max_pages = max_pages

        # Import and setup requests session
        self.session = requests.Session()

        # Headers to mimic a real browser
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.allkeyshop.com/blog/products/",
            }
        )

        # Rate limiting
        self.request_delay = 2  # seconds between requests

    def extract(self) -> list[dict[str, Any]]:
        """Extract games from AllKeyShop using their API endpoint."""
        all_games = []

        # AllKeyShop now uses API calls - try to extract from the JSON data
        api_url = "https://www.allkeyshop.com/api/v2-1-250304/vaks.php"

        # Define different sorting criteria to get variety
        sort_criteria_list = [
            ("popularity", {"sort_field": "popularity", "sort_order": "desc"}),
            ("price_asc", {"sort_field": "price", "sort_order": "asc"}),
            ("deal_score", {"sort_field": "deal_score", "sort_order": "desc"}),
        ]

        for sort_name, sort_params in sort_criteria_list:
            self.logger.info(f"Extracting games with sorting: {sort_name}")
            games = self._extract_games_from_api(sort_name, api_url, sort_params)
            all_games.extend(games)

            # Add delay between different sorting criteria
            time.sleep(2)

        self.logger.info(f"Total games extracted: {len(all_games)}")
        return all_games

    def _extract_games_from_api(
        self, sort_criteria: str, api_url: str, sort_params: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Extract games using AllKeyShop's API endpoint."""
        games = []

        for page_num in range(
            1, min(self.max_pages + 1, 4)
        ):  # Limit to 3 pages per sort
            try:
                # Build API parameters
                params = {
                    "action": "CatalogV2",
                    "locale": "en",
                    "currency": "EUR",
                    "price_mode": "price_card",
                    "rating_min": 0,
                    "deal_score_min": 0,
                    "deal_score_max": 1,
                    "pagenum": page_num,
                    "per_page": 24,
                    "type": "game",
                    "fields": "id,name,link,operating_system.id,operating_system.name,all_operating_systems.id,all_operating_systems.name,release_date,assets.cover,assets.capsule,assets.microtrailer,historical_low_offers.price,historical_low_offers.date,historical_low_offers.merchant.name,historical_low_offers.merchant.slug,offers.price,offers.buy_url,offers.deal_score,offers.stock_status,offers.merchant.name,offers.merchant.slug,offers.edition.name,offers.official_offer_reduction_percent,offers.voucher.id,offers.voucher.code",
                    "_app.id": "catalog-app",
                    "_app.action": "fetchProducts",
                    "_app.version": "2025-04-08",
                }

                # Add sorting parameters
                params.update(sort_params)

                response = self.session.get(api_url, params=params, timeout=30)
                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError:
                    self.logger.warning(f"Non-JSON response for page {page_num}")
                    continue

                if data.get("status") != "success":
                    self.logger.warning(
                        f"API returned non-success status: {data.get('status')}"
                    )
                    continue

                products = data.get("products", [])
                if not products:
                    self.logger.debug(
                        f"No products found on page {page_num} for {sort_criteria}"
                    )
                    break

                page_games = self._parse_games_from_api_response(
                    products, sort_criteria, page_num
                )
                games.extend(page_games)
                self.logger.debug(
                    f"Extracted {len(page_games)} games from API page {page_num}"
                )

                # Add delay between pages
                time.sleep(1)

            except Exception as e:
                self.logger.error(
                    f"Error extracting API page {page_num} for {sort_criteria}: {e}"
                )
                break

        return games

    def _parse_games_from_api_response(
        self, products: list[dict[str, Any]], sort_criteria: str, page_num: int
    ) -> list[dict[str, Any]]:
        """Parse games from a single page using API response."""
        games = []

        for product in products:
            try:
                game_data = self._extract_game_from_api_response(
                    product, sort_criteria, page_num
                )
                if game_data:
                    games.append(game_data)
            except Exception as e:
                self.logger.debug(f"Error parsing game from API response: {e}")
                continue

        return games

    def _extract_game_from_api_response(
        self, product: dict[str, Any], sort_criteria: str, page_num: int
    ) -> dict[str, Any] | None:
        """Extract game data from a single product in API response."""
        game_data = {
            "sort_criteria": sort_criteria,
            "page_number": page_num,
            "extracted_at": datetime.utcnow().isoformat(),
        }

        # Extract title
        title = product.get("name", "")
        if not title:
            return None

        game_data["title"] = title

        # Extract URL
        url = product.get("link", "")
        if url:
            game_data["url"] = url

        # Extract image URL
        assets = product.get("assets", {})
        if assets.get("cover"):
            game_data["image_url"] = assets["cover"]
        elif assets.get("capsule"):
            game_data["image_url"] = assets["capsule"]

        # Extract price information from offers
        offers = product.get("offers", [])
        if offers:
            # Take the first offer (usually the best deal)
            offer = offers[0]

            # Current price
            if "price" in offer:
                game_data["current_price"] = float(offer["price"])

            # Deal score
            if "deal_score" in offer:
                game_data["deal_score"] = float(offer["deal_score"])

            # Store information
            merchant = offer.get("merchant", {})
            if merchant.get("name"):
                game_data["store_name"] = merchant["name"]

            # Discount percentage
            if "official_offer_reduction_percent" in offer:
                game_data["discount_percentage"] = float(
                    offer["official_offer_reduction_percent"]
                )

            # Edition info
            edition = offer.get("edition", {})
            if edition.get("name"):
                game_data["edition"] = edition["name"]

        # Extract historical low price
        historical_low = product.get("historical_low_offers", [])
        if historical_low:
            low_offer = historical_low[0]
            if "price" in low_offer:
                game_data["historical_low_price"] = float(low_offer["price"])
            if "date" in low_offer:
                game_data["historical_low_date"] = low_offer["date"]
            merchant = low_offer.get("merchant", {})
            if merchant.get("name"):
                game_data["historical_low_store"] = merchant["name"]

        # Extract official offers for original price
        official_offers = product.get("official_offers", [])
        if official_offers:
            official_offer = official_offers[0]
            if "price" in official_offer:
                game_data["original_price"] = float(official_offer["price"])

        # Extract operating system info
        operating_system = product.get("operating_system", {})
        if operating_system.get("name"):
            game_data["platform"] = operating_system["name"]

        # Extract release date
        if "release_date" in product:
            game_data["release_date"] = product["release_date"]

        # Extract game ID
        if "id" in product:
            game_data["game_id"] = product["id"]

        # Calculate discount if not already present
        if (
            "discount_percentage" not in game_data
            and game_data.get("original_price")
            and game_data.get("current_price")
            and game_data["original_price"] > game_data["current_price"]
        ):
            original = game_data["original_price"]
            current = game_data["current_price"]
            game_data["discount_percentage"] = int(
                ((original - current) / original) * 100
            )

        # Mark as DLC if it's downloadable content
        title_lower = title.lower()
        game_data["is_dlc"] = any(
            keyword in title_lower
            for keyword in ["dlc", "expansion", "season pass", "add-on"]
        )

        return game_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform raw game data into structured format."""
        self.logger.info(f"Transforming {len(data)} game records 🔧")
        transformed_games = []

        for game_data in data:
            try:
                # Clean and validate data
                cleaned_data = self._clean_game_data(game_data)

                # Only ensure title and URL exist; keep entries even if price/discount missing
                if not cleaned_data.get("title") or not cleaned_data.get("url"):
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

    def _clean_game_data(self, game_data: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize game data."""
        cleaned = game_data.copy()

        # Clean title
        if "title" in cleaned:
            cleaned["title"] = re.sub(r"\s+", " ", cleaned["title"]).strip()

        # Ensure prices are numeric
        for price_field in ["current_price", "original_price"]:
            if cleaned.get(price_field):
                try:
                    cleaned[price_field] = float(cleaned[price_field])
                except (ValueError, TypeError):
                    cleaned[price_field] = None

        # Ensure integers are integers
        for int_field in ["deal_score", "discount_percentage", "metacritic_score"]:
            if cleaned.get(int_field):
                try:
                    cleaned[int_field] = int(cleaned[int_field])
                except (ValueError, TypeError):
                    cleaned[int_field] = None

        # Set platform
        cleaned["platform"] = GamePlatform.PC.value

        # Detect DLC
        title_lower = cleaned.get("title", "").lower()
        cleaned["is_dlc"] = any(
            keyword in title_lower for keyword in ["dlc", "expansion", "season pass"]
        )

        return cleaned

    def _add_calculated_fields(self, game_data: dict[str, Any]) -> None:
        """Add calculated fields to game data."""
        # Calculate discount percentage if not provided
        if (
            not game_data.get("discount_percentage")
            and game_data.get("original_price")
            and game_data.get("current_price")
        ):
            original = game_data["original_price"]
            current = game_data["current_price"]
            if original > current:
                discount = int(((original - current) / original) * 100)
                game_data["discount_percentage"] = discount

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load game deals data to storage."""
        self.logger.info(f"Loading {len(data)} AllKeyShop game deals 💾")

        # Save complete data
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"allkeyshop_games_{timestamp}.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            # Save latest data
            latest_file = self.output_dir / "latest_allkeyshop_games.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            # Create CSV export
            if data:
                df = pd.DataFrame(data)
                csv_file = self.output_dir / f"allkeyshop_games_{timestamp}.csv"
                df.to_csv(csv_file, index=False, encoding="utf-8")

            # Create filtered datasets
            self._create_filtered_datasets(data)

            self.logger.info(f"AllKeyShop games data saved to {output_file}")
            self.metrics.records_loaded = len(data)

            # Log useful stats
            self._log_extraction_stats(data)

        except Exception as e:
            self.logger.error(f"Failed to save AllKeyShop games data: {e}")
            raise

    def _create_filtered_datasets(self, data: list[dict[str, Any]]) -> None:
        """Create filtered datasets for specific use cases."""
        # Best deals (high discount or deal score)
        best_deals = [
            game
            for game in data
            if (
                game.get("discount_percentage", 0) >= 50
                or game.get("deal_score", 0) >= 80
            )
        ]

        # Budget games (under €10)
        budget_games = [
            game for game in data if game.get("current_price", float("inf")) <= 10
        ]

        # Premium games (over €30)
        premium_games = [game for game in data if game.get("current_price", 0) >= 30]

        # Free games
        free_games = [game for game in data if game.get("current_price", 1) == 0]

        # Save filtered datasets
        filters = {
            "best_deals.json": best_deals,
            "budget_games.json": budget_games,
            "premium_games.json": premium_games,
            "free_games.json": free_games,
        }

        for filename, filtered_data in filters.items():
            if filtered_data:
                with open(self.output_dir / filename, "w", encoding="utf-8") as f:
                    json.dump(filtered_data, f, indent=2, default=str)

    def _log_extraction_stats(self, data: list[dict[str, Any]]) -> None:
        """Log extraction statistics."""
        if not data:
            return

        # Group by sort criteria
        by_criteria = {}
        for game in data:
            criteria = game.get("sort_criteria", "unknown")
            by_criteria[criteria] = by_criteria.get(criteria, 0) + 1

        # Price statistics
        prices = [
            game.get("current_price") for game in data if game.get("current_price")
        ]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
        else:
            avg_price = min_price = max_price = 0

        # Discount statistics
        discounts = [
            game.get("discount_percentage")
            for game in data
            if game.get("discount_percentage")
        ]
        avg_discount = sum(discounts) / len(discounts) if discounts else 0

        self.logger.info("Extraction summary:")
        self.logger.info(f"  - Total games: {len(data)}")
        self.logger.info(f"  - By criteria: {by_criteria}")
        self.logger.info(
            f"  - Price range: €{min_price:.2f} - €{max_price:.2f} (avg: €{avg_price:.2f})"
        )
        self.logger.info(f"  - Average discount: {avg_discount:.1f}%")
        self.logger.info(f"  - Games with discounts: {len(discounts)}")


def get_allkeyshop():
    """Run the AllKeyShop ETL process."""
    etl = AllKeyShopETL(max_pages=10)
    metrics = etl.run()
    return metrics


if __name__ == "__main__":
    get_allkeyshop()
