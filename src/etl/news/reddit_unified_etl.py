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

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("RedditUnifiedETL")
STATE_FILE = os.path.join(get_project_root(), "data/reddit_unified/etl_state.json")

# Extended list of relevant subreddits for tech/AI/ML/programming content.
# All RSS since 2026-08-27: reddit's non-OAuth JSON API (hot.json) started
# returning 403 from both the home and Unraid server IPs; the RSS feeds work
# from both. The JSON fetcher is kept for a future OAuth migration.
SUBREDDITS_CONFIG = {
    # AI/ML Focus
    "MachineLearning": {"type": "rss", "category": "ai_ml"},
    "artificial": {"type": "rss", "category": "ai_ml"},
    "deeplearning": {"type": "rss", "category": "ai_ml"},
    "MLQuestions": {"type": "rss", "category": "ai_ml"},
    "datascience": {"type": "rss", "category": "ai_ml"},
    "statistics": {"type": "rss", "category": "ai_ml"},
    "LearnMachineLearning": {"type": "rss", "category": "ai_ml"},
    "LocalLLaMA": {"type": "rss", "category": "ai_ml"},
    "ChatGPT": {"type": "rss", "category": "ai_ml"},
    "OpenAI": {"type": "rss", "category": "ai_ml"},
    # Programming/Development
    "programming": {"type": "rss", "category": "programming"},
    "coding": {"type": "rss", "category": "programming"},
    "webdev": {"type": "rss", "category": "programming"},
    "Python": {"type": "rss", "category": "programming"},
    "javascript": {"type": "rss", "category": "programming"},
    "reactjs": {"type": "rss", "category": "programming"},
    "node": {"type": "rss", "category": "programming"},
    "golang": {"type": "rss", "category": "programming"},
    "rust": {"type": "rss", "category": "programming"},
    "cpp": {"type": "rss", "category": "programming"},
    "java": {"type": "rss", "category": "programming"},
    "learnpython": {"type": "rss", "category": "programming"},
    # Tech/Business
    "technology": {"type": "rss", "category": "tech"},
    "tech": {"type": "rss", "category": "tech"},
    "startups": {"type": "rss", "category": "tech"},
    "entrepreneur": {"type": "rss", "category": "tech"},
    "SideProject": {"type": "rss", "category": "tech"},
    "Futurology": {"type": "rss", "category": "tech"},
    # DevOps/Infrastructure
    "devops": {"type": "rss", "category": "devops"},
    "docker": {"type": "rss", "category": "devops"},
    "kubernetes": {"type": "rss", "category": "devops"},
    "aws": {"type": "rss", "category": "devops"},
    "sysadmin": {"type": "rss", "category": "devops"},
    "homelab": {"type": "rss", "category": "devops"},
    # Self-Hosting (spec 13: community pulse for the Tech Radar tab).
    # RSS type: reddit's JSON API 403-blocks some client IPs; the RSS feed
    # works from the same networks.
    "SelfHosted": {"type": "rss", "category": "selfhosting"},
    # News Aggregators
    "hypeurls": {"type": "rss", "category": "news", "pagination": True},
    # Open Source (Mapped to Knowledge Garden Open Source Tab)
    "coolgithubprojects": {"type": "rss", "category": "opensource"},
    "opensource": {"type": "rss", "category": "opensource"},
    "github": {"type": "rss", "category": "opensource"},
}


