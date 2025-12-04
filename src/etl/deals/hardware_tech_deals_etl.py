"""Hardware & Tech Deals ETL Module

This module fetches hardware and technology deals from major retailers,
manufacturers, and tech deal sites including electronics, computers,
smartphones, and gadgets.

Usage:
    python src/etl/deals/hardware_tech_deals_etl.py

Output:
    - JSON file: data/deals/hardware_tech_deals.json
    - CSV file: data/deals/hardware_tech_deals.csv
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.etl.base import BaseETL
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("HardwareTechDealsETL")


class HardwareTechDealsETL(BaseETL):
    """ETL for hardware and technology deals."""

    def __init__(self):
        super().__init__("hardware_tech_deals")
        self.sources = {
            "amazon_de": {
                "name": "Amazon.de",
                "url": "https://www.amazon.de/",
                "deals_url": "https://www.amazon.de/gp/goldbox",
                "category": "electronics",
                "region": "europe",
            },
            "amazon_uk": {
                "name": "Amazon.co.uk",
                "url": "https://www.amazon.co.uk/",
                "deals_url": "https://www.amazon.co.uk/gp/goldbox",
                "category": "electronics",
                "region": "europe",
            },
            "amazon_fr": {
                "name": "Amazon.fr",
                "url": "https://www.amazon.fr/",
                "deals_url": "https://www.amazon.fr/gp/goldbox",
                "category": "electronics",
                "region": "europe",
            },
            "amazon_es": {
                "name": "Amazon.es",
                "url": "https://www.amazon.es/",
                "deals_url": "https://www.amazon.es/gp/goldbox",
                "category": "electronics",
                "region": "europe",
            },
            "media_markt": {
                "name": "Media Markt",
                "url": "https://www.mediamarkt.de/",
                "deals_url": "https://www.mediamarkt.de/de/category/_angebote-1",
                "category": "electronics",
                "region": "europe",
            },
            "saturn": {
                "name": "Saturn",
                "url": "https://www.saturn.de/",
                "deals_url": "https://www.saturn.de/de/category/_angebote-1",
                "category": "electronics",
                "region": "europe",
            },
            "conrad": {
                "name": "Conrad Electronic",
                "url": "https://www.conrad.de/",
                "deals_url": "https://www.conrad.de/de/c/aktionen-und-angebote-236000.html",
                "category": "electronics",
                "region": "europe",
            },
            "alternate": {
                "name": "Alternate",
                "url": "https://www.alternate.de/",
                "deals_url": "https://www.alternate.de/html/top-angebote.html",
                "category": "electronics",
                "region": "europe",
            },
            "mindfactory": {
                "name": "Mindfactory",
                "url": "https://www.mindfactory.de/",
                "deals_url": "https://www.mindfactory.de/Schnaeppchen",
                "category": "electronics",
                "region": "europe",
            },
            "notebooksbilliger": {
                "name": "Notebooksbilliger",
                "url": "https://www.notebooksbilliger.de/",
                "deals_url": "https://www.notebooksbilliger.de/angebote",
                "category": "electronics",
                "region": "europe",
            },
            "currys_uk": {
                "name": "Currys PC World",
                "url": "https://www.currys.co.uk/",
                "deals_url": "https://www.currys.co.uk/gbuk/clearance-94-commercial.html",
                "category": "electronics",
                "region": "europe",
            },
            "argos": {
                "name": "Argos",
                "url": "https://www.argos.co.uk/",
                "deals_url": "https://www.argos.co.uk/clearance/",
                "category": "electronics",
                "region": "europe",
            },
            "ebuyer": {
                "name": "Ebuyer",
                "url": "https://www.ebuyer.com/",
                "deals_url": "https://www.ebuyer.com/clearance",
                "category": "electronics",
                "region": "europe",
            },
            "scan_uk": {
                "name": "Scan Computers",
                "url": "https://www.scan.co.uk/",
                "deals_url": "https://www.scan.co.uk/shop/clearance",
                "category": "electronics",
                "region": "europe",
            },
            # US/Global sources for digital/software items
            "newegg": {
                "name": "Newegg",
                "url": "https://www.newegg.com/",
                "deals_url": "https://www.newegg.com/todays-deals",
                "category": "electronics",
                "region": "global",
            },
            "best_buy": {
                "name": "Best Buy",
                "url": "https://www.bestbuy.com/",
                "deals_url": "https://www.bestbuy.com/site/electronics/top-deals/pcmcat1563299784499.c?id=pcmcat1563299784499",
                "category": "electronics",
                "region": "global",
            },
            "bh_photo": {
                "name": "B&H Photo",
                "url": "https://www.bhphotovideo.com/",
                "deals_url": "https://www.bhphotovideo.com/find/deals.jsp",
                "category": "electronics",
                "region": "global",
            },
        }

    def extract(self) -> dict[str, Any]:
        """Extract hardware and tech deals from multiple sources."""
        logger.info("Starting hardware & tech deals extraction...")

        all_deals = []

        # Add curated hardware and tech deals
        curated_deals = self._get_curated_hardware_tech_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} hardware & tech deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_hardware_tech_deals(self) -> list[dict[str, Any]]:
        """Get manually curated list of hardware and tech deals."""
        curated = [
            {
                "title": "Amazon.de Electronics Deals",
                "description": "Daily deals on electronics, computers, and accessories from Amazon Germany",
                "url": "https://www.amazon.de/gp/goldbox",
                "platform": "Amazon.de",
                "category": "electronics",
                "deal_type": "daily_deals",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "various",
                "brand_focus": [
                    "Sony",
                    "Samsung",
                    "Apple",
                    "Microsoft",
                    "Bosch",
                    "Siemens",
                ],
                "region": "europe",
                "tags": [
                    "electronics",
                    "computers",
                    "accessories",
                    "daily deals",
                    "german",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Media Markt Electronics Deals",
                "description": "Daily tech deals on computers, components, and electronics from Media Markt Germany",
                "url": "https://www.mediamarkt.de/de/category/_angebote-1",
                "platform": "Media Markt",
                "category": "electronics",
                "deal_type": "daily_deals",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "computers",
                "brand_focus": ["ASUS", "MSI", "Intel", "AMD", "Samsung", "LG"],
                "region": "europe",
                "tags": ["computers", "components", "gaming", "tech", "german"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Currys PC World Clearance",
                "description": "Electronics and appliance deals from Currys PC World UK",
                "url": "https://www.currys.co.uk/gbuk/clearance-94-commercial.html",
                "platform": "Currys PC World",
                "category": "electronics",
                "deal_type": "clearance",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "electronics",
                "brand_focus": [
                    "Apple",
                    "Samsung",
                    "Sony",
                    "LG",
                    "Panasonic",
                    "Toshiba",
                ],
                "region": "europe",
                "tags": ["electronics", "appliances", "clearance", "retail", "uk"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Conrad Electronic Deals",
                "description": "Electronics and technical components from Conrad Germany",
                "url": "https://www.conrad.de/de/c/aktionen-und-angebote-236000.html",
                "platform": "Conrad Electronic",
                "category": "electronics",
                "deal_type": "daily_deals",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "components",
                "brand_focus": [
                    "Arduino",
                    "Raspberry Pi",
                    "Texas Instruments",
                    "STMicroelectronics",
                ],
                "region": "europe",
                "tags": ["electronics", "components", "technical", "german"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Alternate Top Deals",
                "description": "Electronics and computer deals from Alternate Germany",
                "url": "https://www.alternate.de/html/top-angebote.html",
                "platform": "Alternate",
                "category": "electronics",
                "deal_type": "top_deals",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "computers",
                "brand_focus": ["Intel", "AMD", "NVIDIA", "ASUS", "MSI"],
                "region": "europe",
                "tags": ["computers", "components", "gaming", "german"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Mindfactory Schnäppchen",
                "description": "Computer components and electronics deals from Mindfactory Germany",
                "url": "https://www.mindfactory.de/Schnaeppchen",
                "platform": "Mindfactory",
                "category": "electronics",
                "deal_type": "bargains",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "components",
                "brand_focus": ["Intel", "AMD", "NVIDIA", "ASUS", "MSI", "Gigabyte"],
                "region": "europe",
                "tags": ["computers", "components", "gaming", "german"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Notebooksbilliger Deals",
                "description": "Laptop and notebook deals from Notebooksbilliger Germany",
                "url": "https://www.notebooksbilliger.de/angebote",
                "platform": "Notebooksbilliger",
                "category": "electronics",
                "deal_type": "laptop_deals",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "laptops",
                "brand_focus": ["Dell", "HP", "Lenovo", "ASUS", "Acer", "Apple"],
                "region": "europe",
                "tags": ["laptops", "notebooks", "computers", "german"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Argos Clearance Electronics",
                "description": "Electronics clearance deals from Argos UK",
                "url": "https://www.argos.co.uk/clearance/",
                "platform": "Argos",
                "category": "electronics",
                "deal_type": "clearance",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "electronics",
                "brand_focus": ["Sony", "Samsung", "Panasonic", "LG", "Philips"],
                "region": "europe",
                "features": ["clearance", "electronics", "home delivery"],
                "tags": ["clearance", "electronics", "appliances", "uk"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Apple Refurbished Store",
                "description": "Certified refurbished Apple products at discounted prices",
                "url": "https://www.apple.com/shop/refurbished",
                "platform": "Apple",
                "category": "electronics",
                "deal_type": "refurbished",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "apple_products",
                "brand_focus": ["Apple"],
                "features": ["certified refurbished", "warranty", "original packaging"],
                "tags": ["apple", "refurbished", "certified", "warranty"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Dell Outlet Deals",
                "description": "Refurbished and clearance Dell computers and electronics",
                "url": "https://www.dell.com/en-us/dfh/outlet",
                "platform": "Dell",
                "category": "electronics",
                "deal_type": "outlet_deals",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "product_type": "computers",
                "brand_focus": ["Dell"],
                "features": ["refurbished", "clearance", "business grade"],
                "tags": ["dell", "computers", "refurbished", "business"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated hardware & tech deals")
        return curated

    def transform(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform hardware and tech deals data."""
        logger.info("Starting hardware & tech deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate tech value score
                tech_score = self._calculate_tech_value_score(deal)

                # Determine product category
                product_category = self._determine_product_category(deal)

                transformed_deal = {
                    "title": title,
                    "description": deal.get("description", "")[:400],
                    "url": deal["url"],
                    "platform": deal["platform"],
                    "category": deal["category"],
                    "deal_type": deal["deal_type"],
                    "original_price": deal.get("original_price", 0),
                    "current_price": deal.get("current_price", 0),
                    "savings": deal.get("savings", 0),
                    "discount_percentage": deal.get("discount_percentage", 0),
                    "tech_score": tech_score,
                    "product_category": product_category,
                    "product_type": deal.get("product_type", "unknown"),
                    "brand_focus": deal.get("brand_focus", []),
                    "features": deal.get("features", []),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming hardware deal: {e}")
                continue

        # Sort by tech score and savings
        transformed_deals.sort(key=lambda x: (x["tech_score"], x["savings"]), reverse=True)

        logger.info(f"Transformed {len(transformed_deals)} hardware & tech deals")
        return transformed_deals

    def _calculate_tech_value_score(self, deal: dict[str, Any]) -> float:
        """Calculate tech value score for ranking deals."""
        score = 0.0

        # Platform reliability weight - prefer European sources for physical items
        platform = deal.get("platform", "").lower()
        region = deal.get("region", "").lower()

        # European sources get higher scores for physical items
        if region == "europe":
            if any(name in platform for name in ["amazon.de", "amazon.uk", "amazon.fr", "amazon.es"]):
                score += 5.5
            elif any(name in platform for name in ["media markt", "saturn", "conrad", "alternate"]):
                score += 5.0
            elif any(name in platform for name in ["currys", "argos", "mindfactory", "notebooksbilliger"]):
                score += 4.8
            else:
                score += 4.0
        # Global/US sources for digital/software items
        elif any(name in platform for name in ["newegg", "best buy", "bh photo"]):
            score += 4.0
        elif any(name in platform for name in ["apple", "dell"]):
            score += 3.5
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type in ["daily_deals", "top_deals"]:
            score += 4.0
        elif deal_type == "refurbished":
            score += 3.5
        elif deal_type == "cashback" or deal_type == "outlet_deals":
            score += 3.0

        # Product type weight
        product_type = deal.get("product_type", "").lower()
        if "computer" in product_type:
            score += 3.0
        elif "apple" in product_type:
            score += 2.5
        elif "photography" in product_type:
            score += 2.0

        # Brand quality bonus
        brand_focus = deal.get("brand_focus", [])
        premium_brands = ["apple", "sony", "canon", "nikon", "intel", "nvidia"]
        if any(brand.lower() in premium_brands for brand in brand_focus):
            score += 1.0

        # Features bonus
        features = deal.get("features", [])
        if any(feature in ["certified refurbished", "warranty"] for feature in features):
            score += 0.5

        return round(score, 2)

    def _determine_product_category(self, deal: dict[str, Any]) -> str:
        """Determine specific product category."""
        product_type = deal.get("product_type", "").lower()
        category = deal.get("category", "").lower()

        if "computer" in product_type or "laptop" in product_type:
            return "computers"
        elif "apple" in product_type:
            return "apple_products"
        elif "photography" in product_type or "camera" in category:
            return "photography"
        elif "gaming" in category:
            return "gaming"
        elif "smartphone" in category or "phone" in category:
            return "smartphones"
        else:
            return "electronics"

    def load(self, transformed_data: list[dict[str, Any]]) -> bool:
        """Load transformed hardware and tech deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "hardware_tech_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "hardware_tech_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(f"Successfully saved {len(transformed_data)} hardware & tech deals to {output_dir}")
            return True

        except Exception as e:
            logger.error(f"Error saving hardware & tech deals data: {e}")
            return False


def main():
    """Main function to run the Hardware & Tech Deals ETL."""
    etl = HardwareTechDealsETL()
    success = etl.run()

    if success:
        logger.info("Hardware & Tech Deals ETL completed successfully")
    else:
        logger.error("Hardware & Tech Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
