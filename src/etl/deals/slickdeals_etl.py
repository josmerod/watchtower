"""Slickdeals RSS ETL Module

This module fetches community-driven deals from Slickdeals RSS feeds.
Slickdeals provides comprehensive coverage of product deals, coupons,
and community-validated bargains across multiple categories.

Usage:
    python src/etl/deals/slickdeals_etl.py

Output:
    - JSON file: data/deals/slickdeals_latest.json
    - CSV file: data/deals/slickdeals_latest.csv
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("SlickdealsETL")

# Slickdeals RSS feeds for different categories
RSS_FEEDS: dict[str, str] = {
    "slickdeals_frontpage": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
    "slickdeals_hot": "https://slickdeals.net/deal-feed/",
    "slickdeals_electronics": "https://slickdeals.net/newsearch.php?c[]=9&searcharea=deals&searchin=first&rss=1",
    "slickdeals_computers": "https://slickdeals.net/newsearch.php?c[]=4&searcharea=deals&searchin=first&rss=1",
    "slickdeals_home": "https://slickdeals.net/newsearch.php?c[]=23&searcharea=deals&searchin=first&rss=1",
}


def fetch_slickdeals_feeds() -> list[dict[str, Any]]:
    """Fetches and parses RSS feeds from Slickdeals.

    Returns:
        List of deal entries with metadata from Slickdeals RSS feeds.
    """
    entries: list[dict[str, Any]] = []

    for source, url in RSS_FEEDS.items():
        logger.info(f"Fetching Slickdeals RSS feed from {source} at {url}")
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                logger.warning(f"Error parsing feed from {source}: {feed.bozo_exception}")
                continue
        except Exception as e:
            logger.error(f"Could not fetch or parse feed from {source}: {e}")
            continue

        for entry in feed.entries:
            published_raw = entry.get("published", "")
            try:
                # Try multiple date formats in order of preference
                # 1. ISO 8601 format (used by modern feeds)
                if "T" in published_raw and ("+" in published_raw or "-" in published_raw[-6:]):
                    try:
                        # Handle ISO 8601 with timezone offset
                        published = datetime.fromisoformat(published_raw).isoformat()
                    except ValueError:
                        # Try ISO 8601 with Z timezone
                        if published_raw.endswith("Z"):
                            published_raw_utc = published_raw[:-1] + "+00:00"
                            published = datetime.fromisoformat(published_raw_utc).isoformat()
                        else:
                            raise ValueError(f"Could not parse ISO format: {published_raw}")

                # 2. RFC 2822 format (traditional RSS format)
                elif any(day in published_raw for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                    try:
                        published = datetime.strptime(published_raw, "%a, %d %b %Y %H:%M:%S %z").isoformat()
                    except ValueError:
                        try:
                            published = datetime.strptime(published_raw, "%a, %d %b %y %H:%M:%S %z").isoformat()
                        except ValueError:
                            published = datetime.strptime(published_raw, "%a, %d %b %Y %H:%M:%S %Z").isoformat()

                # 3. Try other common formats
                else:
                    # Try simple ISO format without timezone
                    try:
                        published = datetime.fromisoformat(published_raw).isoformat()
                    except ValueError:
                        # Try parsing as timestamp
                        try:
                            published = datetime.fromtimestamp(float(published_raw)).isoformat()
                        except (ValueError, TypeError):
                            raise ValueError(f"Unknown date format: {published_raw}")

            except Exception as e:
                logger.warning(f"Could not parse publication date '{published_raw}' for entry '{entry.get('title')}' from {source}: {e}. Using raw value.")
                published = published_raw

            # Extract categories/tags
            categories = []
            if hasattr(entry, "tags") and entry.tags:
                categories = [tag.term for tag in entry.tags if hasattr(tag, "term")]
            elif hasattr(entry, "category") and entry.category:
                categories = [entry.category]

            # Extract author/poster information
            author = ""
            if hasattr(entry, "author") and entry.author:
                author = entry.author
            elif hasattr(entry, "authors") and entry.authors:
                author = ", ".join([a.name if hasattr(a, "name") else str(a) for a in entry.authors])

            # Extract summary/description
            summary = ""
            if hasattr(entry, "summary") and entry.summary:
                summary = entry.summary
            elif hasattr(entry, "description") and entry.description:
                summary = entry.description
            elif hasattr(entry, "content") and entry.content:
                if isinstance(entry.content, list) and entry.content:
                    summary = entry.content[0].get("value", "")
                else:
                    summary = str(entry.content)

            # Remove HTML tags from summary
            if summary:
                summary = re.sub(r"<[^>]+>", "", summary)
                summary = summary.strip()

            entry_data = {
                "source": source,
                "source_category": _get_category_from_source(source),
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary,
                "author": author,
                "categories": categories,
                "guid": entry.get("id", entry.get("guid", "")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "slickdeals",
                "content_type": "deal",
                "language": "en",
                "region": "us",
                "deal_category": _determine_deal_category(entry.get("title", "") + " " + summary),
                "price_mentioned": _extract_price_info(entry.get("title", "") + " " + summary),
                "discount_percentage": _extract_discount_info(entry.get("title", "") + " " + summary),
                "store_mentioned": _extract_store_mentions(entry.get("title", "") + " " + summary),
                "deal_score": _calculate_deal_score(entry.get("title", "") + " " + summary),
                "community_validated": _check_community_validation(source),
                "deal_urgency": _assess_deal_urgency(entry.get("title", "") + " " + summary),
            }

            entries.append(entry_data)

    logger.info(f"Retrieved {len(entries)} items from Slickdeals RSS feeds")
    return entries


def _get_category_from_source(source: str) -> str:
    """Extract category from source name."""
    category_map = {
        "slickdeals_frontpage": "general",
        "slickdeals_hot": "hot_deals",
        "slickdeals_electronics": "electronics",
        "slickdeals_computers": "computers",
        "slickdeals_home": "home_garden",
    }
    return category_map.get(source, "general")


def _determine_deal_category(text: str) -> list[str]:
    """Determine deal category based on content."""
    text_lower = text.lower()
    categories = []

    category_keywords = {
        "electronics": [
            "electronics",
            "gadget",
            "phone",
            "tablet",
            "camera",
            "headphones",
            "speaker",
            "tv",
            "monitor",
        ],
        "computers": [
            "computer",
            "laptop",
            "desktop",
            "cpu",
            "gpu",
            "ram",
            "ssd",
            "hard drive",
            "motherboard",
            "pc",
        ],
        "home_garden": [
            "home",
            "garden",
            "furniture",
            "kitchen",
            "appliance",
            "decor",
            "cleaning",
            "tools",
        ],
        "clothing": [
            "clothing",
            "shoes",
            "fashion",
            "apparel",
            "shirt",
            "pants",
            "dress",
            "jacket",
            "sneakers",
        ],
        "books_media": [
            "book",
            "ebook",
            "movie",
            "dvd",
            "blu-ray",
            "music",
            "game",
            "software",
            "app",
        ],
        "health_beauty": [
            "health",
            "beauty",
            "cosmetics",
            "skincare",
            "supplements",
            "fitness",
            "wellness",
        ],
        "automotive": [
            "car",
            "automotive",
            "tire",
            "oil",
            "parts",
            "accessories",
            "tools",
        ],
        "toys_games": [
            "toy",
            "games",
            "board game",
            "video game",
            "console",
            "puzzle",
            "kids",
        ],
        "food_grocery": [
            "food",
            "grocery",
            "snack",
            "coffee",
            "tea",
            "restaurant",
            "delivery",
        ],
        "travel": ["travel", "hotel", "flight", "vacation", "cruise", "rental", "trip"],
    }

    for category, keywords in category_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            categories.append(category)

    return categories


def _extract_price_info(text: str) -> dict[str, Any]:
    """Extract price information from deal text."""
    price_info = {"has_price": False, "original_price": None, "sale_price": None}

    # Look for price patterns
    price_patterns = [
        r"\$(\d+(?:\.\d{2})?)",  # $10.99
        r"(\d+(?:\.\d{2})?)\s*dollars?",  # 10.99 dollars
        r"price[:\s]*\$?(\d+(?:\.\d{2})?)",  # price: $10.99
    ]

    prices = []
    for pattern in price_patterns:
        matches = re.findall(pattern, text.lower())
        for match in matches:
            try:
                prices.append(float(match))
            except ValueError:
                continue

    if prices:
        price_info["has_price"] = True
        if len(prices) >= 2:
            # Assume first price is sale price, highest is original
            price_info["sale_price"] = min(prices)
            price_info["original_price"] = max(prices)
        else:
            price_info["sale_price"] = prices[0]

    return price_info


def _extract_discount_info(text: str) -> dict[str, Any]:
    """Extract discount information from deal text."""
    discount_info = {"has_discount": False, "percentage": None, "amount": None}

    # Look for percentage discounts
    percentage_patterns = [
        r"(\d+)%\s*off",
        r"save\s*(\d+)%",
        r"(\d+)\s*percent\s*off",
    ]

    for pattern in percentage_patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                discount_info["has_discount"] = True
                discount_info["percentage"] = int(match.group(1))
                break
            except ValueError:
                continue

    # Look for dollar amount discounts
    amount_patterns = [
        r"\$(\d+(?:\.\d{2})?)\s*off",
        r"save\s*\$(\d+(?:\.\d{2})?)",
        r"(\d+(?:\.\d{2})?)\s*dollars?\s*off",
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                discount_info["has_discount"] = True
                discount_info["amount"] = float(match.group(1))
                break
            except ValueError:
                continue

    return discount_info


def _extract_store_mentions(text: str) -> list[str]:
    """Extract store mentions from deal text."""
    common_stores = [
        "Amazon",
        "Walmart",
        "Target",
        "Best Buy",
        "Home Depot",
        "Lowes",
        "Costco",
        "Sam's Club",
        "eBay",
        "Newegg",
        "B&H",
        "Adorama",
        "Staples",
        "Office Depot",
        "GameStop",
        "Barnes & Noble",
        "Macy's",
        "Nordstrom",
        "Nike",
        "Adidas",
        "Apple",
        "Microsoft",
        "Google",
        "Dell",
        "HP",
        "Lenovo",
        "ASUS",
        "Samsung",
        "Sony",
        "LG",
        "Philips",
        "Panasonic",
        "Canon",
        "Nikon",
    ]

    mentioned_stores = []
    text_lower = text.lower()

    for store in common_stores:
        if store.lower() in text_lower:
            mentioned_stores.append(store)

    return mentioned_stores


def _calculate_deal_score(text: str) -> float:
    """Calculate a deal score based on various factors."""
    score = 0.0
    text_lower = text.lower()

    # High-value keywords
    high_value_keywords = [
        "free",
        "clearance",
        "limited time",
        "flash sale",
        "today only",
        "expires",
    ]
    for keyword in high_value_keywords:
        if keyword in text_lower:
            score += 0.2

    # Discount indicators
    if "%" in text or "off" in text_lower:
        score += 0.3

    # Price mentions
    if "$" in text:
        score += 0.1

    # Urgency indicators
    urgency_keywords = ["hurry", "limited", "while supplies last", "ending soon"]
    for keyword in urgency_keywords:
        if keyword in text_lower:
            score += 0.1

    # Brand mentions
    premium_brands = ["apple", "samsung", "sony", "nike", "adidas", "microsoft"]
    for brand in premium_brands:
        if brand in text_lower:
            score += 0.1

    return min(score, 1.0)  # Cap at 1.0


def _check_community_validation(source: str) -> bool:
    """Check if deal comes from community-validated sources."""
    validated_sources = ["slickdeals_hot", "slickdeals_frontpage"]
    return source in validated_sources


def _assess_deal_urgency(text: str) -> str:
    """Assess the urgency level of the deal."""
    text_lower = text.lower()

    high_urgency_keywords = [
        "today only",
        "flash sale",
        "ending soon",
        "while supplies last",
        "limited quantity",
    ]
    medium_urgency_keywords = [
        "limited time",
        "sale ends",
        "this week only",
        "weekend only",
    ]

    if any(keyword in text_lower for keyword in high_urgency_keywords):
        return "high"
    elif any(keyword in text_lower for keyword in medium_urgency_keywords):
        return "medium"
    else:
        return "low"


def save_slickdeals_entries(entries: list[dict[str, Any]]) -> None:
    """Saves Slickdeals RSS feed entries to JSON and CSV in the data/deals directory.

    Args:
        entries: List of Slickdeals RSS entry dictionaries.
    """
    if not entries:
        logger.info("No Slickdeals entries to save. Skipping file generation.")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "deals")
    ensure_directories([output_dir])

    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save timestamped files
    json_file = os.path.join(output_dir, f"slickdeals_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"slickdeals_{timestamp}.csv")

    # Save latest files (overwrite)
    latest_json = os.path.join(output_dir, "slickdeals_latest.json")
    latest_csv = os.path.join(output_dir, "slickdeals_latest.csv")

    # Save JSON files
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    # Save CSV files
    if entries:
        import csv

        # Flatten complex fields for CSV
        csv_entries = []
        for entry in entries:
            csv_entry = entry.copy()
            # Convert lists to comma-separated strings
            for field in ["categories", "deal_category", "store_mentioned"]:
                if isinstance(csv_entry.get(field), list):
                    csv_entry[field] = ", ".join(csv_entry[field])

            # Convert dictionaries to JSON strings
            for field in ["price_mentioned", "discount_percentage"]:
                if isinstance(csv_entry.get(field), dict):
                    csv_entry[field] = json.dumps(csv_entry[field])

            csv_entries.append(csv_entry)

        fieldnames = csv_entries[0].keys() if csv_entries else []

        # Save both timestamped and latest CSV files
        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_entries)

    logger.info(f"Saved {len(entries)} Slickdeals entries to {json_file} and {csv_file}")
    logger.info(f"Latest files updated: {latest_json} and {latest_csv}")


def main():
    """Main function to run the Slickdeals ETL process."""
    logger.info("Starting Slickdeals RSS ETL process")

    try:
        # Fetch deals from Slickdeals RSS feeds
        entries = fetch_slickdeals_feeds()

        if not entries:
            logger.warning("No entries fetched from Slickdeals. Exiting.")
            return

        # Save the entries
        save_slickdeals_entries(entries)

        # Print summary
        deals_with_price = sum(1 for entry in entries if entry.get("price_mentioned", {}).get("has_price", False))
        deals_with_discount = sum(1 for entry in entries if entry.get("discount_percentage", {}).get("has_discount", False))
        high_score_deals = sum(1 for entry in entries if entry.get("deal_score", 0) > 0.5)

        categories = set()
        stores = set()
        for entry in entries:
            categories.update(entry.get("deal_category", []))
            stores.update(entry.get("store_mentioned", []))

        logger.info("Slickdeals ETL completed successfully!")
        logger.info(f"Total deals: {len(entries)}")
        logger.info(f"Deals with price info: {deals_with_price}")
        logger.info(f"Deals with discounts: {deals_with_discount}")
        logger.info(f"High-score deals: {high_score_deals}")
        logger.info(f"Deal categories covered: {', '.join(sorted(categories))}")
        logger.info(f"Stores mentioned: {', '.join(sorted(stores))}")

    except Exception as e:
        logger.error(f"Slickdeals ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
