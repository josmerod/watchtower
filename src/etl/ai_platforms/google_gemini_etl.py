"""Google Gemini ETL Module.

Specialized monitoring for Google AI platform updates including:
- Gemini model releases (Gemini Pro, Ultra, etc.)
- Google AI Studio updates
- Vertex AI developments
- Google AI blog and research
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

from src.etl.base import BaseETL


class GoogleGeminiETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """Specialized ETL for Google Gemini platform monitoring using BaseETL framework."""

    def __init__(self, **kwargs):
        """Initialize Google Gemini ETL."""
        super().__init__(
            name="google_gemini",
            description="Google Gemini and AI platform updates ETL",
            **kwargs,
        )

        self.sources = {
            "gemini_changelog": "https://ai.google.dev/gemini-api/docs/changelog",
            "ai_blog_rss": "https://blog.google/technology/ai/rss/",
            "developers_blog_rss": "https://developers.googleblog.com/feeds/posts/default/-/Gemini",
            "cloud_ai_blog_rss": "https://cloud.google.com/blog/topics/ai-machine-learning/rss.xml",
            "ai_studio": "https://ai.google.dev/",
            "vertex_ai": "https://cloud.google.com/vertex-ai",
        }

    def extract(self) -> list[dict[str, Any]]:
        """Extract Google AI platform updates from multiple sources.

        Returns:
            List of raw update dictionaries from all sources
        """
        self.logger.info("Starting extraction from Google AI sources")

        all_updates = []

        # Fetch RSS feeds
        all_updates.extend(self._fetch_ai_blog_rss())
        all_updates.extend(self._fetch_developers_blog_rss())
        all_updates.extend(self._fetch_cloud_ai_rss())

        # Fetch scraped sources
        all_updates.extend(self._scrape_gemini_changelog())
        all_updates.extend(self._scrape_ai_studio())

        self.logger.info(f"Extracted {len(all_updates)} total updates from all sources")
        return all_updates

    def transform(self, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform and filter updates to model-related content.

        Args:
            updates: Raw updates from all sources

        Returns:
            Filtered and processed updates
        """
        if not updates:
            self.logger.warning("No updates to transform")
            return []

        self.logger.info(f"Transforming {len(updates)} Google updates")

        # Filter for model-related content
        filtered = self._filter_model_updates(updates)

        # Process and deduplicate
        processed = []
        seen_titles = set()

        for update in filtered:
            title = update.get("title", "").strip()
            if not title or title in seen_titles:
                continue

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

        self.logger.info(
            f"Transformed and filtered to {len(processed)} unique model-related updates"
        )
        return processed

    def load(self, updates: list[dict[str, Any]]) -> None:
        """Load processed updates to JSON and CSV files.

        Args:
            updates: Processed update dictionaries
        """
        if not updates:
            self.logger.warning("No updates to load")
            return

        self.logger.info(f"Loading {len(updates)} Google updates")

        import json

        import pandas as pd

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save timestamped JSON
        json_file = self.output_dir / f"google_updates_{timestamp}.json"
        json_file.write_text(
            json.dumps(updates, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Save latest JSON
        latest_json = self.output_dir / "google_updates_latest.json"
        latest_json.write_text(
            json.dumps(updates, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Save CSV files
        try:
            df = pd.DataFrame(updates)

            # Flatten metadata column for CSV
            if "metadata" in df.columns:
                for key in ["api_source", "processed_at", "entry_id", "feed_url"]:
                    df[f"metadata_{key}"] = df["metadata"].apply(
                        lambda x: x.get(key, "") if isinstance(x, dict) else ""
                    )
                df = df.drop(columns=["metadata"])

            csv_file = self.output_dir / f"google_updates_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding="utf-8")

            latest_csv = self.output_dir / "google_updates_latest.csv"
            df.to_csv(latest_csv, index=False, encoding="utf-8")

            self.logger.info(
                f"Saved {len(updates)} updates to {json_file} and {csv_file}"
            )

        except Exception as e:
            self.logger.error(f"Error saving CSV: {e}")

    def _fetch_ai_blog_rss(self) -> list[dict[str, Any]]:
        """Fetch Google AI blog RSS feed."""
        try:
            self.logger.info("Fetching Google AI blog RSS")

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
                self.logger.warning("No entries found in Google AI blog RSS")
                return []

            updates = []
            for entry in feed.entries:
                update = {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", ""),
                    "content": (
                        getattr(entry, "content", [{}])[0].get("value", "")
                        if hasattr(entry, "content")
                        else ""
                    ),
                    "source": "google_ai_blog",
                    "source_type": "rss",
                    "provider": "google",
                    "entry_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                    "feed_url": self.sources["ai_blog_rss"],
                }
                updates.append(update)

            self.logger.info(f"Fetched {len(updates)} entries from Google AI blog")
            return updates

        except Exception as e:
            self.logger.error(f"Error fetching Google AI blog RSS: {e}")
            self.metrics.records_failed += 1
            return []

    def _fetch_developers_blog_rss(self) -> list[dict[str, Any]]:
        """Fetch Google Developers blog RSS feed."""
        try:
            self.logger.info("Fetching Google Developers blog RSS")

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
                self.logger.warning("No entries found in Google Developers blog RSS")
                return []

            updates = []
            for entry in feed.entries:
                update = {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", ""),
                    "content": (
                        getattr(entry, "content", [{}])[0].get("value", "")
                        if hasattr(entry, "content")
                        else ""
                    ),
                    "source": "google_developers_blog",
                    "source_type": "rss",
                    "provider": "google",
                    "entry_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                    "feed_url": self.sources["developers_blog_rss"],
                }
                updates.append(update)

            self.logger.info(f"Fetched {len(updates)} entries from Google Developers blog")
            return updates

        except Exception as e:
            self.logger.error(f"Error fetching Google Developers blog RSS: {e}")
            self.metrics.records_failed += 1
            return []

    def _fetch_cloud_ai_rss(self) -> list[dict[str, Any]]:
        """Fetch Google Cloud AI blog RSS feed."""
        try:
            self.logger.info("Fetching Google Cloud AI blog RSS")

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
                self.logger.warning("No entries found in Google Cloud AI blog RSS")
                return []

            updates = []
            for entry in feed.entries:
                update = {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", ""),
                    "content": (
                        getattr(entry, "content", [{}])[0].get("value", "")
                        if hasattr(entry, "content")
                        else ""
                    ),
                    "source": "google_cloud_ai_blog",
                    "source_type": "rss",
                    "provider": "google",
                    "entry_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                    "feed_url": self.sources["cloud_ai_blog_rss"],
                }
                updates.append(update)

            self.logger.info(f"Fetched {len(updates)} entries from Google Cloud AI blog")
            return updates

        except Exception as e:
            self.logger.error(f"Error fetching Google Cloud AI blog RSS: {e}")
            self.metrics.records_failed += 1
            return []

    def _scrape_gemini_changelog(self) -> list[dict[str, Any]]:
        """Scrape Gemini API changelog."""
        try:
            self.logger.info("Scraping Gemini API changelog")

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
                            "summary": (
                                content[:500] + "..." if len(content) > 500 else content
                            ),
                            "content": content,
                            "source": "gemini_changelog",
                            "source_type": "scraped",
                            "provider": "google",
                            "entry_id": f"gemini_changelog_{hash(title + published_at)}",
                        }
                    )

            self.logger.info(f"Scraped {len(updates)} updates from Gemini changelog")
            return updates

        except Exception as e:
            self.logger.error(f"Error scraping Gemini changelog: {e}")
            self.metrics.records_failed += 1
            return []

    def _scrape_ai_studio(self) -> list[dict[str, Any]]:
        """Scrape Google AI Studio for updates."""
        try:
            self.logger.info("Scraping Google AI Studio")

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
                            "summary": (
                                content[:500] + "..." if len(content) > 500 else content
                            ),
                            "content": content,
                            "source": "google_ai_studio",
                            "source_type": "scraped",
                            "provider": "google",
                            "entry_id": f"ai_studio_{hash(title + content[:100])}",
                        }
                    )

            self.logger.info(f"Scraped {len(updates)} updates from Google AI Studio")
            return updates

        except Exception as e:
            self.logger.error(f"Error scraping Google AI Studio: {e}")
            self.metrics.records_failed += 1
            return []

    def _filter_model_updates(
        self, updates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter updates to only include model-related content."""
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

        filtered = []
        for update in updates:
            text_content = f"{update.get('title', '')} {update.get('summary', '')} {update.get('content', '')}".lower()

            if any(keyword in text_content for keyword in google_keywords):
                filtered.append(update)

        self.logger.info(
            f"Filtered {len(filtered)} model-related updates from {len(updates)} total"
        )
        return filtered


if __name__ == "__main__":
    # Run the ETL pipeline
    etl = GoogleGeminiETL()
    etl.run()
