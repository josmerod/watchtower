"""Unified Reddit ETL Module.

Centralized ETL for fetching posts from multiple relevant subreddits.
Supports both RSS feeds and JSON endpoints with comprehensive error handling.
"""

import json
import os
import shutil
import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("RedditUnifiedETL")

# Extended list of relevant subreddits for tech/AI/ML/programming content
SUBREDDITS_CONFIG = {
    # AI/ML Focus
    "MachineLearning": {"type": "rss", "category": "ai_ml"},
    "artificial": {"type": "rss", "category": "ai_ml"},
    "deeplearning": {"type": "json", "category": "ai_ml"},
    "MLQuestions": {"type": "json", "category": "ai_ml"},
    "datascience": {"type": "json", "category": "ai_ml"},
    "statistics": {"type": "json", "category": "ai_ml"},
    "LearnMachineLearning": {"type": "json", "category": "ai_ml"},
    "ArtificialIntelligence": {"type": "json", "category": "ai_ml"},
    "ChatGPT": {"type": "json", "category": "ai_ml"},
    "OpenAI": {"type": "json", "category": "ai_ml"},
    # Programming/Development
    "programming": {"type": "json", "category": "programming"},
    "coding": {"type": "json", "category": "programming"},
    "webdev": {"type": "json", "category": "programming"},
    "Python": {"type": "json", "category": "programming"},
    "javascript": {"type": "json", "category": "programming"},
    "reactjs": {"type": "json", "category": "programming"},
    "node": {"type": "json", "category": "programming"},
    "golang": {"type": "json", "category": "programming"},
    "rust": {"type": "json", "category": "programming"},
    "cpp": {"type": "json", "category": "programming"},
    "java": {"type": "json", "category": "programming"},
    "learnpython": {"type": "json", "category": "programming"},
    # Tech/Business
    "technology": {"type": "json", "category": "tech"},
    "tech": {"type": "json", "category": "tech"},
    "startups": {"type": "json", "category": "tech"},
    "entrepreneur": {"type": "json", "category": "tech"},
    "SideProject": {"type": "json", "category": "tech"},
    "ProductHunt": {"type": "json", "category": "tech"},
    "Futurology": {"type": "json", "category": "tech"},
    # DevOps/Infrastructure
    "devops": {"type": "json", "category": "devops"},
    "docker": {"type": "json", "category": "devops"},
    "kubernetes": {"type": "json", "category": "devops"},
    "aws": {"type": "json", "category": "devops"},
    "sysadmin": {"type": "json", "category": "devops"},
    "homelab": {"type": "json", "category": "devops"},
}


def fetch_subreddit_rss(subreddit: str) -> list[dict[str, Any]]:
    """Fetch posts from subreddit RSS feed."""
    rss_url = f"https://www.reddit.com/r/{subreddit}/.rss"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    try:
        response = requests.get(rss_url, headers=headers, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        posts = []
        for entry in feed.entries:
            post = {
                "subreddit": subreddit,
                "title": entry.get("title", "No title"),
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "author": entry.get("author", "Anonymous"),
                "fetch_method": "rss",
            }

            # Parse RSS date
            if post["published"] and hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    time_tuple = entry.published_parsed
                    if isinstance(time_tuple, time.struct_time):
                        post["published"] = datetime(
                            time_tuple.tm_year,
                            time_tuple.tm_mon,
                            time_tuple.tm_mday,
                            time_tuple.tm_hour,
                            time_tuple.tm_min,
                            time_tuple.tm_sec,
                        ).isoformat()
                except (TypeError, IndexError, ValueError, AttributeError):
                    post["published"] = ""

            posts.append(post)

        logger.info(f"Fetched {len(posts)} posts from r/{subreddit} via RSS")
        return posts

    except Exception as e:
        logger.error(f"Error fetching r/{subreddit} via RSS: {e}")
        return []


def fetch_subreddit_json(subreddit: str, limit: int = 25) -> list[dict[str, Any]]:
    """Fetch posts from subreddit JSON endpoint."""
    json_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {"User-Agent": "watchtower-bot/1.0"}

    try:
        response = requests.get(json_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            post = {
                "subreddit": subreddit,
                "title": post_data.get("title", "No title"),
                "url": post_data.get("url", ""),
                "published": datetime.fromtimestamp(post_data.get("created_utc", 0), tz=timezone.utc).isoformat(),
                "score": post_data.get("score", 0),
                "num_comments": post_data.get("num_comments", 0),
                "author": post_data.get("author", "Anonymous"),
                "selftext": post_data.get("selftext", ""),
                "fetch_method": "json",
            }
            posts.append(post)

        logger.info(f"Fetched {len(posts)} posts from r/{subreddit} via JSON")
        return posts

    except Exception as e:
        logger.error(f"Error fetching r/{subreddit} via JSON: {e}")
        return []


def fetch_all_subreddits() -> dict[str, list[dict[str, Any]]]:
    """Fetch posts from all configured subreddits."""
    all_posts = {}

    for subreddit, config in SUBREDDITS_CONFIG.items():
        try:
            if config["type"] == "rss":
                posts = fetch_subreddit_rss(subreddit)
            else:  # json
                posts = fetch_subreddit_json(subreddit)

            # Add category info to each post
            for post in posts:
                post["category"] = config["category"]

            all_posts[subreddit] = posts

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error processing r/{subreddit}: {e}")
            all_posts[subreddit] = []

    return all_posts


def save_reddit_data(all_posts: dict[str, list[dict[str, Any]]]) -> None:
    """Save Reddit data to organized JSON files."""
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/reddit_unified")
    ensure_directories(["data/reddit_unified"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save individual subreddit files
    for subreddit, posts in all_posts.items():
        if posts:
            subreddit_file = os.path.join(output_dir, f"{subreddit}_{timestamp}.json")
            with open(subreddit_file, "w", encoding="utf-8") as f:
                json.dump(posts, f, indent=2)

    # Save combined file
    combined_posts = []
    for posts in all_posts.values():
        combined_posts.extend(posts)

    combined_file = os.path.join(output_dir, f"reddit_unified_{timestamp}.json")
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined_posts, f, indent=2)

    # Create latest copy (Windows compatible)
    latest_combined = os.path.join(output_dir, "reddit_unified_latest.json")
    shutil.copy2(combined_file, latest_combined)

    # Save by category
    categories = {}
    for posts in all_posts.values():
        for post in posts:
            category = post.get("category", "uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(post)

    for category, posts in categories.items():
        category_file = os.path.join(output_dir, f"reddit_{category}_{timestamp}.json")
        with open(category_file, "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=2)

        # Create latest copy for category (Windows compatible)
        latest_category = os.path.join(output_dir, f"reddit_{category}_latest.json")
        shutil.copy2(category_file, latest_category)

    total_posts = len(combined_posts)
    logger.info(f"Saved {total_posts} total posts across {len(all_posts)} subreddits")
    logger.info(f"Categories: {list(categories.keys())}")


def main():
    """Main ETL execution."""
    logger.info("Starting unified Reddit ETL process")

    all_posts = fetch_all_subreddits()
    save_reddit_data(all_posts)

    logger.info("Unified Reddit ETL process completed")


if __name__ == "__main__":
    main()
