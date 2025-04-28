import os
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Any

import feedparser

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("PodcastsETL")

# Define podcast RSS feeds: mapping a name to its URL
PODCAST_FEEDS: Dict[str, str] = {
    "Syntax": "https://feed.syntax.fm/",
    "SoftwareEngineeringDaily": "https://softwareengineeringdaily.com/feed/podcast/",
    "Changelog": "https://changelog.fm/rss",
    "TalkPython": "https://talkpython.fm/subscribe/rss"
}

def get_podcast_episodes(
    max_retries: int = 3, retry_delay: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetches latest podcast episodes from defined RSS feeds.

    Args:
        max_retries: Maximum number of retry attempts on connection failure.
        retry_delay: Delay in seconds between retry attempts.

    Returns:
        List of podcast episode dictionaries.
    """
    episodes: List[Dict[str, Any]] = []
    for source, rss_url in PODCAST_FEEDS.items():
        logger.info(f"Processing podcast feed {source}: {rss_url}")
        for attempt in range(max_retries):
            try:
                feed = feedparser.parse(rss_url)
                if not feed.entries:
                    logger.warning(f"No entries found in podcast feed {rss_url}")
                    break
                for entry in feed.entries:
                    episode = {
                        "title": getattr(entry, "title", ""),
                        "url": getattr(entry, "link", ""),
                        "published_at": getattr(entry, "published", ""),
                        "source": source,
                        "episode_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                        "feed_source": rss_url
                    }
                    episodes.append(episode)
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed for {rss_url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Error fetching podcast feed {rss_url} after {max_retries} attempts: {e}")
    # Deduplicate based on episode_id and title
    unique: Dict[str, Dict[str, Any]] = {}
    seen_titles = set()
    for ep in episodes:
        identifier = ep.get("episode_id")
        title = ep.get("title", "").strip()
        if title and title not in seen_titles and identifier not in unique:
            seen_titles.add(title)
            unique[identifier] = ep
    return list(unique.values())

def process_podcast_episodes(
    episodes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Process and transform podcast episodes into a standardized format.

    Args:
        episodes: List of raw episode dictionaries.

    Returns:
        List of processed episode dictionaries.
    """
    logger.info(f"Processing {len(episodes)} podcast episodes")
    processed: List[Dict[str, Any]] = []
    for ep in episodes:
        processed_ep: Dict[str, Any] = {
            "title": ep.get("title", ""),
            "url": ep.get("url", ""),
            "source": ep.get("source", ""),
            "published_at": ep.get("published_at", ""),
            "metadata": {
                "api_source": "rss",
                "processed_at": datetime.now().isoformat(),
                "episode_id": ep.get("episode_id", ""),
                "feed_source": ep.get("feed_source", "")
            },
        }
        processed.append(processed_ep)
    logger.info(f"Successfully processed {len(processed)} episodes")
    return processed

def main():
    """Main entry point for the podcasts ETL process."""
    logger.info("Starting Podcasts ETL process")
    try:
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/podcasts")
        ensure_directories(["data/podcasts"])

        episodes = get_podcast_episodes()
        if not episodes:
            logger.warning("No podcast episodes retrieved, ETL process will exit")
            return

        processed = process_podcast_episodes(episodes)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(output_dir, f"podcasts_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(processed, f, indent=2)
        latest_json = os.path.join(output_dir, "podcasts_latest.json")
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(processed, f, indent=2)

        # Also save CSV versions
        import pandas as pd
        df = pd.DataFrame(processed)
        csv_file = os.path.join(output_dir, f"podcasts_{timestamp}.csv")
        df.to_csv(csv_file, index=False)
        latest_csv = os.path.join(output_dir, "podcasts_latest.csv")
        df.to_csv(latest_csv, index=False)

        logger.info(f"Saved {len(processed)} episodes to {json_file} and {csv_file}")
    except Exception as e:
        logger.error(f"Error in Podcasts ETL process: {e}", exc_info=True)

if __name__ == "__main__":
    main()
