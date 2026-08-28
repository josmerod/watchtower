"""DeepLearning.AI courses ETL

Builds the DeepLearning.AI course catalog for the Learning tab. Two keyless,
static sources are combined:

1. ``https://www.deeplearning.ai/sitemap.xml`` — the deterministic catalog
   backbone (~119 course URLs; stable across requests).
2. ``https://www.deeplearning.ai/courses/`` — server-rendered course cards
   (title, partner, summary). The grid only shows a rotating subset of the
   catalog per request, so cards are used to *enrich* the sitemap URLs, never
   to define the catalog.

Static HTML only — no Playwright, no API key.

Usage:
    uv run python src/etl/courses/deeplearning_ai_etl.py

Output:
    - data/courses/deeplearning_ai_latest.json (+ timestamped copy)
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("DeepLearningAiETL")

COURSES_URL = "https://www.deeplearning.ai/courses/"
SITEMAP_URL = "https://www.deeplearning.ai/sitemap.xml"
BASE_URL = "https://www.deeplearning.ai"
OUTPUT_FILE = Path("data/courses/deeplearning_ai_latest.json")
HEADERS = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}
REQUEST_TIMEOUT = 60
TAGS = ["deeplearning-ai", "ai", "course"]


def fetch_url(url: str, max_retries: int = 3) -> str | None:
    """Fetch a URL with retries, returning the text body or ``None``."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching {url} (attempt {attempt}/{max_retries})")
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt}/{max_retries} failed: {e!s}")
            if attempt < max_retries:
                time.sleep(5 * attempt)
    logger.error(f"Error fetching {url}: all {max_retries} attempts failed")
    return None


def parse_sitemap(xml_text: str) -> list[str]:
    """Extract course slugs (e.g. ``agentic-ai``) from the sitemap XML."""
    locs = re.findall(r"<loc>([^<]+)</loc>", xml_text)
    slugs = []
    for loc in locs:
        match = re.search(r"/courses/([a-z0-9-]+)/?$", loc)
        if match:
            slugs.append(match.group(1))
    slugs = sorted(set(slugs))
    logger.info(f"Sitemap contains {len(slugs)} course URLs")
    return slugs


def parse_course_cards(html: str) -> dict[str, dict[str, str]]:
    """Parse course cards from the rendered catalog HTML.

    Cards are ``<a class="contents" href="/courses/<slug>">`` blocks with an
    ``h3.card-title``, a partner ``span.line-clamp-1`` and a ``p.body2``
    summary. Non-card links (``Learn More``, nav, …) are skipped by requiring
    a heading inside the anchor.

    Returns:
        Mapping of slug -> ``{"title": ..., "partner": ..., "summary": ...}``.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards: dict[str, dict[str, str]] = {}
    for anchor in soup.select('a[href^="/courses/"]'):
        raw_href = anchor.get("href", "")
        href = raw_href if isinstance(raw_href, str) else ""
        slug = href.removeprefix("/courses/").strip("/")
        if not slug:
            continue
        heading = anchor.find(["h2", "h3", "h4"])
        if heading is None:
            continue
        title = heading.get_text(" ", strip=True)
        if not title:
            img = anchor.find("img")
            alt = img.get("alt") if img else None
            title = (alt or "").strip() if isinstance(alt, str) else ""
        if not title:
            continue

        partner_el = anchor.select_one("span.line-clamp-1")
        partner = partner_el.get_text(" ", strip=True) if partner_el else ""

        summary = ""
        summary_el = anchor.select_one("p.body2") or anchor.find("p")
        if summary_el:
            text = summary_el.get_text(" ", strip=True)
            if len(text) > 30:
                summary = text

        card = {"title": title, "partner": partner, "summary": summary}
        existing = cards.get(slug)
        # Keep the richer card when a slug appears twice (featured + grid).
        if existing is None or len(card["partner"]) + len(card["summary"]) > len(existing["partner"]) + len(existing["summary"]):
            cards[slug] = card
    logger.info(f"Parsed {len(cards)} course cards from catalog page")
    return cards


def _title_from_slug(slug: str) -> str:
    """Derive a human-readable title from a course slug."""
    return slug.replace("-", " ").title()


def build_courses(slugs: list[str], cards: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Merge the sitemap backbone with the parsed cards into output records."""
    now = datetime.now(timezone.utc).isoformat()
    courses: list[dict[str, Any]] = []
    for slug in slugs:
        card = cards.get(slug)
        courses.append(
            {
                "title": card["title"] if card else _title_from_slug(slug),
                "url": f"{BASE_URL}/courses/{slug}",
                "source": "deeplearning.ai/courses",
                "published_at": "",
                "summary": card["summary"] if card else "",
                "duration": "",
                "level": "",
                "is_free": True,
                "language": "en",
                "tags": TAGS,
                "partner": card["partner"] if card else "",
                "metadata": {"api_source": "deeplearning_ai_scrape", "processed_at": now, "card_enriched": card is not None},
            }
        )
    logger.info(f"Built {len(courses)} course records ({sum(1 for c in courses if c['metadata']['card_enriched'])} enriched from cards)")
    return courses


def fetch_courses(max_retries: int = 3) -> list[dict[str, Any]]:
    """Fetch sitemap + catalog page and return the merged course list."""
    xml_text = fetch_url(SITEMAP_URL, max_retries=max_retries)
    html = fetch_url(COURSES_URL, max_retries=max_retries)

    cards = parse_course_cards(html) if html else {}
    slugs = parse_sitemap(xml_text) if xml_text else sorted(cards)
    if not slugs:
        logger.error("No slugs from sitemap or catalog page — nothing to build")
        return []
    return build_courses(slugs, cards)


def main() -> None:
    """Fetch the DeepLearning.AI catalog and persist it (last-good wins)."""
    logger.info("Starting DeepLearning.AI courses ETL")
    courses = fetch_courses()
    if not courses:
        logger.warning("No courses retrieved — keeping any existing file untouched")
        return

    latest_path = Path(get_project_root()) / OUTPUT_FILE
    ensure_directories([str(latest_path.parent)])
    payload = json.dumps(courses, indent=2, ensure_ascii=False)

    latest_path.write_text(payload, encoding="utf-8")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = latest_path.with_name(f"deeplearning_ai_{timestamp}.json")
    archive_path.write_text(payload, encoding="utf-8")
    logger.info(f"Saved {len(courses)} courses to {latest_path} (archive: {archive_path.name})")


if __name__ == "__main__":
    main()
