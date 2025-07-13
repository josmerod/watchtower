"""Reddit r/artificial ETL Module.

Fetches latest posts from r/artificial RSS feed.

Saves to JSON in data/reddit_ai/.
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import time

import feedparser
import requests

# Add the project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger



logger = get_logger("RedditAIETL")

RSS_URL = "https://www.reddit.com/r/artificial.rss"

def fetch_reddit_ai_posts() -> List[Dict[str, Any]]:
    """Fetch posts from r/artificial RSS feed."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(RSS_URL, headers=headers)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch RSS: {e}")
        return []
    posts = []
    for entry in feed.entries:
        post = {
            "title": entry.get("title", "No title"),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "author": entry.get("author", "Anonymous")
        }
        if post["published"] and hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                # Fix type issues by properly accessing the time tuple elements
                time_tuple = entry.published_parsed
                if isinstance(time_tuple, time.struct_time):
                    post["published"] = datetime(
                        time_tuple.tm_year,
                        time_tuple.tm_mon,
                        time_tuple.tm_mday,
                        time_tuple.tm_hour,
                        time_tuple.tm_min,
                        time_tuple.tm_sec
                    ).isoformat()
                else:
                    # Fallback for non-struct_time objects
                    post["published"] = ""
            except (TypeError, IndexError, ValueError, AttributeError):
                post["published"] = ""
        posts.append(post)
    return posts

def main():
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/reddit_ai")
    ensure_directories(["data/reddit_ai"])

    posts = fetch_reddit_ai_posts()
    
    if not posts:
        logger.warning("No posts fetched")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_file = os.path.join(output_dir, f"reddit_ai_{timestamp}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)

    latest_json = os.path.join(output_dir, "reddit_ai_latest.json")
    if os.path.exists(latest_json):
        os.remove(latest_json)
    os.symlink(json_file, latest_json)

    logger.info(f"Fetched {len(posts)} posts")

if __name__ == "__main__":
    main()