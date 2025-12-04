"""Travel & Vacation Deals ETL Module

This module aggregates travel deals, vacation packages, flight discounts,
hotel offers, and travel-related deals from various platforms.

Usage:
    python src/etl/deals/travel_deals_etl.py

Output:
    - JSON file: data/deals/travel_deals.json
    - CSV file: data/deals/travel_deals.csv
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
logger = get_logger("TravelDealsETL")


class TravelDealsETL(BaseETL):
    """ETL for travel and vacation deals."""

    def __init__(self):
        super().__init__("travel_deals")
        self.sources = {
            "skyscanner": {
                "name": "Skyscanner",
                "deals_url": "https://www.skyscanner.com/deals",
                "category": "flights",
            },
            "booking_deals": {
                "name": "Booking.com",
                "deals_url": "https://www.booking.com/deals.html",
                "category": "hotels",
            },
            "expedia": {
                "name": "Expedia",
                "deals_url": "https://www.expedia.com/Deals",
                "category": "packages",
            },
            "airbnb": {
                "name": "Airbnb",
                "deals_url": "https://www.airbnb.com/",
                "category": "accommodations",
            },
            "groupon_travel": {
                "name": "Groupon Travel",
                "deals_url": "https://www.groupon.com/browse/travel",
                "category": "travel_deals",
            },
        }

    def extract(self) -> dict[str, Any]:
        """Extract travel deals from multiple sources."""
        logger.info("Starting travel deals extraction...")

        all_deals = []

        # Add curated travel deals and sources
        curated_deals = self._get_curated_travel_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} travel deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_travel_deals(self) -> list[dict[str, Any]]:
        """Get manually curated list of travel deals and sources."""
        curated = [
            {
                "title": "Skyscanner Flight Deals",
                "description": "Compare millions of flights and find the cheapest deals across airlines",
                "url": "https://www.skyscanner.com/deals",
                "platform": "Skyscanner",
                "category": "flights",
                "deal_type": "flight_comparison",
                "original_price": 0,  # Comparison service
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "travel_type": "flights",
                "destination_type": "global",
                "booking_flexibility": "high",
                "cancellation_policy": "varies",
                "travel_season": "year_round",
                "advance_booking_days": 30,
                "deal_duration": "varies",
                "rating": 4.5,
                "features": ["price comparison", "price alerts", "flexible dates"],
                "tags": ["flights", "comparison", "alerts", "worldwide"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Booking.com Hotel Deals",
                "description": "Special hotel rates, last-minute deals, and free cancellation options",
                "url": "https://www.booking.com/deals.html",
                "platform": "Booking.com",
                "category": "hotels",
                "deal_type": "hotel_discounts",
                "original_price": 200,  # Average hotel night
                "current_price": 140,
                "savings": 60,
                "discount_percentage": 30,
                "travel_type": "accommodations",
                "destination_type": "global",
                "booking_flexibility": "high",
                "cancellation_policy": "free_cancellation",
                "travel_season": "year_round",
                "advance_booking_days": 14,
                "deal_duration": "limited_time",
                "rating": 4.3,
                "features": ["free cancellation", "instant booking", "rewards program"],
                "tags": ["hotels", "discounts", "free cancellation", "rewards"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Expedia Vacation Packages",
                "description": "Bundle flights and hotels for extra savings on vacation packages",
                "url": "https://www.expedia.com/Deals",
                "platform": "Expedia",
                "category": "packages",
                "deal_type": "vacation_bundles",
                "original_price": 1500,  # Flight + hotel
                "current_price": 1200,
                "savings": 300,
                "discount_percentage": 20,
                "travel_type": "vacation_packages",
                "destination_type": "popular_destinations",
                "booking_flexibility": "medium",
                "cancellation_policy": "varies",
                "travel_season": "peak_season",
                "advance_booking_days": 45,
                "deal_duration": "limited_time",
                "rating": 4.2,
                "features": ["bundle savings", "one-stop booking", "rewards points"],
                "tags": ["packages", "bundles", "flights", "hotels"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Airbnb Unique Stays",
                "description": "Unique accommodations and experiences with competitive pricing",
                "url": "https://www.airbnb.com/",
                "platform": "Airbnb",
                "category": "accommodations",
                "deal_type": "alternative_lodging",
                "original_price": 180,  # Hotel equivalent
                "current_price": 120,
                "savings": 60,
                "discount_percentage": 33,
                "travel_type": "unique_accommodations",
                "destination_type": "global",
                "booking_flexibility": "high",
                "cancellation_policy": "varies_by_host",
                "travel_season": "year_round",
                "advance_booking_days": 7,
                "deal_duration": "ongoing",
                "rating": 4.4,
                "features": ["unique stays", "local experiences", "host interaction"],
                "tags": ["unique", "local", "experiences", "alternative"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Groupon Travel Experiences",
                "description": "Discounted travel experiences, tours, and vacation packages",
                "url": "https://www.groupon.com/browse/travel",
                "platform": "Groupon",
                "category": "experiences",
                "deal_type": "experience_deals",
                "original_price": 500,
                "current_price": 250,
                "savings": 250,
                "discount_percentage": 50,
                "travel_type": "experiences",
                "destination_type": "local_and_travel",
                "booking_flexibility": "medium",
                "cancellation_policy": "varies",
                "travel_season": "varies",
                "advance_booking_days": 30,
                "deal_duration": "limited_time",
                "rating": 4.0,
                "features": ["group deals", "local experiences", "travel packages"],
                "tags": ["experiences", "tours", "group deals", "activities"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Google Flights Best Deals",
                "description": "Flight price tracking and alerts for the best travel deals",
                "url": "https://www.google.com/travel/flights",
                "platform": "Google Flights",
                "category": "flights",
                "deal_type": "price_tracking",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "travel_type": "flights",
                "destination_type": "global",
                "booking_flexibility": "high",
                "cancellation_policy": "varies",
                "travel_season": "year_round",
                "advance_booking_days": 21,
                "deal_duration": "ongoing",
                "rating": 4.6,
                "features": [
                    "price tracking",
                    "calendar view",
                    "prediction algorithms",
                ],
                "tags": ["google", "price tracking", "alerts", "predictions"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Scott's Cheap Flights (Going)",
                "description": "Email alerts for international flight deals with savings up to 90%",
                "url": "https://going.com/",
                "platform": "Going",
                "category": "flight_deals",
                "deal_type": "deal_alerts",
                "original_price": 1000,  # International flight
                "current_price": 300,
                "savings": 700,
                "discount_percentage": 70,
                "travel_type": "international_flights",
                "destination_type": "international",
                "booking_flexibility": "medium",
                "cancellation_policy": "varies",
                "travel_season": "off_peak",
                "advance_booking_days": 60,
                "deal_duration": "time_sensitive",
                "rating": 4.7,
                "features": ["email alerts", "mistake fares", "premium support"],
                "tags": ["international", "alerts", "mistake fares", "premium"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Hostelworld Budget Travel",
                "description": "Budget accommodations and backpacker-friendly deals worldwide",
                "url": "https://www.hostelworld.com/",
                "platform": "Hostelworld",
                "category": "budget_travel",
                "deal_type": "budget_accommodation",
                "original_price": 80,  # Hotel equivalent
                "current_price": 25,
                "savings": 55,
                "discount_percentage": 69,
                "travel_type": "budget_accommodations",
                "destination_type": "global",
                "booking_flexibility": "high",
                "cancellation_policy": "flexible",
                "travel_season": "year_round",
                "advance_booking_days": 3,
                "deal_duration": "ongoing",
                "rating": 4.1,
                "features": [
                    "budget friendly",
                    "social atmosphere",
                    "flexible booking",
                ],
                "tags": ["budget", "hostels", "backpacking", "social"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Viator Tours & Activities",
                "description": "Discounted tours, activities, and experiences in destinations worldwide",
                "url": "https://www.viator.com/",
                "platform": "Viator",
                "category": "activities",
                "deal_type": "tour_discounts",
                "original_price": 150,
                "current_price": 120,
                "savings": 30,
                "discount_percentage": 20,
                "travel_type": "tours_activities",
                "destination_type": "tourist_destinations",
                "booking_flexibility": "medium",
                "cancellation_policy": "varies",
                "travel_season": "year_round",
                "advance_booking_days": 7,
                "deal_duration": "varies",
                "rating": 4.3,
                "features": ["skip-the-line", "local guides", "mobile tickets"],
                "tags": ["tours", "activities", "experiences", "guides"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Travelzoo Top 20 Deals",
                "description": "Curated weekly selection of the best travel deals tested by experts",
                "url": "https://www.travelzoo.com/top20/",
                "platform": "Travelzoo",
                "category": "curated_deals",
                "deal_type": "expert_curated",
                "original_price": 800,
                "current_price": 400,
                "savings": 400,
                "discount_percentage": 50,
                "travel_type": "various",
                "destination_type": "various",
                "booking_flexibility": "medium",
                "cancellation_policy": "varies",
                "travel_season": "varies",
                "advance_booking_days": 30,
                "deal_duration": "weekly_refresh",
                "rating": 4.5,
                "features": ["expert tested", "weekly updates", "quality verified"],
                "tags": ["curated", "expert tested", "weekly", "quality"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Priceline Express Deals",
                "description": "Mystery hotel and car rental deals with significant savings",
                "url": "https://www.priceline.com/relax/at/hotel-express-deals",
                "platform": "Priceline",
                "category": "mystery_deals",
                "deal_type": "opaque_booking",
                "original_price": 200,
                "current_price": 100,
                "savings": 100,
                "discount_percentage": 50,
                "travel_type": "hotels_cars",
                "destination_type": "major_cities",
                "booking_flexibility": "low",
                "cancellation_policy": "non_refundable",
                "travel_season": "year_round",
                "advance_booking_days": 1,
                "deal_duration": "ongoing",
                "rating": 4.0,
                "features": ["mystery deals", "significant savings", "instant booking"],
                "tags": ["mystery", "priceline", "express deals", "last minute"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Costco Travel Member Deals",
                "description": "Exclusive travel packages and deals for Costco members",
                "url": "https://www.costcotravel.com/",
                "platform": "Costco Travel",
                "category": "member_deals",
                "deal_type": "membership_exclusive",
                "original_price": 2000,
                "current_price": 1600,
                "savings": 400,
                "discount_percentage": 20,
                "travel_type": "vacation_packages",
                "destination_type": "premium_destinations",
                "booking_flexibility": "medium",
                "cancellation_policy": "varies",
                "travel_season": "varies",
                "advance_booking_days": 60,
                "deal_duration": "member_exclusive",
                "rating": 4.4,
                "features": ["member exclusive", "package deals", "concierge service"],
                "tags": ["costco", "members only", "packages", "premium"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated travel deals")
        return curated

    def transform(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform travel deals data."""
        logger.info("Starting travel deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate travel value score
                travel_score = self._calculate_travel_value_score(deal)

                # Determine deal quality tier
                deal_quality = self._determine_travel_deal_quality(deal)

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
                    "travel_score": travel_score,
                    "deal_quality": deal_quality,
                    "travel_type": deal.get("travel_type", "unknown"),
                    "destination_type": deal.get("destination_type", "various"),
                    "booking_flexibility": deal.get("booking_flexibility", "medium"),
                    "cancellation_policy": deal.get("cancellation_policy", "varies"),
                    "travel_season": deal.get("travel_season", "year_round"),
                    "advance_booking_days": deal.get("advance_booking_days", 30),
                    "deal_duration": deal.get("deal_duration", "limited_time"),
                    "rating": deal.get("rating", 4.0),
                    "features": deal.get("features", []),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming travel deal: {e}")
                continue

        # Sort by travel score and savings
        transformed_deals.sort(key=lambda x: (x["travel_score"], x["savings"]), reverse=True)

        logger.info(f"Transformed {len(transformed_deals)} travel deals")
        return transformed_deals

    def _calculate_travel_value_score(self, deal: dict[str, Any]) -> float:
        """Calculate travel value score for ranking deals."""
        score = 0.0

        # Platform quality weight
        platform = deal.get("platform", "").lower()
        if any(name in platform for name in ["google", "expedia", "booking.com"]):
            score += 5.0  # Major travel platforms
        elif any(name in platform for name in ["skyscanner", "going", "travelzoo"]):
            score += 4.5  # Specialized deal platforms
        elif any(name in platform for name in ["airbnb", "viator", "costco"]):
            score += 4.0  # Quality specialized services
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type in ["deal_alerts", "expert_curated"]:
            score += 5.0  # High-value curated deals
        elif deal_type in ["vacation_bundles", "experience_deals"]:
            score += 4.5  # Package deals
        elif deal_type in ["flight_comparison", "price_tracking"]:
            score += 4.0  # Comparison tools
        elif deal_type in ["hotel_discounts", "tour_discounts"]:
            score += 3.5  # Standard discounts
        elif deal_type == "opaque_booking":
            score += 3.0  # Mystery deals (risk vs reward)

        # Flexibility bonus
        flexibility = deal.get("booking_flexibility", "medium").lower()
        if flexibility == "high":
            score += 2.0
        elif flexibility == "medium":
            score += 1.0

        # Cancellation policy bonus
        cancellation = deal.get("cancellation_policy", "varies").lower()
        if "free" in cancellation:
            score += 1.5
        elif "flexible" in cancellation:
            score += 1.0

        # Rating bonus
        rating = deal.get("rating", 0)
        if rating >= 4.5:
            score += 2.0
        elif rating >= 4.0:
            score += 1.5
        elif rating >= 3.5:
            score += 1.0

        # Savings consideration
        savings = deal.get("savings", 0)
        discount_percent = deal.get("discount_percentage", 0)

        if savings > 500 or discount_percent > 60:
            score += 3.0
        elif savings > 200 or discount_percent > 40:
            score += 2.0
        elif savings > 100 or discount_percent > 20:
            score += 1.0

        # Travel type bonus
        travel_type = deal.get("travel_type", "").lower()
        if "international" in travel_type:
            score += 1.0
        elif any(keyword in travel_type for keyword in ["packages", "experiences"]):
            score += 0.5

        return round(score, 2)

    def _determine_travel_deal_quality(self, deal: dict[str, Any]) -> str:
        """Determine travel deal quality tier."""
        platform = deal.get("platform", "").lower()
        rating = deal.get("rating", 0)
        savings = deal.get("savings", 0)
        flexibility = deal.get("booking_flexibility", "medium").lower()

        # Premium quality indicators
        if any(name in platform for name in ["costco", "travelzoo"]) and savings > 400 or rating >= 4.6 and savings > 500:
            return "premium"

        # High quality indicators
        if any(name in platform for name in ["google", "going"]) and rating >= 4.5 or flexibility == "high" and savings > 200 or rating >= 4.3 and savings > 300:
            return "high"

        # Good quality indicators
        if rating >= 4.0 and savings > 100 or any(name in platform for name in ["booking.com", "expedia", "airbnb"]):
            return "good"

        # Standard quality
        if rating >= 3.5 or savings > 50:
            return "standard"

        return "basic"

    def load(self, transformed_data: list[dict[str, Any]]) -> bool:
        """Load transformed travel deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "travel_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "travel_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(f"Successfully saved {len(transformed_data)} travel deals to {output_dir}")
            return True

        except Exception as e:
            logger.error(f"Error saving travel deals data: {e}")
            return False


def main():
    """Main function to run the Travel Deals ETL."""
    etl = TravelDealsETL()
    success = etl.run()

    if success:
        logger.info("Travel Deals ETL completed successfully")
    else:
        logger.error("Travel Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
