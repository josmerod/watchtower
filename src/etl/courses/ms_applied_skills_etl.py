"""ETL for Microsoft Applied Skills.

Fetches the complete catalog of Applied Skills from Microsoft Learn API.
Tracks the `first_detected_at` timestamp across ETL runs so new skills can be bubbled up.
"""

import datetime
import json
import logging
from pathlib import Path
from typing import Any

import requests

from src.etl.base import BaseETL
from src.models.course import MsAppliedSkillModel

logger = logging.getLogger(__name__)

API_URL = "https://learn.microsoft.com/api/catalog/"


class MsAppliedSkillsETL(BaseETL):
    """ETL process for fetching Microsoft Applied Skills."""

    def __init__(self, batch_size: int | None = None, enable_checkpointing: bool = False):
        super().__init__(
            name="ms_applied_skills_etl",
            description="ETL for Microsoft Applied Skills from Microsoft Learn API.",
            batch_size=batch_size,
            enable_checkpointing=enable_checkpointing,
        )
        # We save data under data/courses/
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.output_file = project_root / "data" / "courses" / "ms_applied_skills.json"

        # We need to maintain state to know when a skill was first detected.
        self.previous_state: dict[str, str] = {}
        self._load_previous_state()

    def _load_previous_state(self) -> None:
        """Loads previous data to preserve the `first_detected_at` timestamps."""
        if self.output_file.exists():
            try:
                with open(self.output_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        url = item.get("url")
                        detected_at = item.get("first_detected_at")
                        if url and detected_at:
                            self.previous_state[url] = detected_at
            except json.JSONDecodeError:
                logger.warning(f"Could not decode JSON from {self.output_file}. Starting fresh.")
            except Exception as e:
                logger.error(f"Error loading previous state: {e}")

    def extract(self) -> list[dict[str, Any]]:
        """Extracts data from the Microsoft Learn Catalog API."""
        self.logger.info(f"Fetching Microsoft Learn Catalog from {API_URL}...")
        try:
            response = requests.get(API_URL, timeout=30)
            response.raise_for_status()
            data = response.json()

            applied_skills = data.get("appliedSkills", [])
            certifications = data.get("certifications", [])
            credentials = [*applied_skills, *certifications]
            self.logger.info(
                "Found %s Applied Skills and %s certifications in catalog.",
                len(applied_skills),
                len(certifications),
            )
            self.metrics.records_extracted = len(credentials)
            return credentials

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error fetching Microsoft Learn catalog: {e}")
            self.metrics.error_count += 1
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error fetching Microsoft Learn catalog: {e}")
            self.metrics.error_count += 1
            raise

    def transform(self, data: list[dict[str, Any]]) -> list[MsAppliedSkillModel]:
        """Transforms raw dict items into MsAppliedSkillModel objects."""
        self.logger.info("Transforming Applied Skills data...")
        transformed_data = []
        now = datetime.datetime.now(datetime.timezone.utc)

        for item in data:
            try:
                url = item.get("url", "")
                credential_type = item.get("type") or "applied_skill"
                title = item.get("title", "Unknown Microsoft credential")

                # Check for first detected at logic
                first_detected = None
                if url in self.previous_state:
                    try:
                        first_detected = datetime.datetime.fromisoformat(self.previous_state[url])
                    except Exception:
                        first_detected = now
                else:
                    first_detected = now

                # Parse level and dates
                levels = item.get("levels", [])
                level = levels[0].capitalize() if levels else None

                last_modified_str = item.get("last_modified")
                published_date = None
                if last_modified_str:
                    try:
                        published_date = datetime.datetime.fromisoformat(last_modified_str)
                    except ValueError:
                        pass

                # Subject mapping
                subjects = item.get("subjects", [])
                subject = subjects[0].replace("-", " ").title() if subjects else None

                skill = MsAppliedSkillModel(
                    title=title,
                    url=url,
                    provider="Microsoft Learn",
                    description=item.get("summary") or item.get("subtitle") or "",
                    level=level,
                    subject=subject,
                    category=credential_type,
                    published_date=published_date,
                    first_detected_at=first_detected,
                    roles=item.get("roles", []),
                    products=item.get("products", []),
                )
                transformed_data.append(skill)
            except Exception as e:
                self.logger.error(f"Failed to transform item {item.get('uid')}: {e}")
                self.metrics.records_failed += 1

        self.metrics.records_transformed = len(transformed_data)
        return transformed_data

    def load(self, data: list[MsAppliedSkillModel]) -> None:
        """Saves the data to the target JSON file."""
        if not data:
            self.logger.warning("No Microsoft Applied Skills to load. Skipping file write out.")
            return

        self.logger.info(f"Saving {len(data)} Applied Skills to {self.output_file}...")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                # Use default=str for formatting datetime safely along with pydantic_encoder
                json.dump([item.model_dump(mode="json") for item in data], f, indent=2)
            self.metrics.records_loaded = len(data)
        except Exception as e:
            self.logger.error(f"Failed to save Microsoft Applied Skills: {e}")
            self.metrics.error_count += 1
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    etl = MsAppliedSkillsETL()
    etl.run()
