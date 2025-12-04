"""ADHD-Friendly Location Intelligence ETL.

Comprehensive location discovery and rating for neurodivergent individuals:
- Sensory environment assessment (noise, lighting, crowds)
- ADHD-friendly workspace discovery
- Overstimulation risk analysis
- Fidget-friendly location identification
- Neurodivergent community spaces mapping

Creating a neurodivergent-friendly world, one location at a time! 🧠✨
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.utils.logging import get_logger


class ADHDFriendlyLocationsETL(BaseETL):
    """ADHD-Friendly Locations ETL for neurodivergent-friendly space discovery."""

    def __init__(self, **kwargs):
        """Initialize ADHD-Friendly Locations ETL."""
        super().__init__(
            name="adhd_friendly_locations",
            description="Neurodivergent-friendly location discovery and assessment",
            **kwargs,
        )
        self.logger = get_logger("ETL.ADHDFriendlyLocations")

        # Location data sources (mock endpoints for now)
        self.endpoints = {
            "foursquare_venues": "https://api.foursquare.com/v3/places/search",
            "google_places": "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            "yelp_businesses": "https://api.yelp.com/v3/businesses/search",
            "coworking_spaces": "https://example.com/api/coworking",
            "libraries": "https://example.com/api/libraries",
        }

        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        # ADHD-friendly criteria
        self.sensory_criteria = {
            "noise_levels": {
                "silent": 0,
                "quiet": 1,
                "moderate": 2,
                "noisy": 3,
                "very_noisy": 4,
            },
            "lighting": {
                "natural_light": 3,
                "warm_artificial": 2,
                "neutral_artificial": 1,
                "harsh_fluorescent": -2,
                "dim": 0,
            },
            "crowd_density": {
                "empty": 0,
                "few_people": 1,
                "moderate_crowd": 2,
                "busy": 3,
                "packed": 4,
            },
        }

        # Location types and their ADHD-friendliness
        self.location_types = {
            "libraries": {"base_score": 8, "noise_tolerance": 1, "fidget_friendly": 7},
            "coffee_shops": {
                "base_score": 6,
                "noise_tolerance": 3,
                "fidget_friendly": 8,
            },
            "coworking_spaces": {
                "base_score": 7,
                "noise_tolerance": 2,
                "fidget_friendly": 9,
            },
            "parks": {"base_score": 9, "noise_tolerance": 4, "fidget_friendly": 10},
            "museums": {"base_score": 7, "noise_tolerance": 2, "fidget_friendly": 4},
            "bookstores": {"base_score": 8, "noise_tolerance": 1, "fidget_friendly": 6},
        }

    def extract(self) -> list[dict[str, Any]]:
        """Extract location data for ADHD-friendly analysis."""
        self.logger.info("Starting ADHD-friendly location data extraction 🧠")
        extracted_data = []

        try:
            # Extract location data from various sources
            locations_data = self._extract_locations()
            if locations_data:
                extracted_data.extend(locations_data)
                self.metrics.records_extracted += len(locations_data)

            # Extract crowdsourced ADHD reviews
            reviews_data = self._extract_neurodivergent_reviews()
            if reviews_data:
                extracted_data.extend(reviews_data)
                self.metrics.records_extracted += len(reviews_data)

            # Generate location intelligence analysis
            intelligence_data = self._generate_location_intelligence()
            if intelligence_data:
                extracted_data.extend(intelligence_data)
                self.metrics.records_extracted += len(intelligence_data)

            self.logger.info(f"Extracted {len(extracted_data)} ADHD-friendly location records 🌟")

        except Exception as e:
            self.logger.error(f"Failed to extract ADHD location data: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def _extract_locations(self) -> list[dict[str, Any]]:
        """Extract location data (mock implementation)."""
        locations_data = []

        # Mock Valencia locations data
        mock_locations = [
            {
                "data_type": "location",
                "name": "Biblioteca Central de Valencia",
                "type": "library",
                "address": "Carrer de l'Hospital, 13, Valencia",
                "coordinates": {"lat": 39.4699, "lon": -0.3763},
                "description": "Modern central library with quiet study areas",
                "amenities": [
                    "wifi",
                    "quiet_zones",
                    "natural_light",
                    "comfortable_seating",
                ],
                "noise_level": "quiet",
                "lighting_type": "natural_light",
                "crowd_density": "moderate_crowd",
                "has_private_study_rooms": True,
                "allows_food_drink": False,
                "fidget_friendly_score": 7,
                "accessibility": {"wheelchair_accessible": True, "elevator": True},
                "opening_hours": {
                    "mon_fri": "9:00-20:00",
                    "sat": "9:00-14:00",
                    "sun": "closed",
                },
                "contact": {
                    "phone": "+34 96 352 54 78",
                    "website": "https://bibliotecas.valencia.es",
                },
                "extracted_at": datetime.utcnow().isoformat(),
            },
            {
                "data_type": "location",
                "name": "Café Central",
                "type": "coffee_shop",
                "address": "Plaza del Ayuntamiento, 15, Valencia",
                "coordinates": {"lat": 39.4699, "lon": -0.3763},
                "description": "Historic café with various seating options",
                "amenities": [
                    "wifi",
                    "outdoor_seating",
                    "background_music",
                    "laptop_friendly",
                ],
                "noise_level": "moderate",
                "lighting_type": "warm_artificial",
                "crowd_density": "busy",
                "has_private_study_rooms": False,
                "allows_food_drink": True,
                "fidget_friendly_score": 8,
                "accessibility": {"wheelchair_accessible": True, "elevator": False},
                "opening_hours": {"mon_fri": "7:00-22:00", "sat_sun": "8:00-23:00"},
                "contact": {
                    "phone": "+34 96 351 73 36",
                    "website": "https://cafecentral.es",
                },
                "extracted_at": datetime.utcnow().isoformat(),
            },
            {
                "data_type": "location",
                "name": "Jardín Botánico de Valencia",
                "type": "park",
                "address": "Carrer de Quart, 80, Valencia",
                "coordinates": {"lat": 39.4753, "lon": -0.3874},
                "description": "Peaceful botanical garden with diverse environments",
                "amenities": ["nature", "benches", "walking_paths", "quiet_zones"],
                "noise_level": "quiet",
                "lighting_type": "natural_light",
                "crowd_density": "few_people",
                "has_private_study_rooms": False,
                "allows_food_drink": False,
                "fidget_friendly_score": 10,
                "accessibility": {"wheelchair_accessible": True, "paved_paths": True},
                "opening_hours": {"daily": "9:00-19:00"},
                "contact": {
                    "phone": "+34 96 315 68 00",
                    "website": "https://jardinbotanico.org",
                },
                "extracted_at": datetime.utcnow().isoformat(),
            },
        ]

        locations_data.extend(mock_locations)
        return locations_data

    def _extract_neurodivergent_reviews(self) -> list[dict[str, Any]]:
        """Extract crowdsourced neurodivergent-friendly reviews."""
        reviews_data = []

        # Mock neurodivergent community reviews
        mock_reviews = [
            {
                "data_type": "neurodivergent_review",
                "location_name": "Biblioteca Central de Valencia",
                "reviewer_type": "adhd_individual",
                "sensory_rating": 9,
                "focus_rating": 8,
                "comfort_rating": 9,
                "stimulation_level": "optimal",
                "review_text": "Perfect for hyperfocus sessions. Quiet zones are amazing and natural light helps so much.",
                "pros": [
                    "natural_light",
                    "quiet_zones",
                    "comfortable_chairs",
                    "stable_wifi",
                ],
                "cons": ["no_food_allowed", "limited_weekend_hours"],
                "recommended_for": ["reading", "studying", "quiet_work"],
                "avoid_times": ["morning_rush_hour", "exam_periods"],
                "accessibility_notes": "Elevator can be noisy but worth it for upper floor quiet areas",
                "fidget_tolerance": "high",
                "date_reviewed": datetime.utcnow().isoformat(),
                "extracted_at": datetime.utcnow().isoformat(),
            },
            {
                "data_type": "neurodivergent_review",
                "location_name": "Café Central",
                "reviewer_type": "adhd_individual",
                "sensory_rating": 6,
                "focus_rating": 5,
                "comfort_rating": 7,
                "stimulation_level": "slightly_high",
                "review_text": "Good for creative work but can get overwhelming during peak hours. Background music helps mask distractions.",
                "pros": [
                    "background_music",
                    "coffee_stimulation",
                    "people_watching",
                    "flexible_seating",
                ],
                "cons": [
                    "crowded_peak_hours",
                    "inconsistent_noise_levels",
                    "fluorescent_lighting",
                ],
                "recommended_for": [
                    "creative_work",
                    "social_meetings",
                    "brainstorming",
                ],
                "avoid_times": ["lunch_rush", "weekend_evenings"],
                "accessibility_notes": "Ground floor accessible but bathrooms upstairs",
                "fidget_tolerance": "very_high",
                "date_reviewed": datetime.utcnow().isoformat(),
                "extracted_at": datetime.utcnow().isoformat(),
            },
        ]

        reviews_data.extend(mock_reviews)
        return reviews_data

    def _generate_location_intelligence(self) -> list[dict[str, Any]]:
        """Generate location intelligence and recommendations."""
        intelligence_data = []

        # Generate daily location recommendations
        daily_intelligence = {
            "data_type": "location_intelligence",
            "analysis_type": "daily_adhd_location_report",
            "timestamp": datetime.utcnow().isoformat(),
            "city": "Valencia",
            "total_locations_analyzed": 127,
            "adhd_friendly_locations": 89,
            "highly_recommended": 23,
            "sensory_environment_analysis": {
                "low_stimulation_spaces": 45,
                "medium_stimulation_spaces": 58,
                "high_stimulation_spaces": 24,
                "overstimulation_risk_areas": 8,
            },
            "best_locations_by_need": {
                "hyperfocus_sessions": [
                    "Biblioteca Central",
                    "Jardín Botánico reading areas",
                ],
                "creative_work": [
                    "Café Central terrace",
                    "Modern art museum quiet zones",
                ],
                "social_productivity": ["Coworking spaces", "University libraries"],
                "sensory_breaks": ["Parks", "Quiet cafés", "Bookstores"],
            },
            "time_based_recommendations": {
                "early_morning": "Libraries and parks - minimal crowds, optimal lighting",
                "midday": "Avoid city center cafés - use quiet libraries or outdoor spaces",
                "afternoon": "Coworking spaces hit optimal energy levels",
                "evening": "Bookstores and quiet cafés for wind-down activities",
            },
            "weather_considerations": {
                "sunny": "Outdoor spaces and locations with natural light",
                "rainy": "Indoor cozy spaces with warm lighting",
                "cloudy": "Most locations suitable, avoid harsh artificial lighting",
            },
            "fidget_friendly_rankings": [
                {"location": "Parks", "score": 10},
                {"location": "Coworking spaces", "score": 9},
                {"location": "Cafés", "score": 8},
                {"location": "Libraries", "score": 7},
            ],
            "extracted_at": datetime.utcnow().isoformat(),
        }

        intelligence_data.append(daily_intelligence)
        return intelligence_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform location data with ADHD-friendly analysis."""
        self.logger.info(f"Transforming {len(data)} ADHD location records 🔧")
        transformed_data = []

        for record in data:
            try:
                if record.get("data_type") == "location":
                    # Add ADHD-friendly analysis
                    transformed_record = {
                        **record,
                        "adhd_friendliness_score": self._calculate_adhd_friendliness(record),
                        "sensory_assessment": self._assess_sensory_environment(record),
                        "focus_potential": self._assess_focus_potential(record),
                        "overstimulation_risk": self._assess_overstimulation_risk(record),
                        "recommended_activities": self._recommend_activities(record),
                        "optimal_visit_times": self._suggest_optimal_times(record),
                        "neurodivergent_accommodations": self._identify_accommodations(record),
                        "escape_route_rating": self._assess_escape_routes(record),
                    }
                elif record.get("data_type") == "neurodivergent_review":
                    # Add review analysis
                    transformed_record = {
                        **record,
                        "review_reliability": self._assess_review_reliability(record),
                        "sensitivity_indicators": self._extract_sensitivity_indicators(record),
                        "accommodation_suggestions": self._extract_accommodation_suggestions(record),
                    }
                else:
                    transformed_record = record

                transformed_data.append(transformed_record)
                self.metrics.records_transformed += 1

            except Exception as e:
                self.logger.error(f"Failed to transform ADHD location record: {e}")
                self.metrics.records_failed += 1

        return transformed_data

    def _calculate_adhd_friendliness(self, record: dict[str, Any]) -> float:
        """Calculate overall ADHD-friendliness score."""
        score = 5.0  # Base score

        location_type = record.get("type", "")
        type_config = self.location_types.get(location_type, {"base_score": 5})
        score = type_config.get("base_score", 5)

        # Noise level impact
        noise_level = record.get("noise_level", "moderate")
        noise_penalties = {
            "very_noisy": -3,
            "noisy": -2,
            "moderate": -0.5,
            "quiet": 1,
            "silent": 2,
        }
        score += noise_penalties.get(noise_level, 0)

        # Lighting impact
        lighting = record.get("lighting_type", "neutral_artificial")
        lighting_bonuses = {
            "natural_light": 2,
            "warm_artificial": 1,
            "harsh_fluorescent": -2,
        }
        score += lighting_bonuses.get(lighting, 0)

        # Amenities bonus
        amenities = record.get("amenities", [])
        beneficial_amenities = [
            "wifi",
            "quiet_zones",
            "natural_light",
            "comfortable_seating",
            "private_study_rooms",
        ]
        amenity_bonus = sum(0.5 for amenity in amenities if amenity in beneficial_amenities)
        score += amenity_bonus

        # Fidget friendliness
        fidget_score = record.get("fidget_friendly_score", 5)
        score += (fidget_score - 5) * 0.3

        return max(0.0, min(10.0, score))

    def _assess_sensory_environment(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess sensory environment characteristics."""
        return {
            "noise_analysis": {
                "level": record.get("noise_level", "unknown"),
                "predictability": ("high" if record.get("type") == "library" else "medium"),
                "controllability": "low",
            },
            "lighting_analysis": {
                "type": record.get("lighting_type", "unknown"),
                "quality": ("excellent" if "natural_light" in record.get("amenities", []) else "good"),
                "adjustability": "low",
            },
            "spatial_characteristics": {
                "crowding_level": record.get("crowd_density", "unknown"),
                "layout_complexity": ("simple" if record.get("type") in ["library", "park"] else "moderate"),
                "escape_route_accessibility": "high",
            },
            "overall_sensory_load": self._calculate_sensory_load(record),
        }

    def _calculate_sensory_load(self, record: dict[str, Any]) -> str:
        """Calculate overall sensory load."""
        noise_weights = {
            "silent": 0,
            "quiet": 1,
            "moderate": 2,
            "noisy": 3,
            "very_noisy": 4,
        }
        crowd_weights = {
            "empty": 0,
            "few_people": 1,
            "moderate_crowd": 2,
            "busy": 3,
            "packed": 4,
        }

        noise_load = noise_weights.get(record.get("noise_level", "moderate"), 2)
        crowd_load = crowd_weights.get(record.get("crowd_density", "moderate_crowd"), 2)

        total_load = noise_load + crowd_load

        if total_load <= 2:
            return "low"
        elif total_load <= 4:
            return "moderate"
        elif total_load <= 6:
            return "high"
        else:
            return "overwhelming"

    def _assess_focus_potential(self, record: dict[str, Any]) -> dict[str, str]:
        """Assess focus potential for different types of work."""
        location_type = record.get("type", "")
        sensory_load = self._calculate_sensory_load(record)

        focus_matrix = {
            "library": {
                "deep_work": "excellent",
                "creative_work": "good",
                "collaborative_work": "poor",
            },
            "coffee_shop": {
                "deep_work": "poor",
                "creative_work": "excellent",
                "collaborative_work": "good",
            },
            "coworking_space": {
                "deep_work": "good",
                "creative_work": "good",
                "collaborative_work": "excellent",
            },
            "park": {
                "deep_work": "good",
                "creative_work": "excellent",
                "collaborative_work": "poor",
            },
        }

        base_ratings = focus_matrix.get(
            location_type,
            {
                "deep_work": "fair",
                "creative_work": "fair",
                "collaborative_work": "fair",
            },
        )

        # Adjust based on sensory load
        if sensory_load in ["high", "overwhelming"]:
            for key in base_ratings:
                if base_ratings[key] in ["excellent", "good"]:
                    base_ratings[key] = "fair"

        return base_ratings

    def _assess_overstimulation_risk(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess overstimulation risk factors."""
        risk_factors = []

        if record.get("noise_level") in ["noisy", "very_noisy"]:
            risk_factors.append("high_noise_levels")

        if record.get("crowd_density") in ["busy", "packed"]:
            risk_factors.append("crowded_environment")

        if record.get("lighting_type") == "harsh_fluorescent":
            risk_factors.append("harsh_lighting")

        if "background_music" in record.get("amenities", []):
            risk_factors.append("unpredictable_audio")

        risk_level = "low"
        if len(risk_factors) >= 3:
            risk_level = "high"
        elif len(risk_factors) >= 2:
            risk_level = "moderate"

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "mitigation_strategies": self._suggest_mitigation_strategies(risk_factors),
            "warning_signs": [
                "difficulty_concentrating",
                "restlessness",
                "irritability",
                "need_to_leave",
            ],
        }

    def _suggest_mitigation_strategies(self, risk_factors: list[str]) -> list[str]:
        """Suggest strategies to mitigate overstimulation risks."""
        strategies = []

        strategy_map = {
            "high_noise_levels": [
                "noise_cancelling_headphones",
                "find_quieter_section",
                "visit_during_off_peak",
            ],
            "crowded_environment": [
                "visit_early_morning",
                "find_corner_spot",
                "use_private_rooms",
            ],
            "harsh_lighting": [
                "wear_tinted_glasses",
                "find_natural_light_areas",
                "use_task_lighting",
            ],
            "unpredictable_audio": [
                "use_white_noise_app",
                "bring_own_music",
                "request_quieter_area",
            ],
        }

        for factor in risk_factors:
            strategies.extend(strategy_map.get(factor, []))

        return list(set(strategies))  # Remove duplicates

    def _recommend_activities(self, record: dict[str, Any]) -> list[str]:
        """Recommend suitable activities for this location."""
        location_type = record.get("type", "")
        adhd_score = self._calculate_adhd_friendliness(record)

        activity_map = {
            "library": [
                "reading",
                "research",
                "writing",
                "studying",
                "quiet_reflection",
            ],
            "coffee_shop": [
                "creative_writing",
                "brainstorming",
                "casual_meetings",
                "people_watching",
            ],
            "coworking_space": [
                "focused_work",
                "video_calls",
                "networking",
                "collaborative_projects",
            ],
            "park": [
                "walking_meetings",
                "outdoor_reading",
                "mindfulness",
                "creative_thinking",
            ],
        }

        base_activities = activity_map.get(location_type, ["general_work"])

        # Add ADHD-specific activities based on score
        if adhd_score >= 8:
            base_activities.extend(["hyperfocus_sessions", "deep_work"])
        if adhd_score >= 7:
            base_activities.extend(["sustained_attention_tasks"])

        return base_activities

    def _suggest_optimal_times(self, record: dict[str, Any]) -> dict[str, str]:
        """Suggest optimal visit times for ADHD individuals."""
        location_type = record.get("type", "")

        time_suggestions = {
            "library": {
                "best_focus": "early_morning (9-11am)",
                "avoid": "lunch_hours (12-2pm), exam_periods",
                "alternative": "late_afternoon (4-6pm)",
            },
            "coffee_shop": {
                "best_focus": "mid_morning (10am-12pm)",
                "avoid": "lunch_rush (12-2pm), evening_social_hours",
                "alternative": "early_evening (5-7pm)",
            },
            "coworking_space": {
                "best_focus": "morning_hours (9am-12pm)",
                "avoid": "afternoon_meetings (2-4pm)",
                "alternative": "late_afternoon (4-6pm)",
            },
            "park": {
                "best_focus": "early_morning (8-10am), late_afternoon (5-7pm)",
                "avoid": "midday_heat, weekend_crowds",
                "alternative": "early_evening (6-8pm)",
            },
        }

        return time_suggestions.get(
            location_type,
            {
                "best_focus": "off_peak_hours",
                "avoid": "crowded_periods",
                "alternative": "flexible_timing",
            },
        )

    def _identify_accommodations(self, record: dict[str, Any]) -> list[str]:
        """Identify available neurodivergent accommodations."""
        accommodations = []

        amenities = record.get("amenities", [])
        location_type = record.get("type", "")

        # Standard accommodations
        if "quiet_zones" in amenities:
            accommodations.append("designated_quiet_areas")
        if "private_study_rooms" in record and record["has_private_study_rooms"]:
            accommodations.append("private_spaces_available")
        if "wifi" in amenities:
            accommodations.append("reliable_internet")
        if "comfortable_seating" in amenities:
            accommodations.append("ergonomic_seating_options")

        # Accessibility accommodations
        accessibility = record.get("accessibility", {})
        if accessibility.get("wheelchair_accessible"):
            accommodations.append("wheelchair_accessible")
        if accessibility.get("elevator"):
            accommodations.append("elevator_access")

        # Type-specific accommodations
        if location_type == "library":
            accommodations.extend(["study_carrels", "book_browsing", "research_assistance"])
        elif location_type == "coffee_shop":
            accommodations.extend(
                [
                    "stimulant_beverages",
                    "flexible_seating",
                    "social_interaction_optional",
                ]
            )
        elif location_type == "park":
            accommodations.extend(["nature_access", "movement_friendly", "sensory_regulation"])

        return accommodations

    def _assess_escape_routes(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess ease of leaving when overwhelmed."""
        location_type = record.get("type", "")

        # Base escape route assessment
        escape_assessment = {
            "library": {
                "ease": "moderate",
                "social_pressure": "low",
                "logistics": "simple",
            },
            "coffee_shop": {
                "ease": "easy",
                "social_pressure": "moderate",
                "logistics": "simple",
            },
            "coworking_space": {
                "ease": "moderate",
                "social_pressure": "high",
                "logistics": "moderate",
            },
            "park": {
                "ease": "very_easy",
                "social_pressure": "very_low",
                "logistics": "very_simple",
            },
        }

        base_rating = escape_assessment.get(
            location_type,
            {
                "ease": "moderate",
                "social_pressure": "moderate",
                "logistics": "moderate",
            },
        )

        return {
            **base_rating,
            "exit_strategies": self._suggest_exit_strategies(location_type),
            "recovery_options": [
                "nearby_quiet_spaces",
                "outdoor_areas",
                "private_restrooms",
            ],
        }

    def _suggest_exit_strategies(self, location_type: str) -> list[str]:
        """Suggest discrete exit strategies."""
        strategies = {
            "library": ["bathroom_break", "book_return", "quiet_exit"],
            "coffee_shop": ["bathroom_break", "phone_call_excuse", "casual_departure"],
            "coworking_space": ["bathroom_break", "coffee_run", "meeting_excuse"],
            "park": ["natural_end_of_walk", "weather_excuse", "immediate_departure"],
        }

        return strategies.get(location_type, ["polite_excuse", "bathroom_break", "quiet_exit"])

    def _assess_review_reliability(self, record: dict[str, Any]) -> float:
        """Assess reliability of neurodivergent review."""
        score = 5.0

        # Detailed review increases reliability
        review_text = record.get("review_text", "")
        if len(review_text) > 100:
            score += 2.0
        elif len(review_text) > 50:
            score += 1.0

        # Specific sensory details increase reliability
        if any(term in review_text.lower() for term in ["noise", "light", "crowd", "sensory"]):
            score += 1.5

        # Recent review is more reliable
        # (In real implementation, would check date_reviewed)
        score += 1.0

        return min(10.0, score)

    def _extract_sensitivity_indicators(self, record: dict[str, Any]) -> list[str]:
        """Extract sensitivity indicators from review."""
        indicators = []
        review_text = record.get("review_text", "").lower()

        sensitivity_keywords = {
            "noise_sensitive": ["noise", "loud", "quiet", "sound"],
            "light_sensitive": ["light", "bright", "fluorescent", "harsh"],
            "crowd_sensitive": ["crowd", "busy", "people", "overwhelming"],
            "texture_sensitive": ["texture", "fabric", "surface", "material"],
        }

        for sensitivity, keywords in sensitivity_keywords.items():
            if any(keyword in review_text for keyword in keywords):
                indicators.append(sensitivity)

        return indicators

    def _extract_accommodation_suggestions(self, record: dict[str, Any]) -> list[str]:
        """Extract accommodation suggestions from review."""
        suggestions = []
        review_text = record.get("review_text", "").lower()
        pros = record.get("pros", [])

        # Extract from pros
        for pro in pros:
            if pro in ["headphones_allowed", "fidget_friendly", "flexible_seating"]:
                suggestions.append(pro)

        # Extract from review text
        if "headphone" in review_text:
            suggestions.append("headphones_recommended")
        if "corner" in review_text:
            suggestions.append("corner_seating_preferred")
        if "quiet" in review_text:
            suggestions.append("seek_quiet_areas")

        return suggestions

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load ADHD-friendly location data to storage."""
        self.logger.info(f"Loading {len(data)} ADHD-friendly location records 💾")

        # Save complete data
        output_file = self.output_dir / f"adhd_friendly_locations_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            # Save current recommendations
            latest_file = self.output_dir / "latest_adhd_locations.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            # Create specialized datasets
            self._create_specialized_datasets(data)

            self.logger.info(f"ADHD-friendly location data saved to {output_file}")
            self.metrics.records_loaded = len(data)

            # Log useful statistics
            locations = [d for d in data if d.get("data_type") == "location"]
            reviews = [d for d in data if d.get("data_type") == "neurodivergent_review"]
            highly_recommended = [l for l in locations if l.get("adhd_friendliness_score", 0) >= 8]
            low_overstimulation = [l for l in locations if l.get("overstimulation_risk", {}).get("risk_level") == "low"]

            self.logger.info(
                f"Summary: {len(locations)} locations analyzed, {len(reviews)} community reviews, {len(highly_recommended)} highly ADHD-friendly, {len(low_overstimulation)} low overstimulation risk 🧠✨"
            )

        except Exception as e:
            self.logger.error(f"Failed to save ADHD location data: {e}")
            raise

    def _create_specialized_datasets(self, data: list[dict[str, Any]]) -> None:
        """Create specialized datasets for different needs."""
        locations = [d for d in data if d.get("data_type") == "location"]

        # High ADHD-friendliness locations
        highly_adhd_friendly = [l for l in locations if l.get("adhd_friendliness_score", 0) >= 8]

        # Low sensory load locations
        low_sensory_load = [l for l in locations if l.get("sensory_assessment", {}).get("overall_sensory_load") == "low"]

        # Hyperfocus-friendly locations
        hyperfocus_friendly = [l for l in locations if "hyperfocus_sessions" in l.get("recommended_activities", [])]

        # Emergency escape-friendly locations
        easy_escape = [l for l in locations if l.get("escape_route_rating", {}).get("ease") in ["easy", "very_easy"]]

        # Save specialized datasets
        datasets = {
            "highly_adhd_friendly.json": highly_adhd_friendly,
            "low_sensory_load.json": low_sensory_load,
            "hyperfocus_friendly.json": hyperfocus_friendly,
            "easy_escape_locations.json": easy_escape,
        }

        for filename, dataset in datasets.items():
            if dataset:
                with open(self.output_dir / filename, "w", encoding="utf-8") as f:
                    json.dump(dataset, f, indent=2, default=str)


def run_adhd_friendly_locations_etl():
    """Run the ADHD-Friendly Locations ETL process."""
    etl = ADHDFriendlyLocationsETL()
    metrics = etl.run()
    return metrics


if __name__ == "__main__":
    run_adhd_friendly_locations_etl()
