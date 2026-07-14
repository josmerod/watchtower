"""Security Intelligence RSS ETL.

Fetches cybersecurity news and advisories from major security sources.
Outputs to data/intelligence/ for the intelligence category.

Sources: CISA Advisories, The Hacker News, BleepingComputer, Krebs on Security
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("SecurityFeedsETL")

FEEDS: dict[str, str] = {
    "cisa_advisories": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
    "the_hacker_news": "https://feeds.feedburner.com/TheHackersNews",
    "bleepingcomputer": "https://www.bleepingcomputer.com/feed/",
    "krebs_security": "https://krebsonsecurity.com/feed/",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WatchtowerBot/1.0; +https://josmerod.es)"}


def _parse_date(date_str: str) -> str:
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(date_str).isoformat()
    except ValueError:
        pass
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
    ]:
        try:
            return datetime.strptime(date_str, fmt).isoformat()
        except ValueError:
            continue
    return date_str


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()[:500]


def _extract_severity(text: str) -> str | None:
    """Extract severity level from security advisory text."""
    text_lower = text.lower()
    for level in ["critical", "high", "medium", "low"]:
        if level in text_lower:
            return level.capitalize()
    return None


def fetch_feeds() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for source, url in FEEDS.items():
        logger.info(f"Fetching {source} from {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            for entry in feed.entries:
                published = _parse_date(entry.get("published", ""))
                title = entry.get("title", "")
                summary = _strip_html(str(entry.get("summary", "") or entry.get("description", "")))
                full_text = f"{title} {summary}"
                severity = _extract_severity(full_text)

                categories = []
                if hasattr(entry, "tags"):
                    categories = [t.term for t in entry.tags if hasattr(t, "term")]

                entries.append(
                    {
                        "source": f"security_{source}",
                        "title": title,
                        "link": entry.get("link", ""),
                        "published": published,
                        "summary": summary,
                        "categories": categories,
                        "severity": severity,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "language": "en",
                        "content_type": "security_advisory",
                    }
                )

        except Exception as e:
            logger.error(f"Failed to fetch {source}: {e}")
            continue

    logger.info(f"Retrieved {len(entries)} items from security feeds")
    return entries


def save_entries(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No entries to save.")
        return

    output_dir = os.path.join(get_project_root(), "data", "security_feeds")
    ensure_directories([output_dir])

    latest = os.path.join(output_dir, "security_feeds_latest.json")
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(entries)} entries to {latest}")


def main():
    logger.info("Starting Security Feeds RSS ETL")
    entries = fetch_feeds()
    save_entries(entries)
    logger.info(f"Done. {len(entries)} items.")


if __name__ == "__main__":
    main()
