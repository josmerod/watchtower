import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src.etl.base import BaseETL
from src.models.course import GcpSkillsBoostModel

logger = logging.getLogger(__name__)


class GcpSkillsBoostETL(BaseETL):
    """ETL process for fetching GCP Skills Boost courses and labs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fetching 200 to get a good chunk of recent and existing items
        self.url = "https://partner.skills.google/catalog/list?page=1&per_page=200"
        self.base_url = "https://partner.skills.google"

        # Determine output path
        self.output_dir = Path("data/courses")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "gcp_skills_boost.json"

    def extract(self) -> str:
        """Fetch the JSON payload from GCP Skills Boost."""
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Watchtower/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req) as response:
                payload = response.read().decode("utf-8")

            logger.info("Successfully fetched payload from GCP Skills Boost.")
            return payload
        except urllib.error.URLError as e:
            logger.error(f"Failed to fetch GCP Skills Boost JSON: {e}")
            raise

    def transform(self, data: str) -> list[dict]:
        """Parse JSON response and assign first_detected_at."""
        try:
            items = json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON payload: {e}")
            raise

        logger.info(f"Extracted {len(items)} items from JSON.")

        # Load previous courses to track first_detected_at
        existing_detection_times = {}
        if self.output_file.exists():
            try:
                with open(self.output_file, encoding="utf-8") as f:
                    old_data = json.load(f)
                    for course in old_data:
                        if course.get("url") and course.get("first_detected_at"):
                            existing_detection_times[course["url"]] = course["first_detected_at"]
            except Exception as e:
                logger.warning(f"Failed to load existing GCP courses for timestamp tracking: {e}")

        # Map to Pydantic models
        models = []
        now = datetime.now(timezone.utc)
        for item in items:
            title = item.get("title")
            path = item.get("path", "")
            if not title or not path:
                continue

            url = f"{self.base_url}{path}"

            detected_at_str = existing_detection_times.get(url)
            if detected_at_str:
                detected_at = datetime.fromisoformat(detected_at_str)
            else:
                detected_at = now

            model = GcpSkillsBoostModel(
                title=title, url=url, duration=item.get("duration"), level=item.get("level"), description=item.get("description"), course_type=item.get("type"), first_detected_at=detected_at
            )
            models.append(model.model_dump(mode="json"))

        return models

    def load(self, data: list[dict]) -> None:
        """Save the courses to JSON."""
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved {len(data)} GCP Skills Boost courses to {self.output_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    etl = GcpSkillsBoostETL(name="gcp_skills_boost_etl")
    etl.run()
