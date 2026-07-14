"""Product Hunt ETL Module

This module fetches and processes product launches using the official Product Hunt GraphQL API
or falls back to the RSS feed if no API token is available.

Usage:
    python src/etl/news/news_get_producthunt.py
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("ProductHuntETL")


class ProductHuntETL:
    def __init__(self):
        self.api_token = os.getenv("PRODUCTHUNT_API_TOKEN")
        self.api_url = "https://api.producthunt.com/v2/api/graphql"
        self.rss_url = "https://www.producthunt.com/feed"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WatchtowerBot/1.0 (https://github.com/josmerod/watchtower)"})

    def fetch_via_graphql(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch products using the official GraphQL API."""
        if not self.api_token:
            logger.warning("PRODUCTHUNT_API_TOKEN not set, skipping GraphQL")
            return []

        query = """
        {
            posts(postedAfter: "%s", order: VOTES, first: %d) {
                edges {
                    node {
                        name
                        tagline
                        url
                        votesCount
                        commentsCount
                        topics {
                            name
                        }
                        createdAt
                        website
                    }
                }
            }
        }
        """ % (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            limit,
        )

        try:
            logger.info("Fetching Product Hunt data via GraphQL API")
            resp = self.session.post(self.api_url, headers={"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}, json={"query": query}, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                return []

            products = []
            for edge in data.get("data", {}).get("posts", {}).get("edges", []):
                node = edge.get("node", {})
                topics = [t.get("name") for t in node.get("topics", []) if t.get("name")]
                products.append(
                    {
                        "name": node.get("name", "").strip(),
                        "tagline": node.get("tagline", ""),
                        "url": node.get("url", ""),
                        "website": node.get("website", ""),
                        "votes": node.get("votesCount", 0),
                        "comments": node.get("commentsCount", 0),
                        "thumbnail": "",  # GraphQL doesn't provide thumbnail in this query
                        "category": ", ".join(topics) if topics else "general",
                        "created_at": node.get("createdAt"),
                    }
                )
            logger.info(f"Fetched {len(products)} products via GraphQL")
            return products
        except Exception as e:
            logger.error(f"GraphQL fetch failed: {e}")
            return []

    def fetch_via_rss(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch products using the RSS feed."""
        try:
            logger.info("Fetching Product Hunt data via RSS feed")
            resp = self.session.get(self.rss_url, timeout=30)
            resp.raise_for_status()

            # Simple RSS parsing (we could use feedparser but avoid extra dep)
            import xml.etree.ElementTree as ET

            root = ET.fromstring(resp.content)

            products = []
            for item in root.findall(".//item")[:limit]:
                title = item.findtext("title", default="").strip()
                link = item.findtext("link", default="")
                description = item.findtext("description", default="")
                pub_date = item.findtext("pubDate", default="")

                # Extract vote count from description if possible (RSS doesn't have it)
                votes = 0
                # TODO: could parse from description if format known

                products.append(
                    {
                        "name": title,
                        "tagline": description,
                        "url": link,
                        "website": link,  # RSS doesn't separate website
                        "votes": votes,
                        "comments": 0,
                        "thumbnail": "",
                        "category": "general",
                        "created_at": pub_date,
                    }
                )
            logger.info(f"Fetched {len(products)} products via RSS")
            return products
        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
            return []

    def fetch(self, limit: int = 50) -> list[dict[str, Any]]:
        """Main fetch method: try GraphQL, fallback to RSS."""
        products = self.fetch_via_graphql(limit)
        if not products:
            logger.info("GraphQL returned no products, trying RSS")
            products = self.fetch_via_rss(limit)
        return products


def process_data(raw_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process raw scraped data into final format."""
    processed = []
    current_time = datetime.now(timezone.utc).isoformat()

    for i, p in enumerate(raw_products):
        try:
            # Clean name
            name = p["name"]
            if name and name[0].isdigit() and ". " in name[:4]:
                name = name.split(". ", 1)[1]

            processed.append(
                {
                    "id": f"ph_product_{i}",
                    "name": name,
                    "tagline": p["tagline"],
                    "description": p["tagline"],
                    "url": p["url"],
                    "website": p["website"],
                    "slug": p["url"].split("/products/")[-1] if "/products/" in p["url"] else p["url"].split("/posts/")[-1] if "/posts/" in p["url"] else "unknown",
                    "votes_count": p["votes"],
                    "comments_count": p["comments"],
                    "reviews_count": 0,
                    "reviews_rating": 0.0,
                    "featured_at": current_time,
                    "created_at": p.get("created_at", current_time),
                    "updated_at": current_time,
                    "thumbnail_url": p["thumbnail"],
                    "gallery_images": [],
                    "topics": [p["category"]] if p["category"] != "general" else [],
                    "makers": [],
                    "hunters": [],
                    "product_links": [{"type": "website", "url": p["url"]}] if p["website"] else [],
                    "category": p["category"],
                    "mock_data": False,
                    "fetched_at": current_time,
                    "platform": "product_hunt",
                    "days_since_launch": 0,
                    "engagement_score": p["votes"],
                    "launch_success_score": p["votes"],
                    "potential_score": p["votes"] * 0.5,
                    "freshness_factor": 1.0,
                    "popularity_category": "viral" if p["votes"] > 1000 else "high" if p["votes"] > 500 else "medium",
                    "launch_phase": "launch_day",
                    "primary_category": p["category"],
                    "innovation_level": "standard",
                    "data_source": "product_hunt_graphql" if p.get("_source") == "graphql" else "product_hunt_rss",
                }
            )
        except Exception as e:
            logger.warning(f"Error processing item {i}: {e}")
            continue

    return processed


def main():
    try:
        etl = ProductHuntETL()
        raw_products = etl.fetch(limit=60)

        if not raw_products:
            logger.warning("No products fetched from Product Hunt.")
            return

        processed_data = process_data(raw_products)

        # Save
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "product_hunt")
        ensure_directories([output_dir])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        latest_json = os.path.join(output_dir, "product_hunt_latest.json")
        archive_json = os.path.join(output_dir, f"product_hunt_{timestamp}.json")

        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)

        with open(archive_json, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(processed_data)} products to {latest_json}")

    except Exception as e:
        logger.error(f"ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
