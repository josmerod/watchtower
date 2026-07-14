"""Cloud Provider Updates RSS ETL.

Fetches new service announcements and updates from major cloud providers.
Outputs to data/cloud_updates/ for a new cloud-updates category.

Sources: AWS What's New, Google Cloud Blog, CNCF Blog
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

logger = get_logger("CloudUpdatesETL")

FEEDS: dict[str, str] = {
    "aws_whats_new": "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
    "google_cloud_blog": "https://cloud.google.com/blog/products/rss/",
    "cncc_blog": "https://www.cncf.io/feed/",
    "github_blog": "https://github.blog/feed/",
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
                summary = _strip_html(str(entry.get("summary", "") or entry.get("description", "")))
                categories = []
                if hasattr(entry, "tags"):
                    categories = [t.term for t in entry.tags if hasattr(t, "term")]

                entries.append(
                    {
                        "source": f"cloud_{source}",
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": published,
                        "summary": summary,
                        "categories": categories,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "language": "en",
                        "content_type": "cloud_update",
                    }
                )

        except Exception as e:
            logger.error(f"Failed to fetch {source}: {e}")
            continue

    logger.info(f"Retrieved {len(entries)} items from cloud feeds")
    return entries


def save_entries(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No entries to save.")
        return

    output_dir = os.path.join(get_project_root(), "data", "cloud_updates")
    ensure_directories([output_dir])

    latest = os.path.join(output_dir, "cloud_updates_latest.json")
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(entries)} entries to {latest}")


def main():
    logger.info("Starting Cloud Updates RSS ETL")
    entries = fetch_feeds()
    save_entries(entries)
    logger.info(f"Done. {len(entries)} items.")


if __name__ == "__main__":
    main()
