"""ETL for Microsoft Applied Skills.

Fetches the complete catalog of Applied Skills from Microsoft Learn API.
Tracks the `first_detected_at` timestamp across ETL runs so new skills can be bubbled up.

The catalog mixes two kinds of credential in one file: Applied Skills and
certifications. A description is stored as plain text, and one that carries a
retirement notice marks its credential with ``retired`` (and with
``retirement_date`` when the notice gives one).
"""

import datetime
import json
import logging
import re
from pathlib import Path
from typing import Any, cast

import requests

from src.etl.base import BaseETL
from src.models.course import MsAppliedSkillModel
from src.utils.text import html_to_text

logger = logging.getLogger(__name__)

API_URL = "https://learn.microsoft.com/api/catalog/"

# A retirement notice talks about the credential itself ("This certification has
# been retired."), so a note about the exams of a credential that is still
# current does not count. The notice can open or close the description.
_SUBJECT = r"\bthis\s+(?:(?:version\s+of\s+the\s+)?(?:certifications?|credentials?|applied\s+skills?\s+assessments?))\b"
_RETIRED_NOTICE = re.compile(_SUBJECT + r"[^.!?]{0,160}?\b(?:ha(?:s|ve)\s+been|was|were|is|are)\s+retired\b", re.IGNORECASE)
_RETIRING_NOTICE = re.compile(_SUBJECT + r"[^.!?]{0,160}?\b(?:will\s+be\s+retired|will\s+retire|retires|is\s+retiring)\b", re.IGNORECASE)
_UNAVAILABLE_NOTICE = re.compile(r"\bthis\s+version\b[^.!?]{0,120}?\bis\s+no\s+longer\s+available\b", re.IGNORECASE)
_RETIREMENT_DATE = re.compile(r"\bretir(?:ed|es|e)\s+on\s+([a-z]+\s+\d{1,2},\s*\d{4})\b", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# Month names are matched by hand: datetime.strptime() would follow the locale of the process.
_MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")


def _notice_date(sentence: str) -> datetime.date | None:
    """Return the date a retirement sentence gives ("... was retired on June 30, 2026."), or None."""
    match = _RETIREMENT_DATE.search(sentence)
    if not match:
        return None
    month, day, year = re.sub(r"\s+", " ", match.group(1)).replace(",", "").split(" ")
    try:
        return datetime.date(int(year), _MONTHS.index(month.lower()) + 1, int(day))
    except ValueError:
        return None


def retirement_notice(description: str | None, today: datetime.date | None = None) -> tuple[bool, str | None]:
    """Read the retirement notice out of a credential's description.

    Microsoft Learn keeps a retired credential in the catalog and says so in its
    description: a warning box ("This certification has been retired.") or a note
    on a superseded version ("This version of the certification is no longer
    available."). The text is read as plain text, anywhere in the description.

    Args:
        description: The description as the catalog serves it, HTML markup included.
        today: The day the answer is for. Defaults to today, in UTC.

    Returns:
        ``(retired, retirement_date)``. The date is ``YYYY-MM-DD`` when the notice
        gives one, and ``None`` when it does not or the credential is current. A
        notice with a date in the future ("will retire on ...") retires the
        credential from the day after that date on.
    """
    sentences = _SENTENCE_END.split(html_to_text(description))
    for sentence in sentences:
        if _RETIRED_NOTICE.search(sentence):
            date = _notice_date(sentence)
            return True, date.isoformat() if date else None
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    for sentence in sentences:
        if _RETIRING_NOTICE.search(sentence):
            date = _notice_date(sentence)
            return date is not None and date < today, date.isoformat() if date else None
    for sentence in sentences:
        if _UNAVAILABLE_NOTICE.search(sentence):
            return True, None
    return False, None


class MsAppliedSkillsETL(BaseETL):
    """ETL process for fetching Microsoft Applied Skills."""

    def __init__(self, batch_size: int | None = None, enable_checkpointing: bool = False):
        super().__init__(
            name="ms_applied_skills_etl",
            description="ETL for Microsoft Applied Skills from Microsoft Learn API.",
            batch_size=batch_size,
            enable_checkpointing=enable_checkpointing,
        )
        # We save data under data/courses/. The settings' validator backfills
        # project_root, so it is never None here (as in BaseETL).
        self.output_file = Path(cast("str", self.settings.project_root)) / "data" / "courses" / "ms_applied_skills.json"

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
                    # The catalog serves the summary as HTML, warning boxes included.
                    description=html_to_text(item.get("summary") or item.get("subtitle") or ""),
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
        """Saves the data to the target JSON file, each record with its retirement notice read."""
        if not data:
            self.logger.warning("No Microsoft Applied Skills to load. Skipping file write out.")
            return

        self.logger.info(f"Saving {len(data)} Applied Skills to {self.output_file}...")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            records = []
            for item in data:
                # The model has no field for the notice, so it is read here, from the
                # description that is written: deduplication rebuilds the models.
                record = item.model_dump(mode="json")
                record["retired"], record["retirement_date"] = retirement_notice(item.description)
                records.append(record)
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            self.metrics.records_loaded = len(data)
        except Exception as e:
            self.logger.error(f"Failed to save Microsoft Applied Skills: {e}")
            self.metrics.error_count += 1
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    etl = MsAppliedSkillsETL()
    etl.run()
