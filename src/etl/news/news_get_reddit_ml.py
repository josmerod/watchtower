"""Reddit r/MachineLearning ETL Module.

Fetches latest posts from r/MachineLearning RSS feed.

Saves to JSON and CSV in data/reddit_ml/.
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("RedditMLETL")

RSS_URL = "https://www.reddit.com/r/MachineLearning/.rss"

def fetch_reddit_ml_posts() -> List[Dict[str, Any]]:
    """Fetch posts from r/MachineLearning RSS."""
    feed = feedparser.parse(RSS_URL)
    posts = []
    for entry in feed.entries:
        post = {
            "title": entry.get("title", "No title"),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "author": entry.get("author", "Anonymous")
        }
        # Parse date if available
        if post["published"]:
            try:
                post["published"] = datetime(*entry.published_parsed[:6]).isoformat()
            except:
                post["published"] = ""
        posts.append(post)
    return posts

def main():
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/reddit_ml")
    ensure_directories(["data/reddit_ml"])

    posts = fetch_reddit_ml_posts()
    
    if not posts:
        logger.warning("No posts fetched")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_file = os.path.join(output_dir, f"reddit_ml_{timestamp}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)

    # Create latest symlink
    latest_json = os.path.join(output_dir, "reddit_ml_latest.json")
    if os.path.exists(latest_json):
        os.remove(latest_json)
    os.symlink(json_file, latest_json)

    logger.info(f"Fetched {len(posts)} posts")

if __name__ == "__main__":
    main() 