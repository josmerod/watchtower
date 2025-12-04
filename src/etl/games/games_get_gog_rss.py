"""GOG New Releases RSS ETL

Parses GOG.com PC new releases RSS for games and deals.
Outputs canonical latest JSON under data/games/.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("GOGRSSETL")


FEED_URL = "https://www.gog.com/rss/newreleases/pc"


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


def _extract_price(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"\$(\d+(?:\.\d{2})?)", text)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return None
    return None


def fetch_gog() -> list[dict[str, Any]]:
    logger.info(f"Fetching GOG RSS: {FEED_URL}")
    entries: list[dict[str, Any]] = []
    try:
        feed = feedparser.parse(FEED_URL)
    except Exception as e:
        logger.error(f"Failed to fetch GOG RSS: {e}")
        return entries

    for entry in getattr(feed, "entries", []) or []:
        summary = getattr(entry, "summary", "")
        summary_text = re.sub(r"<[^>]+>", "", summary).strip() if summary else ""
        price = _extract_price(summary_text)
        entries.append(
            {
                "source": "gog",
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": _parse_date(getattr(entry, "published", None)),
                "summary": summary_text,
                "price": price,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "game_release",
                "language": "en",
                "region": "global",
            }
        )

    logger.info(f"Retrieved {len(entries)} GOG items")
    return entries


def save_gog(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No GOG entries to save")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "games")
    ensure_directories([output_dir])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"gog_{ts}.json")
    latest_json = os.path.join(output_dir, "gog_latest.json")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info("Saved GOG latest and timestamped outputs")


def main():
    logger.info("Starting GOG RSS ETL")
    entries = fetch_gog()
    if entries:
        save_gog(entries)
    logger.info("GOG ETL complete")


if __name__ == "__main__":
    main()
