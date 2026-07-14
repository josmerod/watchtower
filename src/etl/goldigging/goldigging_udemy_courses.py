"""ETL script to aggregate Udemy business courses from a Google Sheet source."""

import csv
import json
import logging
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Any

import pandas as pd
import requests

from src.utils.course_deduplication import deduplicate_courses
from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("udemy_etl")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Constants
BASE_OUTPUT_DIR = "data/udemy"
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1AZ3pw48rDAHZM3C_5S-GkKS7t8dkX9PiGLy39VAYe2U/export?format=csv&gid=1969752702"
CAPGEMINI_UDEMY_BASE_URL = "https://capgemini.udemy.com/"

# Column Mapping
COL_ID = "Course ID"
COL_DATE = "Date Added"
COL_LANG = "Collection Language"
COL_TITLE = "Course Title"
COL_CAT = "Category"
COL_SUBCAT = "Subcategory"


class UdemyCoursesETL:
    """ETL for extracting and aggregating Udemy courses from Google Sheet."""

    def __init__(self) -> None:
        """Initialize output directories."""
        project_root = get_project_root()
        self.output_dir = os.path.join(project_root, BASE_OUTPUT_DIR)
        ensure_directories([BASE_OUTPUT_DIR])

        self.courses_file = os.path.join(self.output_dir, "udemy_courses.json")
        self.csv_file = os.path.join(self.output_dir, "udemy_courses.csv")

    def extract_courses(self) -> list[dict[str, Any]]:
        """Extract courses from Google Sheet CSV.

        Returns:
            List of course dictionaries.
        """
        logger.info(f"Fetching data from Google Sheet: {GOOGLE_SHEET_CSV_URL}")
        try:
            response = requests.get(GOOGLE_SHEET_CSV_URL, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Google Sheet: {e}")
            return []

        courses: list[dict[str, Any]] = []

        # Use csv.DictReader for reliable parsing
        f = StringIO(response.text)
        reader = csv.DictReader(f)

        rows = list(reader)
        logger.info(f"Fetched {len(rows)} raw rows from sheet")

        for row in rows:
            # 1. content filtering (en or es only)
            lang = row.get(COL_LANG, "").strip().lower()
            if lang not in ["en", "es"]:
                continue

            course_id = row.get(COL_ID, "").strip()
            if not course_id:
                continue

            # 2. Extract fields
            date_added_str = row.get(COL_DATE, "").strip()
            title = row.get(COL_TITLE, "").strip()
            category = row.get(COL_CAT, "").strip()
            subcategory = row.get(COL_SUBCAT, "").strip()

            # 3. URL Generation
            # Some IDs might be pure numbers, others might be strings.
            # Assuming simple append works as per requirement.
            url = f"{CAPGEMINI_UDEMY_BASE_URL}{course_id}"

            # 4. Standardize Date
            # Format in CSV seems to be YYYY-MM-DD based on "2025-01-02" example
            scraped_at = ""
            if date_added_str:
                try:
                    dt = datetime.strptime(date_added_str, "%Y-%m-%d")
                    # Set to UTC
                    dt = dt.replace(tzinfo=timezone.utc)
                    scraped_at = dt.isoformat()
                except ValueError:
                    # Try fallback or leave as empty string
                    # Requirement says "sort by added day desc", so preserving the date is important.
                    logger.debug(f"Could not parse date: {date_added_str}")
                    scraped_at = ""

            # If no date, maybe skip or put at end?
            # Let's keep it but it might affect sorting if None.
            # We'll handle sorting in valid list.

            course = {
                "title": title,
                "url": url,
                "scraped_at": scraped_at,
                "language": lang,
                "category": category,
                "subcategory": subcategory,
                "provider": "Udemy",  # Adding static provider for context
            }
            courses.append(course)

        # 5. Sort by added day desc (newer courses first)
        # Helper to handle None/Empty dates (put them last)
        def sort_key(c):
            return c.get("scraped_at") or ""

        courses.sort(key=sort_key, reverse=True)

        logger.info(f"Processed {len(courses)} valid courses (en/es)")
        return courses

    def save_courses(self, courses: list[dict[str, Any]]) -> None:
        """Save extracted courses to JSON and CSV files.

        Args:
            courses: List of course dictionaries to save.
        """
        if not courses:
            logger.warning("No courses to save for Udemy")
            return

        # Deduplicate courses before saving (though sheet might be unique via ID, good practice)
        # Key field is URL since we generated unique URLs from IDs
        deduplicated_courses, removed_count = deduplicate_courses(courses, key_field="url", prefer_newer=True)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate courses")

        # Save to JSON
        try:
            with open(self.courses_file, "w", encoding="utf-8") as f:
                json.dump(deduplicated_courses, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(deduplicated_courses)} unique courses to JSON: {self.courses_file}")
        except Exception as e:
            logger.error(f"Error saving JSON file {self.courses_file}: {e}")

        # Save to CSV
        try:
            df = pd.DataFrame(deduplicated_courses)
            df.to_csv(self.csv_file, index=False)
            logger.info(f"Saved courses to CSV: {self.csv_file}")
        except Exception as e:
            logger.warning(f"Could not save courses to CSV: {e}")


def main() -> None:
    """Main entry point for Udemy courses ETL."""
    logger.info("Starting Udemy courses ETL")
    etl = UdemyCoursesETL()
    courses = etl.extract_courses()
    etl.save_courses(courses)
    logger.info("Udemy courses ETL completed")


if __name__ == "__main__":
    main()
