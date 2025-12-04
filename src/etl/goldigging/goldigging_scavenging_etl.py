import json
from datetime import timezone
from pathlib import Path
from typing import Any

import feedparser
import pandas as pd  # type: ignore
from dateutil import parser as date_parser

from src.utils.file_system import ensure_directories, get_project_root

# Local utilities
from src.utils.logging import get_logger

logger = get_logger("ScavengingETL")

# Constants
CONFIG_FILE = Path(__file__).parent / "scavenging.json"
BASE_OUTPUT_DIR = "data/scavenging"


def load_config() -> dict[str, Any]:
    """Load scavenging configuration JSON."""
    if not CONFIG_FILE.exists():
        logger.error(f"Configuration file not found: {CONFIG_FILE}")
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {CONFIG_FILE}: {e}")
        return {}


def parse_published(date_str: str) -> str:
    """Parse a date string to ISO-8601 in UTC, if possible."""
    if not date_str:
        return ""
    try:
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except Exception:
        return date_str  # Fallback to raw string


def fetch_rss_entries(url: str) -> list[dict[str, Any]]:
    """Fetch entries from an RSS/Atom feed URL."""
    items: list[dict[str, Any]] = []
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            logger.warning(f"Malformed feed at {url}: {feed.bozo_exception}")
        for entry in feed.entries:
            items.append(
                {
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "published": parse_published(entry.get("published", entry.get("pubDate", ""))),
                    "summary": entry.get("summary", entry.get("description", "")),
                }
            )
    except Exception as e:
        logger.error(f"Failed fetching {url}: {e}")
    return items


def process_category(category: str, sources: dict[str, dict[str, str]]) -> None:
    """Process all sources for a single category and save results."""
    all_entries: list[dict[str, Any]] = []
    for source_name, source_info in sources.items():
        if source_info.get("type") != "rss":
            logger.info(f"Skipping non-RSS source {source_name} of category {category}")
            continue
        url = source_info.get("url")
        if not url:
            logger.warning(f"Missing URL for source {source_name} in category {category}")
            continue
        logger.info(f"Fetching {category}/{source_name} -> {url}")
        entries = fetch_rss_entries(url)
        for item in entries:
            item.update(
                {
                    "category": category,
                    "source": source_name,
                }
            )
        all_entries.extend(entries)

        # Save per-source entries as well (optional useful for debugging)
        if entries:
            save_path = Path(get_project_root()) / BASE_OUTPUT_DIR / category
            ensure_directories([str(save_path)])
            json_file = save_path / f"{source_name}_entries.json"
            csv_file = save_path / f"{source_name}_entries.csv"
            _write_output(entries, json_file, csv_file)

    # Save aggregated category entries
    if all_entries:
        save_path = Path(get_project_root()) / BASE_OUTPUT_DIR
        ensure_directories([str(save_path)])
        json_file = save_path / f"{category}_rss_entries.json"
        csv_file = save_path / f"{category}_rss_entries.csv"
        _write_output(all_entries, json_file, csv_file)
        logger.info(f"Saved {len(all_entries)} combined entries for category '{category}'")
    else:
        logger.warning(f"No entries fetched for category '{category}'")


def _write_output(entries: list[dict[str, Any]], json_path: Path, csv_path: Path) -> None:
    """Helper to write JSON and CSV output."""
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error writing JSON to {json_path}: {e}")

    try:
        df = pd.DataFrame(entries)
        df.to_csv(csv_path, index=False, encoding="utf-8")
    except Exception as e:
        logger.error(f"Error writing CSV to {csv_path}: {e}")


def main() -> None:
    logger.info("Starting Scavenging RSS ETL")
    ensure_directories([BASE_OUTPUT_DIR])
    config = load_config()
    if not config:
        logger.error("No configuration loaded. Exiting.")
        return

    for category, sources in config.items():
        if not isinstance(sources, dict):
            logger.warning(f"Skipping malformed category entry: {category}")
            continue
        process_category(category, sources)

    logger.info("Scavenging RSS ETL completed")


if __name__ == "__main__":
    main()
