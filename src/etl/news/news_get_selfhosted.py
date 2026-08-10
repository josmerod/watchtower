"""Self-Hosted News ETL — self-hosting and homelab news from selfh.st.

Fetches the selfh.st RSS feed — a curated news source covering self-hosted
applications, homelab tools, and open-source infrastructure. Complements the
Technology Radar tab's cloud/GenAI/AI focus with the self-hosting perspective.

Usage:
    uv run python -m src.etl.news.news_get_selfhosted

Output:
    data/selfhosted/selfhosted_latest.json
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("SelfHostedETL")

RSS_FEED = "https://selfh.st/rss/"


@with_retry
def fetch_selfhosted_feed() -> list[dict[str, Any]]:
    """Fetch and parse the selfh.st RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching selfh.st RSS feed from {RSS_FEED}")
    try:
        response = requests.get(RSS_FEED, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Feed parse warning: {feed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch selfh.st feed: {exc}")
        return entries

    for entry in feed.entries:
        published_raw = entry.get("published", "")
        published = _parse_date(published_raw)
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = re.sub(r"<[^>]+>", "", entry.summary).strip()
        entries.append(
            {
                "source": "selfhosted",
                "source_category": "self_hosting",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary,
                "author": getattr(entry, "author", ""),
                "categories": [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")],
                "guid": entry.get("id", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "selfh.st",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from selfh.st RSS feed")
    return entries


def _parse_date(published_raw: str) -> str:
    """Parse an RSS date string to ISO format, falling back to the raw value."""
    if not published_raw:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(published_raw, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return published_raw


def save_selfhosted_entries(entries: list[dict[str, Any]]) -> None:
    """Persist selfh.st entries to JSON under ``data/selfhosted/``."""
    if not entries:
        logger.info("No selfh.st entries to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "selfhosted")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"selfhosted_{timestamp}.json")
    latest_json = os.path.join(output_dir, "selfhosted_latest.json")
    for path in (json_file, latest_json):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} selfh.st entries to {latest_json}")


def main() -> None:
    """Run the selfh.st ETL."""
    logger.info("Starting selfh.st RSS ETL")
    try:
        entries = fetch_selfhosted_feed()
        if not entries:
            logger.warning("No entries fetched from selfh.st. Exiting.")
            return
        save_selfhosted_entries(entries)
        logger.info(f"Selfh.st ETL complete: {len(entries)} articles.")
    except Exception as exc:
        logger.error(f"Selfh.st ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
