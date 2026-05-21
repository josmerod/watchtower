"""SEC EDGAR RSS ETL

Parses SEC EDGAR company filings RSS (public feed) for intelligence.
Default feed: recent filings.
Outputs canonical latest JSON under data/intelligence/.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("SECEDGARETL")


FEED_URL = "https://www.sec.gov/Archives/edgar/usgaap.rss.xml"


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


def fetch_sec_edgar() -> list[dict[str, Any]]:
    logger.info(f"Fetching SEC EDGAR RSS: {FEED_URL}")
    entries: list[dict[str, Any]] = []
    try:
        # SEC.gov blocks requests without a proper User-Agent header.
        feed = feedparser.parse(
            FEED_URL,
            request_headers={"User-Agent": "Watchtower/1.0 (contact@example.org)"},
        )
    except Exception as e:
        logger.error(f"Failed to fetch SEC EDGAR RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        entries.append(
            {
                "source": "sec_edgar",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": getattr(entry, "summary", ""),
                "guid": getattr(entry, "id", getattr(entry, "guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "filing",
                "language": "en",
                "region": "us",
            }
        )

    logger.info(f"Retrieved {len(entries)} SEC EDGAR items")
    return entries


def save_sec(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No SEC entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "intelligence")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"sec_edgar_{ts}.json")
    latest_json = os.path.join(output_dir, "sec_edgar_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info("Saved SEC EDGAR latest and timestamped outputs")


def main():
    logger.info("Starting SEC EDGAR RSS ETL")
    entries = fetch_sec_edgar()
    if entries:
        save_sec(entries)
    logger.info("SEC EDGAR ETL complete")


if __name__ == "__main__":
    main()
