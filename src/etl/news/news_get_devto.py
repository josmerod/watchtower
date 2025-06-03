"""DEV Community ETL Module

This module fetches and processes articles, discussions, and trending content from DEV Community
using their public API. It tracks popular programming topics and developer insights.

Usage:
    python src/etl/news/news_get_devto.py

Output:
    - JSON file: data/dev_community/dev_community_latest.json
    - CSV file: data/dev_community/dev_community_latest.csv
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
logger = get_logger("DevCommunityETL")


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
            "User-Agent": "Watchtower-ETL/1.0 (Data Collection for Analytics)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    return session


def get_dev_articles(
    session: requests.Session, per_page: int = 100, max_pages: int = 5
) -> list[dict[str, Any]]:
    """Fetch recent articles from DEV Community API.

    Args:
        session: Requests session with retry configuration
        per_page: Number of articles per page (max 1000)
        max_pages: Maximum number of pages to fetch

    Returns:
        List of article dictionaries
    """
    base_url = "https://dev.to/api/articles"
    all_articles = []
    seen_ids = set()

    # Track popular programming tags
    popular_tags = [
        "webdev",
        "javascript",
        "python",
        "react",
        "tutorial",
        "beginners",
        "programming",
        "productivity",
        "career",
        "opensource",
        "devops",
        "ai",
        "machinelearning",
        "database",
        "security",
        "cloud",
        "docker",
        "kubernetes",
        "typescript",
        "nodejs",
        "backend",
    ]

    for page in range(1, max_pages + 1):
        try:
            # Fetch trending articles with popular tags
            params = {
                "page": page,
                "per_page": per_page,
                "state": "fresh",  # Get recent articles
                "top": "7",  # Get top articles from last 7 days
            }

            logger.info(f"Fetching DEV articles page {page}")
            response = session.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            articles = response.json()

            if not articles:
                logger.info(f"No more articles found on page {page}")
                break

            for article in articles:
                article_id = article.get("id")
                if article_id in seen_ids:
                    continue

                seen_ids.add(article_id)

                # Extract article data
                processed_article = {
                    "id": article_id,
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "canonical_url": article.get("canonical_url", ""),
                    "published_at": article.get("published_at", ""),
                    "created_at": article.get("created_at", ""),
                    "edited_at": article.get("edited_at"),
                    "crossposted_at": article.get("crossposted_at"),
                    "last_comment_at": article.get("last_comment_at"),
                    "published_timestamp": article.get("published_timestamp"),
                    "slug": article.get("slug", ""),
                    "path": article.get("path", ""),
                    "public_reactions_count": article.get("public_reactions_count", 0),
                    "comments_count": article.get("comments_count", 0),
                    "page_views_count": article.get("page_views_count", 0),
                    "positive_reactions_count": article.get(
                        "positive_reactions_count", 0
                    ),
                    "cover_image": article.get("cover_image"),
                    "social_image": article.get("social_image"),
                    "reading_time_minutes": article.get("reading_time_minutes", 0),
                    "tag_list": article.get("tag_list", []),
                    "tags": article.get("tags", ""),
                    "body_html": article.get("body_html", ""),
                    "body_markdown": article.get("body_markdown", ""),
                    "user": {
                        "name": article.get("user", {}).get("name", ""),
                        "username": article.get("user", {}).get("username", ""),
                        "twitter_username": article.get("user", {}).get(
                            "twitter_username"
                        ),
                        "github_username": article.get("user", {}).get(
                            "github_username"
                        ),
                        "website_url": article.get("user", {}).get("website_url"),
                        "profile_image": article.get("user", {}).get("profile_image"),
                        "profile_image_90": article.get("user", {}).get(
                            "profile_image_90"
                        ),
                    },
                    "organization": article.get("organization"),
                    "flare_tag": article.get("flare_tag"),
                    "type_of": article.get("type_of", "article"),
                }

                all_articles.append(processed_article)

            logger.info(f"Collected {len(articles)} articles from page {page}")

            # Rate limiting - be respectful to the API
            time.sleep(2)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching page {page}: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error on page {page}: {e}")
            break

    logger.info(f"Total DEV articles collected: {len(all_articles)}")
    return all_articles


def get_dev_tags(session: requests.Session) -> list[dict[str, Any]]:
    """Fetch trending tags from DEV Community.

    Args:
        session: Requests session with retry configuration

    Returns:
        List of tag dictionaries
    """
    try:
        url = "https://dev.to/api/tags"
        params = {"per_page": 100}

        logger.info("Fetching DEV Community tags")
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error fetching tags: {e}")
        return []


def process_dev_data(
    articles: list[dict[str, Any]], tags: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Process and enrich DEV Community data with additional metrics and categorization.

    Args:
        articles: List of article dictionaries
        tags: List of tag dictionaries

    Returns:
        List of processed and enriched article data
    """
    current_time = datetime.utcnow()
    processed_articles = []

    # Create tag lookup for popularity scoring
    tag_lookup = {tag.get("name"): tag for tag in tags}

    for article in articles:
        try:
            # Parse published date
            published_at = article.get("published_at")
            if published_at:
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                hours_since_published = (
                    current_time.replace(tzinfo=pub_date.tzinfo) - pub_date
                ).total_seconds() / 3600
            else:
                hours_since_published = 24  # Default fallback

            # Calculate engagement metrics
            reactions = article.get("public_reactions_count", 0)
            comments = article.get("comments_count", 0)
            views = article.get("page_views_count", 0)
            reading_time = article.get("reading_time_minutes", 1)

            # Engagement scoring
            engagement_score = reactions * 2 + comments * 3 + min(views / 100, 50)

            # Trend analysis (boost newer content)
            freshness_factor = (
                max(0, (48 - hours_since_published) / 48)
                if hours_since_published <= 48
                else 0
            )
            trend_score = engagement_score * (1 + freshness_factor)

            # Tag analysis
            article_tags = article.get("tag_list", [])
            tag_popularity_score = sum(
                tag_lookup.get(tag, {}).get("taggings_count", 0)
                for tag in article_tags[:5]
            )

            # Content classification
            title_lower = article.get("title", "").lower()
            description_lower = article.get("description", "").lower()

            content_type = "general"
            if any(
                word in title_lower
                for word in ["tutorial", "guide", "how to", "step by step"]
            ):
                content_type = "tutorial"
            elif any(
                word in title_lower
                for word in ["tips", "tricks", "best practices", "advice"]
            ):
                content_type = "tips"
            elif any(
                word in title_lower for word in ["review", "comparison", "vs", "versus"]
            ):
                content_type = "review"
            elif any(
                word in title_lower
                for word in ["news", "release", "update", "announcement"]
            ):
                content_type = "news"
            elif any(
                word in title_lower for word in ["career", "job", "interview", "salary"]
            ):
                content_type = "career"

            # Reading difficulty estimation
            if reading_time <= 3:
                difficulty = "beginner"
            elif reading_time <= 8:
                difficulty = "intermediate"
            else:
                difficulty = "advanced"

            # Popularity categorization
            if trend_score >= 100:
                popularity = "viral"
            elif trend_score >= 50:
                popularity = "high"
            elif trend_score >= 20:
                popularity = "medium"
            else:
                popularity = "low"

            processed_article = {
                **article,
                "fetched_at": current_time.isoformat(),
                "hours_since_published": round(hours_since_published, 2),
                "engagement_score": round(engagement_score, 2),
                "trend_score": round(trend_score, 2),
                "freshness_factor": round(freshness_factor, 2),
                "tag_popularity_score": tag_popularity_score,
                "content_type": content_type,
                "reading_difficulty": difficulty,
                "popularity_category": popularity,
                "platform": "dev_community",
                "data_source": "dev.to_api",
            }

            processed_articles.append(processed_article)

        except Exception as e:
            logger.warning(
                f"Error processing article {article.get('id', 'unknown')}: {e}"
            )
            continue

    # Sort by trend score
    processed_articles.sort(key=lambda x: x.get("trend_score", 0), reverse=True)

    logger.info(f"Successfully processed {len(processed_articles)} DEV articles")
    return processed_articles


