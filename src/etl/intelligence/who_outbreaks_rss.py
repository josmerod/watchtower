"""WHO Disease Outbreak News RSS ETL

Parses WHO outbreaks RSS feed for global health intelligence.
Outputs canonical latest JSON under data/intelligence/.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger


logger = get_logger("WHOOutbreaksETL")


FEED_URL = "https://www.who.int/feeds/entity/csr/don/en/rss.xml"


def _parse_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z").isoformat()
    except Exception:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            return date_str


def fetch_who_outbreaks() -> List[Dict[str, Any]]:
    logger.info(f"Fetching WHO Outbreaks RSS: {FEED_URL}")
    entries: List[Dict[str, Any]] = []
    try:
        feed = feedparser.parse(FEED_URL)
    except Exception as e:
        logger.error(f"Failed to fetch WHO Outbreaks RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        summary = getattr(entry, "summary", "")
        summary_text = re.sub(r"<[^>]+>", "", summary).strip() if summary else ""
        entries.append(
            {
                "source": "who_outbreaks",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": summary_text,
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "health_alert",
                "language": "en",
                "region": "global",
            }
        )

    logger.info(f"Retrieved {len(entries)} WHO outbreak items")
    return entries


def save_who(entries: List[Dict[str, Any]]) -> None:
    if not entries:
        logger.info("No WHO outbreak entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "intelligence")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"who_outbreaks_{ts}.json")
    latest_json = os.path.join(output_dir, "who_outbreaks_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info("Saved WHO outbreaks latest and timestamped outputs")


def main():
    logger.info("Starting WHO Outbreaks RSS ETL")
    entries = fetch_who_outbreaks()
    if entries:
        save_who(entries)
    logger.info("WHO Outbreaks ETL complete")


if __name__ == "__main__":
    main()

