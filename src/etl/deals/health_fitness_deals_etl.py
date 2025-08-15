"""Health & Fitness Deals ETL Module

This module aggregates health and fitness deals, gym memberships,
workout equipment, supplements, and wellness service discounts.

Usage:
    python src/etl/deals/health_fitness_deals_etl.py

Output:
    - JSON file: data/deals/health_fitness_deals.json
    - CSV file: data/deals/health_fitness_deals.csv
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Add the project root to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.etl.base import BaseETL
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("HealthFitnessDealsETL")


class HealthFitnessDealsETL(BaseETL):
    """ETL for health and fitness deals."""

    def __init__(self):
        super().__init__("health_fitness_deals")
        self.sources = {
            "planet_fitness": {
                "name": "Planet Fitness",
                "deals_url": "https://www.planetfitness.com/deals",
                "category": "gym_membership",
            },
            "la_fitness": {
                "name": "LA Fitness",
                "promotions_url": "https://www.lafitness.com/promotions",
                "category": "gym_membership",
            },
            "myfitnesspal": {
                "name": "MyFitnessPal",
                "premium_url": "https://www.myfitnesspal.com/premium",
                "category": "fitness_apps",
            },
            "vitacost": {
                "name": "Vitacost",
                "deals_url": "https://www.vitacost.com/deals",
                "category": "supplements",
            },
        }

    def extract(self) -> Dict[str, Any]:
        """Extract health and fitness deals from multiple sources."""
        logger.info("Starting health & fitness deals extraction...")

        all_deals = []

        # Add curated health and fitness deals
        curated_deals = self._get_curated_health_fitness_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} health & fitness deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_health_fitness_deals(self) -> List[Dict[str, Any]]:
        """Get manually curated list of health and fitness deals."""
        curated = [
            {
                "title": "Planet Fitness $1 Down Summer Deal",
                "description": "Join for just $1 down and $10/month with no commitment required",
                "url": "https://www.planetfitness.com/deals",
                "platform": "Planet Fitness",
                "category": "gym_membership",
                "deal_type": "promotional_pricing",
                "original_price": 50,  # Typical signup fee
                "current_price": 1,
                "savings": 49,
                "discount_percentage": 98,
                "service_type": "gym_membership",
                "duration": "ongoing_monthly",
                "location_type": "physical_locations",
                "equipment_access": "full_gym",
                "class_access": "group_fitness",
                "commitment_required": False,
                "trial_period": "none",
                "additional_fees": "annual_fee",
                "health_focus": "general_fitness",
                "experience_level": "beginner_friendly",
                "tags": ["gym", "membership", "no commitment", "budget friendly"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "LA Fitness Free Guest Passes",
                "description": "Try LA Fitness free for 3 days with guest passes and tour facilities",
                "url": "https://www.lafitness.com/promotions",
                "platform": "LA Fitness",
                "category": "gym_membership",
                "deal_type": "free_trial",
                "original_price": 90,  # 3-day value
                "current_price": 0,
                "savings": 90,
                "discount_percentage": 100,
                "service_type": "gym_trial",
                "duration": "3_days",
                "location_type": "physical_locations",
                "equipment_access": "full_gym_pool",
                "class_access": "unlimited_classes",
                "commitment_required": False,
                "trial_period": "3_days",
                "additional_fees": "none_during_trial",
                "health_focus": "comprehensive_fitness",
                "experience_level": "all_levels",
                "tags": ["gym trial", "free", "pool access", "classes"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Peloton App Free 30-Day Trial",
                "description": "Access thousands of workout classes from home with 30-day free trial",
                "url": "https://www.onepeloton.com/app",
                "platform": "Peloton",
                "category": "fitness_apps",
                "deal_type": "free_trial",
                "original_price": 39,  # Monthly subscription
                "current_price": 0,
                "savings": 39,
                "discount_percentage": 100,
                "service_type": "fitness_app",
                "duration": "30_days",
                "location_type": "home_based",
                "equipment_access": "bodyweight_equipment",
                "class_access": "unlimited_streaming",
                "commitment_required": False,
                "trial_period": "30_days",
                "additional_fees": "subscription_after_trial",
                "health_focus": "varied_workouts",
                "experience_level": "all_levels",
                "tags": ["home workouts", "streaming", "free trial", "variety"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "MyFitnessPal Premium Free Trial",
                "description": "Track nutrition and fitness with premium features free for 30 days",
                "url": "https://www.myfitnesspal.com/premium",
                "platform": "MyFitnessPal",
                "category": "health_apps",
                "deal_type": "free_trial",
                "original_price": 20,  # Monthly premium
                "current_price": 0,
                "savings": 20,
                "discount_percentage": 100,
                "service_type": "nutrition_tracking",
                "duration": "30_days",
                "location_type": "mobile_app",
                "equipment_access": "none_required",
                "class_access": "premium_features",
                "commitment_required": False,
                "trial_period": "30_days",
                "additional_fees": "subscription_after_trial",
                "health_focus": "nutrition_tracking",
                "experience_level": "all_levels",
                "tags": ["nutrition", "tracking", "premium features", "free trial"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Vitacost Supplements 25% Off First Order",
                "description": "Save 25% on vitamins, supplements, and health products on your first order",
                "url": "https://www.vitacost.com/deals",
                "platform": "Vitacost",
                "category": "supplements",
                "deal_type": "first_order_discount",
                "original_price": 100,
                "current_price": 75,
                "savings": 25,
                "discount_percentage": 25,
                "service_type": "supplement_retailer",
                "duration": "one_time",
                "location_type": "online_shipping",
                "equipment_access": "supplements_vitamins",
                "class_access": "none",
                "commitment_required": False,
                "trial_period": "none",
                "additional_fees": "shipping_fees",
                "health_focus": "nutritional_supplements",
                "experience_level": "all_levels",
                "tags": ["supplements", "vitamins", "first order", "health products"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Beachbody On Demand Free Trial",
                "description": "Stream hundreds of workout programs including P90X and Insanity for free",
                "url": "https://www.beachbodyondemand.com/",
                "platform": "Beachbody",
                "category": "fitness_streaming",
                "deal_type": "free_trial",
                "original_price": 39,  # 3-month value
                "current_price": 0,
                "savings": 39,
                "discount_percentage": 100,
                "service_type": "workout_streaming",
                "duration": "14_days",
                "location_type": "home_based",
                "equipment_access": "minimal_equipment",
                "class_access": "unlimited_programs",
                "commitment_required": False,
                "trial_period": "14_days",
                "additional_fees": "subscription_after_trial",
                "health_focus": "structured_programs",
                "experience_level": "beginner_to_advanced",
                "tags": [
                    "home workouts",
                    "structured programs",
                    "free trial",
                    "variety",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Headspace Meditation Free Content",
                "description": "Free meditation sessions and mindfulness exercises for mental health",
                "url": "https://www.headspace.com/meditation/free",
                "platform": "Headspace",
                "category": "mental_health",
                "deal_type": "free_content",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "service_type": "meditation_app",
                "duration": "ongoing",
                "location_type": "mobile_app",
                "equipment_access": "none_required",
                "class_access": "free_sessions",
                "commitment_required": False,
                "trial_period": "unlimited",
                "additional_fees": "premium_upgrade_available",
                "health_focus": "mental_wellness",
                "experience_level": "all_levels",
                "tags": ["meditation", "mental health", "free", "mindfulness"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Nike Training Club Free App",
                "description": "Free workouts designed by Nike trainers with no subscription required",
                "url": "https://www.nike.com/ntc-app",
                "platform": "Nike",
                "category": "fitness_apps",
                "deal_type": "completely_free",
                "original_price": 120,  # Equivalent training value
                "current_price": 0,
                "savings": 120,
                "discount_percentage": 100,
                "service_type": "fitness_app",
                "duration": "permanent",
                "location_type": "home_gym_anywhere",
                "equipment_access": "bodyweight_minimal",
                "class_access": "unlimited_workouts",
                "commitment_required": False,
                "trial_period": "none_needed",
                "additional_fees": "none",
                "health_focus": "athletic_training",
                "experience_level": "beginner_to_advanced",
                "tags": ["nike", "free app", "athletic training", "no subscription"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Strava Free Activity Tracking",
                "description": "Track runs, rides, and workouts with free social fitness features",
                "url": "https://www.strava.com/",
                "platform": "Strava",
                "category": "fitness_tracking",
                "deal_type": "freemium",
                "original_price": 60,  # Annual premium
                "current_price": 0,
                "savings": 60,
                "discount_percentage": 100,
                "service_type": "activity_tracking",
                "duration": "ongoing",
                "location_type": "outdoor_indoor",
                "equipment_access": "smartphone_gps",
                "class_access": "community_features",
                "commitment_required": False,
                "trial_period": "none_needed",
                "additional_fees": "premium_upgrade_available",
                "health_focus": "endurance_sports",
                "experience_level": "all_levels",
                "tags": ["activity tracking", "social fitness", "running", "cycling"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Yoga with Adriene Free YouTube Classes",
                "description": "Free yoga classes for all levels on YouTube with 30-day challenges",
                "url": "https://yogawithadriene.com/",
                "platform": "Yoga with Adriene",
                "category": "yoga",
                "deal_type": "completely_free",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "service_type": "yoga_instruction",
                "duration": "ongoing",
                "location_type": "home_based",
                "equipment_access": "yoga_mat",
                "class_access": "unlimited_youtube",
                "commitment_required": False,
                "trial_period": "none_needed",
                "additional_fees": "none",
                "health_focus": "yoga_mindfulness",
                "experience_level": "all_levels",
                "tags": ["yoga", "youtube", "free", "mindfulness"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Calm App Daily Free Sessions",
                "description": "Daily free meditation and sleep stories with premium upgrade options",
                "url": "https://www.calm.com/",
                "platform": "Calm",
                "category": "mental_health",
                "deal_type": "daily_free_content",
                "original_price": 70,  # Annual subscription
                "current_price": 0,
                "savings": 70,
                "discount_percentage": 100,
                "service_type": "meditation_sleep",
                "duration": "ongoing_daily",
                "location_type": "mobile_app",
                "equipment_access": "none_required",
                "class_access": "daily_free_sessions",
                "commitment_required": False,
                "trial_period": "daily_access",
                "additional_fees": "premium_upgrade_available",
                "health_focus": "mental_wellness_sleep",
                "experience_level": "all_levels",
                "tags": ["meditation", "sleep stories", "daily free", "mental health"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Fitbit Community Challenges Free",
                "description": "Join free community fitness challenges and track progress with friends",
                "url": "https://www.fitbit.com/global/us/products/services/premium",
                "platform": "Fitbit",
                "category": "fitness_tracking",
                "deal_type": "community_features",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "service_type": "fitness_tracking",
                "duration": "ongoing",
                "location_type": "anywhere",
                "equipment_access": "fitbit_device",
                "class_access": "community_challenges",
                "commitment_required": False,
                "trial_period": "none_needed",
                "additional_fees": "device_purchase",
                "health_focus": "daily_activity",
                "experience_level": "all_levels",
                "tags": ["fitness tracking", "community", "challenges", "social"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "iHerb First Order 20% Off + Free Shipping",
                "description": "Save on vitamins, supplements, and natural products with first order discount",
                "url": "https://www.iherb.com/",
                "platform": "iHerb",
                "category": "supplements",
                "deal_type": "first_order_discount",
                "original_price": 50,
                "current_price": 40,
                "savings": 10,
                "discount_percentage": 20,
                "service_type": "supplement_retailer",
                "duration": "one_time",
                "location_type": "online_shipping",
                "equipment_access": "supplements_natural_products",
                "class_access": "none",
                "commitment_required": False,
                "trial_period": "none",
                "additional_fees": "none_with_minimum",
                "health_focus": "nutritional_supplements",
                "experience_level": "all_levels",
                "tags": [
                    "supplements",
                    "natural products",
                    "first order",
                    "free shipping",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated health & fitness deals")
        return curated

    def transform(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform health and fitness deals data."""
        logger.info("Starting health & fitness deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate health value score
                health_score = self._calculate_health_value_score(deal)

                # Determine accessibility level
                accessibility = self._determine_accessibility_level(deal)

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
                    "health_score": health_score,
                    "accessibility": accessibility,
                    "service_type": deal.get("service_type", "unknown"),
                    "duration": deal.get("duration", "unknown"),
                    "location_type": deal.get("location_type", "unknown"),
                    "equipment_access": deal.get("equipment_access", "unknown"),
                    "class_access": deal.get("class_access", "none"),
                    "commitment_required": deal.get("commitment_required", True),
                    "trial_period": deal.get("trial_period", "none"),
                    "additional_fees": deal.get("additional_fees", "unknown"),
                    "health_focus": deal.get("health_focus", "general"),
                    "experience_level": deal.get("experience_level", "all_levels"),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming health/fitness deal: {e}")
                continue

        # Sort by health score and savings
        transformed_deals.sort(
            key=lambda x: (x["health_score"], x["savings"]), reverse=True
        )

        logger.info(f"Transformed {len(transformed_deals)} health & fitness deals")
        return transformed_deals

    def _calculate_health_value_score(self, deal: Dict[str, Any]) -> float:
        """Calculate health value score for ranking deals."""
        score = 0.0

        # Platform reputation weight
        platform = deal.get("platform", "").lower()
        if any(name in platform for name in ["nike", "peloton", "beachbody"]):
            score += 5.0  # Premium fitness brands
        elif any(name in platform for name in ["planet fitness", "la fitness"]):
            score += 4.5  # Established gym chains
        elif any(name in platform for name in ["headspace", "calm", "strava"]):
            score += 4.0  # Popular wellness apps
        elif any(name in platform for name in ["myfitnesspal", "fitbit"]):
            score += 3.5  # Health tracking
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type in ["completely_free", "freemium"]:
            score += 5.0  # Permanent free access
        elif deal_type == "free_trial":
            score += 4.0  # Try before buy
        elif deal_type in ["promotional_pricing", "first_order_discount"]:
            score += 3.0  # Reduced cost entry
        elif deal_type in ["free_content", "daily_free_content"]:
            score += 3.5  # Regular free value

        # No commitment bonus
        if not deal.get("commitment_required", True):
            score += 2.0

        # Location flexibility bonus
        location_type = deal.get("location_type", "").lower()
        if any(keyword in location_type for keyword in ["home", "mobile", "anywhere"]):
            score += 1.5  # Convenience factor

        # Equipment requirements (less is better)
        equipment = deal.get("equipment_access", "").lower()
        if "none" in equipment or "bodyweight" in equipment:
            score += 1.0
        elif "minimal" in equipment:
            score += 0.5

        # Health focus bonus
        health_focus = deal.get("health_focus", "").lower()
        if any(
            keyword in health_focus for keyword in ["mental", "wellness", "mindfulness"]
        ):
            score += 1.0  # Mental health is important
        elif "nutrition" in health_focus:
            score += 0.5

        # Experience level inclusivity
        if deal.get("experience_level") == "all_levels":
            score += 1.0

        # Trial period length bonus
        trial_period = deal.get("trial_period", "").lower()
        if "30" in trial_period:
            score += 1.5
        elif "14" in trial_period or "7" in trial_period:
            score += 1.0
        elif "unlimited" in trial_period or "ongoing" in trial_period:
            score += 2.0

        # Savings consideration
        savings = deal.get("savings", 0)
        if savings > 75:
            score += 2.0
        elif savings > 25:
            score += 1.0
        elif savings > 0:
            score += 0.5

        return round(score, 2)

    def _determine_accessibility_level(self, deal: Dict[str, Any]) -> str:
        """Determine accessibility level of the health/fitness deal."""
        location_type = deal.get("location_type", "").lower()
        equipment = deal.get("equipment_access", "").lower()
        commitment = deal.get("commitment_required", True)
        fees = deal.get("additional_fees", "").lower()

        # Highly accessible indicators
        if (
            any(keyword in location_type for keyword in ["home", "mobile", "anywhere"])
            and ("none" in equipment or "bodyweight" in equipment)
            and not commitment
            and "none" in fees
        ):
            return "highly_accessible"

        # Very accessible indicators
        if (
            any(keyword in location_type for keyword in ["home", "mobile"])
            and "minimal" in equipment
            and not commitment
        ):
            return "very_accessible"

        # Accessible indicators
        if not commitment or "home" in location_type:
            return "accessible"

        # Moderately accessible indicators
        if "physical" in location_type and "full" in equipment:
            return "moderately_accessible"

        # Limited accessibility
        return "limited_accessibility"

    def load(self, transformed_data: List[Dict[str, Any]]) -> bool:
        """Load transformed health and fitness deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "health_fitness_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "health_fitness_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(
                f"Successfully saved {len(transformed_data)} health & fitness deals to {output_dir}"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving health & fitness deals data: {e}")
            return False


def main():
    """Main function to run the Health & Fitness Deals ETL."""
    etl = HealthFitnessDealsETL()
    success = etl.run()

    if success:
        logger.info("Health & Fitness Deals ETL completed successfully")
    else:
        logger.error("Health & Fitness Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