def save_data(data: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """Save processed data to JSON and CSV files.

    Args:
        data: List of processed articles
        output_dir: Directory to save files

    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # File paths
    json_file = os.path.join(output_dir, f"dev_community_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"dev_community_{timestamp}.csv")
    latest_json = os.path.join(output_dir, "dev_community_latest.json")
    latest_csv = os.path.join(output_dir, "dev_community_latest.csv")

    # Save JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Save CSV
    if data:
        # Flatten user data for CSV
        csv_data = []
        for item in data:
            flat_item = {**item}
            user_data = flat_item.pop("user", {})
            flat_item.update({f"user_{k}": v for k, v in user_data.items()})

            # Convert lists to strings
            if isinstance(flat_item.get("tag_list"), list):
                flat_item["tag_list"] = ", ".join(flat_item["tag_list"])

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
    """Main function to run the DEV Community ETL process."""
    logger.info("Starting DEV Community ETL process")

    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "dev_community")
        session = create_session()

        # Fetch data
        logger.info("Fetching articles and tags from DEV Community")
        articles = get_dev_articles(session)
        tags = get_dev_tags(session)

        if not articles:
            logger.warning("No articles fetched. Exiting.")
            return

        # Process data
        logger.info("Processing and enriching data")
        processed_data = process_dev_data(articles, tags)

        # Save data
        file_paths = save_data(processed_data, output_dir)

        # Summary
        total_articles = len(processed_data)
        high_engagement = len(
            [a for a in processed_data if a.get("engagement_score", 0) >= 50]
        )
        viral_content = len(
            [a for a in processed_data if a.get("popularity_category") == "viral"]
        )

        logger.info("DEV Community ETL completed successfully!")
        logger.info(f"Total articles: {total_articles}")
        logger.info(f"High engagement articles: {high_engagement}")
        logger.info(f"Viral content: {viral_content}")
        logger.info(f"Files saved: {list(file_paths.values())}")

        # Print trending tags distribution
        if processed_data:
            all_tags = []
            for article in processed_data:
                all_tags.extend(article.get("tag_list", []))

            from collections import Counter

            top_tags = Counter(all_tags).most_common(10)
            logger.info(f"Top trending tags: {top_tags}")

    except Exception as e:
        logger.error(f"DEV Community ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
