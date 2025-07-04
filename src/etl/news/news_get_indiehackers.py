"""Indie Hackers ETL Module.

This module fetches and processes content from Indie Hackers community,
including posts about startups, entrepreneurship, and indie product discussions.

Usage:
    python src/etl/news/news_get_indiehackers.py

Output:
    - JSON file: data/indie_hackers/posts.json
    - CSV file: data/indie_hackers/posts.csv
"""

import json
import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import requests

# Add the project root to the path to ensure imports work correctly
from utils.file_system import ensure_directories, get_project_root
from utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("IndieHackersETL")


class IndieHackersAPI:
    """Handler for Indie Hackers data extraction."""

    def __init__(self):
        """Initialize the Indie Hackers scraper."""
        self.base_url = "https://www.indiehackers.com"
        self.session = requests.Session()

        # Set headers to mimic a real browser
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://www.indiehackers.com/",
            }
        )

    def get_trending_posts(self, pages: int = 3) -> list[dict[str, Any]]:
        """Fetch trending posts from Indie Hackers.

        Args:
            pages: Number of pages to fetch

        Returns:
            List of post dictionaries
        """
        posts = []

        for page in range(1, pages + 1):
            logger.info(f"Fetching trending posts page {page}")

            url = f"{self.base_url}/posts"
            if page > 1:
                url += f"?page={page}"

            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Extract posts from the response
                # This would require proper HTML parsing with BeautifulSoup
                # For now, we'll use a simplified approach with regex
                page_posts = self._extract_posts_from_html(response.text)
                posts.extend(page_posts)

                # Rate limiting
                time.sleep(2 + random.uniform(0, 1))

            except requests.RequestException as e:
                logger.error(f"Error fetching trending posts page {page}: {e}")
                continue

        return posts

    def get_recent_posts(self, pages: int = 3) -> list[dict[str, Any]]:
        """Fetch recent posts from Indie Hackers.

        Args:
            pages: Number of pages to fetch

        Returns:
            List of post dictionaries
        """
        posts = []

        for page in range(1, pages + 1):
            logger.info(f"Fetching recent posts page {page}")

            url = f"{self.base_url}/posts/newest"
            if page > 1:
                url += f"?page={page}"

            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                page_posts = self._extract_posts_from_html(response.text)
                posts.extend(page_posts)

                # Rate limiting
                time.sleep(2 + random.uniform(0, 1))

            except requests.RequestException as e:
                logger.error(f"Error fetching recent posts page {page}: {e}")
                continue

        return posts

    def get_group_posts(self, group_slug: str, pages: int = 2) -> list[dict[str, Any]]:
        """Fetch posts from a specific group.

        Args:
            group_slug: The group slug (e.g., 'bootstrapped')
            pages: Number of pages to fetch

        Returns:
            List of post dictionaries
        """
        posts = []

        for page in range(1, pages + 1):
            logger.info(f"Fetching posts from group '{group_slug}' page {page}")

            url = f"{self.base_url}/group/{group_slug}"
            if page > 1:
                url += f"?page={page}"

            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                page_posts = self._extract_posts_from_html(response.text, group_slug)
                posts.extend(page_posts)

                # Rate limiting
                time.sleep(2 + random.uniform(0, 1))

            except requests.RequestException as e:
                logger.error(
                    f"Error fetching group '{group_slug}' posts page {page}: {e}"
                )
                continue

        return posts

    def _extract_posts_from_html(
        self, html: str, group_slug: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract posts from HTML content.

        Args:
            html: HTML content
            group_slug: Optional group slug

        Returns:
            List of post dictionaries
        """
        posts = []

        # This is a simplified implementation
        # In a real scenario, you would use BeautifulSoup or similar

        # Extract post URLs using regex patterns
        post_url_pattern = r'href="(/post/[^"]+)"'
        post_urls = re.findall(post_url_pattern, html)

        # Extract post titles
        title_pattern = r"<h3[^>]*>([^<]+)</h3>"
        titles = re.findall(title_pattern, html)

        # Extract author information
        author_pattern = r'by\s+<a[^>]*href="/[^/]+/([^"]+)"[^>]*>([^<]+)</a>'
        authors = re.findall(author_pattern, html)

        # Extract timestamps (simplified)
        time_pattern = r"(\d+)\s+(day|hour|minute)s?\s+ago"
        timestamps = re.findall(time_pattern, html)

        # Combine extracted data (this is a simplified approach)
        max_posts = min(len(post_urls), len(titles), 20)  # Limit to 20 posts per page

        for i in range(max_posts):
            try:
                post_url = post_urls[i] if i < len(post_urls) else ""
                title = titles[i] if i < len(titles) else ""

                # Create a basic post structure
                post = {
                    "id": f"ih_{hash(post_url)}"
                    if post_url
                    else f"ih_{i}_{int(time.time())}",
                    "title": title.strip(),
                    "url": urljoin(self.base_url, post_url) if post_url else "",
                    "path": post_url,
                    "group_slug": group_slug,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "indiehackers.com",
                }

                # Add author if available
                if i < len(authors):
                    post["author_username"] = authors[i][0]
                    post["author_name"] = authors[i][1]

                # Add timestamp if available
                if i < len(timestamps):
                    time_value, time_unit = timestamps[i]
                    post["relative_time"] = (
                        f"{time_value} {time_unit}{'s' if int(time_value) != 1 else ''} ago"
                    )

                    # Convert to approximate timestamp
                    now = datetime.now(timezone.utc)
                    if time_unit == "minute":
                        estimated_time = now - timedelta(minutes=int(time_value))
                    elif time_unit == "hour":
                        estimated_time = now - timedelta(hours=int(time_value))
                    elif time_unit == "day":
                        estimated_time = now - timedelta(days=int(time_value))
                    else:
                        estimated_time = now

                    post["estimated_published_at"] = estimated_time.isoformat()

                posts.append(post)

            except (IndexError, ValueError) as e:
                logger.warning(f"Error processing post {i}: {e}")
                continue

        return posts

    def get_post_details(self, post_url: str) -> dict[str, Any] | None:
        """Fetch detailed information for a specific post.

        Args:
            post_url: URL of the post

        Returns:
            Detailed post information or None
        """
        try:
            response = self.session.get(post_url, timeout=30)
            response.raise_for_status()

            # Extract additional details from the post page
            html = response.text

            details = {}

            # Extract content preview
            content_pattern = (
                r'<div[^>]*class="[^"]*post-content[^"]*"[^>]*>(.*?)</div>'
            )
            content_match = re.search(content_pattern, html, re.DOTALL)
            if content_match:
                content = re.sub(r"<[^>]+>", "", content_match.group(1))
                details["content_preview"] = (
                    content.strip()[:500] + "..."
                    if len(content) > 500
                    else content.strip()
                )

            # Extract vote count
            vote_pattern = r"(\d+)\s+votes?"
            vote_match = re.search(vote_pattern, html)
            if vote_match:
                details["votes"] = int(vote_match.group(1))

            # Extract comment count
            comment_pattern = r"(\d+)\s+comments?"
            comment_match = re.search(comment_pattern, html)
            if comment_match:
                details["comments_count"] = int(comment_match.group(1))

            return details

        except requests.RequestException as e:
            logger.error(f"Error fetching post details for {post_url}: {e}")
            return None


def get_indiehackers_data(groups_to_track: list[str] | None = None) -> list[dict[str, Any]]:
    """Fetches content from Indie Hackers.

    Args:
        groups_to_track: List of groups to track

    Returns:
        List of processed post dictionaries
    """
    if groups_to_track is None:
        groups_to_track = [
            "bootstrapped",
            "saas",
            "makers",
            "founders",
            "revenue",
            "growth",
            "marketing",
            "product",
            "tech",
            "feedback",
        ]

    logger.info(f"Fetching Indie Hackers data for groups: {groups_to_track}")

    api = IndieHackersAPI()
    all_posts = []
    seen_urls = set()

    try:
        # Fetch trending posts
        logger.info("Fetching trending posts...")
        trending_posts = api.get_trending_posts(pages=2)

        for post in trending_posts:
            if post.get("url") and post["url"] not in seen_urls:
                seen_urls.add(post["url"])
                all_posts.append(process_post(post))

        # Fetch recent posts
        logger.info("Fetching recent posts...")
        recent_posts = api.get_recent_posts(pages=2)

        for post in recent_posts:
            if post.get("url") and post["url"] not in seen_urls:
                seen_urls.add(post["url"])
                all_posts.append(process_post(post))

        # Fetch posts from specific groups
        for group in groups_to_track:
            logger.info(f"Fetching posts from group: {group}")

            group_posts = api.get_group_posts(group, pages=1)

            for post in group_posts:
                if post.get("url") and post["url"] not in seen_urls:
                    seen_urls.add(post["url"])
                    all_posts.append(process_post(post, tracked_group=group))

            # Rate limiting between groups
            time.sleep(3)

        logger.info(
            f"Successfully fetched {len(all_posts)} unique posts from Indie Hackers"
        )
        return all_posts

    except Exception as e:
        logger.error(f"Error fetching Indie Hackers data: {e}")
        return []


def process_post(
    post: dict[str, Any], tracked_group: str | None = None
) -> dict[str, Any]:
    """Process and normalize an Indie Hackers post.

    Args:
        post: Raw post data
        tracked_group: The group that was used to find this post

    Returns:
        Processed post dictionary
    """
    processed_post = {
        "id": post.get("id"),
        "title": post.get("title", "").strip(),
        "url": post.get("url", ""),
        "path": post.get("path", ""),
        # Author information
        "author_username": post.get("author_username", ""),
        "author_name": post.get("author_name", ""),
        # Timestamps
        "relative_time": post.get("relative_time", ""),
        "estimated_published_at": post.get("estimated_published_at", ""),
        "fetched_at": post.get("fetched_at", ""),
        # Engagement metrics (will be filled if available)
        "votes": post.get("votes", 0),
        "comments_count": post.get("comments_count", 0),
        "engagement_score": 0,  # Will be calculated
        # Classification
        "group_slug": post.get("group_slug"),
        "tracked_group": tracked_group,
        # Content
        "content_preview": post.get("content_preview", ""),
        # Metadata
        "source": "indiehackers.com",
        "platform": "indie_hackers",
    }

    # Calculate engagement score
    votes = processed_post.get("votes", 0)
    comments = processed_post.get("comments_count", 0)
    processed_post["engagement_score"] = votes + (comments * 2)

    return processed_post


def process_indiehackers_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Additional processing and enrichment of Indie Hackers posts.

    Args:
        posts: List of processed posts

    Returns:
        Enhanced posts with additional analysis
    """
    logger.info(f"Processing {len(posts)} Indie Hackers posts")

    enhanced_posts = []

    for post in posts:
        # Add post category based on title keywords
        title = post.get("title", "").lower()

        if any(
            keyword in title
            for keyword in ["revenue", "mrr", "arr", "profit", "income", "$"]
        ):
            category = "revenue_sharing"
        elif any(
            keyword in title
            for keyword in ["launch", "launched", "built", "made", "created"]
        ):
            category = "product_launch"
        elif any(
            keyword in title
            for keyword in ["marketing", "growth", "traffic", "users", "customers"]
        ):
            category = "growth_marketing"
        elif any(
            keyword in title for keyword in ["feedback", "roast", "review", "critique"]
        ):
            category = "feedback_request"
        elif any(
            keyword in title
            for keyword in ["advice", "help", "tips", "how", "question"]
        ):
            category = "advice_seeking"
        elif any(
            keyword in title
            for keyword in ["story", "journey", "experience", "learned"]
        ):
            category = "experience_sharing"
        else:
            category = "discussion"

        post["post_category"] = category

        # Add interest level based on engagement
        engagement = post.get("engagement_score", 0)
        if engagement >= 50:
            interest_level = "high"
        elif engagement >= 10:
            interest_level = "medium"
        elif engagement > 0:
            interest_level = "low"
        else:
            interest_level = "new"

        post["interest_level"] = interest_level

        # Add freshness indicator
        relative_time = post.get("relative_time", "")
        if "minute" in relative_time or "hour" in relative_time:
            freshness = "very_fresh"
        elif "1 day" in relative_time:
            freshness = "fresh"
        elif "day" in relative_time:
            days_match = re.search(r"(\d+) days?", relative_time)
            if days_match and int(days_match.group(1)) <= 7:
                freshness = "recent"
            else:
                freshness = "older"
        else:
            freshness = "unknown"

        post["freshness"] = freshness

        # Add priority score for ranking
        priority_score = 0

        # Base score from engagement
        priority_score += min(post.get("engagement_score", 0), 20)

        # Bonus for certain categories
        if post["post_category"] in ["revenue_sharing", "product_launch"]:
            priority_score += 15
        elif post["post_category"] in ["growth_marketing", "experience_sharing"]:
            priority_score += 10
        elif post["post_category"] == "feedback_request":
            priority_score += 5

        # Bonus for freshness
        if post["freshness"] == "very_fresh":
            priority_score += 10
        elif post["freshness"] == "fresh":
            priority_score += 7
        elif post["freshness"] == "recent":
            priority_score += 3

        # Bonus for specific groups
        if post.get("tracked_group") in ["bootstrapped", "saas", "revenue"]:
            priority_score += 5

        post["priority_score"] = round(priority_score, 1)

        enhanced_posts.append(post)

    # Sort by priority score for final ranking
    enhanced_posts.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    logger.info(f"Successfully processed {len(enhanced_posts)} posts")
    return enhanced_posts


def main():
    """Main execution function for Indie Hackers ETL."""
    logger.info("Starting Indie Hackers ETL process")

    try:
        # Create output directory
        from pathlib import Path
        project_root = Path(get_project_root())
        output_dir = project_root / "data" / "indie_hackers"
        ensure_directories([str(output_dir)])

        # Fetch data
        posts = get_indiehackers_data()

        if not posts:
            logger.warning("No posts fetched from Indie Hackers")
            return

        # Process posts
        processed_posts = process_indiehackers_posts(posts)

        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON output
        json_file = output_dir / f"indiehackers_posts_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(processed_posts, f, indent=2, ensure_ascii=False)

        # CSV output
        csv_file = output_dir / f"indiehackers_posts_{timestamp}.csv"
        import pandas as pd

        df = pd.DataFrame(processed_posts)
        df.to_csv(csv_file, index=False, encoding="utf-8")

        # Create symlinks for latest files
        latest_json = output_dir / "indiehackers_posts_latest.json"
        latest_csv = output_dir / "indiehackers_posts_latest.csv"

        # Remove existing symlinks if they exist
        for latest_file in [latest_json, latest_csv]:
            if latest_file.exists():
                latest_file.unlink()

        # Create new symlinks (works on both Unix and Windows)
        try:
            latest_json.symlink_to(json_file.name)
            latest_csv.symlink_to(csv_file.name)
        except OSError:
            # Fallback: copy files if symlinks aren't supported
            import shutil

            shutil.copy2(json_file, latest_json)
            shutil.copy2(csv_file, latest_csv)

        logger.info(f"Successfully saved {len(processed_posts)} posts")
        logger.info(f"JSON output: {json_file}")
        logger.info(f"CSV output: {csv_file}")

        # Print summary statistics
        print("\n=== Indie Hackers ETL Summary ===")
        print(f"Total posts fetched: {len(processed_posts)}")
        print(
            f"Average priority score: {sum(p.get('priority_score', 0) for p in processed_posts) / len(processed_posts):.2f}"
        )
        print(f"Post categories: {get_category_distribution(processed_posts)}")
        print(f"Interest levels: {get_interest_distribution(processed_posts)}")
        print(f"Freshness distribution: {get_freshness_distribution(processed_posts)}")

    except Exception as e:
        logger.error(f"Error in Indie Hackers ETL process: {e}")
        raise


def get_category_distribution(posts: list[dict[str, Any]]) -> dict[str, int]:
    """Get distribution of post categories."""
    distribution = {}
    for post in posts:
        category = post.get("post_category", "unknown")
        distribution[category] = distribution.get(category, 0) + 1

    return distribution


def get_interest_distribution(posts: list[dict[str, Any]]) -> dict[str, int]:
    """Get distribution of interest levels."""
    distribution = {}
    for post in posts:
        interest = post.get("interest_level", "unknown")
        distribution[interest] = distribution.get(interest, 0) + 1

    return distribution


def get_freshness_distribution(posts: list[dict[str, Any]]) -> dict[str, int]:
    """Get distribution of freshness levels."""
    distribution = {}
    for post in posts:
        freshness = post.get("freshness", "unknown")
        distribution[freshness] = distribution.get(freshness, 0) + 1

    return distribution


if __name__ == "__main__":
    main()
