"""Fashion & Retail Deals ETL Module

This module aggregates fashion deals, clothing discounts, retail promotions,
and lifestyle shopping deals from major brands and platforms.

Usage:
    python src/etl/deals/fashion_retail_deals_etl.py

Output:
    - JSON file: data/deals/fashion_retail_deals.json
    - CSV file: data/deals/fashion_retail_deals.csv
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
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.etl.base import BaseETL

# Initialize logger
logger = get_logger("FashionRetailDealsETL")


class FashionRetailDealsETL(BaseETL):
    """ETL for fashion and retail deals."""

    def __init__(self):
        super().__init__("fashion_retail_deals")
        self.sources = {
            "nordstrom_rack": {
                "name": "Nordstrom Rack",
                "clearance_url": "https://www.nordstromrack.com/clearance",
                "category": "fashion",
            },
            "6pm": {
                "name": "6PM",
                "deals_url": "https://www.6pm.com/",
                "category": "fashion",
            },
            "rue_la_la": {
                "name": "Rue La La",
                "boutiques_url": "https://www.ruelala.com/boutiques",
                "category": "fashion",
            },
            "overstock": {
                "name": "Overstock",
                "deals_url": "https://www.overstock.com/deals",
                "category": "home_fashion",
            },
        }

    def extract(self) -> Dict[str, Any]:
        """Extract fashion and retail deals from multiple sources."""
        logger.info("Starting fashion & retail deals extraction...")

        all_deals = []

        # Add curated fashion and retail deals
        curated_deals = self._get_curated_fashion_retail_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} fashion & retail deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_fashion_retail_deals(self) -> List[Dict[str, Any]]:
        """Get manually curated list of fashion and retail deals."""
        curated = [
            {
                "title": "Nordstrom Rack Up to 70% Off Designer",
                "description": "Designer clothing, shoes, and accessories at up to 70% off retail prices",
                "url": "https://www.nordstromrack.com/clearance",
                "platform": "Nordstrom Rack",
                "category": "fashion",
                "deal_type": "clearance_sale",
                "original_price": 200,
                "current_price": 60,
                "savings": 140,
                "discount_percentage": 70,
                "brand_tier": "designer",
                "product_category": "clothing",
                "size_availability": "full_range",
                "return_policy": "30_days",
                "shipping": "free_over_89",
                "seasonal_trend": "year_round",
                "quality_grade": "high",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": ["designer", "clearance", "nordstrom", "fashion"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "6PM Designer Shoes & Clothing",
                "description": "Up to 75% off designer shoes, clothing, and accessories from top brands",
                "url": "https://www.6pm.com/",
                "platform": "6PM",
                "category": "fashion",
                "deal_type": "outlet_pricing",
                "original_price": 150,
                "current_price": 37,
                "savings": 113,
                "discount_percentage": 75,
                "brand_tier": "premium",
                "product_category": "shoes",
                "size_availability": "full_range",
                "return_policy": "365_days",
                "shipping": "free_shipping",
                "seasonal_trend": "year_round",
                "quality_grade": "high",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": ["shoes", "designer", "outlet", "free shipping"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Rue La La Flash Sales",
                "description": "Members-only boutique sales with up to 80% off luxury brands",
                "url": "https://www.ruelala.com/boutiques",
                "platform": "Rue La La",
                "category": "luxury_fashion",
                "deal_type": "flash_sales",
                "original_price": 300,
                "current_price": 60,
                "savings": 240,
                "discount_percentage": 80,
                "brand_tier": "luxury",
                "product_category": "accessories",
                "size_availability": "limited",
                "return_policy": "30_days",
                "shipping": "flat_rate",
                "seasonal_trend": "seasonal",
                "quality_grade": "premium",
                "authenticity": "guaranteed",
                "membership_required": True,
                "tags": ["luxury", "flash sales", "members only", "boutique"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "ThredUp Secondhand Fashion",
                "description": "High-quality secondhand clothing from top brands at up to 90% off retail",
                "url": "https://www.thredup.com/",
                "platform": "ThredUp",
                "category": "sustainable_fashion",
                "deal_type": "secondhand",
                "original_price": 100,
                "current_price": 25,
                "savings": 75,
                "discount_percentage": 75,
                "brand_tier": "mixed",
                "product_category": "clothing",
                "size_availability": "varies",
                "return_policy": "14_days",
                "shipping": "standard_rates",
                "seasonal_trend": "year_round",
                "quality_grade": "good",
                "authenticity": "verified",
                "membership_required": False,
                "tags": ["sustainable", "secondhand", "eco-friendly", "thrift"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Poshmark Social Shopping",
                "description": "Buy and sell secondhand fashion in a social marketplace with daily deals",
                "url": "https://poshmark.com/",
                "platform": "Poshmark",
                "category": "social_commerce",
                "deal_type": "marketplace",
                "original_price": 80,
                "current_price": 40,
                "savings": 40,
                "discount_percentage": 50,
                "brand_tier": "mixed",
                "product_category": "clothing",
                "size_availability": "varies",
                "return_policy": "3_days",
                "shipping": "prepaid_labels",
                "seasonal_trend": "year_round",
                "quality_grade": "varies",
                "authenticity": "user_verified",
                "membership_required": False,
                "tags": ["social shopping", "marketplace", "secondhand", "community"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "UNIQLO Weekly Promotions",
                "description": "Japanese fast fashion with weekly promotions and limited-time offers",
                "url": "https://www.uniqlo.com/us/en/sale",
                "platform": "UNIQLO",
                "category": "fast_fashion",
                "deal_type": "weekly_promotions",
                "original_price": 40,
                "current_price": 20,
                "savings": 20,
                "discount_percentage": 50,
                "brand_tier": "mid_tier",
                "product_category": "basics",
                "size_availability": "full_range",
                "return_policy": "30_days",
                "shipping": "free_over_99",
                "seasonal_trend": "seasonal",
                "quality_grade": "good",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": ["japanese fashion", "basics", "weekly deals", "quality"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "H&M Conscious Collection Deals",
                "description": "Sustainable fashion pieces made from recycled materials at promotional prices",
                "url": "https://www2.hm.com/en_us/ladies/shop-by-feature/conscious-choice.html",
                "platform": "H&M",
                "category": "sustainable_fashion",
                "deal_type": "sustainable_deals",
                "original_price": 30,
                "current_price": 18,
                "savings": 12,
                "discount_percentage": 40,
                "brand_tier": "fast_fashion",
                "product_category": "eco_fashion",
                "size_availability": "full_range",
                "return_policy": "30_days",
                "shipping": "standard_rates",
                "seasonal_trend": "year_round",
                "quality_grade": "standard",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": ["sustainable", "eco-friendly", "recycled", "conscious"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Zara End of Season Sales",
                "description": "Spanish fast fashion with up to 60% off end-of-season collections",
                "url": "https://www.zara.com/us/en/sale-l1314.html",
                "platform": "Zara",
                "category": "fast_fashion",
                "deal_type": "seasonal_clearance",
                "original_price": 60,
                "current_price": 24,
                "savings": 36,
                "discount_percentage": 60,
                "brand_tier": "mid_tier",
                "product_category": "trendy_fashion",
                "size_availability": "limited_sizes",
                "return_policy": "30_days",
                "shipping": "free_over_50",
                "seasonal_trend": "end_of_season",
                "quality_grade": "good",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": ["trendy", "seasonal sale", "spanish fashion", "fast fashion"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "DSW Shoe Warehouse Deals",
                "description": "Designer shoes and accessories with frequent BOGO offers and rewards program",
                "url": "https://www.dsw.com/en/us/category/sale/N-1z141jt",
                "platform": "DSW",
                "category": "footwear",
                "deal_type": "bogo_offers",
                "original_price": 100,
                "current_price": 50,
                "savings": 50,
                "discount_percentage": 50,
                "brand_tier": "mixed",
                "product_category": "shoes",
                "size_availability": "full_range",
                "return_policy": "60_days",
                "shipping": "free_shipping",
                "seasonal_trend": "year_round",
                "quality_grade": "good",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": ["shoes", "bogo", "rewards program", "free shipping"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Target Circle Fashion Deals",
                "description": "Exclusive member deals on clothing, shoes, and accessories with additional savings",
                "url": "https://www.target.com/c/clothing-shoes-accessories/-/N-5xsxf",
                "platform": "Target",
                "category": "mass_retail",
                "deal_type": "membership_deals",
                "original_price": 25,
                "current_price": 15,
                "savings": 10,
                "discount_percentage": 40,
                "brand_tier": "affordable",
                "product_category": "basics",
                "size_availability": "full_range",
                "return_policy": "90_days",
                "shipping": "free_over_35",
                "seasonal_trend": "year_round",
                "quality_grade": "standard",
                "authenticity": "guaranteed",
                "membership_required": True,
                "tags": ["target circle", "affordable", "membership", "basics"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Kohls Cash Rewards Program",
                "description": "Earn Kohls Cash on purchases and stack with sales for maximum savings",
                "url": "https://www.kohls.com/",
                "platform": "Kohls",
                "category": "department_store",
                "deal_type": "rewards_stacking",
                "original_price": 50,
                "current_price": 25,
                "savings": 25,
                "discount_percentage": 50,
                "brand_tier": "mid_tier",
                "product_category": "clothing",
                "size_availability": "full_range",
                "return_policy": "180_days",
                "shipping": "free_over_75",
                "seasonal_trend": "year_round",
                "quality_grade": "good",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": [
                    "kohls cash",
                    "rewards",
                    "stacking discounts",
                    "department store",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "TJ Maxx & Marshall's Designer Finds",
                "description": "Off-price designer fashion with new arrivals daily at 20-60% off retail",
                "url": "https://tjmaxx.tjx.com/",
                "platform": "TJX Companies",
                "category": "off_price_retail",
                "deal_type": "off_price",
                "original_price": 120,
                "current_price": 48,
                "savings": 72,
                "discount_percentage": 60,
                "brand_tier": "designer",
                "product_category": "clothing",
                "size_availability": "varies",
                "return_policy": "30_days",
                "shipping": "in_store_pickup",
                "seasonal_trend": "year_round",
                "quality_grade": "high",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": [
                    "off-price",
                    "designer finds",
                    "treasure hunt",
                    "daily arrivals",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Nordstrom Anniversary Sale",
                "description": "Annual presale event with new fall merchandise at discounted prices",
                "url": "https://www.nordstrom.com/browse/anniversary-sale",
                "platform": "Nordstrom",
                "category": "luxury_retail",
                "deal_type": "annual_sale",
                "original_price": 250,
                "current_price": 175,
                "savings": 75,
                "discount_percentage": 30,
                "brand_tier": "luxury",
                "product_category": "clothing",
                "size_availability": "full_range",
                "return_policy": "30_days",
                "shipping": "free_shipping",
                "seasonal_trend": "summer_presale",
                "quality_grade": "premium",
                "authenticity": "guaranteed",
                "membership_required": False,
                "tags": ["anniversary sale", "presale", "luxury", "nordstrom"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated fashion & retail deals")
        return curated

    def transform(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform fashion and retail deals data."""
        logger.info("Starting fashion & retail deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate fashion value score
                fashion_score = self._calculate_fashion_value_score(deal)

                # Determine shopping tier
                shopping_tier = self._determine_shopping_tier(deal)

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
                    "fashion_score": fashion_score,
                    "shopping_tier": shopping_tier,
                    "brand_tier": deal.get("brand_tier", "unknown"),
                    "product_category": deal.get("product_category", "general"),
                    "size_availability": deal.get("size_availability", "unknown"),
                    "return_policy": deal.get("return_policy", "standard"),
                    "shipping": deal.get("shipping", "standard"),
                    "seasonal_trend": deal.get("seasonal_trend", "year_round"),
                    "quality_grade": deal.get("quality_grade", "standard"),
                    "authenticity": deal.get("authenticity", "verified"),
                    "membership_required": deal.get("membership_required", False),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming fashion/retail deal: {e}")
                continue

        # Sort by fashion score and discount percentage
        transformed_deals.sort(
            key=lambda x: (x["fashion_score"], x["discount_percentage"]), reverse=True
        )

        logger.info(f"Transformed {len(transformed_deals)} fashion & retail deals")
        return transformed_deals

    def _calculate_fashion_value_score(self, deal: Dict[str, Any]) -> float:
        """Calculate fashion value score for ranking deals."""
        score = 0.0

        # Platform reputation weight
        platform = deal.get("platform", "").lower()
        if any(name in platform for name in ["nordstrom", "nordstrom rack"]):
            score += 5.0  # Premium reputation
        elif any(name in platform for name in ["6pm", "rue la la", "dsw"]):
            score += 4.5  # Specialized fashion
        elif any(name in platform for name in ["tjx", "marshall", "tj maxx"]):
            score += 4.0  # Off-price value
        elif any(name in platform for name in ["zara", "uniqlo", "h&m"]):
            score += 3.5  # Fast fashion
        else:
            score += 2.0

        # Brand tier weight
        brand_tier = deal.get("brand_tier", "").lower()
        if brand_tier == "luxury":
            score += 5.0
        elif brand_tier == "designer":
            score += 4.5
        elif brand_tier == "premium":
            score += 4.0
        elif brand_tier == "mid_tier":
            score += 3.0
        elif brand_tier == "affordable":
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type in ["flash_sales", "annual_sale"]:
            score += 4.0  # Time-sensitive high value
        elif deal_type in ["clearance_sale", "seasonal_clearance"]:
            score += 3.5  # Good discounts
        elif deal_type in ["outlet_pricing", "off_price"]:
            score += 3.0  # Consistent value
        elif deal_type == "rewards_stacking":
            score += 2.5  # Compound savings

        # Quality grade bonus
        quality = deal.get("quality_grade", "").lower()
        if quality == "premium":
            score += 2.0
        elif quality == "high":
            score += 1.5
        elif quality == "good":
            score += 1.0

        # Authenticity bonus
        authenticity = deal.get("authenticity", "").lower()
        if authenticity == "guaranteed":
            score += 1.0
        elif authenticity == "verified":
            score += 0.5

        # Return policy bonus
        return_policy = deal.get("return_policy", "").lower()
        if "180" in return_policy or "365" in return_policy:
            score += 1.5  # Generous return policy
        elif "90" in return_policy or "60" in return_policy:
            score += 1.0
        elif "30" in return_policy:
            score += 0.5

        # Shipping bonus
        shipping = deal.get("shipping", "").lower()
        if "free" in shipping:
            score += 1.0

        # Size availability bonus
        size_availability = deal.get("size_availability", "").lower()
        if "full_range" in size_availability:
            score += 1.0

        # Savings consideration
        savings = deal.get("savings", 0)
        discount_percent = deal.get("discount_percentage", 0)

        if savings > 100 or discount_percent > 60:
            score += 2.0
        elif savings > 50 or discount_percent > 40:
            score += 1.5
        elif savings > 25 or discount_percent > 20:
            score += 1.0

        # Membership penalty (slight)
        if deal.get("membership_required", False):
            score -= 0.5

        return round(score, 2)

    def _determine_shopping_tier(self, deal: Dict[str, Any]) -> str:
        """Determine shopping tier based on brand, platform, and value."""
        brand_tier = deal.get("brand_tier", "").lower()
        platform = deal.get("platform", "").lower()
        savings = deal.get("savings", 0)
        quality = deal.get("quality_grade", "").lower()

        # Luxury tier indicators
        if brand_tier == "luxury" and savings > 75:
            return "luxury_deal"
        elif (
            any(name in platform for name in ["nordstrom", "rue la la"])
            and brand_tier == "luxury"
        ):
            return "luxury_deal"

        # Premium tier indicators
        if brand_tier in ["designer", "premium"] and savings > 50:
            return "premium_deal"
        elif quality == "premium" and savings > 100:
            return "premium_deal"

        # Value tier indicators
        if any(name in platform for name in ["tjx", "nordstrom rack", "6pm"]):
            return "value_deal"
        elif savings > 50 and deal.get("discount_percentage", 0) > 50:
            return "value_deal"

        # Fast fashion tier
        if brand_tier == "fast_fashion" or any(
            name in platform for name in ["zara", "h&m", "uniqlo"]
        ):
            return "trend_deal"

        # Budget tier
        if brand_tier == "affordable" or savings < 25:
            return "budget_deal"

        return "standard_deal"

    def load(self, transformed_data: List[Dict[str, Any]]) -> bool:
        """Load transformed fashion and retail deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "fashion_retail_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "fashion_retail_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(
                f"Successfully saved {len(transformed_data)} fashion & retail deals to {output_dir}"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving fashion & retail deals data: {e}")
            return False


def main():
    """Main function to run the Fashion & Retail Deals ETL."""
    etl = FashionRetailDealsETL()
    success = etl.run()

    if success:
        logger.info("Fashion & Retail Deals ETL completed successfully")
    else:
        logger.error("Fashion & Retail Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
