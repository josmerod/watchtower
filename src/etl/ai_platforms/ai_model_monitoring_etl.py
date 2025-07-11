"""AI Model Monitoring ETL Module.

Monitors new model releases and updates from major AI providers:
- OpenAI (GPT models)
- Anthropic (Claude models)
- Google (Gemini models)

Uses RSS feeds where available, web scraping as fallback.
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

# Ensure project root is on path
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("AIModelMonitoringETL")


class AIModelMonitoringETL:
    """ETL system for monitoring AI model releases and updates."""

    def __init__(self):
        """Initialize the AI model monitoring ETL."""
        self.project_root = get_project_root()
        self.output_dir = os.path.join(self.project_root, "data/ai_models")
        ensure_directories(["data/ai_models"])

        # RSS feeds and URLs for each provider
        self.sources = {
            "openai": {
                "changelog_url": "https://platform.openai.com/docs/changelog",
                "blog_rss": "https://openai.com/blog/rss.xml",
                "research_rss": "https://openai.com/research/rss.xml",
                # Unofficial community feeds found in research
                "community_models_json": "https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/api_request_parallel_processor.py",
                "platform_docs": "https://platform.openai.com/docs/models",
            },
            "anthropic": {
                "news_url": "https://www.anthropic.com/news",
                "blog_url": "https://www.anthropic.com/blog",
                "research_url": "https://www.anthropic.com/research",
                "claude_updates": "https://claude.ai/updates",
            },
            "google": {
                "gemini_changelog": "https://ai.google.dev/gemini-api/docs/changelog",
                "ai_blog_rss": "https://blog.google/technology/ai/rss/",
                "developers_blog": "https://developers.googleblog.com/feeds/posts/default/-/Gemini",
                "cloud_ai_blog": "https://cloud.google.com/blog/topics/ai-machine-learning/rss.xml",
            },
        }

    async def fetch_all_sources(self) -> list[dict[str, Any]]:
        """Fetch AI model updates from all sources.

        Returns:
            List of model update dictionaries.
        """
        all_updates = []

        # Fetch RSS feeds concurrently
        rss_tasks = []

        # OpenAI RSS feeds
        rss_tasks.append(
            self._fetch_rss_feed("openai_blog", self.sources["openai"]["blog_rss"])
        )
        rss_tasks.append(
            self._fetch_rss_feed(
                "openai_research", self.sources["openai"]["research_rss"]
            )
        )

        # Google RSS feeds
        rss_tasks.append(
            self._fetch_rss_feed(
                "google_ai_blog", self.sources["google"]["ai_blog_rss"]
            )
        )
        rss_tasks.append(
            self._fetch_rss_feed(
                "google_cloud_ai", self.sources["google"]["cloud_ai_blog"]
            )
        )
        rss_tasks.append(
            self._fetch_rss_feed(
                "google_developers", self.sources["google"]["developers_blog"]
            )
        )

        # Execute RSS fetches concurrently
        rss_results = await asyncio.gather(*rss_tasks, return_exceptions=True)

        for result in rss_results:
            if isinstance(result, list):
                all_updates.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"RSS fetch failed: {result}")

        # Fetch web scraped sources
        scraped_updates = await self._fetch_scraped_sources()
        all_updates.extend(scraped_updates)

        # Filter for model-related content
        model_updates = self._filter_model_updates(all_updates)

        return model_updates

    async def _fetch_rss_feed(
        self, source_name: str, rss_url: str
    ) -> list[dict[str, Any]]:
        """Fetch and parse RSS feed.

        Args:
            source_name: Name of the source
            rss_url: RSS feed URL

        Returns:
            List of parsed entries
        """
        try:
            logger.info(f"Fetching RSS feed {source_name}: {rss_url}")

            # Use requests with timeout to avoid hangs
            response = requests.get(
                rss_url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if hasattr(feed, "status") and feed.status != 200:
                logger.warning(f"RSS feed {source_name} returned status {feed.status}")
                return []

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed {source_name}")
                return []

            entries = []
            for entry in feed.entries:
                parsed_entry = {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", ""),
                    "content": getattr(entry, "content", [{}])[0].get("value", "")
                    if hasattr(entry, "content")
                    else "",
                    "source": source_name,
                    "source_type": "rss",
                    "provider": self._get_provider_from_source(source_name),
                    "entry_id": getattr(entry, "id", "") or getattr(entry, "link", ""),
                    "feed_url": rss_url,
                }
                entries.append(parsed_entry)

            logger.info(
                f"Successfully fetched {len(entries)} entries from {source_name}"
            )
            return entries

        except Exception as e:
            logger.error(f"Error fetching RSS feed {source_name} at {rss_url}: {e}")
            return []

    async def _fetch_scraped_sources(self) -> list[dict[str, Any]]:
        """Fetch updates from sources requiring web scraping.

        Returns:
            List of scraped update dictionaries.
        """
        scraped_updates = []

        # OpenAI changelog scraping
        openai_updates = await self._scrape_openai_changelog()
        scraped_updates.extend(openai_updates)

        # Anthropic news scraping
        anthropic_updates = await self._scrape_anthropic_news()
        scraped_updates.extend(anthropic_updates)

        # Google Gemini changelog scraping
        gemini_updates = await self._scrape_gemini_changelog()
        scraped_updates.extend(gemini_updates)

        return scraped_updates

    async def _scrape_openai_changelog(self) -> list[dict[str, Any]]:
        """Scrape OpenAI platform changelog for model updates.

        Returns:
            List of changelog entries.
        """
        try:
            logger.info("Scraping OpenAI changelog")

            response = requests.get(
                self.sources["openai"]["changelog_url"],
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            updates = []

            # Look for changelog entries - these vary by site structure
            changelog_sections = soup.find_all(
                ["section", "div"], class_=re.compile(r"changelog|update|release")
            )

            if not changelog_sections:
                # Try alternative selectors
                changelog_sections = soup.find_all(
                    ["h2", "h3", "div"],
                    string=re.compile(
                        r"202[3-9]|January|February|March|April|May|June|July|August|September|October|November|December"
                    ),
                )

            for section in changelog_sections[:20]:  # Limit to recent entries
                title_elem = section.find(["h1", "h2", "h3", "h4"])
                title = (
                    title_elem.get_text(strip=True)
                    if title_elem
                    else "OpenAI Platform Update"
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
                content_elem = section.find_next(["p", "div", "ul"])
                content = content_elem.get_text(strip=True) if content_elem else ""

                if self._is_model_related(title + " " + content):
                    updates.append(
                        {
                            "title": title,
                            "url": self.sources["openai"]["changelog_url"],
                            "published_at": published_at,
                            "summary": content[:500] + "..."
                            if len(content) > 500
                            else content,
                            "content": content,
                            "source": "openai_changelog",
                            "source_type": "scraped",
                            "provider": "openai",
                            "entry_id": f"openai_changelog_{hash(title + published_at)}",
                        }
                    )

            logger.info(f"Scraped {len(updates)} updates from OpenAI changelog")
            return updates

        except Exception as e:
            logger.error(f"Error scraping OpenAI changelog: {e}")
            return []

    async def _scrape_anthropic_news(self) -> list[dict[str, Any]]:
        """Scrape Anthropic news for Claude model updates.

        Returns:
            List of news entries.
        """
        try:
            logger.info("Scraping Anthropic news")

            updates = []

            for url_key, url in [
                ("news_url", self.sources["anthropic"]["news_url"]),
                ("blog_url", self.sources["anthropic"]["blog_url"]),
            ]:
                try:
                    response = requests.get(
                        url,
                        timeout=30,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                    )
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, "html.parser")

                    # Look for news/blog articles
                    articles = soup.find_all(
                        ["article", "div"], class_=re.compile(r"post|article|news|blog")
                    )

                    if not articles:
                        # Try alternative selectors for links
                        articles = soup.find_all(
                            "a", href=re.compile(r"/news/|/blog/|/research/")
                        )

                    for article in articles[:15]:  # Limit to recent entries
                        title_elem = article.find(["h1", "h2", "h3", "h4"]) or article
                        title = title_elem.get_text(strip=True) if title_elem else ""

                        # Get article URL
                        link_elem = (
                            article.find("a") if article.name != "a" else article
                        )
                        article_url = (
                            urljoin(url, link_elem.get("href", ""))
                            if link_elem
                            else url
                        )

                        # Extract date
                        date_elem = article.find(
                            ["time", "span"], class_=re.compile(r"date|time")
                        )
                        published_at = (
                            date_elem.get_text(strip=True)
                            if date_elem
                            else datetime.now().isoformat()
                        )

                        # Extract summary
                        summary_elem = article.find(
                            ["p", "div"],
                            class_=re.compile(r"summary|excerpt|description"),
                        )
                        summary = (
                            summary_elem.get_text(strip=True) if summary_elem else title
                        )

                        if title and self._is_model_related(title + " " + summary):
                            updates.append(
                                {
                                    "title": title,
                                    "url": article_url,
                                    "published_at": published_at,
                                    "summary": summary[:500] + "..."
                                    if len(summary) > 500
                                    else summary,
                                    "content": summary,
                                    "source": f"anthropic_{url_key}",
                                    "source_type": "scraped",
                                    "provider": "anthropic",
                                    "entry_id": f"anthropic_{hash(title + article_url)}",
                                }
                            )

                except Exception as e:
                    logger.warning(f"Error scraping {url}: {e}")
                    continue

            logger.info(f"Scraped {len(updates)} updates from Anthropic sources")
            return updates

        except Exception as e:
            logger.error(f"Error scraping Anthropic news: {e}")
            return []

    async def _scrape_gemini_changelog(self) -> list[dict[str, Any]]:
        """Scrape Google Gemini API changelog.

        Returns:
            List of changelog entries.
        """
        try:
            logger.info("Scraping Google Gemini changelog")

            response = requests.get(
                self.sources["google"]["gemini_changelog"],
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            updates = []

            # Look for changelog sections
            changelog_sections = soup.find_all(
                ["section", "div"], class_=re.compile(r"changelog|release|update")
            )

            if not changelog_sections:
                # Try finding by date headers
                changelog_sections = soup.find_all(
                    ["h2", "h3"],
                    string=re.compile(
                        r"202[3-9]|January|February|March|April|May|June|July|August|September|October|November|December"
                    ),
                )

            for section in changelog_sections[:20]:  # Limit to recent entries
                title_elem = (
                    section
                    if section.name in ["h2", "h3"]
                    else section.find(["h1", "h2", "h3", "h4"])
                )
                title = (
                    title_elem.get_text(strip=True)
                    if title_elem
                    else "Gemini API Update"
                )

                # Extract date
                date_match = re.search(
                    r"(202[3-9]-\d{2}-\d{2}|\w+ \d{1,2}, 202[3-9])", title
                )
                published_at = (
                    date_match.group(1) if date_match else datetime.now().isoformat()
                )

                # Extract content
                content_elem = section.find_next(["p", "div", "ul"])
                content = content_elem.get_text(strip=True) if content_elem else ""

                if self._is_model_related(title + " " + content, provider="google"):
                    updates.append(
                        {
                            "title": title,
                            "url": self.sources["google"]["gemini_changelog"],
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

    def _get_provider_from_source(self, source_name: str) -> str:
        """Get provider name from source name."""
        if "openai" in source_name.lower():
            return "openai"
        elif "anthropic" in source_name.lower() or "claude" in source_name.lower():
            return "anthropic"
        elif "google" in source_name.lower() or "gemini" in source_name.lower():
            return "google"
        else:
            return "unknown"

    def _is_model_related(self, text: str, provider: str = None) -> bool:
        """Check if content is related to AI model updates.

        Args:
            text: Text content to check
            provider: Optional provider name for specific keywords

        Returns:
            True if content appears to be model-related
        """
        text_lower = text.lower()

        # General model keywords
        model_keywords = [
            "gpt",
            "claude",
            "gemini",
            "bard",
            "model",
            "api",
            "launch",
            "release",
            "update",
            "version",
            "capability",
            "feature",
            "improvement",
            "performance",
            "new model",
            "model update",
            "api update",
            "beta",
            "preview",
            "general availability",
        ]

        # Provider-specific keywords
        if provider == "openai":
            model_keywords.extend(
                [
                    "gpt-4",
                    "gpt-3.5",
                    "turbo",
                    "davinci",
                    "curie",
                    "babbage",
                    "ada",
                    "embedding",
                    "fine-tuning",
                ]
            )
        elif provider == "anthropic":
            model_keywords.extend(
                [
                    "claude-3",
                    "claude-2",
                    "claude instant",
                    "opus",
                    "sonnet",
                    "haiku",
                    "constitutional ai",
                ]
            )
        elif provider == "google":
            model_keywords.extend(
                ["gemini pro", "gemini ultra", "palm", "bard", "vertex ai", "ai studio"]
            )

        # Check if any model keywords are present
        return any(keyword in text_lower for keyword in model_keywords)

    def _filter_model_updates(
        self, updates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter updates to only include model-related content.

        Args:
            updates: List of all updates

        Returns:
            Filtered list of model-related updates
        """
        filtered = []

        for update in updates:
            text_content = f"{update.get('title', '')} {update.get('summary', '')} {update.get('content', '')}"
            provider = update.get("provider", "")

            if self._is_model_related(text_content, provider):
                filtered.append(update)

        logger.info(
            f"Filtered {len(filtered)} model-related updates from {len(updates)} total updates"
        )
        return filtered

    def process_updates(self, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process and standardize AI model updates.

        Args:
            updates: List of raw update dictionaries

        Returns:
            List of processed update dictionaries
        """
        logger.info(f"Processing {len(updates)} AI model updates")

        processed = []
        seen_titles = set()

        for update in updates:
            # Deduplicate by title
            title = update.get("title", "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)

                processed_update = {
                    "title": title,
                    "url": update.get("url", ""),
                    "provider": update.get("provider", "unknown"),
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

        logger.info(f"Successfully processed {len(processed)} unique updates")
        return processed

    def save_updates(self, updates: list[dict[str, Any]]) -> None:
        """Save AI model updates to JSON and CSV files.

        Args:
            updates: List of processed update dictionaries
        """
        if not updates:
            logger.warning("No updates to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON files
        json_file = os.path.join(self.output_dir, f"ai_models_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(updates, f, indent=2, ensure_ascii=False)

        latest_json = os.path.join(self.output_dir, "ai_models_latest.json")
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(updates, f, indent=2, ensure_ascii=False)

        # Save CSV files
        try:
            import pandas as pd

            df = pd.DataFrame(updates)

            csv_file = os.path.join(self.output_dir, f"ai_models_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding="utf-8")

            latest_csv = os.path.join(self.output_dir, "ai_models_latest.csv")
            df.to_csv(latest_csv, index=False, encoding="utf-8")

            logger.info(f"Saved {len(updates)} updates to {json_file} and {csv_file}")

        except ImportError:
            logger.warning("pandas not available, skipping CSV export")
            logger.info(f"Saved {len(updates)} updates to {json_file}")


async def main():
    """Main entry point for the AI model monitoring ETL process."""
    logger.info("Starting AI Model Monitoring ETL process")

    try:
        etl = AIModelMonitoringETL()

        # Fetch updates from all sources
        logger.info("Fetching AI model updates from all sources...")
        updates = await etl.fetch_all_sources()

        if not updates:
            logger.warning("No AI model updates retrieved, ETL process will exit")
            return

        # Process updates
        processed_updates = etl.process_updates(updates)

        # Save results
        etl.save_updates(processed_updates)

        logger.info(
            f"AI Model Monitoring ETL completed successfully. Processed {len(processed_updates)} updates."
        )

    except Exception as e:
        logger.error(f"Error in AI Model Monitoring ETL process: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
