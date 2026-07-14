"""ETL pipeline for fetching Udemy courses from a Google Spreadsheet."""

import json
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import ValidationError

from src.etl.base import BaseETL
from src.models.course import CourseModel


class UdemySpreadsheetETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """Fetches Udemy courses from a specific public Google Spreadsheet CSV."""

    def __init__(self):
        super().__init__(name="udemy")
        self.csv_url = "https://docs.google.com/spreadsheets/d/1AZ3pw48rDAHZM3C_5S-GkKS7t8dkX9PiGLy39VAYe2U/export?format=csv&gid=2134015255"

    def extract(self) -> list[dict[str, Any]]:
        """Download and parse the CSV from Google Sheets."""
        self.logger.info(f"Downloading Udemy courses from {self.csv_url}")
        try:
            df = pd.read_csv(self.csv_url)
            # Create a list of dicts. Fill na with empty string or None.
            df = df.where(pd.notna(df), None)
            records = df.to_dict(orient="records")
            self.logger.info(f"Extracted {len(records)} records.")
            return records
        except Exception as e:
            self.logger.error(f"Failed to extract Data: {e}")
            return []

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform spreadsheet rows to CourseModel structures."""
        self.logger.info("Transforming Udemy spreadsheet data")
        transformed = []

        for row in data:
            course_id = row.get("Course ID")
            title = row.get("Course Title")
            date_added = row.get("Date Added")
            lang = row.get("Collection Language")
            category = row.get("Category")
            subcategory = row.get("Subcategory")

            if not title:
                # self.metrics.records_failed += 1 (handled by BaseETL counting transformed len)
                continue

            # Construct a basic udemy search or course URL if missing
            url = f"https://www.udemy.com/course/{course_id}/" if course_id else f"https://www.udemy.com/courses/search/?q={title}"

            # Parse date if possible
            scraped_at = datetime.utcnow()
            if date_added:
                try:
                    scraped_at = datetime.strptime(str(date_added).strip(), "%Y-%m-%d")
                except ValueError:
                    try:
                        scraped_at = datetime.strptime(str(date_added).strip(), "%m/%d/%Y")
                    except ValueError:
                        pass  # keep utcnow

            try:
                # Use CourseModel to validate
                course = CourseModel(
                    title=str(title).strip(),
                    url=url,
                    provider="Udemy",
                    language=str(lang).strip() if lang else "Unknown",
                    category=str(category).strip() if category else "Other",
                    subcategory=str(subcategory).strip() if subcategory else "Other",
                    scraped_at=scraped_at,
                    published_date=scraped_at,  # Map date_added to published as well
                    is_free=False,  # By default, assumed mostly paid or unknown based on sheet
                )

                # Dashboard specifically expects this dictionary
                course_dict = course.model_dump()
                # Ensure scraped_at is string for JSON
                course_dict["scraped_at"] = course.scraped_at.isoformat()
                if course.published_date:
                    course_dict["published_date"] = course.published_date.isoformat()

                transformed.append(course_dict)
            except ValidationError as e:
                self.logger.error(f"Validation error for {title}: {e}")
                self.metrics.records_failed += 1

        self.logger.info(f"Transformed {len(transformed)} valid courses.")
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Save the transformed data to data/udemy/udemy_courses.json"""
        if not data:
            self.logger.warning("No data to save.")
            return

        # Dashboard expects udemy_courses.json in data/udemy/
        # The base dir path is self.output_dir which is data/udemy/output
        # Actually the frontend looks for get_data_path("udemy", "udemy_courses.json")
        # which points to data/udemy/udemy_courses.json (parent of output_dir)
        custom_path = self.data_dir / "udemy_courses.json"

        try:
            with open(custom_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            self.logger.info(f"Saved specific dashboard file: {custom_path}")
        except Exception as e:
            self.logger.error(f"Failed to save dashboard file {custom_path}: {e}")
            raise

        # Also save a timestamped / latest in output_dir for archiving/tracking
        latest_file = self.output_dir / "latest.json"
        try:
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass


if __name__ == "__main__":
    etl = UdemySpreadsheetETL()
    etl.run()
