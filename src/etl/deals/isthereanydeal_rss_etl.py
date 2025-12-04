"""IsThereAnyDeal RSS ETL

Fetches Deals, Bundles, and Giveaways from IsThereAnyDeal RSS feeds.
Uses BaseETL framework for robust processing with metrics and error handling.

Feeds per docs: https://isthereanydeal.com/feeds/
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.etl.base import BaseETL

BASE = "https://isthereanydeal.com"
FEEDS = {
    "deals": f"{BASE}/feeds/US/USD/deals.rss",
    "bundles": f"{BASE}/feeds/US/USD/bundles.rss",
    "giveaways": f"{BASE}/feeds/US/giveaways.rss",
}


class IsThereAnyDealRSSETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """ETL for IsThereAnyDeal RSS feeds using BaseETL framework."""

    def __init__(self, feed_type: str = "deals", **kwargs):
        """Initialize the IsThereAnyDeal RSS ETL.

        Args:
            feed_type: Type of feed to fetch (deals, bundles, or giveaways)
            **kwargs: Additional arguments for BaseETL
        """
        if feed_type not in FEEDS:
            raise ValueError(f"Invalid feed_type '{feed_type}'. Must be one of: {list(FEEDS.keys())}")

        super().__init__(
            name=f"isthereanydeal_{feed_type}",
            description=f"IsThereAnyDeal {feed_type} RSS feed ETL",
            **kwargs,
        )
        self.feed_type = feed_type
        self.feed_url = FEEDS[feed_type]

    def extract(self) -> list[dict[str, Any]]:
        """Extract items from IsThereAnyDeal RSS feed.

        Returns:
            List of raw feed entries
        """
        self.logger.info(f"Fetching ITAD {self.feed_type} feed: {self.feed_url}")

        try:
            feed = feedparser.parse(self.feed_url)

            if not feed.entries:
                self.logger.warning(f"No entries found in {self.feed_type} feed")
                return []

            # Convert feed entries to dictionaries
            items = []
            for entry in feed.entries:
                item = {
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "summary": getattr(entry, "summary", getattr(entry, "description", "")) or "",
                    "published": getattr(entry, "published", None),
                    "published_parsed": getattr(entry, "published_parsed", None),
                }
                items.append(item)

            self.logger.info(f"Retrieved {len(items)} ITAD {self.feed_type} items")
            return items

        except Exception as e:
            self.logger.error(f"Failed to fetch ITAD {self.feed_type}: {e}")
            return []

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform raw feed entries into standardized deal format.

        Args:
            data: Raw feed entries

        Returns:
            Transformed deal items
        """
        if not data:
            return []

        self.logger.info(f"Transforming {len(data)} {self.feed_type} items")

        transformed = []
        for entry in data:
            try:
                # Clean HTML from summary
                summary = entry.get("summary", "")
                summary_txt = re.sub(r"<[^>]+>", "", summary).strip()

                # Extract prices and discount percentage
                orig_price, sale_price, discount_pct = self._extract_prices(summary_txt)

                # Parse date
                published_date = self._parse_date(entry.get("published"))

                item = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "platform": "IsThereAnyDeal",
                    "category": "games",
                    "deal_type": self.feed_type,
                    "original_price": orig_price or 0.0,
                    "current_price": sale_price or 0.0,
                    "discount_percentage": discount_pct or 0,
                    "store_name": "Multiple",
                    "description": summary_txt[:500],
                    "published_date": published_date,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": f"itad_{self.feed_type}",
                }
                transformed.append(item)

            except Exception as e:
                self.logger.warning(f"Failed to transform item: {e}")
                self.metrics.records_failed += 1
                continue

        self.logger.info(f"Successfully transformed {len(transformed)} items")
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load transformed data to JSON files.

        Args:
            data: Transformed deal items
        """
        if not data:
            self.logger.warning("No data to load")
            return

        self.logger.info(f"Loading {len(data)} {self.feed_type} items")

        import json

        # Save timestamped version
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_file = self.output_dir / f"isthereanydeal_{self.feed_type}_{timestamp}.json"

        timestamped_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Save latest version
        latest_file = self.output_dir / f"isthereanydeal_{self.feed_type}_latest.json"
        latest_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        self.logger.info(f"Saved ITAD {self.feed_type} to {timestamped_file} and {latest_file}")

    def _parse_date(self, date_str: str | None) -> str | None:
        """Parse date string into ISO format.

        Args:
            date_str: Date string to parse

        Returns:
            ISO formatted date string or None
        """
        if not date_str:
            return None

        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %y %H:%M:%S %z"):
            try:
                return datetime.strptime(date_str, fmt).isoformat()
            except Exception:
                continue

        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            return date_str

    def _extract_prices(self, text: str) -> tuple[float | None, float | None, int | None]:
        """Extract original price, sale price, and discount percentage from text.

        Args:
            text: Text containing price information

        Returns:
            Tuple of (original_price, sale_price, discount_percentage)
        """
        if not text:
            return None, None, None

        # Extract percentage like "-75%" or "75% off"
        discount_pct = None
        m = re.search(r"(\d{1,3})\s*%", text)
        if m:
            try:
                discount_pct = int(m.group(1))
            except Exception:
                pass

        # Extract prices like "$19.99"
        prices = []
        for match in re.finditer(r"\$(\d+(?:\.\d{2})?)", text):
            try:
                prices.append(float(match.group(1)))
            except Exception:
                pass

        sale_price = min(prices) if prices else None
        orig_price = max(prices) if prices and len(prices) > 1 else None

        return orig_price, sale_price, discount_pct


def main():
    """Run all IsThereAnyDeal RSS ETLs."""
    import logging

    logging.basicConfig(level=logging.INFO)

    for feed_type in ("deals", "bundles", "giveaways"):
        try:
            etl = IsThereAnyDealRSSETL(feed_type=feed_type)
            metrics = etl.run()
            print(f"✅ {feed_type.capitalize()}: {metrics.records_loaded} items loaded")
        except Exception as e:
            print(f"❌ {feed_type.capitalize()} failed: {e}")


if __name__ == "__main__":
    main()
