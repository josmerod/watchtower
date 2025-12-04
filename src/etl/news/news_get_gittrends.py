"""GitHub Trends ETL Module

This module fetches and processes trending GitHub repositories, popular topics,
and developer activity patterns to track open-source trends and innovation.

Usage:
    python src/etl/news/news_get_gittrends.py

Output:
    - JSON file: data/github_trends/github_trends_latest.json
    - CSV file: data/github_trends/github_trends_latest.csv
"""

import csv
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models.github import GitHubRepositoryModel

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("GitHubTrendsETL")


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
            "User-Agent": "Watchtower-ETL/1.0 (GitHub Trends Analytics)",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
    )

    return session


def get_trending_repositories(session: requests.Session, language: str = None, since: str = "daily") -> list[dict[str, Any]]:
    """Fetch trending repositories from GitHub.

    Args:
        session: Requests session with retry configuration
        language: Programming language filter
        since: Time period (daily, weekly, monthly)

    Returns:
        List of repository dictionaries
    """
    # GitHub doesn't have an official trending API, so we'll use the search API
    # to find repositories with high recent activity

    base_url = "https://api.github.com/search/repositories"
    repositories = []

    # Define search queries for different time periods
    date_filter = {
        "daily": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "weekly": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "monthly": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
    }

    # Popular programming languages to track
    languages = (
        [
            "python",
            "javascript",
            "typescript",
            "rust",
            "go",
            "java",
            "cpp",
            "csharp",
            "php",
            "ruby",
        ]
        if not language
        else [language]
    )

    for lang in languages:
        try:
            # Search for repositories with high recent activity
            query = f"language:{lang} created:>{date_filter[since]} stars:>1"

            params = {"q": query, "sort": "stars", "order": "desc", "per_page": 20}

            logger.info(f"Fetching trending {lang} repositories for {since} period")
            response = session.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            for repo in data.get("items", []):
                processed_repo = {
                    "id": repo.get("id"),
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "description": repo.get("description", ""),
                    "html_url": repo.get("html_url"),
                    "language": repo.get("language"),
                    "stars_count": repo.get("stargazers_count", 0),
                    "forks_count": repo.get("forks_count", 0),
                    "watchers_count": repo.get("watchers_count", 0),
                    "open_issues_count": repo.get("open_issues_count", 0),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "pushed_at": repo.get("pushed_at"),
                    "size": repo.get("size", 0),
                    "default_branch": repo.get("default_branch"),
                    "topics": repo.get("topics", []),
                    "license": (repo.get("license", {}).get("name") if repo.get("license") else None),
                    "owner": {
                        "login": repo.get("owner", {}).get("login"),
                        "type": repo.get("owner", {}).get("type"),
                        "html_url": repo.get("owner", {}).get("html_url"),
                    },
                    "archived": repo.get("archived", False),
                    "disabled": repo.get("disabled", False),
                    "has_wiki": repo.get("has_wiki", False),
                    "has_pages": repo.get("has_pages", False),
                    "has_downloads": repo.get("has_downloads", False),
                    "period": since,
                    "fetched_at": datetime.now().isoformat(),
                }

                # Soft validation to enforce dashboard contract shape
                try:
                    _ = GitHubRepositoryModel(
                        repository_id=processed_repo.get("id"),
                        name=processed_repo.get("name", ""),
                        full_name=processed_repo.get("full_name", ""),
                        description=processed_repo.get("description", ""),
                        html_url=processed_repo.get("html_url", ""),
                        language=processed_repo.get("language"),
                        stars_count=processed_repo.get("stars_count", 0),
                        forks_count=processed_repo.get("forks_count", 0),
                        watchers_count=processed_repo.get("watchers_count", 0),
                        open_issues_count=processed_repo.get("open_issues_count", 0),
                        default_branch=processed_repo.get("default_branch"),
                        topics=processed_repo.get("topics", []),
                        license_name=processed_repo.get("license"),
                        owner=processed_repo.get("owner"),
                        repository_created_at=processed_repo.get("created_at"),
                        repository_updated_at=processed_repo.get("updated_at"),
                        pushed_at=processed_repo.get("pushed_at"),
                        trending_period=since,
                        trending_language=processed_repo.get("language") or "all",
                        rss_title=None,
                        rss_link=None,
                        rss_published=None,
                        source="github_trends",
                        source_url=None,
                    )
                except Exception as e:
                    logger.warning(f"Validation failed for GitHub repo {processed_repo.get('full_name', '')}: {e}")

                repositories.append(processed_repo)

            # Rate limiting for GitHub API
            time.sleep(1)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {lang} repositories: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error for {lang}: {e}")
            continue

    logger.info(f"Total trending repositories collected: {len(repositories)}")
    return repositories


