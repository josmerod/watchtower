"""Generic RSS/Atom Feed ETL Pipeline.

Parses RSS and Atom feeds from a configurable list of URLs, transforms
into a unified format, and loads to JSON for Knowledge Garden consumption.
"""

import json
import os
from datetime import datetime

import feedparser

from src.etl.base import BaseETL

# Default feeds — add more as needed
DEFAULT_FEEDS: list[dict[str, str]] = [
    {
        "url": "https://tom-doerr.github.io/repo_posts/feed.xml",
        "name": "Tom Doerr Repo Posts",
    },
]


class RSSFeedETL(BaseETL):
    """ETL pipeline for RSS/Atom feeds.

    Uses feedparser to extract entries from one or more feed URLs,
    normalises them, and outputs JSON for Knowledge Garden.
    """

    def __init__(
        self,
        name: str = "rss_feeds",
        feeds: list[dict[str, str]] | None = None,
        max_entries_per_feed: int = 50,
        **kwargs,
    ):
        """Initialize RSSFeedETL.

        Args:
            name: ETL pipeline name.
            feeds: List of dicts with 'url' and 'name' keys.
            max_entries_per_feed: Cap entries per feed.
            **kwargs: Additional BaseETL keyword arguments.
        """
        super().__init__(name=name, **kwargs)
        self.feeds = feeds or DEFAULT_FEEDS
        self.max_entries_per_feed = max_entries_per_feed

    def extract(self) -> list[dict]:
        """Fetch and parse all configured RSS/Atom feeds."""
        all_entries: list[dict] = []

        for feed_cfg in self.feeds:
            feed_url = feed_cfg["url"]
            feed_name = feed_cfg.get("name", feed_url)
            self.logger.info(f"Parsing feed: {feed_name} ({feed_url})")

            try:
                parsed = feedparser.parse(feed_url)

                if parsed.bozo and not parsed.entries:
                    self.logger.warning(f"Feed '{feed_name}' returned errors: {parsed.bozo_exception}")
                    continue

                entries = parsed.entries[: self.max_entries_per_feed]
                for entry in entries:
                    entry["_feed_name"] = feed_name
                    entry["_feed_url"] = feed_url
                all_entries.extend(entries)
                self.logger.info(f"  → Got {len(entries)} entries from '{feed_name}'")

            except Exception as e:
                self.logger.error(f"  → Error parsing feed '{feed_name}': {e}")

        self.logger.info(f"Total extracted entries: {len(all_entries)}")
        self.metrics.records_extracted = len(all_entries)
        return all_entries

    def transform(self, data: list[dict]) -> list[dict]:
        """Transform feed entries into Knowledge Garden format.

        Args:
            data: Raw feedparser entry dicts.

        Returns:
            Normalised article dicts.
        """
        transformed: list[dict] = []

        for entry in data:
            try:
                title = entry.get("title", "Untitled")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))

                # Parse date — feedparser gives 'published_parsed' as time.struct_time
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    published_at = datetime(*published_parsed[:6]).isoformat()
                else:
                    published_at = entry.get("published", entry.get("updated", ""))

                feed_name = entry.get("_feed_name", "RSS")

                transformed.append(
                    {
                        "title": title,
                        "url": link,
                        "description": summary[:500] if summary else "",
                        "published_at": str(published_at),
                        "source": f"RSS ({feed_name})",
                        "author": entry.get("author", feed_name),
                    }
                )
            except Exception as e:
                self.logger.warning(f"Skipping entry due to transform error: {e}")

        self.logger.info(f"Transformed {len(transformed)} entries")
        self.metrics.records_transformed = len(transformed)
        return transformed

    def load(self, data: list[dict]) -> None:
        """Write feed entries to JSON."""
        if not data:
            self.logger.warning("No data to load.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        ts_path = os.path.join(self.output_dir, f"rss_feeds_{timestamp}.json")
        with open(ts_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        latest_path = os.path.join(self.output_dir, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Saved {len(data)} entries → {latest_path}")
        self.metrics.records_loaded = len(data)


if __name__ == "__main__":
    etl = RSSFeedETL()
    etl.run()
