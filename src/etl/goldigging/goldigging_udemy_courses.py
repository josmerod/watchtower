"""ETL script to aggregate Udemy Universal course links from miner output files."""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

# Add project root to Python path
global_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../..")
)
import pandas as pd

from src.utils.course_deduplication import deduplicate_courses
from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("udemy_universal_etl")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Constants
BASE_OUTPUT_DIR = "data/udemy"
SOURCE_RELATIVE_DIR = "src/miners/udemy-universal/Courses"


class UdemyUniversalCoursesETL:
    """ETL for extracting and aggregating Udemy Universal courses."""

    def __init__(self) -> None:
        """Initialize source and output directories and ensure output exists."""
        project_root = get_project_root()
        self.source_dir = os.path.join(project_root, SOURCE_RELATIVE_DIR)
        self.output_dir = os.path.join(project_root, BASE_OUTPUT_DIR)
        ensure_directories([BASE_OUTPUT_DIR])

        self.courses_file = os.path.join(self.output_dir, "udemy_courses.json")
        self.csv_file = os.path.join(self.output_dir, "udemy_courses.csv")

    def extract_courses(self) -> list[dict[str, Any]]:
        """Extract courses from miner files sorted newest to oldest.

        Returns:
            List of course dictionaries with 'title', 'url', and 'scraped_at'.
        """
        courses: list[dict[str, Any]] = []
        try:
            filenames = sorted(os.listdir(self.source_dir), reverse=True)
        except FileNotFoundError:
            logger.error(f"Source directory not found: {self.source_dir}")
            return courses

        for filename in filenames:
            if not filename.lower().endswith(".txt"):
                continue
            filepath = os.path.join(self.source_dir, filename)
            # Parse timestamp from filename
            name_no_ext, _ = os.path.splitext(filename)
            try:
                dt = datetime.strptime(name_no_ext, "%Y-%m-%d--%H-%M")
                scraped_at = dt.isoformat()
            except ValueError:
                scraped_at = datetime.now().isoformat()
                logger.warning(
                    f"Could not parse timestamp from filename: {filename}, using current time"
                )

            try:
                with open(filepath, encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                logger.error(f"Error reading file {filepath}: {e}")
                continue

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    title, url = line.rsplit(" - ", 1)
                except ValueError:
                    logger.warning(f"Could not parse line in {filename}: {line}")
                    continue

                courses.append(
                    {
                        "title": title.strip(),
                        "url": url.strip(),
                        "scraped_at": scraped_at,
                    }
                )

        logger.info(f"Extracted {len(courses)} courses from {self.source_dir}")
        return courses

    def save_courses(self, courses: list[dict[str, Any]]) -> None:
        """Save extracted courses to JSON and CSV files.

        Args:
            courses: List of course dictionaries to save.
        """
        if not courses:
            logger.warning("No courses to save for Udemy Universal")
            return

        # Check if existing courses file exists and combine with new courses
        all_courses = courses
        if os.path.exists(self.courses_file):
            try:
                with open(self.courses_file, encoding="utf-8") as f:
                    existing_courses = json.load(f)
                    all_courses = existing_courses + courses
                    logger.info(
                        f"Combined {len(courses)} new courses with {len(existing_courses)} existing courses"
                    )
            except json.JSONDecodeError:
                logger.warning("Error reading existing courses file. Starting fresh.")

        # Deduplicate courses before saving
        deduplicated_courses, removed_count = deduplicate_courses(
            all_courses, key_field="url", prefer_newer=True
        )
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate courses")

        # Save to JSON
        try:
            with open(self.courses_file, "w", encoding="utf-8") as f:
                json.dump(deduplicated_courses, f, ensure_ascii=False, indent=2)
            logger.info(
                f"Saved {len(deduplicated_courses)} unique courses to JSON: {self.courses_file}"
            )
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
    """Main entry point for Udemy Universal courses ETL."""
    logger.info("Starting Udemy Universal courses ETL")
    etl = UdemyUniversalCoursesETL()
    courses = etl.extract_courses()
    etl.save_courses(courses)
    logger.info("Udemy Universal courses ETL completed")


if __name__ == "__main__":
    main()
