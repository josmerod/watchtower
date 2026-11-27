"""Ben's Bites ETL Module

Fetches the Ben's Bites newsletter feed (an AI digest, two or three issues a week) for the
News tab. No API key required. Each item of the feed is one issue.

Usage:
    uv run python src/etl/news/news_get_bensbites.py

Output:
    - JSON file: data/bensbites/bensbites_news.json
    - CSV file: data/bensbites/bensbites_news.csv

The newsletter lives on Substack. Until the 2026-11-27 this script scraped
``news.bensbites.com/trending`` with Playwright: that page stopped loading in April 2026 and
every cycle ended with "No articles retrieved" and exit code 0, so the tab went on showing
the articles of 2026-04-29 (T-176). A fetch that returns nothing is a failure now: the
script exits with 1, the cycle lists it, and the previous file stays where it was.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.text import html_to_text

logger = get_logger("BensBitesETL")

RSS_URL = "https://www.bensbites.com/feed"
SOURCE_NAME = "Ben's Bites"
DESCRIPTION_MAX_CHARS = 300


def fetch_feed(url: str = RSS_URL, max_retries: int = 3, retry_delay: int = 5) -> list[Any]:
    """Download and parse the feed.

    Args:
        url: The feed URL.
        max_retries: Attempts before giving up.
        retry_delay: Seconds between attempts.

    Returns:
        The feed entries, or an empty list when every attempt failed or came back empty.
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching RSS feed from {url}")
            response = requests.get(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if feed.entries:
                return feed.entries
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: the feed has no entries")
        except Exception as e:  # broad by design: network fetch and parse of an external feed (retry loop)
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    logger.error(f"Error fetching {url} after {max_retries} attempts")
    return []


def _published_iso(entry: Any) -> str:
    """The entry's publication date as an ISO-8601 timestamp in UTC, or an empty string."""
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not isinstance(parsed, time.struct_time):
        return ""
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    except (TypeError, IndexError, ValueError):  # a struct_time feedparser built from a date it did not validate
        return ""


def _description(entry: Any) -> str:
    """The issue's subtitle, or the opening of its body when the subtitle is long or missing."""
    subtitle = html_to_text(getattr(entry, "summary", None))
    if subtitle and len(subtitle) <= DESCRIPTION_MAX_CHARS:
        return subtitle
    content = getattr(entry, "content", None) or []
    text = html_to_text(content[0].get("value")) if content else subtitle
    if len(text) > DESCRIPTION_MAX_CHARS:
        return f"{text[:DESCRIPTION_MAX_CHARS].rstrip()}..."
    return text


def process_entries(entries: list[Any]) -> list[dict[str, Any]]:
    """Turn feed entries into the records the News tab reads, newest first."""
    issues: list[dict[str, Any]] = []
    for entry in entries:
        title = (getattr(entry, "title", "") or "").strip()
        url = getattr(entry, "link", "") or ""
        if not title or not url:
            logger.warning("Skipping an entry without title or link")
            continue
        issues.append(
            {
                "title": title,
                "url": url,
                "source": SOURCE_NAME,
                "published_at": _published_iso(entry),
                "description": _description(entry),
                "metadata": {
                    "api_source": "bensbites_rss",
                    "author": getattr(entry, "author", ""),
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        )
    issues.sort(key=lambda issue: issue["published_at"], reverse=True)
    logger.info(f"Processed {len(issues)} issues")
    return issues


def main() -> bool:
    """Fetch the feed and save its issues.

    Returns:
        True when the files were written; False when the feed gave nothing or the run failed,
        in which case the previous files are left untouched.
    """
    logger.info("Starting Ben's Bites ETL process")
    try:
        issues = process_entries(fetch_feed())
        if not issues:
            logger.warning("No issues retrieved, ETL process cannot continue")
            return False

        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "bensbites")
        ensure_directories(["data/bensbites"])

        output_file = os.path.join(output_dir, "bensbites_news.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(issues)} issues to {output_file}")

        csv_file = os.path.join(output_dir, "bensbites_news.csv")
        import pandas as pd

        pd.DataFrame(issues).to_csv(csv_file, index=False)
        logger.debug(f"Saved CSV data to {csv_file}")
        return True

    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save) incl. pandas save
        logger.error(f"Error in Ben's Bites ETL process: {e!s}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("Ben's Bites ETL script started")
    raise SystemExit(0 if main() else 1)