def load_state() -> dict:
    """Load the ETL state (last processed IDs)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state file: {e}")
    return {}


def save_state(state: dict) -> None:
    """Save the ETL state."""
    try:
        ensure_directories([os.path.dirname(STATE_FILE)])
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state file: {e}")


def fetch_subreddit_rss(subreddit: str, stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Fetch posts from subreddit RSS feed.

    Args:
        subreddit: Subreddit name without the r/ prefix.
        stats: Optional mutable dict; sets ``stats["rate_limited"]`` when the
            fetch hits a 429 so the caller can slow down its feed pacing.
    """
    rss_url = f"https://www.reddit.com/r/{subreddit}/.rss"
    headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}

    try:
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                # Reddit RSS rate-limits bursts; back off once and retry
                if stats is not None:
                    stats["rate_limited"] = True
                logger.warning(f"r/{subreddit} RSS rate-limited (429) — backing off 60s")
                time.sleep(60)
                response = requests.get(rss_url, headers=headers, timeout=10)
                response.raise_for_status()
            else:
                raise
        feed = feedparser.parse(response.content)

        posts = []
        for entry in feed.entries:
            post = {
                "subreddit": subreddit,
                "title": entry.get("title", "No title"),
                "url": entry.get("link", ""),
                "published": entry.get("published", "") or entry.get("updated", ""),
                "summary": entry.get("summary", ""),
                "author": entry.get("author", "Anonymous"),
                "fetch_method": "rss",
            }

            # Parse RSS/atom date (atom feeds expose <updated> instead of <published>)
            parsed_date = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if post["published"] and isinstance(parsed_date, time.struct_time):
                try:
                    post["published"] = datetime(*parsed_date[:6], tzinfo=timezone.utc).isoformat()
                except (TypeError, IndexError, ValueError, AttributeError):
                    post["published"] = ""

            posts.append(post)

        logger.info(f"Fetched {len(posts)} posts from r/{subreddit} via RSS")
        return posts

    except Exception as e:
        logger.error(f"Error fetching r/{subreddit} via RSS: {e}")
        return []


def fetch_subreddit_json(subreddit: str, limit: int = 25, use_pagination: bool = False, last_known_id: str | None = None) -> list[dict[str, Any]]:
    """Fetch posts from subreddit JSON endpoint, optionally with pagination."""
    headers = {"User-Agent": "web:watchtower.etl:v0.1 (by /u/watchtower)"}
    base_url = f"https://www.reddit.com/r/{subreddit}/hot.json"

    posts = []
    after = None
    fetched_count = 0
    max_fetch_limit = 100 if use_pagination else limit  # Safety cap for pagination

    while True:
        try:
            params = {"limit": limit}
            if after:
                params["after"] = after

            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            children = data.get("data", {}).get("children", [])
            if not children:
                break

            batch_posts = []
            stop_fetching = False

            for child in children:
                post_data = child.get("data", {})
                post_id = post_data.get("name")  # format: t3_xxxxx

                # Incremental stop condition
                if use_pagination and last_known_id and post_id == last_known_id:
                    logger.info(f"Reached last known ID {last_known_id} for r/{subreddit}. Stopping incremental fetch.")
                    stop_fetching = True
                    break

                # Quality Filtering
                score = post_data.get("score", 0)
                upvote_ratio = post_data.get("upvote_ratio", 1.0)
                is_stickied = post_data.get("stickied", False)

                # Skip low quality or pinned posts (except for hypeurls which is an aggregator)
                min_score = 0 if subreddit == "hypeurls" else 10
                if score < min_score or is_stickied:
                    continue

                post = {
                    "id": post_id,
                    "subreddit": subreddit,
                    "title": post_data.get("title", "No title"),
                    "url": post_data.get("url", ""),
                    "published": datetime.fromtimestamp(post_data.get("created_utc", 0), tz=timezone.utc).isoformat(),
                    "score": score,
                    "upvote_ratio": upvote_ratio,
                    "num_comments": post_data.get("num_comments", 0),
                    "author": post_data.get("author", "Anonymous"),
                    "selftext": post_data.get("selftext", ""),
                    "fetch_method": "json",
                }
                batch_posts.append(post)

            posts.extend(batch_posts)
            fetched_count += len(children)  # Count raw items fetched

            if stop_fetching or not use_pagination or fetched_count >= max_fetch_limit:
                break

            after = data.get("data", {}).get("after")
            if not after:
                break

            time.sleep(1)  # Polite pagination delay

        except Exception as e:
            logger.error(f"Error fetching r/{subreddit} via JSON (page loop): {e}")
            break

    logger.info(f"Fetched {len(posts)} posts from r/{subreddit} via JSON (Paginated: {use_pagination})")
    return posts


