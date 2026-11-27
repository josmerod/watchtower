import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants.etl import SCRAPER_BRANDED_USER_AGENT
from src.etl.base import BaseETL
from src.models.course import GcpSkillsBoostModel

logger = logging.getLogger(__name__)

CATALOG_URL = "https://partner.skills.google/catalog/list"
BASE_URL = "https://partner.skills.google"
PER_PAGE = 200
# The catalog had 715 items on 4 pages on 2026-11-27. The cap only stops the
# loop if the site ever stops marking the end of the list.
MAX_PAGES = 25
REQUEST_DELAY_SECONDS = 0.5

LANGUAGE_ENGLISH = "en"
LANGUAGE_ENGLISH_SPANISH = "en+es"


def catalog_path(raw_path: Any) -> str:
    """Return the catalog path without its query string.

    Every ``path`` of the list API carries a ``catalog_rank`` query that
    differs per item and per listing, so two records of the same lab or course
    only share a URL once the query is gone.
    """
    return str(raw_path or "").split("?", 1)[0]


class GcpSkillsBoostETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """GCP Skills Boost catalog: every page, in English and again in Spanish.

    The list API has no language field. Asked with ``locale=es`` the same
    catalog answers with the Spanish title for the items that have a Spanish
    version, so a title that changes between the two listings marks a
    translated item. Everything in the catalog exists in English.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.courses_file = Path(self.settings.project_root) / "data" / "courses" / "gcp_skills_boost.json"

    def _fetch_page(self, page: int, locale: str | None = None) -> list[dict[str, Any]] | None:
        """Return one page of the catalog, or None when the answer is not a list."""
        query: dict[str, Any] = {"page": page, "per_page": PER_PAGE}
        if locale:
            query["locale"] = locale
        request = urllib.request.Request(f"{CATALOG_URL}?{urllib.parse.urlencode(query)}", headers={"User-Agent": SCRAPER_BRANDED_USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error(f"Failed to fetch GCP Skills Boost page {page}: {e}")
            raise
        if not isinstance(payload, list):
            return None
        return payload

    def _fetch_all_pages(self, locale: str | None = None) -> list[dict[str, Any]]:
        """Fetch every page of the catalog. Past the last page the site answers an object instead of a list."""
        items: list[dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            payload = self._fetch_page(page, locale)
            if payload is None:
                if page == 1:
                    raise ValueError(f"GCP Skills Boost did not answer a catalog list (locale {locale!r}): the site changed or is blocking the request.")
                break
            items.extend(payload)
            if len(payload) < PER_PAGE:
                break
            time.sleep(REQUEST_DELAY_SECONDS)
        return items

    def extract(self) -> list[dict[str, Any]]:
        """Fetch the whole catalog in English, then again in Spanish to learn which items are translated."""
        items = self._fetch_all_pages()
        spanish_titles = {catalog_path(item.get("path")): item.get("title") for item in self._fetch_all_pages("es")}
        for item in items:
            item["title_es"] = spanish_titles.get(catalog_path(item.get("path")))
        logger.info(f"Fetched {len(items)} items from the GCP Skills Boost catalog.")
        return items

    def _load_detection_times(self) -> dict[str, str]:
        """First detection time of each known course, by URL without query string."""
        if not self.courses_file.exists():
            return {}
        try:
            with open(self.courses_file, encoding="utf-8") as f:
                old_data = json.load(f)
            return {str(course.get("url", "")).split("?", 1)[0]: course["first_detected_at"] for course in old_data if course.get("url") and course.get("first_detected_at")}
        except Exception as e:
            logger.warning(f"Failed to load existing GCP courses for timestamp tracking: {e}")
            return {}

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build one record per catalog path, keeping `first_detected_at` of the courses already known."""
        detected_times = self._load_detection_times()
        now = datetime.now(timezone.utc)
        records: dict[str, dict[str, Any]] = {}
        for item in data:
            title, path = item.get("title"), catalog_path(item.get("path"))
            if not title or not path:
                continue
            url = f"{BASE_URL}{path}"
            if url in records:
                continue
            detected_at = detected_times.get(url)
            title_es = item.get("title_es")
            model = GcpSkillsBoostModel(
                title=title,
                url=url,
                duration=item.get("duration"),
                level=item.get("level"),
                description=item.get("description"),
                course_type=item.get("type"),
                language=LANGUAGE_ENGLISH_SPANISH if title_es and title_es != title else LANGUAGE_ENGLISH,
                first_detected_at=datetime.fromisoformat(detected_at) if detected_at else now,
            )
            records[url] = model.model_dump(mode="json")

        if data and not records:
            raise ValueError(f"None of the {len(data)} GCP Skills Boost items had a title and a path: the catalog format changed.")
        logger.info(f"{len(records)} catalog items, {sum(1 for record in records.values() if record['language'] == LANGUAGE_ENGLISH_SPANISH)} of them with a Spanish version.")
        return list(records.values())

    def load(self, data: list[dict[str, Any]]) -> None:
        """Save the catalog to JSON."""
        self.courses_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.courses_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved {len(data)} GCP Skills Boost items to {self.courses_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    GcpSkillsBoostETL(name="gcp_skills_boost_etl").run()
