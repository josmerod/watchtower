"""ExpatCircle News ETL Module.

This module fetches and processes news posts from ExpatCircle News,
an expat-focused news aggregation and community platform.

Usage:
    python src/etl/news/news_get_expatcircle.py

Output:
- JSON file: data/expatcircle/posts.json
- CSV file: data/expatcircle/posts.csv
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from config.settings import get_settings
from utils.logging import get_logger

# Initialize logger and settings
logger = get_logger("ExpatCircleETL")
settings = get_settings()

# ExpatCircle News configuration
EXPATCIRCLE_BASE_URL = "https://news.expatcircle.com"
EXPATCIRCLE_POSTS_URL = f"{EXPATCIRCLE_BASE_URL}/"

# Request headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
    "Referer": "https://news.expatcircle.com/",
}


def fetch_expatcircle_posts(
    session: requests.Session, max_posts: int = 50, max_pages: int = 5
) -> list[dict[str, Any]]:
    """Fetch posts from ExpatCircle News main page.

    Args:
        session: Requests session for connection pooling
        max_posts: Maximum number of posts to fetch
        max_pages: Maximum number of pages to scrape

    Returns:
        List of post dictionaries
    """
    posts = []

    try:
        base_url = "https://news.expatcircle.com"

        logger.info("Fetching posts from ExpatCircle News")

        for page in range(1, max_pages + 1):
            if len(posts) >= max_posts:
                break

            # Construct page URL
            url = base_url if page == 1 else f"{base_url}?page={page}"

            logger.info(f"Scraping page {page}: {url}")

            response = session.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Find post containers (adjust selectors based on actual site structure)
            post_containers = soup.find_all(
                ["article", "div"], class_=re.compile(r"post|item|entry|story")
            )

            if not post_containers:
                # Fallback: look for common post patterns
                post_containers = soup.find_all("div", attrs={"data-post": True})
                if not post_containers:
                    post_containers = soup.select(
                        'div[class*="post"], article[class*="post"], .post-item, .story-item'
                    )

            logger.info(
                f"Found {len(post_containers)} potential post containers on page {page}"
            )

            for container in post_containers:
                if len(posts) >= max_posts:
                    break

                post_data = parse_expatcircle_post(container, base_url)
                if post_data:
                    posts.append(post_data)

            # Add delay between requests
            time.sleep(1)

        logger.info(f"Found {len(posts)} posts from ExpatCircle News")
        return posts

    except Exception as e:
        logger.error(f"Error fetching ExpatCircle posts: {e}")
        return posts


def parse_expatcircle_post(container, base_url: str) -> dict[str, Any] | None:
    """Parse a post element from the ExpatCircle News page.

    Args:
        container: BeautifulSoup element containing post data
        base_url: Base URL for resolving relative links

    Returns:
        Dictionary with post data or None if parsing fails
    """
    try:
        post_data = {}

        # Extract title
        title_elem = container.find(
            ["h1", "h2", "h3", "h4"], class_=re.compile(r"title|headline")
        )
        if not title_elem:
            title_elem = container.find("a", href=True)

        if title_elem:
            post_data["title"] = title_elem.get_text(strip=True)

            # Extract URL from title link
            link_elem = (
                title_elem.find("a", href=True)
                if title_elem.name != "a"
                else title_elem
            )
            if link_elem:
                href = link_elem.get("href", "")
                post_data["url"] = urljoin(base_url, href)
            else:
                post_data["url"] = base_url
        else:
            return None  # Skip posts without titles

        # Extract description/excerpt
        desc_elem = container.find(
            ["p", "div"], class_=re.compile(r"excerpt|description|summary|content")
        )
        if desc_elem:
            post_data["description"] = desc_elem.get_text(strip=True)[
                :500
            ]  # Limit length
        else:
            # Fallback: get first paragraph
            p_elem = container.find("p")
            if p_elem:
                post_data["description"] = p_elem.get_text(strip=True)[:500]
            else:
                post_data["description"] = ""

        # Extract publication date
        date_elem = container.find(["time", "span", "div"], attrs={"datetime": True})
        if not date_elem:
            date_elem = container.find(
                text=re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}")
            )

        if date_elem:
            if hasattr(date_elem, "get"):
                date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
            else:
                date_str = str(date_elem).strip()

            post_data["published_date"] = parse_date_string(date_str)
        else:
            post_data["published_date"] = datetime.now().isoformat()

        # Extract category
        category_elem = container.find(
            ["span", "div", "a"], class_=re.compile(r"category|tag|topic")
        )
        if category_elem:
            post_data["category"] = category_elem.get_text(strip=True)
        else:
            post_data["category"] = "General"

        # Extract author
        author_elem = container.find(
            ["span", "div", "a"], class_=re.compile(r"author|by|user")
        )
        if author_elem:
            post_data["author"] = author_elem.get_text(strip=True)
        else:
            post_data["author"] = "ExpatCircle"

        # Extract engagement metrics
        comments_elem = container.find(text=re.compile(r"\d+\s*(comment|reply)", re.I))
        if comments_elem:
            comments_match = re.search(r"(\d+)", str(comments_elem))
            post_data["comments_count"] = (
                int(comments_match.group(1)) if comments_match else 0
            )
        else:
            post_data["comments_count"] = 0

        # Check for trending indicators
        trending_indicators = container.find(
            ["span", "div"], class_=re.compile(r"trending|hot|popular")
        )
        post_data["trending"] = bool(trending_indicators)

        # Add metadata
        post_data.update({"source": "expatcircle", "platform": "expatcircle"})

        return post_data

    except Exception as e:
        logger.error(f"Error parsing ExpatCircle post: {e}")
        return None


def process_expatcircle_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and enrich ExpatCircle posts with additional metrics and categorization.

    Args:
        posts: Raw post data from scraping

    Returns:
        Processed and enriched post data
    """
    if not posts:
        return []

    logger.info(f"Processing {len(posts)} ExpatCircle posts")

    processed_posts = []

    # Define expat-related keywords for categorization
    expat_keywords = {
        "visa": ["visa", "immigration", "permit", "residency", "citizenship"],
        "housing": ["housing", "apartment", "rent", "property", "accommodation"],
        "work": ["job", "employment", "career", "salary", "workplace", "remote work"],
        "finance": ["tax", "banking", "insurance", "finances", "money", "currency"],
        "culture": ["culture", "language", "local", "customs", "traditions"],
        "lifestyle": ["lifestyle", "living", "expat life", "community", "social"],
        "travel": ["travel", "transport", "flight", "vacation", "tourism"],
        "health": ["health", "medical", "healthcare", "doctor", "insurance"],
        "education": [
            "school",
            "education",
            "university",
            "children",
            "international school",
        ],
        "business": ["business", "entrepreneur", "startup", "investment", "company"],
    }

    for post in posts:
        try:
            # Create processed post copy
            processed_post = post.copy()

            # Enhance categorization based on content
            title_lower = post.get("title", "").lower()
            desc_lower = post.get("description", "").lower()
            content_text = f"{title_lower} {desc_lower}"

            # Determine more specific category
            category_scores = {}
            for category, keywords in expat_keywords.items():
                score = sum(1 for keyword in keywords if keyword in content_text)
                if score > 0:
                    category_scores[category] = score

            if category_scores:
                best_category = max(category_scores, key=category_scores.get)
                processed_post["expat_category"] = best_category
                processed_post["category_confidence"] = category_scores[best_category]
            else:
                processed_post["expat_category"] = "general"
                processed_post["category_confidence"] = 0

            # Calculate engagement score
            engagement_score = 0

            # Base score from comments
            comments = post.get("comments_count", 0)
            engagement_score += comments * 2

            # Trending bonus
            if post.get("trending", False):
                engagement_score += 10

            # Title/description quality bonus
            title_len = len(post.get("title", ""))
            desc_len = len(post.get("description", ""))

            if title_len > 20:
                engagement_score += 2
            if desc_len > 100:
                engagement_score += 3

            # Recency bonus (posts from last 24 hours)
            try:
                pub_date = datetime.fromisoformat(
                    post.get("published_date", "").replace("Z", "+00:00")
                )
                if datetime.now().replace(
                    tzinfo=pub_date.tzinfo
                ) - pub_date < timedelta(days=1):
                    engagement_score += 5
            except (ValueError, TypeError, AttributeError):
                # Date parsing failed, skip recency bonus
                pass

            processed_post["engagement_score"] = engagement_score

            # Add content type classification
            if any(
                word in content_text for word in ["guide", "how to", "tips", "advice"]
            ):
                processed_post["content_type"] = "guide"
            elif any(
                word in content_text for word in ["news", "update", "announcement"]
            ):
                processed_post["content_type"] = "news"
            elif any(
                word in content_text for word in ["question", "help", "advice", "?"]
            ):
                processed_post["content_type"] = "question"
            elif any(
                word in content_text for word in ["experience", "story", "review"]
            ):
                processed_post["content_type"] = "experience"
            else:
                processed_post["content_type"] = "discussion"

            # Add processing timestamp
            processed_post["processed_at"] = datetime.now().isoformat()

            # Add quality score
            quality_score = 0

            # Title quality
            if 10 <= title_len <= 100:
                quality_score += 2

            # Description quality
            if 50 <= desc_len <= 300:
                quality_score += 2

            # Has URL
            if post.get("url") and post["url"] != base_url:
                quality_score += 1

            # Has category
            if post.get("category") and post["category"] != "General":
                quality_score += 1

            processed_post["quality_score"] = quality_score

            processed_posts.append(processed_post)

        except Exception as e:
            logger.error(f"Error processing post {post.get('title', 'Unknown')}: {e}")
            # Add the original post if processing fails
            processed_posts.append(post)

    logger.info(f"Successfully processed {len(processed_posts)} ExpatCircle posts")
    return processed_posts


