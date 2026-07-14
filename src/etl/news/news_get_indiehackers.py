#!/usr/bin/env python3
"""Indie Hackers-style ETL using Reddit data.

This module fetches entrepreneurship and indie hacker content from relevant subreddits
as an alternative to scraping Indie Hackers directly.

Usage:
    python src/etl/news/news_get_indiehackers_reddit.py

Output:
    - JSON file: data/indie_hackers/posts.json
    - CSV file: data/indie_hackers/posts.csv
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import requests

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("IndieHackersRedditETL")


def get_reddit_posts(subreddits: list[str] = None, limit: int = 25) -> list[dict[str, Any]]:
    """Fetch posts from entrepreneur/startup-focused subreddits.

    Args:
        subreddits: List of subreddits to fetch from
        limit: Number of posts to fetch per subreddit

    Returns:
        List of post dictionaries
    """
    if subreddits is None:
        subreddits = [
            "entrepreneur",
            "startups",
            "SaaS",
            "IndieHackers",
            "sideproject",
            "EntrepreneurRideAlong",
            "growmybusiness",
        ]

    all_posts = []
    session = requests.Session()
    session.headers.update({"User-Agent": "IndieHackersETL/1.0 (by /u/watchtower_etl)"})

    for subreddit in subreddits:
        try:
            logger.info(f"Fetching posts from r/{subreddit}")

            # Use Reddit's JSON API
            url = f"https://www.reddit.com/r/{subreddit}/hot.json"
            params = {"limit": limit}

            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if "data" in data and "children" in data["data"]:
                posts = data["data"]["children"]
                logger.info(f"Retrieved {len(posts)} posts from r/{subreddit}")

                for post_data in posts:
                    post = post_data.get("data", {})

                    # Skip removed/deleted posts
                    if post.get("removed_by_category") or post.get("title") == "[deleted]":
                        continue

                    # Create standardized post object
                    processed_post = {
                        "id": f"reddit_{post.get('id', '')}",
                        "title": post.get("title", ""),
                        "url": f"https://www.reddit.com{post.get('permalink', '')}",
                        "external_url": post.get("url", ""),
                        "author": post.get("author", ""),
                        "subreddit": subreddit,
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "created_utc": post.get("created_utc", 0),
                        "selftext": (post.get("selftext", "")[:500] + "..." if len(post.get("selftext", "")) > 500 else post.get("selftext", "")),
                        "is_self": post.get("is_self", False),
                        "over_18": post.get("over_18", False),
                        "locked": post.get("locked", False),
                        "stickied": post.get("stickied", False),
                        "flair_text": post.get("link_flair_text", ""),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "source": f"reddit_r_{subreddit}",
                    }

                    # Convert timestamp to readable format
                    if processed_post["created_utc"]:
                        try:
                            published_dt = datetime.fromtimestamp(processed_post["created_utc"], tz=timezone.utc)
                            processed_post["published_at"] = published_dt.isoformat()
                        except (ValueError, OSError):
                            processed_post["published_at"] = ""

                    all_posts.append(processed_post)

            # Rate limiting - Reddit asks for max 1 request per second
            time.sleep(1.1)

        except requests.RequestException as e:
            logger.error(f"Error fetching from r/{subreddit}: {e}")
            continue
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing data from r/{subreddit}: {e}")
            continue

    logger.info(f"Total posts fetched: {len(all_posts)}")
    return all_posts


def process_indie_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and standardize indie hacker posts.

    Args:
        posts: Raw post data

    Returns:
        Processed posts
    """
    logger.info(f"Processing {len(posts)} indie hacker posts")
    processed_posts = []

    for post in posts:
        try:
            # Create standardized format for dashboard
            processed_post = {
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "source": post.get("source", "reddit"),
                "published_at": post.get("published_at", ""),
                "description": (post.get("selftext", "")[:300] + "..." if len(post.get("selftext", "")) > 300 else post.get("selftext", "")),
                "metadata": {
                    "api_source": "reddit_indie_hackers",
                    "processed_at": datetime.now().isoformat(),
                    "author": post.get("author", ""),
                    "subreddit": post.get("subreddit", ""),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "flair_text": post.get("flair_text", ""),
                    "external_url": post.get("external_url", ""),
                    "is_self": post.get("is_self", False),
                },
            }

            processed_posts.append(processed_post)

        except Exception as e:
            logger.error(f"Error processing post: {e}")
            continue

    # Sort by score (upvotes) to get most popular content first
    processed_posts.sort(key=lambda x: x.get("metadata", {}).get("score", 0), reverse=True)

    logger.info(f"Successfully processed {len(processed_posts)} posts")
    return processed_posts


def main():
    """Main function to fetch and process indie hacker content."""
    logger.info("Starting Indie Hackers Reddit ETL process")

    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "indie_hackers")
        ensure_directories(["data/indie_hackers"])

        # Fetch posts from relevant subreddits
        posts = get_reddit_posts()

        if not posts:
            logger.warning("No posts retrieved, ETL process cannot continue")
            return

        # Process the posts
        processed_posts = process_indie_posts(posts)

        # Save to JSON file
        output_file = os.path.join(output_dir, "posts.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_posts, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "posts.csv")
        import pandas as pd

        pd.DataFrame(processed_posts).to_csv(csv_file, index=False, encoding="utf-8")
        logger.info(f"Saved CSV data to {csv_file}")

        logger.info(f"Saved {len(processed_posts)} processed posts to {output_file} and {csv_file}")

    except Exception as e:
        logger.error(f"Error in Indie Hackers Reddit ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Indie Hackers Reddit ETL script started")
    main()
    logger.info("Indie Hackers Reddit ETL script completed")
