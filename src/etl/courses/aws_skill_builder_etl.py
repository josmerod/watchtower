import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
import urllib.request
import urllib.error

from src.etl.base import BaseETL
from src.models.course import AwsSkillBuilderModel

logger = logging.getLogger(__name__)


class AwsSkillBuilderETL(BaseETL):
    """ETL process for fetching AWS Skill Builder courses from ClassCentral."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = "https://www.classcentral.com/provider/aws-skill-builder?sort=created-up"
        
        # Determine output path
        self.output_dir = Path("data/courses")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "aws_skill_builder.json"

    def extract(self) -> str:
        """Fetch the HTML content from ClassCentral."""
        try:
            req = urllib.request.Request(
                self.url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Watchtower/1.0'}
            )
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            if "Cloudflare" in html or "Just a moment" in html:
                logger.warning("Cloudflare challenge page detected.")
            
            logger.info("Successfully fetched HTML from ClassCentral for AWS Skill Builder.")
            return html
        except urllib.error.URLError as e:
            logger.error(f"Failed to fetch ClassCentral HTML: {e}")
            raise

    def transform(self, data: str) -> list[dict]:
        """Parse HTML to extract courses and assign first_detected_at."""
        soup = BeautifulSoup(data, "html.parser")
        
        # Extract courses using 'course-name' class
        extracted_courses = []
        for a in soup.find_all("a", class_="course-name"):
            title = a.get_text(strip=True)
            url = "https://www.classcentral.com" + a.get('href', '')
            
            infos = []
            parent = a.find_parent("li")
            if parent:
                spans = parent.find_all("span")
                infos = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]
                
            duration = None
            level = None
            is_free = False
            
            # Simple heuristic mapping based on ClassCentral's common span text
            for info in infos:
                lower_info = info.lower()
                if "hour" in lower_info or "minute" in lower_info:
                    duration = info
                elif "beginner" in lower_info or "intermediate" in lower_info or "advanced" in lower_info:
                    level = info
                elif "free" in lower_info:
                    is_free = True
            
            description = " | ".join(infos) if infos else None

            extracted_courses.append({
                "title": title,
                "url": url,
                "duration": duration,
                "level": level,
                "is_free": is_free,
                "description": description
            })

        logger.info(f"Extracted {len(extracted_courses)} courses from HTML.")
        
        # Load previous courses to track first_detected_at
        existing_detection_times = {}
        if self.output_file.exists():
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    for course in old_data:
                        if course.get("url") and course.get("first_detected_at"):
                            existing_detection_times[course["url"]] = course["first_detected_at"]
            except Exception as e:
                logger.warning(f"Failed to load existing AWS courses for timestamp tracking: {e}")

        # Map to Pydantic models
        models = []
        now = datetime.now(timezone.utc)
        for ec in extracted_courses:
            detected_at_str = existing_detection_times.get(ec["url"])
            if detected_at_str:
                detected_at = datetime.fromisoformat(detected_at_str)
            else:
                detected_at = now

            model = AwsSkillBuilderModel(
                title=ec["title"],
                url=ec["url"],
                duration=ec["duration"],
                level=ec["level"],
                is_free=ec["is_free"],
                description=ec["description"],
                first_detected_at=detected_at
            )
            models.append(model.model_dump(mode="json"))

        return models

    def load(self, data: list[dict]) -> None:
        """Save the courses to JSON."""
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved {len(data)} AWS Skill Builder courses to {self.output_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    etl = AwsSkillBuilderETL(name="aws_skill_builder_etl")
    etl.run()