def parse_date_string(date_str: str) -> str:
    """Parse various date formats into ISO format.

    Args:
        date_str: Date string in various formats

    Returns:
        ISO formatted date string
    """
    if not date_str:
        return datetime.now().isoformat()

    # Common date patterns
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    # Clean up the date string
    date_str = re.sub(r"[^\w\s:/-]", "", date_str.strip())

    for pattern in patterns:
        try:
            parsed_date = datetime.strptime(date_str, pattern)
            return parsed_date.isoformat()
        except ValueError:
            continue

    # If all else fails, try to extract a simple date
    date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if date_match:
        try:
            year, month, day = date_match.groups()
            parsed_date = datetime(int(year), int(month), int(day))
            return parsed_date.isoformat()
        except ValueError:
            pass

    # Last resort: return current date
    logger.warning(f"Could not parse date: {date_str}")
    return datetime.now().isoformat()


def save_expatcircle_data(data: list[dict[str, Any]], output_dir: str):
    """Save ExpatCircle data to JSON and CSV files.

    Args:
        data: Processed post data
        output_dir: Output directory path
    """
    if not data:
        logger.warning("No data to save")
        return

    try:
        # Save JSON
        json_file = os.path.join(output_dir, "expatcircle_posts.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Saved {len(data)} posts to {json_file}")

        # Save CSV
        csv_file = os.path.join(output_dir, "expatcircle_posts.csv")

        if data:
            # Get all unique keys for CSV headers
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())

            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(data)

            logger.info(f"Saved {len(data)} posts to {csv_file}")

    except Exception as e:
        logger.error(f"Error saving data: {e}")


