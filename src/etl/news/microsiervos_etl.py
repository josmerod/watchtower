import json

import feedparser

from src.etl.base import SimpleETL
from src.utils.logging import get_logger

logger = get_logger("MicrosiervosETL")

RSS_URL = "https://www.microsiervos.com/index.xml"
SOURCE_NAME = "microsiervos"


class MicrosiervosETL(SimpleETL):
    def __init__(self):
        super().__init__(name=SOURCE_NAME, batch_size=50)

    def load(self, data: list[dict]) -> None:
        """Persist the timestamped snapshot (SimpleETL) plus a stable latest file.

        The dashboard news tab reads ``microsiervos_latest.json``, which the
        base SimpleETL.load() does not produce.
        """
        super().load(data)
        latest = self.output_dir / f"{self.name}_latest.json"
        latest.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        logger.info(f"Latest data saved to {latest}")

    def parse_date(self, date_str: str) -> str:
        """Parses date string to ISO format."""
        from datetime import datetime, timezone

        try:
            # Common RSS formats
            dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            try:
                dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                return dt.replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                return date_str

    def extract(self) -> list[dict]:
        """Fetch and parse RSS feed using requests session with proxy support."""
        logger.info(f"Fetching RSS feed from {RSS_URL}")

        try:
            # Story 7.2: Use proxied session
            response = self.http_session.get(RSS_URL, timeout=30)
            response.raise_for_status()
            content = response.content
        except Exception as e:  # broad by design: proxied session fetch via BaseETL infra (transport/proxy failures)
            logger.error(f"Failed to fetch feed: {e}")
            return []

        feed = feedparser.parse(content)

        if feed.bozo:
            logger.warning(f"Error parsing feed: {feed.bozo_exception}")

        entries = []
        for entry in feed.entries:
            try:
                published = self.parse_date(entry.get("published", ""))

                item = {
                    "source": SOURCE_NAME,
                    "id": entry.get("id", entry.get("link")),
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "published_at": published,
                    "description": entry.get("summary", ""),
                    "author": entry.get("author", "Microsiervos"),
                    "tags": [tag.term for tag in entry.get("tags", [])] if "tags" in entry else [],
                }
                entries.append(item)
            except (AttributeError, KeyError, TypeError) as e:
                logger.error(f"Error processing entry {entry.get('title', 'Unknown')}: {e}")

        return entries

    def transform(self, data: list[dict]) -> list[dict]:
        """No transformation needed as we formatted in extract."""
        return data


if __name__ == "__main__":
    etl = MicrosiervosETL()
    etl.run()
