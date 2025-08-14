"""Hacker News Ask ETL Module

This module fetches and processes "Ask HN" posts from Hacker News,
which are valuable discussion threads where the community asks questions
and shares insights about technology, careers, and startups.

Usage:
    python src/etl/news/news_get_hackernews_ask.py

Output:
    - JSON file: data/hackernews_ask/hackernews_ask_latest.json
    - CSV file: data/hackernews_ask/hackernews_ask_latest.csv
"""

import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("HackerNewsAskETL")


def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers
    session.headers.update(
        {
            "User-Agent": "Watchtower-ETL/1.0 (HackerNews Ask Analytics)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    return session


def fetch_ask_hn_posts(
    session: requests.Session, max_posts: int = 100
) -> list[dict[str, Any]]:
    """Fetch Ask HN posts from Hacker News API.

    Args:
        session: Requests session with retry configuration
        max_posts: Maximum number of posts to fetch

    Returns:
        List of Ask HN post dictionaries
    """
    base_url = "https://hacker-news.firebaseio.com/v0"
    posts = []

    try:
        # Get top stories
        logger.info("Fetching top stories from Hacker News")
        response = session.get(f"{base_url}/topstories.json", timeout=30)
        response.raise_for_status()

        story_ids = response.json()
        ask_posts_found = 0

        logger.info(f"Processing stories to find Ask HN posts (target: {max_posts})")

        for story_id in story_ids:
            if ask_posts_found >= max_posts:
                break

            try:
                # Get story details
                story_response = session.get(
                    f"{base_url}/item/{story_id}.json", timeout=30
                )
                story_response.raise_for_status()
                story_data = story_response.json()

                if not story_data:
                    continue

                title = story_data.get("title", "").lower()

                # Check if it's an Ask HN post
                if title.startswith("ask hn:"):
                    processed_post = {
                        "id": story_data.get("id"),
                        "title": story_data.get("title"),
                        "url": f"https://news.ycombinator.com/item?id={story_data.get('id')}",
                        "text": story_data.get("text", ""),
                        "author": story_data.get("by"),
                        "score": story_data.get("score", 0),
                        "comments_count": story_data.get("descendants", 0),
                        "time": story_data.get("time"),
                        "created_at": (
                            datetime.fromtimestamp(
                                story_data.get("time", 0)
                            ).isoformat()
                            if story_data.get("time")
                            else None
                        ),
                        "type": story_data.get("type"),
                        "kids": story_data.get("kids", []),
                        "fetched_at": datetime.now().isoformat(),
                    }

                    posts.append(processed_post)
                    ask_posts_found += 1

                # Small delay to be respectful to the API
                time.sleep(0.1)

            except requests.exceptions.RequestException as e:
                logger.warning(f"Error fetching story {story_id}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error processing story {story_id}: {e}")
                continue

        logger.info(f"Found {len(posts)} Ask HN posts")
        return posts

    except Exception as e:
        logger.error(f"Error fetching Ask HN posts: {e}")
        return []


def process_ask_hn_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and enrich Ask HN posts with additional metrics and categorization.

    Args:
        posts: List of Ask HN post dictionaries

    Returns:
        List of processed and enriched post data
    """
    logger.info(f"Processing {len(posts)} Ask HN posts")

    processed_posts = []
    current_time = datetime.now()

    for post in posts:
        try:
            # Parse creation time
            created_at_str = post.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
                hours_since_posted = (
                    current_time.replace(tzinfo=created_at.tzinfo) - created_at
                ).total_seconds() / 3600
            else:
                hours_since_posted = 0

            # Extract metrics
            score = post.get("score", 0)
            comments_count = post.get("comments_count", 0)
            title = post.get("title", "")
            text = post.get("text", "")

            # Calculate engagement score
            engagement_score = score + (comments_count * 2)

            # Categorize the post based on title and content
            title_lower = title.lower()
            text_lower = text.lower()
            combined_text = f"{title_lower} {text_lower}"

            if any(
                word in combined_text
                for word in [
                    "career",
                    "job",
                    "interview",
                    "salary",
                    "work",
                    "employment",
                ]
            ):
                category = "career"
            elif any(
                word in combined_text
                for word in [
                    "startup",
                    "business",
                    "entrepreneur",
                    "revenue",
                    "funding",
                ]
            ):
                category = "startup"
            elif any(
                word in combined_text
                for word in [
                    "ai",
                    "machine learning",
                    "ml",
                    "artificial intelligence",
                    "gpt",
                    "llm",
                ]
            ):
                category = "ai_ml"
            elif any(
                word in combined_text
                for word in [
                    "programming",
                    "code",
                    "developer",
                    "software",
                    "language",
                    "framework",
                ]
            ):
                category = "programming"
            elif any(
                word in combined_text
                for word in [
                    "advice",
                    "recommendation",
                    "suggest",
                    "opinion",
                    "experience",
                ]
            ):
                category = "advice"
            elif any(
                word in combined_text
                for word in ["tool", "app", "service", "platform", "product"]
            ):
                category = "tools"
            elif any(
                word in combined_text
                for word in [
                    "learn",
                    "education",
                    "course",
                    "book",
                    "study",
                    "tutorial",
                ]
            ):
                category = "learning"
            elif any(
                word in combined_text
                for word in ["freelance", "remote", "side project", "consulting"]
            ):
                category = "freelance"
            else:
                category = "general"

            # Determine discussion quality
            if engagement_score >= 200:
                discussion_quality = "high"
            elif engagement_score >= 50:
                discussion_quality = "medium"
            elif engagement_score >= 10:
                discussion_quality = "low"
            else:
                discussion_quality = "minimal"

            # Freshness indicator
            if hours_since_posted <= 6:
                freshness = "very_fresh"
            elif hours_since_posted <= 24:
                freshness = "fresh"
            elif hours_since_posted <= 72:
                freshness = "recent"
            else:
                freshness = "older"

            # Calculate priority score
            priority_score = engagement_score
            if freshness in ["very_fresh", "fresh"]:
                priority_score *= 1.3
            if discussion_quality == "high":
                priority_score *= 1.2

            # Question type analysis
            question_indicators = [
                "how",
                "what",
                "why",
                "which",
                "where",
                "when",
                "who",
            ]
            has_question = any(
                indicator in title_lower for indicator in question_indicators
            )

            processed_post = {
                **post,
                "hours_since_posted": round(hours_since_posted, 2),
                "engagement_score": engagement_score,
                "category": category,
                "discussion_quality": discussion_quality,
                "freshness": freshness,
                "priority_score": round(priority_score, 2),
                "has_question": has_question,
                "is_trending": engagement_score >= 100,
                "platform": "hackernews_ask",
                "text_length": len(text),
            }

            processed_posts.append(processed_post)

        except Exception as e:
            logger.warning(f"Error processing post {post.get('id', 'unknown')}: {e}")
            continue

    # Sort by priority score
    processed_posts.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    logger.info(f"Successfully processed {len(processed_posts)} Ask HN posts")
    return processed_posts


def save_data(data: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """Save processed data to JSON and CSV files.

    Args:
        data: List of processed Ask HN posts
        output_dir: Directory to save files

    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # File paths
    json_file = os.path.join(output_dir, f"hackernews_ask_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"hackernews_ask_{timestamp}.csv")
    latest_json = os.path.join(output_dir, "hackernews_ask_latest.json")
    latest_csv = os.path.join(output_dir, "hackernews_ask_latest.csv")

    # Save JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Save CSV
    if data:
        # Flatten data for CSV
        csv_data = []
        for item in data:
            flat_item = {**item}

            # Convert lists to strings
            if isinstance(flat_item.get("kids"), list):
                flat_item["kids"] = ", ".join(map(str, flat_item["kids"]))

            csv_data.append(flat_item)

        fieldnames = csv_data[0].keys() if csv_data else []

        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

    logger.info(f"Data saved to {json_file} and {csv_file}")

    return {
        "json_file": json_file,
        "csv_file": csv_file,
        "latest_json": latest_json,
        "latest_csv": latest_csv,
    }


def main():
    """Main function to run the HackerNews Ask ETL process."""
    logger.info("Starting HackerNews Ask ETL process")

    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "hackernews_ask")
        session = create_session()

        # Fetch data
        logger.info("Fetching Ask HN posts")
        posts = fetch_ask_hn_posts(session, max_posts=100)

        if not posts:
            logger.warning("No Ask HN posts fetched. Exiting.")
            return

        # Process data
        logger.info("Processing and enriching Ask HN data")
        processed_data = process_ask_hn_posts(posts)

        # Save data
        file_paths = save_data(processed_data, output_dir)

        # Summary
        total_posts = len(processed_data)
        high_engagement = len(
            [p for p in processed_data if p.get("discussion_quality") == "high"]
        )
        trending_posts = len([p for p in processed_data if p.get("is_trending", False)])

        logger.info("HackerNews Ask ETL completed successfully!")
        logger.info(f"Total Ask HN posts: {total_posts}")
        logger.info(f"High engagement discussions: {high_engagement}")
        logger.info(f"Trending posts: {trending_posts}")
        logger.info(f"Files saved: {list(file_paths.values())}")

        # Print category distribution
        if processed_data:
            categories = [p.get("category", "Unknown") for p in processed_data]
            from collections import Counter

            top_categories = Counter(categories).most_common(10)
            logger.info(f"Top categories: {top_categories}")

    except Exception as e:
        logger.error(f"HackerNews Ask ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