def main():
    """Main function to run the ExpatCircle News ETL process."""
    logger.info("Starting ExpatCircle News ETL process")

    try:
        # Create output directory
        project_root = Path(__file__).parent.parent.parent.parent
        output_dir = os.path.join(project_root, "data", "expatcircle")
        os.makedirs(output_dir, exist_ok=True)

        # Create session for connection pooling
        session = requests.Session()
        session.headers.update(HEADERS)

        logger.info("Fetching ExpatCircle News posts")
        posts = fetch_expatcircle_posts(session, max_posts=50)

        if not posts:
            logger.warning("No posts fetched from ExpatCircle News")
            return

        logger.info(f"Fetched {len(posts)} posts")

        logger.info("Processing and enriching ExpatCircle data")
        processed_data = process_expatcircle_posts(posts)

        # Save data
        save_expatcircle_data(processed_data, output_dir)

        # Print summary
        logger.info("ExpatCircle News ETL completed successfully!")
        logger.info(f"Total posts processed: {len(processed_data)}")

        if processed_data:
            categories = {}
            for post in processed_data:
                cat = post.get("expat_category", "unknown")
                categories[cat] = categories.get(cat, 0) + 1

            logger.info("Category breakdown:")
            for cat, count in sorted(
                categories.items(), key=lambda x: x[1], reverse=True
            ):
                logger.info(f"  {cat}: {count} posts")

    except Exception as e:
        logger.error(f"ExpatCircle News ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
