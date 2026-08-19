"""Hugging Face Learn ETL

Scrapes the public Hugging Face course catalog (huggingface.co/learn) and
writes it for the Learning tab. Static HTML — no Playwright, no API key.

Usage:
    uv run python src/etl/courses/hf_learn_etl.py

Output:
    - data/courses/hf_learn.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("HfLearnETL")

CATALOG_URL = "https://huggingface.co/learn"
HEADERS = {"User-Agent": "Mozilla/5.0 (WatchtowerBot)"}
OUTPUT_FILE = Path("data/courses/hf_learn.json")


def fetch_courses(max_retries: int = 3) -> list[dict[str, Any]]:
    """Fetch the course catalog from huggingface.co/learn."""
    html = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching {CATALOG_URL}")
            resp = requests.get(CATALOG_URL, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            html = resp.text
            break
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt == max_retries - 1:
                logger.error(f"Error fetching HF Learn catalog: {e!s}")
                return []

    soup = BeautifulSoup(html or "", "html.parser")
    courses: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Course cards link to /learn/<slug>; the card also carries the course name.
    for anchor in soup.select('a[href^="/learn/"]'):
        href = anchor.get("href", "")
        slug = href.removeprefix("/learn/").strip("/")
        if not slug or slug in seen:
            continue
        # Card headline is the first heading inside the anchor, else its text
        heading = anchor.find(["h2", "h3", "h4"]) or anchor
        name = heading.get_text(" ", strip=True)
        if not name or name.lower() in {"learn", "view all"}:
            name = slug.replace("-", " ").title()
        seen.add(slug)
        courses.append(
            {
                "title": name,
                "url": f"https://huggingface.co{href}",
                "source": "huggingface.co/learn",
                "published_at": "",
                "summary": "Free Hugging Face course",
                "duration": "",
                "level": "",
                "is_free": True,
                "language": "en",
                "tags": ["huggingface", "ai", "course"],
                "metadata": {"api_source": "hf_learn_scrape", "processed_at": datetime.now().isoformat()},
            }
        )

    logger.info(f"Retrieved {len(courses)} HF Learn courses")
    return courses


def main() -> None:
    """Fetch the HF Learn catalog and persist it for the Learning tab."""
    logger.info("Starting Hugging Face Learn ETL")
    courses = fetch_courses()
    if not courses:
        logger.warning("No courses retrieved — keeping any existing file untouched")
        return

    output_path = Path(get_project_root()) / OUTPUT_FILE
    ensure_directories([str(output_path.parent)])
    output_path.write_text(json.dumps(courses, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved {len(courses)} courses to {output_path}")


if __name__ == "__main__":
    main()
