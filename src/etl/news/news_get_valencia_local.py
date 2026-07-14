"""Valencia Local Feeds ETL.

Fetches local news and transport updates for Valencia/Burjassot area.
Outputs to data/valencia_local/ for the Valencia Events tab enrichment.

Sources: 20minutos Comunidad Valenciana, Metro Valencia service alerts
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

logger = get_logger("ValenciaLocalETL")

FEEDS: dict[str, str] = {
    "20minutos_cv": "https://www.20minutos.es/rss/comunidad-valenciana/",
    "metro_valencia": "https://www.metrovalencia.es/feed/",
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
            # Some local sites (e.g. metrovalencia.es) have broken SSL certs
            verify_ssl = "metrovalencia" not in source
            resp = requests.get(url, headers=HEADERS, timeout=30, verify=verify_ssl)
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
                        "source": f"valencia_{source}",
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": published,
                        "summary": summary,
                        "categories": categories,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "language": "es",
                        "region": "valencia",
                        "content_type": "local_news",
                    }
                )

        except Exception as e:
            logger.error(f"Failed to fetch {source}: {e}")
            continue

    logger.info(f"Retrieved {len(entries)} items from Valencia local feeds")
    return entries


def save_entries(entries: list[dict[str, Any]]) -> None:
    if not entries:
        logger.info("No entries to save.")
        return

    output_dir = os.path.join(get_project_root(), "data", "valencia_local")
    ensure_directories([output_dir])

    latest = os.path.join(output_dir, "valencia_local_latest.json")
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(entries)} entries to {latest}")


def main():
    logger.info("Starting Valencia Local Feeds ETL")
    entries = fetch_feeds()
    save_entries(entries)
    logger.info(f"Done. {len(entries)} items.")


if __name__ == "__main__":
    main()
