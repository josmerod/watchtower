"""Google Gemini ETL Module.

Specialized monitoring for Google AI platform updates including:
- Gemini model releases (Gemini Pro, Ultra, etc.)
- Google AI Studio updates
- Vertex AI developments
- Google AI blog and research
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

# Ensure project root is on path
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("GoogleGeminiETL")


class GoogleGeminiETL:
    """Specialized ETL for Google Gemini platform monitoring."""

    def __init__(self):
        """Initialize Google Gemini ETL."""
        self.project_root = get_project_root()
        self.output_dir = os.path.join(self.project_root, "data/ai_models/google")
        ensure_directories(["data/ai_models/google"])

        self.sources = {
            "gemini_changelog": "https://ai.google.dev/gemini-api/docs/changelog",
            "ai_blog_rss": "https://blog.google/technology/ai/rss/",
            "developers_blog_rss": "https://developers.googleblog.com/feeds/posts/default/-/Gemini",
            "cloud_ai_blog_rss": "https://cloud.google.com/blog/topics/ai-machine-learning/rss.xml",
            "ai_studio": "https://ai.google.dev/",
            "vertex_ai": "https://cloud.google.com/vertex-ai",
        }

    async def fetch_google_updates(self) -> list[dict[str, Any]]:
        """Fetch all Google AI platform updates.

        Returns:
            List of Google update dictionaries.
        """
        all_updates = []

        # Fetch RSS feeds
        ai_blog_updates = await self._fetch_ai_blog_rss()
        developers_blog_updates = await self._fetch_developers_blog_rss()
        cloud_ai_updates = await self._fetch_cloud_ai_rss()

        # Fetch scraped sources
        changelog_updates = await self._scrape_gemini_changelog()
        ai_studio_updates = await self._scrape_ai_studio()

        all_updates.extend(ai_blog_updates)
        all_updates.extend(developers_blog_updates)
        all_updates.extend(cloud_ai_updates)
        all_updates.extend(changelog_updates)
        all_updates.extend(ai_studio_updates)

        # Filter for model-related content
        model_updates = self._filter_model_updates(all_updates)

        return model_updates

    async def _fetch_ai_blog_rss(self) -> list[dict[str, Any]]:
        """Fetch Google AI blog RSS feed."""
        try:
            logger.info("Fetching Google AI blog RSS")

            response = requests.get(
                self.sources["ai_blog_rss"],
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning("No entries found in Google AI blog RSS")
                return []

            updates = []
            for entry in feed.entries:
                update = {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", ""),
                    "content": getattr(entry, "content", [{}])[0].get("value", "")
                    if hasattr(entry, "content")
                    else "",
                    "source": "google_ai_blog",
                    "source_type": "rss",
                    "provider": "google",
                    "entry_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                    "feed_url": self.sources["ai_blog_rss"],
                }
                updates.append(update)

            logger.info(f"Fetched {len(updates)} entries from Google AI blog")
            return updates

        except Exception as e:
            logger.error(f"Error fetching Google AI blog RSS: {e}")
            return []

    async def _fetch_developers_blog_rss(self) -> list[dict[str, Any]]:
        """Fetch Google Developers blog RSS feed."""
        try:
            logger.info("Fetching Google Developers blog RSS")

            response = requests.get(
                self.sources["developers_blog_rss"],
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning("No entries found in Google Developers blog RSS")
                return []

            updates = []
            for entry in feed.entries:
                update = {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", ""),
                    "content": getattr(entry, "content", [{}])[0].get("value", "")
                    if hasattr(entry, "content")
                    else "",
                    "source": "google_developers_blog",
                    "source_type": "rss",
                    "provider": "google",
                    "entry_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                    "feed_url": self.sources["developers_blog_rss"],
                }
                updates.append(update)

            logger.info(f"Fetched {len(updates)} entries from Google Developers blog")
            return updates

        except Exception as e:
            logger.error(f"Error fetching Google Developers blog RSS: {e}")
            return []

    async def _fetch_cloud_ai_rss(self) -> list[dict[str, Any]]:
        """Fetch Google Cloud AI blog RSS feed."""
        try:
            logger.info("Fetching Google Cloud AI blog RSS")

            response = requests.get(
                self.sources["cloud_ai_blog_rss"],
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning("No entries found in Google Cloud AI blog RSS")
                return []

            updates = []
            for entry in feed.entries:
                update = {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", ""),
                    "content": getattr(entry, "content", [{}])[0].get("value", "")
                    if hasattr(entry, "content")
                    else "",
                    "source": "google_cloud_ai_blog",
                    "source_type": "rss",
                    "provider": "google",
                    "entry_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                    "feed_url": self.sources["cloud_ai_blog_rss"],
                }
                updates.append(update)

            logger.info(f"Fetched {len(updates)} entries from Google Cloud AI blog")
            return updates

        except Exception as e:
            logger.error(f"Error fetching Google Cloud AI blog RSS: {e}")
            return []

    async def _scrape_gemini_changelog(self) -> list[dict[str, Any]]:
        """Scrape Gemini API changelog."""
        try:
            logger.info("Scraping Gemini API changelog")

            response = requests.get(
                self.sources["gemini_changelog"],
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            updates = []

            # Look for changelog entries
            changelog_sections = soup.find_all(
                ["section", "div", "article"],
                class_=re.compile(r"changelog|update|release|entry"),
            )

            if not changelog_sections:
                # Try finding by date patterns
                date_headers = soup.find_all(
                    ["h1", "h2", "h3", "h4"],
                    string=re.compile(
                        r"202[3-9]|January|February|March|April|May|June|July|August|September|October|November|December"
                    ),
                )
                changelog_sections = []
                for header in date_headers:
                    parent = header.find_parent(["section", "div", "article"])
                    if parent:
                        changelog_sections.append(parent)

            for section in changelog_sections[:25]:  # Limit to recent entries
                # Extract title
                title_elem = section.find(["h1", "h2", "h3", "h4"])
                title = (
                    title_elem.get_text(strip=True)
                    if title_elem
                    else "Gemini API Update"
                )

                # Extract date
                date_match = re.search(
                    r"(202[3-9]-\d{2}-\d{2}|\w+ \d{1,2}, 202[3-9])",
                    title + " " + section.get_text(),
                )
                published_at = (
                    date_match.group(1) if date_match else datetime.now().isoformat()
                )

                # Extract content
                content_paragraphs = section.find_all(["p", "li"])
                content = " ".join([p.get_text(strip=True) for p in content_paragraphs])

                if content and len(content.strip()) > 10:  # Filter out empty entries
                    updates.append(
                        {
                            "title": title,
                            "url": self.sources["gemini_changelog"],
                            "published_at": published_at,
                            "summary": content[:500] + "..."
                            if len(content) > 500
                            else content,
                            "content": content,
                            "source": "gemini_changelog",
                            "source_type": "scraped",
                            "provider": "google",
                            "entry_id": f"gemini_changelog_{hash(title + published_at)}",
                        }
                    )

            logger.info(f"Scraped {len(updates)} updates from Gemini changelog")
            return updates

        except Exception as e:
            logger.error(f"Error scraping Gemini changelog: {e}")
            return []

    async def _scrape_ai_studio(self) -> list[dict[str, Any]]:
        """Scrape Google AI Studio for updates."""
        try:
            logger.info("Scraping Google AI Studio")

            response = requests.get(
                self.sources["ai_studio"],
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            updates = []

            # Look for announcement or update sections
            update_sections = soup.find_all(
                ["section", "div"],
                class_=re.compile(r"announcement|update|news|feature"),
            )

            if not update_sections:
                # Try finding model information
                model_sections = soup.find_all(
                    ["section", "div"], class_=re.compile(r"model|capability")
                )
                update_sections = model_sections

            for section in update_sections[:10]:  # Limit to recent entries
                # Extract title
                title_elem = section.find(["h1", "h2", "h3", "h4"])
                title = (
                    title_elem.get_text(strip=True)
                    if title_elem
                    else "Google AI Studio Update"
                )

                # Extract content
                content_paragraphs = section.find_all(["p", "li"])
                content = " ".join([p.get_text(strip=True) for p in content_paragraphs])

                if content and len(content.strip()) > 10:  # Filter out empty entries
                    updates.append(
                        {
                            "title": title,
                            "url": self.sources["ai_studio"],
                            "published_at": datetime.now().isoformat(),
                            "summary": content[:500] + "..."
                            if len(content) > 500
                            else content,
                            "content": content,
                            "source": "google_ai_studio",
                            "source_type": "scraped",
                            "provider": "google",
                            "entry_id": f"ai_studio_{hash(title + content[:100])}",
                        }
                    )

            logger.info(f"Scraped {len(updates)} updates from Google AI Studio")
            return updates

        except Exception as e:
            logger.error(f"Error scraping Google AI Studio: {e}")
            return []

    def _filter_model_updates(
        self, updates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter updates to only include model-related content."""
        filtered = []

        google_keywords = [
            "gemini",
            "bard",
            "palm",
            "model",
            "ai",
            "launch",
            "release",
            "update",
            "version",
            "capability",
            "feature",
            "improvement",
            "performance",
            "beta",
            "gemini pro",
            "gemini ultra",
            "gemini nano",
            "palm 2",
            "vertex ai",
            "ai studio",
            "makersuite",
            "api",
            "generative ai",
            "llm",
            "multimodal",
        ]

        for update in updates:
            text_content = f"{update.get('title', '')} {update.get('summary', '')} {update.get('content', '')}".lower()

            if any(keyword in text_content for keyword in google_keywords):
                filtered.append(update)

        logger.info(
            f"Filtered {len(filtered)} model-related updates from {len(updates)} total Google updates"
        )
        return filtered

    def process_updates(self, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process and standardize Google updates."""
        logger.info(f"Processing {len(updates)} Google updates")

        processed = []
        seen_titles = set()

        for update in updates:
            title = update.get("title", "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)

                processed_update = {
                    "title": title,
                    "url": update.get("url", ""),
                    "provider": "google",
                    "source": update.get("source", ""),
                    "source_type": update.get("source_type", "unknown"),
                    "published_at": update.get("published_at", ""),
                    "summary": update.get("summary", ""),
                    "content": update.get("content", ""),
                    "metadata": {
                        "api_source": update.get("source_type", "unknown"),
                        "processed_at": datetime.now().isoformat(),
                        "entry_id": update.get("entry_id", ""),
                        "feed_url": update.get("feed_url", ""),
                    },
                }
                processed.append(processed_update)

        logger.info(f"Successfully processed {len(processed)} unique Google updates")
        return processed

    def save_updates(self, updates: list[dict[str, Any]]) -> None:
        """Save Google updates to JSON and CSV files."""
        if not updates:
            logger.warning("No Google updates to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON files
        json_file = os.path.join(self.output_dir, f"google_updates_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(updates, f, indent=2, ensure_ascii=False)

        latest_json = os.path.join(self.output_dir, "google_updates_latest.json")
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(updates, f, indent=2, ensure_ascii=False)

        # Save CSV files
        try:
            import pandas as pd

            df = pd.DataFrame(updates)

            csv_file = os.path.join(self.output_dir, f"google_updates_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding="utf-8")

            latest_csv = os.path.join(self.output_dir, "google_updates_latest.csv")
            df.to_csv(latest_csv, index=False, encoding="utf-8")

            logger.info(
                f"Saved {len(updates)} Google updates to {json_file} and {csv_file}"
            )

        except ImportError:
            logger.warning("pandas not available, skipping CSV export")
            logger.info(f"Saved {len(updates)} Google updates to {json_file}")


async def main():
    """Main entry point for the Google Gemini ETL process."""
    logger.info("Starting Google Gemini ETL process")

    try:
        etl = GoogleGeminiETL()

        # Fetch updates
        updates = await etl.fetch_google_updates()

        if not updates:
            logger.warning("No Google updates retrieved, ETL process will exit")
            return

        # Process updates
        processed_updates = etl.process_updates(updates)

        # Save results
        etl.save_updates(processed_updates)

        logger.info(
            f"Google Gemini ETL completed successfully. Processed {len(processed_updates)} updates."
        )

    except Exception as e:
        logger.error(f"Error in Google Gemini ETL process: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
