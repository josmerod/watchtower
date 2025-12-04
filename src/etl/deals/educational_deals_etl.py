"""Educational Content & Courses Deals ETL Module

This module aggregates educational deals, free courses, certifications,
and learning content from Udemy, Coursera, edX, and other platforms.

Usage:
    python src/etl/deals/educational_deals_etl.py

Output:
    - JSON file: data/deals/educational_deals.json
    - CSV file: data/deals/educational_deals.csv
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
logger = get_logger("EducationalDealsETL")


class EducationalDealsETL(BaseETL):
    """ETL for educational content and course deals."""

    def __init__(self):
        super().__init__("educational_deals")
        self.sources = {
            "udemy_free": {
                "name": "Udemy",
                "free_courses_url": "https://www.udemy.com/courses/free/",
                "api_url": "https://www.udemy.com/api-2.0/",
                "category": "courses",
            },
            "coursera_free": {
                "name": "Coursera",
                "free_courses_url": "https://www.coursera.org/courses?query=free",
                "category": "courses",
            },
            "edx_free": {
                "name": "edX",
                "free_courses_url": "https://www.edx.org/search?q=&free=true",
                "category": "courses",
            },
            "khan_academy": {
                "name": "Khan Academy",
                "url": "https://www.khanacademy.org/",
                "category": "education",
            },
            "mit_opencourseware": {
                "name": "MIT OpenCourseWare",
                "url": "https://ocw.mit.edu/",
                "category": "education",
            },
        }

    def extract(self) -> dict[str, Any]:
        """Extract educational deals from multiple sources."""
        logger.info("Starting educational deals extraction...")

        all_deals = []

        # Add curated educational deals and free sources
        curated_deals = self._get_curated_educational_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} educational deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_educational_deals(self) -> list[dict[str, Any]]:
        """Get manually curated list of educational deals and free sources."""
        curated = [
            {
                "title": "Udemy Free Courses Collection",
                "description": "Thousands of free courses on technology, business, personal development, and more",
                "url": "https://www.udemy.com/courses/free/",
                "platform": "Udemy",
                "category": "courses",
                "deal_type": "free_courses",
                "original_price": 200,  # Average course price
                "current_price": 0,
                "savings": 200,
                "discount_percentage": 100,
                "course_type": "video_lectures",
                "subject_area": "technology",
                "difficulty_level": "all_levels",
                "certification": True,
                "language": "multiple",
                "duration_hours": 0,  # Varies
                "instructor_rating": 4.5,
                "tags": ["technology", "business", "free", "certification"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Coursera Free Courses",
                "description": "Audit courses from top universities including Stanford, Yale, and Princeton for free",
                "url": "https://www.coursera.org/courses?query=free",
                "platform": "Coursera",
                "category": "courses",
                "deal_type": "free_audit",
                "original_price": 79,  # Monthly subscription
                "current_price": 0,
                "savings": 79,
                "discount_percentage": 100,
                "course_type": "university_courses",
                "subject_area": "academic",
                "difficulty_level": "intermediate",
                "certification": False,  # Free audit only
                "language": "english",
                "duration_hours": 40,
                "instructor_rating": 4.7,
                "tags": ["university", "academic", "free audit", "stanford"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "edX Free Course Access",
                "description": "Free access to Harvard, MIT courses with option to purchase certificates",
                "url": "https://www.edx.org/search?q=&free=true",
                "platform": "edX",
                "category": "courses",
                "deal_type": "free_access",
                "original_price": 99,  # Certificate cost
                "current_price": 0,
                "savings": 99,
                "discount_percentage": 100,
                "course_type": "university_courses",
                "subject_area": "computer_science",
                "difficulty_level": "advanced",
                "certification": "optional_paid",
                "language": "english",
                "duration_hours": 60,
                "instructor_rating": 4.8,
                "tags": ["harvard", "mit", "computer science", "free access"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Khan Academy Complete Library",
                "description": "Completely free K-12 education, college prep, and life skills courses",
                "url": "https://www.khanacademy.org/",
                "platform": "Khan Academy",
                "category": "education",
                "deal_type": "free_education",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "course_type": "interactive_lessons",
                "subject_area": "k12_education",
                "difficulty_level": "beginner",
                "certification": False,
                "language": "multiple",
                "duration_hours": 0,  # Self-paced
                "instructor_rating": 4.9,
                "tags": ["k-12", "math", "science", "completely free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "MIT OpenCourseWare",
                "description": "Free access to MIT course materials from over 2,400 courses",
                "url": "https://ocw.mit.edu/",
                "platform": "MIT OpenCourseWare",
                "category": "education",
                "deal_type": "free_materials",
                "original_price": 53000,  # MIT tuition equivalent
                "current_price": 0,
                "savings": 53000,
                "discount_percentage": 100,
                "course_type": "course_materials",
                "subject_area": "engineering",
                "difficulty_level": "advanced",
                "certification": False,
                "language": "english",
                "duration_hours": 150,  # Full semester equivalent
                "instructor_rating": 5.0,
                "tags": ["mit", "engineering", "course materials", "research"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "freeCodeCamp Full Stack",
                "description": "Free coding bootcamp with 3,000+ hours of programming courses",
                "url": "https://www.freecodecamp.org/",
                "platform": "freeCodeCamp",
                "category": "programming",
                "deal_type": "free_bootcamp",
                "original_price": 15000,  # Bootcamp equivalent
                "current_price": 0,
                "savings": 15000,
                "discount_percentage": 100,
                "course_type": "coding_bootcamp",
                "subject_area": "programming",
                "difficulty_level": "beginner_to_advanced",
                "certification": True,
                "language": "english",
                "duration_hours": 3000,
                "instructor_rating": 4.8,
                "tags": ["coding", "web development", "free certification", "bootcamp"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "YouTube EDU Channels",
                "description": "Educational YouTube channels with university-level content",
                "url": "https://www.youtube.com/education",
                "platform": "YouTube Education",
                "category": "education",
                "deal_type": "free_videos",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "course_type": "video_lectures",
                "subject_area": "various",
                "difficulty_level": "all_levels",
                "certification": False,
                "language": "multiple",
                "duration_hours": 0,  # Unlimited
                "instructor_rating": 4.3,
                "tags": ["youtube", "video lectures", "various subjects", "free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Codecademy Free Tier",
                "description": "Interactive coding lessons with free basic access to programming courses",
                "url": "https://www.codecademy.com/catalog/subject/all",
                "platform": "Codecademy",
                "category": "programming",
                "deal_type": "freemium",
                "original_price": 240,  # Annual pro
                "current_price": 0,
                "savings": 240,
                "discount_percentage": 100,
                "course_type": "interactive_coding",
                "subject_area": "programming",
                "difficulty_level": "beginner",
                "certification": False,  # Pro feature
                "language": "english",
                "duration_hours": 50,
                "instructor_rating": 4.4,
                "tags": ["interactive", "coding", "python", "javascript"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Harvard CS50 Online",
                "description": "Harvard's legendary computer science course available free online",
                "url": "https://cs50.harvard.edu/x/",
                "platform": "Harvard Extension",
                "category": "computer_science",
                "deal_type": "free_course",
                "original_price": 3000,  # Harvard extension equivalent
                "current_price": 0,
                "savings": 3000,
                "discount_percentage": 100,
                "course_type": "university_course",
                "subject_area": "computer_science",
                "difficulty_level": "intermediate",
                "certification": "optional_paid",
                "language": "english",
                "duration_hours": 120,
                "instructor_rating": 4.9,
                "tags": ["harvard", "computer science", "cs50", "programming"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Skillshare Free Trial + Free Classes",
                "description": "Free classes plus 1-month trial access to premium creative courses",
                "url": "https://www.skillshare.com/browse/free",
                "platform": "Skillshare",
                "category": "creative",
                "deal_type": "free_trial",
                "original_price": 168,  # Annual premium
                "current_price": 0,
                "savings": 168,
                "discount_percentage": 100,
                "course_type": "creative_workshops",
                "subject_area": "design",
                "difficulty_level": "intermediate",
                "certification": False,
                "language": "english",
                "duration_hours": 20,
                "instructor_rating": 4.6,
                "tags": ["creative", "design", "art", "free trial"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Google Digital Garage",
                "description": "Free courses on digital marketing, data analytics, and career development",
                "url": "https://learndigital.withgoogle.com/digitalgarage",
                "platform": "Google Digital Garage",
                "category": "digital_marketing",
                "deal_type": "free_certification",
                "original_price": 500,  # Professional course equivalent
                "current_price": 0,
                "savings": 500,
                "discount_percentage": 100,
                "course_type": "professional_development",
                "subject_area": "digital_marketing",
                "difficulty_level": "beginner",
                "certification": True,
                "language": "multiple",
                "duration_hours": 40,
                "instructor_rating": 4.5,
                "tags": ["google", "digital marketing", "free certification", "career"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "LinkedIn Learning Free Month",
                "description": "Free month access to professional development and business courses",
                "url": "https://www.linkedin.com/learning/",
                "platform": "LinkedIn Learning",
                "category": "professional_development",
                "deal_type": "free_trial",
                "original_price": 29.99,  # Monthly cost
                "current_price": 0,
                "savings": 29.99,
                "discount_percentage": 100,
                "course_type": "professional_courses",
                "subject_area": "business",
                "difficulty_level": "intermediate",
                "certification": True,
                "language": "multiple",
                "duration_hours": 0,  # Unlimited during trial
                "instructor_rating": 4.4,
                "tags": ["linkedin", "professional", "business", "free month"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated educational deals")
        return curated

    def transform(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform educational deals data."""
        logger.info("Starting educational deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate educational value score
                educational_score = self._calculate_educational_value_score(deal)

                # Determine quality tier
                quality_tier = self._determine_educational_quality_tier(deal)

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
                    "educational_score": educational_score,
                    "quality_tier": quality_tier,
                    "course_type": deal.get("course_type", "unknown"),
                    "subject_area": deal.get("subject_area", "general"),
                    "difficulty_level": deal.get("difficulty_level", "unknown"),
                    "certification": deal.get("certification", False),
                    "language": deal.get("language", "english"),
                    "duration_hours": deal.get("duration_hours", 0),
                    "instructor_rating": deal.get("instructor_rating", 0),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming educational deal: {e}")
                continue

        # Sort by educational score and savings
        transformed_deals.sort(key=lambda x: (x["educational_score"], x["savings"]), reverse=True)

        logger.info(f"Transformed {len(transformed_deals)} educational deals")
        return transformed_deals

    def _calculate_educational_value_score(self, deal: dict[str, Any]) -> float:
        """Calculate educational value score for ranking deals."""
        score = 0.0

        # Platform quality weight
        platform = deal.get("platform", "").lower()
        if any(name in platform for name in ["mit", "harvard", "stanford"]):
            score += 5.0  # Top universities
        elif any(name in platform for name in ["coursera", "edx"]):
            score += 4.5  # University platforms
        elif any(name in platform for name in ["khan academy", "freecodecamp"]):
            score += 4.0  # High-quality free platforms
        elif any(name in platform for name in ["udemy", "linkedin"]):
            score += 3.5  # Professional platforms
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type in ["free_education", "free_materials", "free_bootcamp"]:
            score += 5.0
        elif deal_type in ["free_courses", "free_certification"]:
            score += 4.5
        elif deal_type in ["free_access", "free_audit"]:
            score += 4.0
        elif deal_type in ["free_trial", "freemium"]:
            score += 3.0

        # Certification bonus
        certification = deal.get("certification")
        if certification is True:
            score += 2.0
        elif certification == "optional_paid":
            score += 1.0

        # Instructor rating bonus
        instructor_rating = deal.get("instructor_rating", 0)
        if instructor_rating >= 4.8:
            score += 2.0
        elif instructor_rating >= 4.5:
            score += 1.5
        elif instructor_rating >= 4.0:
            score += 1.0

        # Duration value (more content = higher score)
        duration = deal.get("duration_hours", 0)
        if duration > 100:
            score += 2.0
        elif duration > 50:
            score += 1.5
        elif duration > 20:
            score += 1.0

        # Subject area bonus for high-demand skills
        subject = deal.get("subject_area", "").lower()
        if any(keyword in subject for keyword in ["programming", "computer_science", "data"]):
            score += 1.5
        elif any(keyword in subject for keyword in ["business", "digital_marketing"]):
            score += 1.0

        # Savings consideration
        savings = deal.get("savings", 0)
        if savings > 1000:
            score += 3.0
        elif savings > 500:
            score += 2.0
        elif savings > 100:
            score += 1.0

        return round(score, 2)

    def _determine_educational_quality_tier(self, deal: dict[str, Any]) -> str:
        """Determine quality tier of the educational content."""
        platform = deal.get("platform", "").lower()
        instructor_rating = deal.get("instructor_rating", 0)
        certification = deal.get("certification", False)

        # Elite tier indicators
        if any(name in platform for name in ["mit", "harvard", "stanford"]):
            return "elite"

        # Premium tier indicators
        if instructor_rating >= 4.7 and certification or (any(name in platform for name in ["coursera", "edx"]) and instructor_rating >= 4.5):
            return "premium"

        # High tier indicators
        if instructor_rating >= 4.5 or certification or any(name in platform for name in ["khan academy", "freecodecamp"]):
            return "high"

        # Standard tier
        if instructor_rating >= 4.0:
            return "standard"

        return "basic"

    def load(self, transformed_data: list[dict[str, Any]]) -> bool:
        """Load transformed educational deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "educational_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "educational_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(f"Successfully saved {len(transformed_data)} educational deals to {output_dir}")
            return True

        except Exception as e:
            logger.error(f"Error saving educational deals data: {e}")
            return False


def main():
    """Main function to run the Educational Deals ETL."""
    etl = EducationalDealsETL()
    success = etl.run()

    if success:
        logger.info("Educational Deals ETL completed successfully")
    else:
        logger.error("Educational Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