def fetch_all_subreddits() -> dict[str, list[dict[str, Any]]]:
    """Fetch posts from all configured subreddits."""
    all_posts = {}
    state = load_state()
    # Adaptive pacing state shared with fetch_subreddit_rss via the stats dict
    feed_delay = 3.0
    feed_stats: dict[str, Any] = {"rate_limited": False}

    for subreddit, config in SUBREDDITS_CONFIG.items():
        try:
            if config["type"] == "rss":
                posts = fetch_subreddit_rss(subreddit, stats=feed_stats)
            else:  # json
                use_pagination = config.get("pagination", False)
                last_id = state.get(subreddit) if use_pagination else None

                # If paginating, fetch more initially
                limit = 100 if use_pagination else 25

                posts = fetch_subreddit_json(subreddit, limit=limit, use_pagination=use_pagination, last_known_id=last_id)

                # Update state with newest post ID if available
                if use_pagination and posts:
                    # Assuming posts are returned newest first (standard Reddit Hot/New)
                    # We might want to sort to be sure, but usually 'hot' is roughly temporal or we just take the top one
                    # from the first batch as the new marker.
                    # Ideally we store the ID of the very first item we encountered (even if filtered out? No, filtered items are fine to skip).
                    # Actually, we should probably grab the ID from the raw response if possible, but here we only have filtered posts.
                    # Let's use the first post in our filtered list as the new checkpoint.
                    state[subreddit] = posts[0].get("id")

            # Add category info to each post
            for post in posts:
                post["category"] = config["category"]

            all_posts[subreddit] = posts

            # Rate limiting — adaptive pacing: reddit RSS 429s sustained bursts;
            # slow down permanently after every rate-limit hit (3s -> 8s cap)
            time.sleep(feed_delay)
            if feed_stats.get("rate_limited"):
                feed_delay = min(8.0, feed_delay + 1)
                feed_stats["rate_limited"] = False

        except Exception as e:
            logger.error(f"Error processing r/{subreddit}: {e}")
            all_posts[subreddit] = []

    save_state(state)
    return all_posts


def save_reddit_data(all_posts: dict[str, list[dict[str, Any]]]) -> None:
    """Save Reddit data to organized JSON files."""
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data/reddit_unified")
    ensure_directories(["data/reddit_unified"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save individual subreddit files (timestamped + latest so per-subreddit
    # consumers like the Tech Radar pulse column have a stable path)
    for subreddit, posts in all_posts.items():
        if posts:
            subreddit_file = os.path.join(output_dir, f"{subreddit}_{timestamp}.json")
            with open(subreddit_file, "w", encoding="utf-8") as f:
                json.dump(posts, f, indent=2)
            subreddit_latest = os.path.join(output_dir, f"{subreddit}_latest.json")
            shutil.copy2(subreddit_file, subreddit_latest)

    # Save combined file — but never let a partial run (heavy rate-limiting)
    # replace a fuller previous snapshot: keep the last-good latest instead
    populated = sum(1 for posts in all_posts.values() if posts)
    if populated < len(SUBREDDITS_CONFIG) // 2:
        logger.warning(f"Partial run ({populated}/{len(SUBREDDITS_CONFIG)} feeds) — keeping previous combined/category latest files")
        return

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

    try:
        all_posts = fetch_all_subreddits()
        save_reddit_data(all_posts)
    except Exception:
        logger.exception("Fatal error in Reddit Unified ETL")

    logger.info("Unified Reddit ETL process completed")


if __name__ == "__main__":
    main()
