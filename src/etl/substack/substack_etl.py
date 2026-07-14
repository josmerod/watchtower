"""Substack Newsletter ETL Pipeline.

Extracts post metadata from configured Substack newsletters using their
native RSS feeds (no third-party library needed), transforms into a
unified format, and loads to JSON for Knowledge Garden consumption.
"""

import json
import os
from datetime import datetime

import feedparser

from src.etl.base import BaseETL

# Newsletter slugs to scrape — add more as needed
DEFAULT_NEWSLETTERS: list[str] = [
    "aimadesimple0",  # AI Made Simple by Nitin Sharma
    "adhdweasel",  # The ADHD Weasel
]


class SubstackETL(BaseETL):
    """ETL pipeline for Substack newsletters.

    Uses Substack's native RSS feeds ({slug}.substack.com/feed) via
    feedparser to extract post metadata.
    """

    def __init__(
        self,
        name: str = "substack",
        newsletters: list[str] | None = None,
        max_posts_per_newsletter: int = 30,
        **kwargs,
    ):
        """Initialize SubstackETL.

        Args:
            name: ETL pipeline name (used for output directory).
            newsletters: List of Substack newsletter slugs.
            max_posts_per_newsletter: Max posts to fetch per newsletter.
            **kwargs: Additional BaseETL keyword arguments.
        """
        super().__init__(name=name, **kwargs)
        self.newsletters = newsletters or DEFAULT_NEWSLETTERS
        self.max_posts_per_newsletter = max_posts_per_newsletter

    # ------------------------------------------------------------------ #
    # ETL phases
    # ------------------------------------------------------------------ #

    def extract(self) -> list[dict]:
        """Extract post metadata from Substack RSS feeds."""
        all_entries: list[dict] = []

        for slug in self.newsletters:
            feed_url = f"https://{slug}.substack.com/feed"
            self.logger.info(f"Fetching RSS feed: {feed_url}")

            try:
                parsed = feedparser.parse(feed_url)

                if parsed.bozo and not parsed.entries:
                    self.logger.warning(f"Feed for '{slug}' returned errors: {parsed.bozo_exception}")
                    continue

                entries = parsed.entries[: self.max_posts_per_newsletter]
                for entry in entries:
                    entry["_newsletter_slug"] = slug
                all_entries.extend(entries)
                self.logger.info(f"  → Got {len(entries)} posts from '{slug}'")

            except Exception as e:
                self.logger.error(f"  → Error fetching '{slug}': {e}")

        self.logger.info(f"Total extracted posts: {len(all_entries)}")
        self.metrics.records_extracted = len(all_entries)
        return all_entries

    def transform(self, data: list[dict]) -> list[dict]:
        """Transform RSS entries into Knowledge Garden format.

        Args:
            data: Raw feedparser entry dicts from Substack RSS.

        Returns:
            Normalised article dicts.
        """
        transformed: list[dict] = []

        for entry in data:
            try:
                title = entry.get("title", "Untitled")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                newsletter_slug = entry.get("_newsletter_slug", "unknown")

                # Parse date
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    published_at = datetime(*published_parsed[:6]).isoformat()
                else:
                    published_at = entry.get("published", entry.get("updated", ""))

                # Author — Substack feeds often include this
                author = entry.get("author", newsletter_slug)

                # Clean summary (strip HTML tags for a short description)
                if summary and len(summary) > 300:
                    summary = summary[:300] + "…"

                transformed.append(
                    {
                        "title": title,
                        "url": link,
                        "description": summary,
                        "published_at": str(published_at),
                        "source": f"Substack ({newsletter_slug})",
                        "author": author,
                        "newsletter": newsletter_slug,
                    }
                )
            except Exception as e:
                self.logger.warning(f"Skipping post due to transform error: {e}")

        self.logger.info(f"Transformed {len(transformed)} posts")
        self.metrics.records_transformed = len(transformed)
        return transformed

    def load(self, data: list[dict]) -> None:
        """Write transformed posts to JSON files.

        Args:
            data: Transformed article dicts.
        """
        if not data:
            self.logger.warning("No data to load.")
            return

        os.makedirs(self.output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Timestamped snapshot
        ts_path = os.path.join(self.output_dir, f"substack_{timestamp}.json")
        with open(ts_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Saved timestamped snapshot → {ts_path}")

        # Latest file (consumed by the dashboard)
        latest_path = os.path.join(self.output_dir, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Updated latest.json → {latest_path}")

        self.metrics.records_loaded = len(data)


if __name__ == "__main__":
    etl = SubstackETL()
    etl.run()
