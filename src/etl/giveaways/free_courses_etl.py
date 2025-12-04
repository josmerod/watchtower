"""Free Courses ETL Module

This module tracks free courses and educational content from Udemy, Coursera, edX, and other platforms.

Usage:
    python src/etl/giveaways/free_courses_etl.py

Output:
    - JSON file: data/giveaways/free_courses.json
    - CSV file: data/giveaways/free_courses.csv
"""

import json
import os
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
logger = get_logger("FreeCoursesETL")


class FreeCoursesETL(BaseETL):
    """ETL for free courses from multiple educational platforms."""

    def __init__(self):
        super().__init__("free_courses")
        self.sources = {
            "freecodecamp": {
                "name": "FreeCodeCamp",
                "rss_url": "https://www.freecodecamp.org/news/rss/",
                "category": "programming",
                "base_url": "https://www.freecodecamp.org",
            },
            "coursera_free": {
                "name": "Coursera Free Courses",
                "search_urls": [
                    "https://www.coursera.org/courses?query=free",
                    "https://www.coursera.org/browse/computer-science",
                ],
                "category": "general",
            },
            "edx_free": {
                "name": "edX Free Courses",
                "api_url": "https://courses.edx.org/api/courses/v1/courses/",
                "category": "academic",
            },
            "khan_academy": {
                "name": "Khan Academy",
                "api_url": "https://www.khanacademy.org/api/internal/scratchpads/top",
                "category": "academic",
            },
        }

    def extract(self) -> dict[str, Any]:
        """Extract free courses from multiple sources."""
        logger.info("Starting free courses extraction...")

        all_courses = []

        # Extract from FreeCodeCamp RSS
        freecodecamp_courses = self._extract_freecodecamp()
        all_courses.extend(freecodecamp_courses)

        # Add some manually curated free course resources
        curated_courses = self._get_curated_free_courses()
        all_courses.extend(curated_courses)

        logger.info(f"Total extracted {len(all_courses)} free courses")
        return {"courses": all_courses, "total_count": len(all_courses)}

    def _extract_freecodecamp(self) -> list[dict[str, Any]]:
        """Extract recent courses from FreeCodeCamp RSS."""
        try:
            logger.info("Extracting courses from FreeCodeCamp RSS...")

            url = self.sources["freecodecamp"]["rss_url"]
            headers = {"User-Agent": "Watchtower/1.0 (Educational Research Bot)"}

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")

            courses = []
            for item in items[:20]:  # Get latest 20 posts
                try:
                    title = item.find("title").text if item.find("title") else "Unknown"
                    link = item.find("link").text if item.find("link") else ""
                    description = item.find("description").text if item.find("description") else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") else ""

                    # Only include items that look like courses/tutorials
                    title_lower = title.lower()
                    if any(
                        keyword in title_lower
                        for keyword in [
                            "course",
                            "tutorial",
                            "learn",
                            "guide",
                            "handbook",
                            "complete",
                            "bootcamp",
                            "masterclass",
                            "training",
                        ]
                    ):
                        # Parse publication date
                        created_date = datetime.now(timezone.utc).isoformat()
                        try:
                            from email.utils import parsedate_to_datetime

                            created_date = parsedate_to_datetime(pub_date).isoformat()
                        except:
                            pass

                        courses.append(
                            {
                                "title": title,
                                "description": BeautifulSoup(description, "html.parser").get_text()[:500],
                                "url": link,
                                "platform": "FreeCodeCamp",
                                "category": "programming",
                                "course_type": "tutorial",
                                "original_price": 0,
                                "current_price": 0,
                                "duration": "Variable",
                                "level": "All Levels",
                                "language": "English",
                                "tags": self._extract_course_tags(title, description),
                                "created_date": created_date,
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                                "source": "FreeCodeCamp RSS",
                            }
                        )

                except Exception as e:
                    logger.warning(f"Error processing FreeCodeCamp item: {e}")
                    continue

            logger.info(f"Extracted {len(courses)} courses from FreeCodeCamp")
            return courses

        except Exception as e:
            logger.error(f"Error extracting from FreeCodeCamp: {e}")
            return []

    def _get_curated_free_courses(self) -> list[dict[str, Any]]:
        """Get manually curated list of high-quality free courses."""
        curated = [
            {
                "title": "CS50x: Introduction to Computer Science",
                "description": "Harvard University's introduction to computer science and programming",
                "url": "https://cs50.harvard.edu/x/",
                "platform": "Harvard/edX",
                "category": "computer_science",
                "course_type": "university_course",
                "original_price": 0,
                "current_price": 0,
                "duration": "12 weeks",
                "level": "Beginner",
                "language": "English",
                "tags": ["computer science", "programming", "harvard", "algorithms"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "MIT 6.001x: Introduction to Computer Science and Programming",
                "description": "MIT's foundational computer science course using Python",
                "url": "https://www.edx.org/course/introduction-to-computer-science-and-programming-7",
                "platform": "MIT/edX",
                "category": "computer_science",
                "course_type": "university_course",
                "original_price": 0,
                "current_price": 0,
                "duration": "9 weeks",
                "level": "Beginner",
                "language": "English",
                "tags": ["python", "programming", "mit", "computer science"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "The Odin Project - Full Stack Web Development",
                "description": "Complete web development curriculum covering HTML, CSS, JavaScript, and more",
                "url": "https://www.theodinproject.com/",
                "platform": "The Odin Project",
                "category": "web_development",
                "course_type": "curriculum",
                "original_price": 0,
                "current_price": 0,
                "duration": "Self-paced",
                "level": "Beginner to Advanced",
                "language": "English",
                "tags": ["web development", "javascript", "react", "node.js"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Khan Academy - Computer Programming",
                "description": "Interactive programming courses covering JavaScript, HTML/CSS, and SQL",
                "url": "https://www.khanacademy.org/computing/computer-programming",
                "platform": "Khan Academy",
                "category": "programming",
                "course_type": "interactive",
                "original_price": 0,
                "current_price": 0,
                "duration": "Self-paced",
                "level": "Beginner",
                "language": "English",
                "tags": ["javascript", "html", "css", "sql", "interactive"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Coursera - Machine Learning by Stanford",
                "description": "Andrew Ng's famous machine learning course (audit for free)",
                "url": "https://www.coursera.org/learn/machine-learning",
                "platform": "Coursera/Stanford",
                "category": "machine_learning",
                "course_type": "university_course",
                "original_price": 79,
                "current_price": 0,
                "duration": "11 weeks",
                "level": "Intermediate",
                "language": "English",
                "tags": ["machine learning", "stanford", "andrew ng", "algorithms"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated free courses")
        return curated

    def _extract_course_tags(self, title: str, description: str) -> list[str]:
        """Extract relevant tags from course title and description."""
        text = f"{title} {description}".lower()

        technology_keywords = [
            "python",
            "javascript",
            "java",
            "react",
            "node.js",
            "angular",
            "vue",
            "html",
            "css",
            "sql",
            "mongodb",
            "docker",
            "kubernetes",
            "aws",
            "machine learning",
            "data science",
            "ai",
            "blockchain",
            "cybersecurity",
            "web development",
            "mobile",
            "android",
            "ios",
            "flutter",
            "swift",
        ]

        tags = []
        for keyword in technology_keywords:
            if keyword in text:
                tags.append(keyword)

        return tags[:5]  # Limit to 5 tags

    def transform(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform free courses data."""
        logger.info("Starting free courses transformation...")

        courses = raw_data.get("courses", [])
        transformed_courses = []

        for course in courses:
            try:
                # Clean up title
                title = course["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate relevance score
                relevance_score = self._calculate_course_relevance_score(course)

                # Determine course value
                value_rating = self._determine_course_value(course)

                transformed_course = {
                    "title": title,
                    "description": course.get("description", "")[:400],  # Limit description
                    "url": course["url"],
                    "platform": course["platform"],
                    "category": course["category"],
                    "course_type": course.get("course_type", "course"),
                    "original_price": course.get("original_price", 0),
                    "current_price": course.get("current_price", 0),
                    "savings": course.get("original_price", 0) - course.get("current_price", 0),
                    "duration": course.get("duration", "Not specified"),
                    "level": course.get("level", "All Levels"),
                    "language": course.get("language", "English"),
                    "value_rating": value_rating,
                    "relevance_score": relevance_score,
                    "tags": course.get("tags", []),
                    "created_date": course.get("created_date"),
                    "fetched_at": course["fetched_at"],
                    "source": course["source"],
                }

                transformed_courses.append(transformed_course)

            except Exception as e:
                logger.warning(f"Error transforming course: {e}")
                continue

        # Sort by relevance score and value rating
        transformed_courses.sort(key=lambda x: (x["relevance_score"], x["value_rating"]), reverse=True)

        logger.info(f"Transformed {len(transformed_courses)} free courses")
        return transformed_courses

    def _calculate_course_relevance_score(self, course: dict[str, Any]) -> float:
        """Calculate relevance score for ranking courses."""
        score = 0.0

        # Platform reputation weight
        platform = course.get("platform", "").lower()
        if any(name in platform for name in ["harvard", "mit", "stanford"]):
            score += 5.0
        elif any(name in platform for name in ["coursera", "edx"]):
            score += 4.0
        elif any(name in platform for name in ["freecodecamp", "khan academy"]):
            score += 3.5
        else:
            score += 2.0

        # Course type weight
        course_type = course.get("course_type", "")
        if course_type == "university_course":
            score += 3.0
        elif course_type == "curriculum":
            score += 2.5
        elif course_type in ["tutorial", "interactive"]:
            score += 2.0

        # Value consideration (free courses with original price)
        original_price = course.get("original_price", 0)
        current_price = course.get("current_price", 0)
        if original_price > current_price:
            score += min((original_price - current_price) / 20, 3.0)

        # Technology relevance
        tags = course.get("tags", [])
        high_demand_skills = [
            "python",
            "javascript",
            "react",
            "machine learning",
            "aws",
            "data science",
        ]
        for tag in tags:
            if tag in high_demand_skills:
                score += 0.5

        return round(score, 2)

    def _determine_course_value(self, course: dict[str, Any]) -> str:
        """Determine course value rating."""
        original_price = course.get("original_price", 0)
        platform = course.get("platform", "").lower()
        course_type = course.get("course_type", "")

        if any(name in platform for name in ["harvard", "mit", "stanford"]):
            return "premium"
        elif original_price > 100 or course_type == "university_course":
            return "high_value"
        elif original_price > 50 or "coursera" in platform or "edx" in platform:
            return "good_value"
        else:
            return "standard"

    def load(self, transformed_data: list[dict[str, Any]]) -> bool:
        """Load transformed free courses data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "giveaways")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "free_courses.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "free_courses.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(f"Successfully saved {len(transformed_data)} free courses to {output_dir}")
            return True

        except Exception as e:
            logger.error(f"Error saving free courses data: {e}")
            return False


def main():
    """Main function to run the Free Courses ETL."""
    etl = FreeCoursesETL()
    success = etl.run()

    if success:
        logger.info("Free Courses ETL completed successfully")
    else:
        logger.error("Free Courses ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
