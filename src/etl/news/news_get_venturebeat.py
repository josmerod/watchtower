"""VentureBeat RSS ETL Module

This module fetches business technology news from VentureBeat RSS feeds.
VentureBeat provides comprehensive coverage of enterprise technology, AI/ML,
gaming industry, and business technology trends.

Usage:
    python src/etl/news/news_get_venturebeat.py

Output:
    - JSON file: data/news/venturebeat_latest.json
    - CSV file: data/news/venturebeat_latest.csv
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests
import feedparser

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("VentureBeatETL")

# VentureBeat RSS feeds for different categories
RSS_FEEDS: dict[str, str] = {
    "venturebeat_main": "https://venturebeat.com/feed/",
    "venturebeat_ai": "https://venturebeat.com/ai/feed/",
    "venturebeat_enterprise": "https://venturebeat.com/business/feed/",
    "venturebeat_gaming": "https://venturebeat.com/games/feed/",
    "venturebeat_security": "https://venturebeat.com/security/feed/",
    "venturebeat_mobile": "https://venturebeat.com/mobile/feed/",
}


def fetch_venturebeat_feeds() -> list[dict[str, Any]]:
    """Fetches and parses RSS feeds from VentureBeat.

    Returns:
        List of news entries with metadata from VentureBeat RSS feeds.
    """
    entries: list[dict[str, Any]] = []

    for source, url in RSS_FEEDS.items():
        logger.info(f"Fetching VentureBeat RSS feed from {source} at {url}")
        try:
            # Use requests with User-Agent to avoid blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"Error parsing feed from {source}: {feed.bozo_exception}")
                # Continue if we have entries despite bozo error
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
                "platform": "venturebeat",
                "content_type": "business_tech_news",
                "language": "en",
                "region": "global",
                "industry_focus": _determine_industry_focus(entry.get("title", "") + " " + summary),
                "business_impact": _assess_business_impact(entry.get("title", "") + " " + summary),
                "technology_trend": _identify_tech_trends(entry.get("title", "") + " " + summary),
                "enterprise_relevance": _check_enterprise_relevance(entry.get("title", "") + " " + summary),
            }

            entries.append(entry_data)

    logger.info(f"Retrieved {len(entries)} items from VentureBeat RSS feeds")
    return entries


def _get_category_from_source(source: str) -> str:
    """Extract category from source name."""
    category_map = {
        "venturebeat_main": "general",
        "venturebeat_ai": "artificial_intelligence",
        "venturebeat_enterprise": "enterprise",
        "venturebeat_gaming": "gaming",
        "venturebeat_security": "cybersecurity",
        "venturebeat_mobile": "mobile_tech",
    }
    return category_map.get(source, "general")


def _determine_industry_focus(text: str) -> list[str]:
    """Determine industry focus based on article content."""
    text_lower = text.lower()
    industries = []

    industry_keywords = {
        "artificial_intelligence": [
            "ai",
            "artificial intelligence",
            "machine learning",
            "ml",
            "deep learning",
            "neural",
            "llm",
            "chatgpt",
            "generative ai",
        ],
        "enterprise_software": [
            "enterprise",
            "saas",
            "b2b",
            "business software",
            "erp",
            "crm",
            "productivity",
            "collaboration",
        ],
        "cybersecurity": [
            "cybersecurity",
            "security",
            "privacy",
            "encryption",
            "cyber",
            "data protection",
            "breach",
            "vulnerability",
        ],
        "cloud_computing": [
            "cloud",
            "aws",
            "azure",
            "google cloud",
            "serverless",
            "containers",
            "kubernetes",
            "devops",
        ],
        "gaming": [
            "gaming",
            "games",
            "esports",
            "mobile games",
            "console",
            "pc gaming",
            "metaverse",
            "vr",
            "ar",
        ],
        "fintech": [
            "fintech",
            "payments",
            "banking",
            "financial services",
            "cryptocurrency",
            "blockchain",
            "digital wallet",
        ],
        "healthtech": [
            "healthtech",
            "digital health",
            "telemedicine",
            "medical technology",
            "healthcare",
            "biotech",
        ],
        "mobility": [
            "autonomous vehicles",
            "self-driving",
            "electric vehicles",
            "mobility",
            "transportation",
            "automotive",
        ],
        "retail_tech": [
            "e-commerce",
            "retail technology",
            "online shopping",
            "marketplace",
            "supply chain",
            "logistics",
        ],
        "media_tech": [
            "media technology",
            "streaming",
            "content creation",
            "digital marketing",
            "advertising technology",
        ],
    }

    for industry, keywords in industry_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            industries.append(industry)

    return industries


def _assess_business_impact(text: str) -> str:
    """Assess the business impact level of the news."""
    text_lower = text.lower()

    high_impact_keywords = [
        "acquisition",
        "merger",
        "ipo",
        "bankruptcy",
        "lawsuit",
        "regulation",
        "partnership",
        "expansion",
        "layoffs",
        "restructuring",
        "billion",
        "market share",
    ]

    medium_impact_keywords = [
        "funding",
        "investment",
        "new product",
        "launch",
        "milestone",
        "growth",
        "revenue",
        "earnings",
        "strategy",
        "million",
        "agreement",
    ]

    if any(keyword in text_lower for keyword in high_impact_keywords):
        return "high"
    elif any(keyword in text_lower for keyword in medium_impact_keywords):
        return "medium"
    else:
        return "low"


def _identify_tech_trends(text: str) -> list[str]:
    """Identify technology trends mentioned in the article."""
    text_lower = text.lower()
    trends = []

    trend_keywords = {
        "generative_ai": [
            "generative ai",
            "chatgpt",
            "llm",
            "large language model",
            "text generation",
            "ai content",
        ],
        "quantum_computing": [
            "quantum computing",
            "quantum",
            "qubits",
            "quantum supremacy",
        ],
        "edge_computing": [
            "edge computing",
            "edge ai",
            "distributed computing",
            "fog computing",
        ],
        "5g_connectivity": ["5g", "connectivity", "wireless", "network infrastructure"],
        "automation": [
            "automation",
            "rpa",
            "robotic process automation",
            "workflow automation",
        ],
        "low_code": ["low-code", "no-code", "citizen developer", "visual programming"],
        "web3": ["web3", "blockchain", "cryptocurrency", "nft", "defi", "dao"],
        "sustainability_tech": [
            "sustainability",
            "green tech",
            "carbon neutral",
            "renewable energy",
            "climate tech",
        ],
        "digital_transformation": [
            "digital transformation",
            "modernization",
            "cloud migration",
            "digitization",
        ],
        "data_analytics": [
            "data analytics",
            "big data",
            "business intelligence",
            "data science",
            "predictive analytics",
        ],
    }

    for trend, keywords in trend_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            trends.append(trend)

    return trends


def _check_enterprise_relevance(text: str) -> bool:
    """Check if the article is relevant to enterprise decision makers."""
    enterprise_keywords = [
        "enterprise",
        "b2b",
        "business",
        "corporate",
        "organization",
        "company",
        "cio",
        "cto",
        "it department",
        "digital transformation",
        "productivity",
        "efficiency",
        "cost reduction",
        "roi",
        "business intelligence",
        "analytics",
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in enterprise_keywords)


def save_venturebeat_entries(entries: list[dict[str, Any]]) -> None:
    """Saves VentureBeat RSS feed entries to JSON and CSV in the data/news directory.

    Args:
        entries: List of VentureBeat RSS entry dictionaries.
    """
    if not entries:
        logger.info("No VentureBeat entries to save. Skipping file generation.")
        return

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "news")
    ensure_directories([output_dir])

    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save timestamped files
    json_file = os.path.join(output_dir, f"venturebeat_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"venturebeat_{timestamp}.csv")

    # Save latest files (overwrite)
    latest_json = os.path.join(output_dir, "venturebeat_latest.json")
    latest_csv = os.path.join(output_dir, "venturebeat_latest.csv")

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
            for field in ["categories", "industry_focus", "technology_trend"]:
                if isinstance(csv_entry.get(field), list):
                    csv_entry[field] = ", ".join(csv_entry[field])
            csv_entries.append(csv_entry)

        fieldnames = csv_entries[0].keys() if csv_entries else []

        # Save both timestamped and latest CSV files
        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_entries)

    logger.info(f"Saved {len(entries)} VentureBeat entries to {json_file} and {csv_file}")
    logger.info(f"Latest files updated: {latest_json} and {latest_csv}")


def main():
    """Main function to run the VentureBeat ETL process."""
    logger.info("Starting VentureBeat RSS ETL process")

    try:
        # Fetch articles from VentureBeat RSS feeds
        entries = fetch_venturebeat_feeds()

        if not entries:
            logger.warning("No entries fetched from VentureBeat. Exiting.")
            return

        # Save the entries
        save_venturebeat_entries(entries)

        # Print summary
        enterprise_articles = sum(1 for entry in entries if entry.get("enterprise_relevance", False))
        high_impact_articles = sum(1 for entry in entries if entry.get("business_impact") == "high")
        ai_articles = sum(1 for entry in entries if "artificial_intelligence" in entry.get("industry_focus", []))

        categories = set()
        trends = set()
        for entry in entries:
            categories.update(entry.get("industry_focus", []))
            trends.update(entry.get("technology_trend", []))

        logger.info("VentureBeat ETL completed successfully!")
        logger.info(f"Total articles: {len(entries)}")
        logger.info(f"Enterprise-relevant articles: {enterprise_articles}")
        logger.info(f"High business impact articles: {high_impact_articles}")
        logger.info(f"AI-related articles: {ai_articles}")
        logger.info(f"Industry categories covered: {', '.join(sorted(categories))}")
        logger.info(f"Technology trends identified: {', '.join(sorted(trends))}")

    except Exception as e:
        logger.error(f"VentureBeat ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
