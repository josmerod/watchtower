"""TechCrunch RSS ETL Module

This module fetches startup and enterprise technology news from TechCrunch RSS feed.
TechCrunch provides comprehensive coverage of startup funding, enterprise technology,
and Silicon Valley business news.

Usage:
    python src/etl/news/news_get_techcrunch.py

Output:
    - JSON file: data/news/techcrunch_latest.json
    - CSV file: data/news/techcrunch_latest.csv
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("TechCrunchETL")

# TechCrunch RSS feeds for different categories
RSS_FEEDS: dict[str, str] = {
    "techcrunch_main": "https://techcrunch.com/feed/",
    "techcrunch_startups": "https://techcrunch.com/category/startups/feed/",
    "techcrunch_enterprise": "https://techcrunch.com/category/enterprise/feed/",
    "techcrunch_funding": "https://techcrunch.com/category/fundings-exits/feed/",
    "techcrunch_apps": "https://techcrunch.com/category/apps/feed/",
}


def fetch_techcrunch_feeds() -> list[dict[str, Any]]:
    """Fetches and parses RSS feeds from TechCrunch.

    Returns:
        List of news entries with metadata from TechCrunch RSS feeds.
    """
    entries: list[dict[str, Any]] = []

    for source, url in RSS_FEEDS.items():
        logger.info(f"Fetching TechCrunch RSS feed from {source} at {url}")
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

            # Extract author information
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
            import re

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
                "platform": "techcrunch",
                "content_type": "news_article",
                "language": "en",
                "region": "global",
                "industry_focus": _determine_industry_focus(entry.get("title", "") + " " + summary),
                "funding_mentioned": _check_funding_mentions(entry.get("title", "") + " " + summary),
                "company_mentioned": _extract_company_mentions(entry.get("title", "") + " " + summary),
            }

            entries.append(entry_data)

    logger.info(f"Retrieved {len(entries)} items from TechCrunch RSS feeds")
    return entries


def _get_category_from_source(source: str) -> str:
    """Extract category from source name."""
    category_map = {
        "techcrunch_main": "general",
        "techcrunch_startups": "startups",
        "techcrunch_enterprise": "enterprise",
        "techcrunch_funding": "funding",
        "techcrunch_apps": "apps",
    }
    return category_map.get(source, "general")


def _determine_industry_focus(text: str) -> list[str]:
    """Determine industry focus based on article content."""
    text_lower = text.lower()
    industries = []

    industry_keywords = {
        "ai_ml": [
            "artificial intelligence",
            "machine learning",
            "ai",
            "ml",
            "neural",
            "llm",
            "gpt",
            "openai",
            "anthropic",
        ],
        "fintech": [
            "fintech",
            "cryptocurrency",
            "bitcoin",
            "blockchain",
            "payments",
            "banking",
            "financial",
        ],
        "healthcare": [
            "healthcare",
            "healthtech",
            "medical",
            "pharma",
            "biotech",
            "telemedicine",
        ],
        "enterprise": [
            "enterprise",
            "saas",
            "b2b",
            "business software",
            "productivity",
            "crm",
            "erp",
        ],
        "consumer": [
            "consumer",
            "b2c",
            "social media",
            "entertainment",
            "gaming",
            "e-commerce",
        ],
        "mobility": [
            "autonomous",
            "self-driving",
            "transportation",
            "mobility",
            "automotive",
            "ev",
        ],
        "climate": [
            "climate",
            "clean energy",
            "sustainability",
            "carbon",
            "renewable",
            "green tech",
        ],
        "cybersecurity": [
            "cybersecurity",
            "security",
            "privacy",
            "encryption",
            "cyber",
            "data protection",
        ],
    }

    for industry, keywords in industry_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            industries.append(industry)

    return industries


def _check_funding_mentions(text: str) -> bool:
    """Check if the article mentions funding/investment."""
    funding_keywords = [
        "funding",
        "investment",
        "raised",
        "series a",
        "series b",
        "series c",
        "seed",
        "venture",
        "vc",
        "valuation",
        "million",
        "billion",
        "round",
        "investors",
        "equity",
        "acquisition",
        "merger",
        "ipo",
        "exit",
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in funding_keywords)


def _extract_company_mentions(text: str) -> list[str]:
    """Extract company mentions from article text."""
    # Simple extraction of capitalized words that might be company names

    # Look for patterns like "Company Name" or common tech company names
    tech_companies = [
        "Google",
        "Apple",
        "Microsoft",
        "Amazon",
        "Meta",
        "Tesla",
        "Netflix",
        "Uber",
        "Airbnb",
        "Stripe",
        "Spotify",
        "Zoom",
        "Slack",
        "Salesforce",
        "Adobe",
        "Oracle",
        "SAP",
        "IBM",
        "Intel",
        "Nvidia",
        "AMD",
        "Qualcomm",
        "OpenAI",
        "Anthropic",
        "Databricks",
        "Snowflake",
        "Palantir",
        "Unity",
    ]

    mentioned_companies = []
    for company in tech_companies:
        if company.lower() in text.lower():
            mentioned_companies.append(company)

    return mentioned_companies


def save_techcrunch_entries(entries: list[dict[str, Any]]) -> None:
    """Saves TechCrunch RSS feed entries to JSON and CSV in the data/news directory.

    Args:
        entries: List of TechCrunch RSS entry dictionaries.
    """
    if not entries:
        logger.info("No TechCrunch entries to save. Skipping file generation.")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "news")
    ensure_directories([output_dir])

    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save timestamped files
    json_file = os.path.join(output_dir, f"techcrunch_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"techcrunch_{timestamp}.csv")

    # Save latest files (overwrite)
    latest_json = os.path.join(output_dir, "techcrunch_latest.json")
    latest_csv = os.path.join(output_dir, "techcrunch_latest.csv")

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
            if isinstance(csv_entry.get("categories"), list):
                csv_entry["categories"] = ", ".join(csv_entry["categories"])
            if isinstance(csv_entry.get("industry_focus"), list):
                csv_entry["industry_focus"] = ", ".join(csv_entry["industry_focus"])
            if isinstance(csv_entry.get("company_mentioned"), list):
                csv_entry["company_mentioned"] = ", ".join(csv_entry["company_mentioned"])
            csv_entries.append(csv_entry)

        fieldnames = csv_entries[0].keys() if csv_entries else []

        # Save both timestamped and latest CSV files
        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_entries)

    logger.info(f"Saved {len(entries)} TechCrunch entries to {json_file} and {csv_file}")
    logger.info(f"Latest files updated: {latest_json} and {latest_csv}")


def main():
    """Main function to run the TechCrunch ETL process."""
    logger.info("Starting TechCrunch RSS ETL process")

    try:
        # Fetch articles from TechCrunch RSS feeds
        entries = fetch_techcrunch_feeds()

        if not entries:
            logger.warning("No entries fetched from TechCrunch. Exiting.")
            return

        # Save the entries
        save_techcrunch_entries(entries)

        # Print summary
        funding_articles = sum(1 for entry in entries if entry.get("funding_mentioned", False))
        categories = set()
        for entry in entries:
            categories.update(entry.get("industry_focus", []))

        logger.info("TechCrunch ETL completed successfully!")
        logger.info(f"Total articles: {len(entries)}")
        logger.info(f"Funding-related articles: {funding_articles}")
        logger.info(f"Industry categories covered: {', '.join(sorted(categories))}")

    except Exception as e:
        logger.error(f"TechCrunch ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