def get_github_topics(session: requests.Session) -> list[dict[str, Any]]:
    """Fetch trending topics from GitHub.

    Args:
        session: Requests session with retry configuration

    Returns:
        List of topic dictionaries
    """
    try:
        # Search for trending topics
        base_url = "https://api.github.com/search/topics"
        params = {
            "q": "repositories:>1000",
            "sort": "updated",
            "order": "desc",
            "per_page": 50,
        }

        logger.info("Fetching GitHub trending topics")
        response = session.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        topics = []

        for topic in data.get("items", []):
            processed_topic = {
                "name": topic.get("name"),
                "display_name": topic.get("display_name"),
                "short_description": topic.get("short_description", ""),
                "description": topic.get("description", ""),
                "created_by": topic.get("created_by"),
                "created_at": topic.get("created_at"),
                "updated_at": topic.get("updated_at"),
                "featured": topic.get("featured", False),
                "curated": topic.get("curated", False),
                "score": topic.get("score", 0),
                "fetched_at": datetime.now().isoformat(),
            }
            topics.append(processed_topic)

        return topics

    except Exception as e:
        logger.error(f"Error fetching GitHub topics: {e}")
        return []


def process_github_data(repositories: list[dict[str, Any]], topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and enrich GitHub data with additional metrics and categorization.

    Args:
        repositories: List of repository dictionaries
        topics: List of topic dictionaries

    Returns:
        List of processed and enriched repository data
    """
    current_time = datetime.now()
    processed_repos = []

    # Create topic lookup for enrichment
    topic_lookup = {topic.get("name"): topic for topic in topics}

    for repo in repositories:
        try:
            # Calculate activity metrics
            stars = repo.get("stars_count", 0)
            forks = repo.get("forks_count", 0)
            watchers = repo.get("watchers_count", 0)
            open_issues = repo.get("open_issues_count", 0)

            # Parse dates
            created_at = repo.get("created_at")
            updated_at = repo.get("updated_at")
            pushed_at = repo.get("pushed_at")

            if created_at:
                created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                days_since_created = (current_time.replace(tzinfo=created_date.tzinfo) - created_date).days
            else:
                days_since_created = 0

            if updated_at:
                updated_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                days_since_updated = (current_time.replace(tzinfo=updated_date.tzinfo) - updated_date).days
            else:
                days_since_updated = 999

            # Calculate popularity score
            popularity_score = stars * 1.0 + forks * 2.0 + watchers * 0.5

            # Calculate activity score (recent activity is valued)
            activity_score = popularity_score
            if days_since_updated <= 7:
                activity_score *= 1.5
            elif days_since_updated <= 30:
                activity_score *= 1.2
            elif days_since_updated > 365:
                activity_score *= 0.5

            # Categorize repository maturity
            if days_since_created <= 30:
                maturity = "new"
            elif days_since_created <= 365:
                maturity = "young"
            elif days_since_created <= 1825:  # 5 years
                maturity = "mature"
            else:
                maturity = "established"

            # Categorize by activity level
            if days_since_updated <= 1:
                activity_level = "very_active"
            elif days_since_updated <= 7:
                activity_level = "active"
            elif days_since_updated <= 30:
                activity_level = "moderate"
            elif days_since_updated <= 180:
                activity_level = "low"
            else:
                activity_level = "inactive"

            # Determine project category
            description = (repo.get("description") or "").lower()
            language = (repo.get("language") or "").lower()
            topics_list = repo.get("topics", [])

            if any(
                word in description
                for word in [
                    "ai",
                    "machine learning",
                    "neural",
                    "tensorflow",
                    "pytorch",
                ]
            ):
                category = "ai_ml"
            elif any(word in description for word in ["web", "frontend", "backend", "api", "server"]):
                category = "web_development"
            elif any(word in description for word in ["mobile", "ios", "android", "flutter", "react native"]):
                category = "mobile"
            elif any(word in description for word in ["data", "analytics", "visualization", "dashboard"]):
                category = "data_tools"
            elif any(word in description for word in ["devops", "deployment", "ci/cd", "docker", "kubernetes"]):
                category = "devops"
            elif any(word in description for word in ["game", "gaming", "engine", "unity", "graphics"]):
                category = "gaming"
            elif any(word in description for word in ["security", "crypto", "blockchain", "vulnerability"]):
                category = "security"
            elif language in ["python", "javascript", "typescript", "rust", "go"]:
                category = f"{language}_tools"
            else:
                category = "general"

            # Calculate trending score
            trending_score = activity_score
            if repo.get("period") == "daily":
                trending_score *= 1.5
            if maturity == "new":
                trending_score *= 1.3
            if activity_level in ["very_active", "active"]:
                trending_score *= 1.2

            processed_repo = {
                **repo,
                "days_since_created": days_since_created,
                "days_since_updated": days_since_updated,
                "popularity_score": round(popularity_score, 2),
                "activity_score": round(activity_score, 2),
                "trending_score": round(trending_score, 2),
                "maturity": maturity,
                "activity_level": activity_level,
                "category": category,
                "has_recent_activity": days_since_updated <= 7,
                "is_trending": trending_score >= 100,
                "platform": "github",
            }

            processed_repos.append(processed_repo)

        except Exception as e:
            logger.warning(f"Error processing repository {repo.get('full_name', 'unknown')}: {e}")
            continue

    # Sort by trending score
    processed_repos.sort(key=lambda x: x.get("trending_score", 0), reverse=True)

    logger.info(f"Successfully processed {len(processed_repos)} GitHub repositories")
    return processed_repos


def save_data(data: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """Save processed data to JSON and CSV files.

    Args:
        data: List of processed repositories
        output_dir: Directory to save files

    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # File paths
    json_file = os.path.join(output_dir, f"github_trends_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"github_trends_{timestamp}.csv")
    latest_json = os.path.join(output_dir, "github_trends_latest.json")
    latest_csv = os.path.join(output_dir, "github_trends_latest.csv")

    # Save JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Save CSV
    if data:
        # Flatten nested data for CSV
        csv_data = []
        for item in data:
            flat_item = {**item}

            # Flatten owner data
            owner_data = flat_item.pop("owner", {})
            flat_item.update({f"owner_{k}": v for k, v in owner_data.items()})

            # Convert lists to strings
            if isinstance(flat_item.get("topics"), list):
                flat_item["topics"] = ", ".join(flat_item["topics"])

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
    """Main function to run the GitHub Trends ETL process."""
    logger.info("Starting GitHub Trends ETL process")

    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "github_trends")
        session = create_session()

        # Fetch data
        logger.info("Fetching trending repositories and topics from GitHub")
        repositories = get_trending_repositories(session, since="daily")
        topics = get_github_topics(session)

        if not repositories:
            logger.warning("No repositories fetched. Exiting.")
            return

        # Process data
        logger.info("Processing and enriching data")
        processed_data = process_github_data(repositories, topics)

        # Save data
        file_paths = save_data(processed_data, output_dir)

        # Summary
        total_repos = len(processed_data)
        trending_repos = len([r for r in processed_data if r.get("is_trending", False)])
        active_repos = len([r for r in processed_data if r.get("has_recent_activity", False)])

        logger.info("GitHub Trends ETL completed successfully!")
        logger.info(f"Total repositories: {total_repos}")
        logger.info(f"Trending repositories: {trending_repos}")
        logger.info(f"Recently active repositories: {active_repos}")
        logger.info(f"Files saved: {list(file_paths.values())}")

        # Print language distribution
        if processed_data:
            languages = [r.get("language", "Unknown") for r in processed_data if r.get("language")]
            from collections import Counter

            top_languages = Counter(languages).most_common(10)
            logger.info(f"Top programming languages: {top_languages}")

    except Exception as e:
        logger.error(f"GitHub Trends ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
