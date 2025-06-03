# src/etl/courses/aws_training_etl.py
import os
import sys
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
import feedparser
import pandas as pd # type: ignore
from dateutil import parser as date_parser # For robust date parsing

# Ensure project root is on path
from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("AWSTrainingETL")

# RSS feed for AWS Training and Certification Blog
RSS_FEEDS: Dict[str, str] = {
    "aws_training_certification": "https://aws.amazon.com/blogs/training-and-certification/feed/"
}

def fetch_aws_training_feed() -> List[Dict[str, Any]]:
    """
    Fetches and parses RSS feed from the AWS Training and Certification blog.

    Returns:
        List of entries with metadata from the RSS feed.
    """
    entries: List[Dict[str, Any]] = []
    source_name = "aws_training_certification" # Should be the key from RSS_FEEDS
    url = RSS_FEEDS[source_name]

    logger.info(f"Fetching RSS feed from {source_name} at {url}")
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            logger.warning(f"Error parsing feed from {source_name}: {feed.bozo_exception}")
            return entries # Return empty list on feed parse error
    except Exception as e:
        logger.error(f"Could not fetch or parse feed from {source_name}: {e}")
        return entries # Return empty list on fetch error

    for entry in feed.entries:
        published_iso = ""
        published_raw = entry.get("published", "")
        if published_raw:
            try:
                # Use dateutil.parser for robust parsing
                dt_obj = date_parser.parse(published_raw)
                # Convert to UTC if naive, or ensure it's UTC then to ISO format
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                else:
                    dt_obj = dt_obj.astimezone(timezone.utc)
                published_iso = dt_obj.isoformat()
            except Exception as e:
                logger.warning(f"Could not parse publication date '{published_raw}' for entry '{entry.get('title')}': {e}. Storing raw value.")
                published_iso = published_raw # Store raw if parsing fails
        else:
            logger.warning(f"No publication date found for entry '{entry.get('title')}'. Storing empty string.")


        summary = entry.get("summary", entry.get("description", "")) # Get summary or fallback to description

        categories = []
        if hasattr(entry, 'tags') and entry.tags:
            categories = [tag.term for tag in entry.tags if hasattr(tag, 'term') and tag.term]

        if not categories:
            logger.info(f"No categories found for entry '{entry.get('title')}' or tags attribute missing/malformed.")


        entries.append({
            "source": source_name,
            "title": entry.get("title"),
            "link": entry.get("link"),
            "published": published_iso,
            "summary": summary,
            "categories": categories
        })

    logger.info(f"Retrieved {len(entries)} items from {source_name} RSS feed")
    return entries


def save_aws_training_entries(entries: List[Dict[str, Any]]) -> None:
    """
    Saves AWS Training blog entries to JSON and CSV in the data/courses directory.

    Args:
        entries: List of AWS Training blog entry dictionaries.
    """
    if not entries:
        logger.info("No entries to save for AWS Training. Skipping file generation.")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/courses")
    ensure_directories([output_dir]) # Ensures data/courses exists

    json_path = os.path.join(output_dir, "aws_training_updates.json")
    csv_path = os.path.join(output_dir, "aws_training_updates.csv")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(entries)} AWS Training entries to {json_path}")
    except Exception as e:
        logger.error(f"Error saving AWS Training entries to JSON at {json_path}: {e}")

    try:
        df = pd.DataFrame(entries)
        # Ensure all expected columns are present
        expected_columns = ["source", "title", "link", "published", "summary", "categories"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None # Add missing columns with None/NaN

        # Select columns in specific order for CSV
        df = df[expected_columns]

        df.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"Saved {len(entries)} AWS Training entries to {csv_path}")
    except ImportError:
        logger.warning("pandas library not found. Skipping CSV generation for AWS Training entries.")
    except Exception as e:
        logger.error(f"Error saving AWS Training entries to CSV at {csv_path}: {e}")


def main() -> None:
    """
    Main entry point for the AWS Training RSS ETL process.
    """
    logger.info("Starting AWS Training RSS ETL process")
    aws_entries = fetch_aws_training_feed()
    save_aws_training_entries(aws_entries)
    logger.info("AWS Training RSS ETL process completed")


if __name__ == "__main__":
    main()
```
