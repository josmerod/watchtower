"""LessWrong RSS ETL

Parses LessWrong RSS feed for the Knowledge Garden.
Feed: https://www.lesswrong.com/feed.xml
Outputs canonical latest JSON under data/lesswrong/.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("LessWrongETL")

FEED_URL = "https://www.lesswrong.com/feed.xml"


def _parse_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        # LessWrong uses standard formats, usually
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z").isoformat()
    except Exception:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            return date_str


def fetch_lesswrong() -> list[dict[str, Any]]:
    logger.info(f"Fetching LessWrong RSS: {FEED_URL}")
    entries: list[dict[str, Any]] = []
    try:
        feed = feedparser.parse(FEED_URL)
    except Exception as e:
        logger.error(f"Failed to fetch LessWrong RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        entries.append(
            {
                "source": "lesswrong",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": getattr(entry, "summary", ""),
                "author": getattr(entry, "author", "LessWrong"),
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "article",
                "language": "en",
            }
        )

    logger.info(f"Retrieved {len(entries)} LessWrong items")
    return entries


def save_lesswrong(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No LessWrong entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "lesswrong")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"lesswrong_{ts}.json")
    latest_json = os.path.join(output_dir, "lesswrong_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(entries)} items to {latest_json}")


def main():
    logger.info("Starting LessWrong RSS ETL")
    entries = fetch_lesswrong()
    if entries:
        save_lesswrong(entries)
    logger.info("LessWrong ETL complete")


if __name__ == "__main__":
    main()
