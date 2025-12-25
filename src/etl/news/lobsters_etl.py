import logging
from datetime import datetime, timezone
from typing import Any, List

from src.etl.base import SimpleETL

logger = logging.getLogger("LobstersETL")

SOURCE_NAME = "lobsters"
URL = "https://lobste.rs/hottest.json"


class LobstersETL(SimpleETL):
    def __init__(self):
        super().__init__(name=SOURCE_NAME, batch_size=50)

    def extract(self) -> List[dict[str, Any]]:
        """Fetch hottest stories from Lobste.rs."""
        logger.info(f"Fetching data from {URL}")
        try:
            # Use proxied session from BaseETL
            response = self.http_session.get(URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"Failed to fetch Lobsters data: {e}")
            return []

    def transform(self, data: List[dict[str, Any]]) -> List[dict[str, Any]]:
        """Transform Lobsters JSON into standard News format."""
        transformed = []
        for item in data:
            try:
                # Parse date (Lobsters uses ISO 8601)
                # e.g., "2023-10-27T14:00:00.000-05:00"
                created_at = item.get("created_at", "")
                published_at = created_at  # Default fallback
                
                try:
                    # Attempt to standardize to UTC
                    if created_at:
                        dt = datetime.fromisoformat(created_at)
                        if dt.tzinfo:
                            published_at = dt.astimezone(timezone.utc).isoformat()
                        else:
                            published_at = dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    pass

                transformed_item = {
                    "source": SOURCE_NAME,
                    "id": item.get("short_id", item.get("url")),
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "published_at": published_at,
                    "description": item.get("description") or "", # often empty in json
                    "author": item.get("submitter_user", {}).get("username", "Unknown"),
                    "score": item.get("score", 0),
                    "comments": item.get("comment_count", 0),
                    "tags": item.get("tags", []),
                }
                transformed.append(transformed_item)
            except Exception as e:
                logger.warning(f"Error processing Lobsters item {item.get('short_id')}: {e}")
        
        return transformed

if __name__ == "__main__":
    etl = LobstersETL()
    etl.run()
