# src/etl/courses/azure_training_etl.py
import json
import os
from datetime import timezone
from typing import Any

import feedparser
import pandas as pd  # type: ignore
from dateutil import parser as date_parser  # For robust date parsing

from utils.file_system import ensure_directories, get_project_root

# Ensure project root is on path
from utils.logging import get_logger

logger = get_logger("AzureTrainingETL")  # Updated logger name

# RSS feed for Azure Microsoft Learn Blog
RSS_FEEDS: dict[str, str] = {
    "azure_microsoft_learn_blog": "https://techcommunity.microsoft.com/t5/s/gxcuf89792/rss/board?board.id=MicrosoftLearnBlog"
}


def fetch_azure_training_feed() -> list[dict[str, Any]]:  # Renamed function
    """Fetches and parses RSS feed from the Azure Microsoft Learn blog.

    Returns:
        List of entries with metadata from the RSS feed.
    """
    entries: list[dict[str, Any]] = []
    source_name = "azure_microsoft_learn_blog"  # Updated source name
    url = RSS_FEEDS[source_name]

    logger.info(f"Fetching RSS feed from {source_name} at {url}")
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            logger.warning(
                f"Error parsing feed from {source_name}: {feed.bozo_exception}"
            )
            return entries
    except Exception as e:
        logger.error(f"Could not fetch or parse feed from {source_name}: {e}")
        return entries

    for entry in feed.entries:
        published_iso = ""
        published_raw = entry.get("published", "")
        if published_raw:
            try:
                dt_obj = date_parser.parse(published_raw)
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                else:
                    dt_obj = dt_obj.astimezone(timezone.utc)
                published_iso = dt_obj.isoformat()
            except Exception as e:
                logger.warning(
                    f"Could not parse publication date '{published_raw}' for entry '{entry.get('title')}': {e}. Storing raw value."
                )
                published_iso = published_raw
        else:
            logger.warning(
                f"No publication date found for entry '{entry.get('title')}'. Storing empty string."
            )

        summary = entry.get("summary", entry.get("description", ""))

        categories = []
        if hasattr(entry, "tags") and entry.tags:
            categories = [
                tag.term for tag in entry.tags if hasattr(tag, "term") and tag.term
            ]

        if not categories:  # Log if categories are empty, even if tags attribute exists but has no actual terms
            logger.info(
                f"No valid categories extracted for entry '{entry.get('title')}'. Tags attribute might be empty or malformed."
            )

        entries.append(
            {
                "source": source_name,  # Ensure this uses the updated source_name
                "title": entry.get("title"),
                "link": entry.get("link"),
                "published": published_iso,
                "summary": summary,
                "categories": categories,
            }
        )

    logger.info(f"Retrieved {len(entries)} items from {source_name} RSS feed")
    return entries


def save_azure_training_entries(
    entries: list[dict[str, Any]],
) -> None:  # Renamed function
    """Saves Azure Training blog entries to JSON and CSV in the data/courses directory.

    Args:
        entries: List of Azure Training blog entry dictionaries.
    """
    if not entries:
        logger.info("No entries to save for Azure Training. Skipping file generation.")
        return

    project_root = get_project_root()
    output_dir = os.path.join(
        project_root, "data/courses"
    )  # Directory remains data/courses
    ensure_directories([output_dir])

    json_path = os.path.join(
        output_dir, "azure_training_updates.json"
    )  # Updated filename
    csv_path = os.path.join(
        output_dir, "azure_training_updates.csv"
    )  # Updated filename

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(entries)} Azure Training entries to {json_path}")
    except Exception as e:
        logger.error(f"Error saving Azure Training entries to JSON at {json_path}: {e}")

    try:
        df = pd.DataFrame(entries)
        expected_columns = [
            "source",
            "title",
            "link",
            "published",
            "summary",
            "categories",
        ]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None

        df = df[expected_columns]

        df.to_csv(csv_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(entries)} Azure Training entries to {csv_path}")
    except ImportError:
        logger.warning(
            "pandas library not found. Skipping CSV generation for Azure Training entries."
        )
    except Exception as e:
        logger.error(f"Error saving Azure Training entries to CSV at {csv_path}: {e}")


def main() -> None:
    """Main entry point for the Azure Training RSS ETL process."""
    logger.info("Starting Azure Training RSS ETL process")  # Updated log message
    azure_entries = fetch_azure_training_feed()  # Updated function call
    save_azure_training_entries(azure_entries)  # Updated function call
    logger.info("Azure Training RSS ETL process completed")  # Updated log message


if __name__ == "__main__":
    main()
