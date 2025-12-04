# src/etl/news/news_get_media_rss.py
import json
import os
from datetime import datetime
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root

# Ensure project root is on path
from src.utils.logging import get_logger

logger = get_logger("MediaRSSETL")

# Mapping of source names to RSS feed URLs
RSS_FEEDS: dict[str, str] = {
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/index",
    "the_verge": "https://www.theverge.com/rss/index.xml",
    "hackernoon": "https://hackernoon.com/feed",
    "google_cloud_blog": "https://cloudblog.withgoogle.com/rss/",
}


def fetch_media_feeds() -> list[dict[str, Any]]:
    """Fetches and parses RSS feeds from specialized media sources.

    Returns:
        List of entries with metadata from each RSS feed.
    """
    entries: list[dict[str, Any]] = []

    for source, url in RSS_FEEDS.items():
        logger.info(f"Fetching RSS feed from {source} at {url}")
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                logger.warning(f"Error parsing feed from {source}: {feed.bozo_exception}")
                continue
        except Exception as e:
            logger.error(f"Could not fetch or parse feed from {source}: {e}")
            continue

        for entry in feed.entries:
            published_raw = entry.get("published", "")
            try:
                # Try multiple date formats in order of preference
                # 1. ISO 8601 format (used by The Verge and modern feeds)
                if "T" in published_raw and ("+" in published_raw or "-" in published_raw[-6:]):
                    try:
                        # Handle ISO 8601 with timezone offset (e.g., 2025-08-15T13:30:00-04:00)
                        published = datetime.fromisoformat(published_raw).isoformat()
                    except ValueError:
                        # Try ISO 8601 with Z timezone
                        if published_raw.endswith("Z"):
                            published_raw_utc = published_raw[:-1] + "+00:00"
                            published = datetime.fromisoformat(published_raw_utc).isoformat()
                        else:
                            raise ValueError(f"Could not parse ISO format: {published_raw}")

                # 2. RFC 2822 format with timezone (traditional RSS format)
                elif any(day in published_raw for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                    try:
                        published = datetime.strptime(published_raw, "%a, %d %b %Y %H:%M:%S %z").isoformat()
                    except ValueError:
                        published = datetime.strptime(published_raw, "%a, %d %b %Y %H:%M:%S %Z").isoformat()

                # 3. Try other common formats
                else:
                    # Try simple ISO format without timezone
                    try:
                        published = datetime.fromisoformat(published_raw).isoformat()
                    except ValueError:
                        # Try parsing as timestamp
                        try:
                            published = datetime.fromtimestamp(float(published_raw)).isoformat()
                        except (ValueError, TypeError):
                            raise ValueError(f"Unknown date format: {published_raw}")

            except Exception as e:
                logger.warning(f"Could not parse publication date '{published_raw}' for entry '{entry.get('title')}' from {source}: {e}. Using raw value.")
                published = published_raw

            entry_data = {
                "source": source,
                "title": entry.get("title"),
                "link": entry.get("link"),
                "published": published,
                "categories": [],  # Default to empty list
            }

            if source == "google_cloud_blog":
                categories = [term.term for term in entry.get("tags", []) if term.term] if entry.get("tags") else []
                entry_data["categories"] = categories

                # Filter for 'training and certifications'
                found_category = False
                for cat in categories:
                    if "training and certifications" in cat.lower():
                        found_category = True
                        break

                if found_category:
                    logger.info(f"Entry '{entry.get('title')}' from {source} included due to category match.")
                    entries.append(entry_data)
                else:
                    logger.info(f"Entry '{entry.get('title')}' from {source} skipped, no matching category. Categories: {categories}")
            else:
                entries.append(entry_data)

    logger.info(f"Retrieved {len(entries)} items from media RSS feeds")
    return entries


def save_media_entries(entries: list[dict[str, Any]], source_type: str) -> None:
    """Saves media RSS feed entries to JSON and CSV in the data/news directory,
    with filenames based on the source_type.

    Args:
        entries: List of media RSS entry dictionaries.
        source_type: String identifying the source type (e.g., 'media_general', 'google_cloud_blog').
    """
    if not entries:
        logger.info(f"No entries to save for source type '{source_type}'. Skipping file generation.")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/news")
    ensure_directories(["data/news"])  # Ensures data/news exists

    base_filename = source_type.lower().replace(" ", "_")
    json_path = os.path.join(output_dir, f"{base_filename}.json")
    csv_path = os.path.join(output_dir, f"{base_filename}.csv")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        logger.info(f"Saved {len(entries)} entries for '{source_type}' to {json_path}")
    except Exception as e:
        logger.error(f"Error saving entries for '{source_type}' to JSON at {json_path}: {e}")

    try:
        import pandas as pd  # type: ignore

        df = pd.DataFrame(entries)
        # Ensure all columns expected by potential consumers are present, even if empty for some sources
        expected_columns = ["source", "title", "link", "published", "categories"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None  # Add missing columns with None/NaN
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved {len(entries)} entries for '{source_type}' to {csv_path}")
    except ImportError:
        logger.warning("pandas library not found. Skipping CSV generation.")
    except Exception as e:
        logger.error(f"Error saving entries for '{source_type}' to CSV at {csv_path}: {e}")


def main() -> None:
    """Main entry point for the media RSS ETL process."""
    all_entries = fetch_media_feeds()

    google_cloud_blog_entries = [entry for entry in all_entries if entry["source"] == "google_cloud_blog"]
    other_media_entries = [entry for entry in all_entries if entry["source"] != "google_cloud_blog"]

    save_media_entries(google_cloud_blog_entries, "google_cloud_blog")
    save_media_entries(other_media_entries, "media_general")


if __name__ == "__main__":
    logger.info("Starting Media RSS ETL process")
    main()
    logger.info("Media RSS ETL process completed")
