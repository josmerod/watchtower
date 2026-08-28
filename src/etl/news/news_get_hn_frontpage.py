"""Hacker News front-page ETL via the Algolia API (spec 13 source table).

Fetches the current Hacker News front page through the public, keyless
Algolia Search API — what the community is discussing right now, not just
what outlets are publishing. Feeds the Tech Radar tab's discussion column.

Usage:
    uv run python -m src.etl.news.news_get_hn_frontpage

Output:
    data/news/hn_frontpage_latest.json (+ timestamped snapshot)
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("HNFrontPageETL")

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
HITS_PER_PAGE = 30


@with_retry
def fetch_hn_frontpage() -> list[dict[str, Any]]:
    """Fetch the current HN front page from the Algolia API."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching HN front page from {HN_ALGOLIA_URL}")
    try:
        response = requests.get(
            HN_ALGOLIA_URL,
            params={"tags": "front_page", "hitsPerPage": HITS_PER_PAGE},
            headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        hits = response.json().get("hits", [])
    except (requests.RequestException, ValueError) as exc:
        logger.error(f"Could not fetch HN front page: {exc}")
        return entries

    for hit in hits:
        object_id = hit.get("objectID", "")
        hn_link = f"https://news.ycombinator.com/item?id={object_id}" if object_id else ""
        article_url = hit.get("url", "") or ""
        points = hit.get("points", 0) or 0
        comments = hit.get("num_comments", 0) or 0
        author = hit.get("author", "")
        summary = f"⬆ {points} points · 💬 {comments} comments · by {author}"
        if hit.get("story_text"):
            summary += f" — {hit['story_text'][:200]}"
        entries.append(
            {
                "source": "hn_frontpage",
                "source_category": "tech_discussion",
                "title": hit.get("title", ""),
                "link": article_url or hn_link,
                "hn_link": hn_link,
                "published": hit.get("created_at", ""),
                "summary": summary[:500],
                "author": author,
                "points": points,
                "num_comments": comments,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "hackernews",
                "content_type": "discussion_thread",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from the HN front page")
    return entries


def save_hn_entries(entries: list[dict[str, Any]]) -> None:
    """Persist the HN front-page entries under ``data/news/``."""
    if not entries:
        logger.info("No HN front-page entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "news")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "hn_frontpage_latest.json")
    snapshot = os.path.join(output_dir, f"hn_frontpage_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} HN front-page entries to {latest}")


def main() -> None:
    """Run the HN front-page ETL."""
    logger.info("Starting HN front-page ETL")
    try:
        entries = fetch_hn_frontpage()
        if not entries:
            logger.warning("No entries fetched from HN front page. Exiting.")
            return
        save_hn_entries(entries)
        logger.info(f"HN front-page ETL complete: {len(entries)} stories.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"HN front-page ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
