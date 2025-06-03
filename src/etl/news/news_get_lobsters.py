"""Lobsters ETL Module

This module fetches and processes content from Lobsters (lobste.rs), a technology-focused
community platform that aggregates programming and tech news with quality discussions.

Usage:
    python src/etl/news/news_get_lobsters.py

Output:
    - JSON file: data/lobsters/posts.json
    - CSV file: data/lobsters/posts.csv
"""

import json
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("LobstersETL")


class LobstersAPI:
    """Handler for Lobsters data extraction."""

    def __init__(self):
        """Initialize the Lobsters data fetcher."""
        self.base_url = "https://lobste.rs"
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
            }
        )

    def get_homepage_stories(self) -> list[dict[str, Any]]:
        """Fetch stories from the Lobsters homepage.

        Returns:
            List of story dictionaries
        """
        logger.info("Fetching stories from Lobsters homepage")

        try:
            response = self.session.get(f"{self.base_url}/", timeout=30)
            response.raise_for_status()

            return self._extract_stories_from_html(response.text)

        except requests.RequestException as e:
            logger.error(f"Error fetching homepage stories: {e}")
            return []

    def get_recent_stories(self) -> list[dict[str, Any]]:
        """Fetch recent stories from Lobsters.

        Returns:
            List of story dictionaries
        """
        logger.info("Fetching recent stories from Lobsters")

        try:
            response = self.session.get(f"{self.base_url}/recent", timeout=30)
            response.raise_for_status()

            return self._extract_stories_from_html(response.text)

        except requests.RequestException as e:
            logger.error(f"Error fetching recent stories: {e}")
            return []

    def get_stories_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Fetch stories filtered by tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of story dictionaries
        """
        logger.info(f"Fetching stories for tag: {tag}")

        try:
            response = self.session.get(f"{self.base_url}/t/{tag}", timeout=30)
            response.raise_for_status()

            return self._extract_stories_from_html(response.text, tag)

        except requests.RequestException as e:
            logger.error(f"Error fetching stories for tag {tag}: {e}")
            return []

    def get_top_stories(self, period: str = "week") -> list[dict[str, Any]]:
        """Fetch top stories from a given period.

        Args:
            period: Time period (week, month, year, all)

        Returns:
            List of story dictionaries
        """
        logger.info(f"Fetching top stories for period: {period}")

        try:
            response = self.session.get(f"{self.base_url}/top/{period}", timeout=30)
            response.raise_for_status()

            return self._extract_stories_from_html(response.text)

        except requests.RequestException as e:
            logger.error(f"Error fetching top stories for {period}: {e}")
            return []

    def _extract_stories_from_html(
        self, html: str, filter_tag: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract stories from HTML content.

        Args:
            html: HTML content from Lobsters
            filter_tag: Optional tag that was used to filter

        Returns:
            List of story dictionaries
        """
        stories = []

        # Extract story data using regex patterns
        # This is a simplified approach - BeautifulSoup would be better for production

        # Find story containers
        story_pattern = r'<div[^>]*class="[^"]*story[^"]*"[^>]*>(.*?)</div>\s*</div>'
        story_matches = re.findall(story_pattern, html, re.DOTALL)

        for i, story_html in enumerate(story_matches):
            try:
                story = {}

                # Extract title and URL
                title_pattern = (
                    r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*u-url[^"]*"[^>]*>(.*?)</a>'
                )
                title_match = re.search(title_pattern, story_html, re.DOTALL)
                if title_match:
                    story["url"] = title_match.group(1)
                    story["title"] = re.sub(
                        r"<[^>]+>", "", title_match.group(2)
                    ).strip()

                # Extract Lobsters discussion URL
                discussion_pattern = (
                    r'<a[^>]*href="(/s/[^"]*)"[^>]*>(\d+)\s*comments?</a>'
                )
                discussion_match = re.search(discussion_pattern, story_html)
                if discussion_match:
                    story["lobsters_url"] = urljoin(
                        self.base_url, discussion_match.group(1)
                    )
                    story["comments_count"] = int(discussion_match.group(2))
                else:
                    story["comments_count"] = 0

                # Extract score/votes
                score_pattern = r'<div[^>]*class="[^"]*score[^"]*"[^>]*>(\d+)</div>'
                score_match = re.search(score_pattern, story_html)
                if score_match:
                    story["score"] = int(score_match.group(1))
                else:
                    story["score"] = 0

                # Extract submitter
                submitter_pattern = r'by\s+<a[^>]*class="[^"]*u-author[^"]*"[^>]*href="/u/([^"]*)"[^>]*>([^<]*)</a>'
                submitter_match = re.search(submitter_pattern, story_html)
                if submitter_match:
                    story["submitter_username"] = submitter_match.group(1)
                    story["submitter_name"] = submitter_match.group(2).strip()

                # Extract tags
                tag_pattern = r'<a[^>]*class="[^"]*tag[^"]*"[^>]*href="/t/([^"]*)"[^>]*>([^<]*)</a>'
                tag_matches = re.findall(tag_pattern, story_html)
                if tag_matches:
                    story["tags"] = [
                        {"slug": tag[0], "name": tag[1].strip()} for tag in tag_matches
                    ]
                    story["tag_names"] = [tag["name"] for tag in story["tags"]]
                else:
                    story["tags"] = []
                    story["tag_names"] = []

                # Extract timestamp
                time_pattern = r'<span[^>]*class="[^"]*time[^"]*"[^>]*title="([^"]*)"'
                time_match = re.search(time_pattern, story_html)
                if time_match:
                    story["published_at"] = time_match.group(1)

                # Extract domain from URL
                if "url" in story:
                    try:
                        parsed_url = urlparse(story["url"])
                        story["domain"] = parsed_url.netloc
                    except:
                        story["domain"] = ""

                # Generate unique ID
                if "lobsters_url" in story:
                    story_id = story["lobsters_url"].split("/")[-1]
                    story["id"] = f"lobsters_{story_id}"
                else:
                    story["id"] = f"lobsters_{hash(story.get('title', ''))}"

                # Add metadata
                story["source"] = "lobste.rs"
                story["filter_tag"] = filter_tag
                story["fetched_at"] = datetime.utcnow().isoformat()

                stories.append(story)

            except Exception as e:
                logger.warning(f"Error processing story {i}: {e}")
                continue

        return stories


def get_lobsters_data(tags_to_track: list[str] = None) -> list[dict[str, Any]]:
    """Fetches content from Lobsters.

    Args:
        tags_to_track: List of tags to track

    Returns:
        List of processed story dictionaries
    """
    if tags_to_track is None:
        tags_to_track = [
            "programming",
            "web",
            "python",
            "javascript",
            "linux",
            "security",
            "databases",
            "devops",
            "ai",
            "rust",
            "golang",
            "mobile",
            "games",
            "networking",
            "science",
            "cryptography",
            "distributed",
            "compilers",
        ]

    logger.info(f"Fetching Lobsters data for tags: {tags_to_track}")

    api = LobstersAPI()
    all_stories = []
    seen_ids = set()

    try:
        # Fetch homepage stories (trending)
        logger.info("Fetching homepage stories...")
        homepage_stories = api.get_homepage_stories()

        for story in homepage_stories:
            if story.get("id") and story["id"] not in seen_ids:
                seen_ids.add(story["id"])
                all_stories.append(process_story(story))

        # Fetch recent stories
        logger.info("Fetching recent stories...")
        recent_stories = api.get_recent_stories()

        for story in recent_stories:
            if story.get("id") and story["id"] not in seen_ids:
                seen_ids.add(story["id"])
                all_stories.append(process_story(story))

        # Fetch top stories for this week
        logger.info("Fetching top stories...")
        top_stories = api.get_top_stories(period="week")

        for story in top_stories:
            if story.get("id") and story["id"] not in seen_ids:
                seen_ids.add(story["id"])
                all_stories.append(process_story(story))

        # Fetch stories by specific tags
        for tag in tags_to_track:
            logger.info(f"Fetching stories for tag: {tag}")

            tag_stories = api.get_stories_by_tag(tag)

            for story in tag_stories:
                if story.get("id") and story["id"] not in seen_ids:
                    seen_ids.add(story["id"])
                    all_stories.append(process_story(story, tracked_tag=tag))

            # Rate limiting
            time.sleep(2 + random.uniform(0, 1))

        logger.info(
            f"Successfully fetched {len(all_stories)} unique stories from Lobsters"
        )
        return all_stories

    except Exception as e:
        logger.error(f"Error fetching Lobsters data: {e}")
        return []


def process_story(
    story: dict[str, Any], tracked_tag: str | None = None
) -> dict[str, Any]:
    """Process and normalize a Lobsters story.

    Args:
        story: Raw story data
        tracked_tag: The tag that was used to find this story

    Returns:
        Processed story dictionary
    """
    processed_story = {
        "id": story.get("id"),
        "title": story.get("title", "").strip(),
        "url": story.get("url", ""),
        "lobsters_url": story.get("lobsters_url", ""),
        "domain": story.get("domain", ""),
        # Submitter information
        "submitter_username": story.get("submitter_username", ""),
        "submitter_name": story.get("submitter_name", ""),
        # Engagement metrics
        "score": story.get("score", 0),
        "comments_count": story.get("comments_count", 0),
        "engagement_score": 0,  # Will be calculated
        # Timestamps
        "published_at": story.get("published_at", ""),
        "fetched_at": story.get("fetched_at", ""),
        # Classification
        "tags": story.get("tags", []),
        "tag_names": story.get("tag_names", []),
        "filter_tag": story.get("filter_tag"),
        "tracked_tag": tracked_tag,
        # Metadata
        "source": "lobste.rs",
        "platform": "lobsters",
    }

    # Calculate engagement score
    score = processed_story.get("score", 0)
    comments = processed_story.get("comments_count", 0)
    processed_story["engagement_score"] = score + (comments * 1.5)

    return processed_story


def process_lobsters_stories(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Additional processing and enrichment of Lobsters stories.

    Args:
        stories: List of processed stories

    Returns:
        Enhanced stories with additional analysis
    """
    logger.info(f"Processing {len(stories)} Lobsters stories")

    enhanced_stories = []

    for story in stories:
        # Add story category based on tags
        tag_names = [tag.lower() for tag in story.get("tag_names", [])]

        if any(
            tag in ["ai", "machinelearning", "ml", "deeplearning"] for tag in tag_names
        ):
            category = "ai_ml"
        elif any(tag in ["security", "cryptography", "privacy"] for tag in tag_names):
            category = "security"
        elif any(
            tag in ["web", "javascript", "frontend", "react", "vue"]
            for tag in tag_names
        ):
            category = "web_development"
        elif any(tag in ["programming", "languages", "compilers"] for tag in tag_names):
            category = "programming_languages"
        elif any(tag in ["databases", "sql", "nosql"] for tag in tag_names):
            category = "databases"
        elif any(
            tag in ["devops", "docker", "kubernetes", "deployment"] for tag in tag_names
        ):
            category = "devops"
        elif any(tag in ["mobile", "ios", "android"] for tag in tag_names):
            category = "mobile"
        elif any(tag in ["games", "gamedev"] for tag in tag_names):
            category = "gaming"
        elif any(tag in ["science", "research", "papers"] for tag in tag_names):
            category = "research"
        else:
            category = "general_tech"

        story["story_category"] = category

        # Add quality indicator based on engagement
        engagement = story.get("engagement_score", 0)
        score = story.get("score", 0)
        comments = story.get("comments_count", 0)

        # Lobsters has high-quality community, so adjust thresholds accordingly
        if score >= 20 and comments >= 5:
            quality = "high"
        elif score >= 10 or comments >= 3:
            quality = "medium"
        elif score >= 5 or comments >= 1:
            quality = "decent"
        else:
            quality = "emerging"

        story["quality_indicator"] = quality

        # Add content type based on domain and URL patterns
        url = story.get("url", "").lower()
        domain = story.get("domain", "").lower()

        if any(
            domain.endswith(site)
            for site in [".edu", "arxiv.org", "scholar.google.com"]
        ):
            content_type = "academic"
        elif "github.com" in domain or "gitlab.com" in domain:
            content_type = "open_source"
        elif any(site in domain for site in ["blog", "medium.com", "dev.to"]):
            content_type = "blog_post"
        elif "youtube.com" in domain or "vimeo.com" in domain:
            content_type = "video"
        elif any(
            site in domain
            for site in ["news", "techcrunch", "ycombinator", "arstechnica"]
        ):
            content_type = "news"
        elif any(ext in url for ext in [".pdf", ".doc", ".docx"]):
            content_type = "document"
        else:
            content_type = "article"

        story["content_type"] = content_type

        # Add discussion potential based on tags and content type
        discussion_potential = 0

        # Base score from current engagement
        discussion_potential += min(engagement / 5, 10)

        # Bonus for controversial or discussion-prone topics
        if any(
            tag in tag_names for tag in ["politics", "privacy", "ethics", "philosophy"]
        ):
            discussion_potential += 8
        elif any(tag in tag_names for tag in ["security", "ai", "programming"]):
            discussion_potential += 5

        # Bonus for certain content types
        if content_type in ["academic", "blog_post"]:
            discussion_potential += 3
        elif content_type == "news":
            discussion_potential += 2

        # Bonus for high-quality indicators
        if quality == "high":
            discussion_potential += 5
        elif quality == "medium":
            discussion_potential += 3

        story["discussion_potential"] = round(discussion_potential, 1)

        # Add freshness based on timestamp
        published_at = story.get("published_at")
        if published_at:
            try:
                # Parse various timestamp formats that Lobsters might use
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                hours_since_pub = (
                    datetime.utcnow().replace(tzinfo=pub_date.tzinfo) - pub_date
                ).total_seconds() / 3600

                if hours_since_pub <= 2:
                    freshness = "very_fresh"
                elif hours_since_pub <= 12:
                    freshness = "fresh"
                elif hours_since_pub <= 48:
                    freshness = "recent"
                else:
                    freshness = "older"

                story["freshness"] = freshness
                story["hours_since_published"] = round(hours_since_pub, 1)

            except (ValueError, TypeError):
                story["freshness"] = "unknown"
                story["hours_since_published"] = None
        else:
            story["freshness"] = "unknown"
            story["hours_since_published"] = None

        enhanced_stories.append(story)

    # Sort by discussion potential for final ranking
    enhanced_stories.sort(key=lambda x: x.get("discussion_potential", 0), reverse=True)

    logger.info(f"Successfully processed {len(enhanced_stories)} stories")
    return enhanced_stories


def main():
    """Main execution function for Lobsters ETL."""
    logger.info("Starting Lobsters ETL process")

    try:
        # Create output directory
        project_root = get_project_root()
        output_dir = project_root / "data" / "lobsters"
        ensure_directories([output_dir])

        # Fetch data
        stories = get_lobsters_data()

        if not stories:
            logger.warning("No stories fetched from Lobsters")
            return

        # Process stories
        processed_stories = process_lobsters_stories(stories)

        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON output
        json_file = output_dir / f"lobsters_stories_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(processed_stories, f, indent=2, ensure_ascii=False)

        # CSV output
        csv_file = output_dir / f"lobsters_stories_{timestamp}.csv"
        import pandas as pd

        # Flatten the data for CSV
        csv_data = []
        for story in processed_stories:
            csv_row = story.copy()
            csv_row["tag_names"] = ", ".join(story.get("tag_names", []))
            # Remove complex nested data for CSV
            csv_row.pop("tags", None)
            csv_data.append(csv_row)

        df = pd.DataFrame(csv_data)
        df.to_csv(csv_file, index=False, encoding="utf-8")

        # Create symlinks for latest files
        latest_json = output_dir / "lobsters_stories_latest.json"
        latest_csv = output_dir / "lobsters_stories_latest.csv"

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

        logger.info(f"Successfully saved {len(processed_stories)} stories")
        logger.info(f"JSON output: {json_file}")
        logger.info(f"CSV output: {csv_file}")

        # Print summary statistics
        print("\n=== Lobsters ETL Summary ===")
        print(f"Total stories fetched: {len(processed_stories)}")
        print(
            f"Average discussion potential: {sum(s.get('discussion_potential', 0) for s in processed_stories) / len(processed_stories):.2f}"
        )
        print(f"Story categories: {get_category_distribution(processed_stories)}")
        print(f"Quality distribution: {get_quality_distribution(processed_stories)}")
        print(f"Content types: {get_content_type_distribution(processed_stories)}")

    except Exception as e:
        logger.error(f"Error in Lobsters ETL process: {e}")
        raise


def get_category_distribution(stories: list[dict[str, Any]]) -> dict[str, int]:
    """Get distribution of story categories."""
    distribution = {}
    for story in stories:
        category = story.get("story_category", "unknown")
        distribution[category] = distribution.get(category, 0) + 1

    return distribution


def get_quality_distribution(stories: list[dict[str, Any]]) -> dict[str, int]:
    """Get distribution of quality indicators."""
    distribution = {}
    for story in stories:
        quality = story.get("quality_indicator", "unknown")
        distribution[quality] = distribution.get(quality, 0) + 1

    return distribution


def get_content_type_distribution(stories: list[dict[str, Any]]) -> dict[str, int]:
    """Get distribution of content types."""
    distribution = {}
    for story in stories:
        content_type = story.get("content_type", "unknown")
        distribution[content_type] = distribution.get(content_type, 0) + 1

    return distribution


if __name__ == "__main__":
    main()
