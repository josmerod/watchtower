"""Discord Trending Communities ETL Module

This module fetches and processes trending Discord communities and servers,
particularly focusing on tech, developer, and gaming communities that are
publicly discoverable and growing.

Usage:
    python src/etl/news/news_get_discord_trending.py

Output:
    - JSON file: data/discord_trending/discord_communities_latest.json
    - CSV file: data/discord_trending/discord_communities_latest.csv
"""

import csv
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("DiscordTrendingETL")


def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers
    session.headers.update(
        {
            "User-Agent": "Watchtower-ETL/1.0 (Discord Communities Analytics)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    return session


def generate_mock_discord_communities() -> list[dict[str, Any]]:
    """Generate mock Discord community data for demonstration.
    In production, you'd integrate with Discord's API or scrape public directories.

    Returns:
        List of mock Discord community dictionaries
    """
    from datetime import datetime

    communities = []

    # Community data with realistic tech/dev server information
    community_data = [
        {
            "name": "The Coding Den",
            "category": "programming",
            "focus": "general programming",
            "size_range": "large",
        },
        {
            "name": "Python Discord",
            "category": "programming",
            "focus": "python development",
            "size_range": "very_large",
        },
        {
            "name": "JavaScript Mastery",
            "category": "programming",
            "focus": "javascript development",
            "size_range": "large",
        },
        {
            "name": "React Developers",
            "category": "frameworks",
            "focus": "react development",
            "size_range": "large",
        },
        {
            "name": "Vue.js Community",
            "category": "frameworks",
            "focus": "vue development",
            "size_range": "medium",
        },
        {
            "name": "Angular Community",
            "category": "frameworks",
            "focus": "angular development",
            "size_range": "medium",
        },
        {
            "name": "Rust Programming",
            "category": "programming",
            "focus": "rust development",
            "size_range": "medium",
        },
        {
            "name": "Go Developers",
            "category": "programming",
            "focus": "golang development",
            "size_range": "medium",
        },
        {
            "name": "AI/ML Engineers",
            "category": "ai_ml",
            "focus": "artificial intelligence",
            "size_range": "large",
        },
        {
            "name": "Data Science Hub",
            "category": "ai_ml",
            "focus": "data science",
            "size_range": "large",
        },
        {
            "name": "DevOps Community",
            "category": "devops",
            "focus": "devops practices",
            "size_range": "large",
        },
        {
            "name": "Cloud Architects",
            "category": "cloud",
            "focus": "cloud computing",
            "size_range": "medium",
        },
        {
            "name": "Cybersecurity Pros",
            "category": "security",
            "focus": "cybersecurity",
            "size_range": "large",
        },
        {
            "name": "Web3 Developers",
            "category": "blockchain",
            "focus": "blockchain development",
            "size_range": "medium",
        },
        {
            "name": "Game Developers",
            "category": "gamedev",
            "focus": "game development",
            "size_range": "large",
        },
        {
            "name": "Mobile App Devs",
            "category": "mobile",
            "focus": "mobile development",
            "size_range": "medium",
        },
        {
            "name": "Open Source Contributors",
            "category": "opensource",
            "focus": "open source projects",
            "size_range": "large",
        },
        {
            "name": "Tech Startups",
            "category": "startup",
            "focus": "startup discussions",
            "size_range": "medium",
        },
        {
            "name": "Freelance Developers",
            "category": "freelance",
            "focus": "freelance work",
            "size_range": "medium",
        },
        {
            "name": "UI/UX Designers",
            "category": "design",
            "focus": "user interface design",
            "size_range": "large",
        },
        {
            "name": "Backend Engineers",
            "category": "programming",
            "focus": "backend development",
            "size_range": "large",
        },
        {
            "name": "Frontend Masters",
            "category": "programming",
            "focus": "frontend development",
            "size_range": "large",
        },
        {
            "name": "Database Admins",
            "category": "database",
            "focus": "database management",
            "size_range": "small",
        },
        {
            "name": "System Administrators",
            "category": "sysadmin",
            "focus": "system administration",
            "size_range": "medium",
        },
        {
            "name": "Tech Career Advice",
            "category": "career",
            "focus": "career development",
            "size_range": "large",
        },
    ]

    # Member count ranges
    size_to_members = {
        "small": (500, 2000),
        "medium": (2000, 10000),
        "large": (10000, 50000),
        "very_large": (50000, 200000),
    }

    # Generate communities
    for i, community_info in enumerate(community_data):
        min_members, max_members = size_to_members[community_info["size_range"]]
        member_count = random.randint(min_members, max_members)

        # Calculate growth metrics
        daily_growth = (
            random.randint(5, 200)
            if community_info["size_range"] in ["large", "very_large"]
            else random.randint(1, 50)
        )
        weekly_growth = daily_growth * random.randint(5, 7)

        # Generate activity metrics
        online_members = random.randint(
            int(member_count * 0.02), int(member_count * 0.15)
        )
        messages_per_day = (
            random.randint(100, 5000)
            if community_info["size_range"] in ["large", "very_large"]
            else random.randint(20, 1000)
        )

        # Server features
        features = random.sample(
            [
                "voice_channels",
                "stage_channels",
                "community_features",
                "threads",
                "announcements",
                "moderation_tools",
                "welcome_screen",
                "rules_channel",
                "events",
                "server_discovery",
                "verified",
                "partnered",
            ],
            random.randint(4, 8),
        )

        # Generate server description
        descriptions = {
            "programming": f"A community for {community_info['focus']} enthusiasts to share knowledge, collaborate on projects, and help each other grow.",
            "frameworks": f"Dedicated to {community_info['focus']}, sharing best practices, troubleshooting, and staying updated with the latest features.",
            "ai_ml": f"Exploring the world of {community_info['focus']}, from beginners to experts discussing algorithms, tools, and industry trends.",
            "devops": "DevOps professionals sharing experiences, tools, and practices for better software delivery and infrastructure management.",
            "security": "Cybersecurity community focused on threat analysis, security tools, ethical hacking, and industry best practices.",
            "blockchain": "Web3 and blockchain development community exploring DeFi, smart contracts, and decentralized applications.",
            "gamedev": "Game developers of all levels sharing experiences, showcasing projects, and collaborating on game development.",
            "design": "UI/UX designers sharing design trends, critiques, resources, and career advice in the design industry.",
        }

        description = descriptions.get(
            community_info["category"],
            f"A thriving community focused on {community_info['focus']} and related technologies.",
        )

        # Created date (communities are 6 months to 3 years old)
        days_old = random.randint(180, 1095)
        created_date = datetime.now() - timedelta(days=days_old)

        community = {
            "id": f"discord_server_{i}_{int(time.time())}",
            "name": community_info["name"],
            "description": description,
            "category": community_info["category"],
            "focus": community_info["focus"],
            "member_count": member_count,
            "online_members": online_members,
            "daily_growth": daily_growth,
            "weekly_growth": weekly_growth,
            "messages_per_day": messages_per_day,
            "features": features,
            "created_date": created_date.isoformat(),
            "days_active": days_old,
            "invite_url": f"https://discord.gg/{community_info['name'].replace(' ', '').lower()}",
            "verified": random.choice([True, False])
            if community_info["size_range"] in ["large", "very_large"]
            else False,
            "partnered": random.choice([True, False])
            if community_info["size_range"] == "very_large"
            else False,
            "has_discovery": random.choice([True, False]),
            "language": "English",
            "region": random.choice(
                ["US West", "US East", "Europe", "US Central", "US South"]
            ),
            "fetched_at": datetime.now().isoformat(),
        }

        communities.append(community)

    return communities


def process_discord_communities(
    communities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and enrich Discord community data with additional metrics and categorization.

    Args:
        communities: List of Discord community dictionaries

    Returns:
        List of processed and enriched community data
    """
    logger.info(f"Processing {len(communities)} Discord communities")

    processed_communities = []
    current_time = datetime.now()

    for community in communities:
        try:
            # Parse creation date
            created_date_str = community.get("created_date")
            if created_date_str:
                created_date = datetime.fromisoformat(
                    created_date_str.replace("Z", "+00:00")
                )
                days_since_created = (
                    current_time.replace(tzinfo=created_date.tzinfo) - created_date
                ).days
            else:
                days_since_created = 0

            # Extract metrics
            member_count = community.get("member_count", 0)
            online_members = community.get("online_members", 0)
            daily_growth = community.get("daily_growth", 0)
            messages_per_day = community.get("messages_per_day", 0)

            # Calculate engagement metrics
            engagement_rate = (
                (online_members / member_count * 100) if member_count > 0 else 0
            )
            activity_score = (
                (messages_per_day / member_count * 1000) if member_count > 0 else 0
            )
            growth_rate = (daily_growth / member_count * 100) if member_count > 0 else 0

            # Size categorization
            if member_count >= 50000:
                size_category = "massive"
            elif member_count >= 10000:
                size_category = "large"
            elif member_count >= 2000:
                size_category = "medium"
            elif member_count >= 500:
                size_category = "small"
            else:
                size_category = "tiny"

            # Activity level
            if activity_score >= 10:
                activity_level = "very_active"
            elif activity_score >= 5:
                activity_level = "active"
            elif activity_score >= 2:
                activity_level = "moderate"
            elif activity_score >= 0.5:
                activity_level = "low"
            else:
                activity_level = "minimal"

            # Growth trend
            if growth_rate >= 1:
                growth_trend = "explosive"
            elif growth_rate >= 0.5:
                growth_trend = "fast"
            elif growth_rate >= 0.1:
                growth_trend = "steady"
            elif growth_rate >= 0.05:
                growth_trend = "slow"
            else:
                growth_trend = "stagnant"

            # Community maturity
            if days_since_created <= 30:
                maturity = "new"
            elif days_since_created <= 180:
                maturity = "young"
            elif days_since_created <= 365:
                maturity = "established"
            else:
                maturity = "mature"

            # Calculate trending score
            trending_score = 0
            trending_score += member_count / 1000  # Base score from size
            trending_score += daily_growth * 2  # Growth weight
            trending_score += activity_score * 10  # Activity weight
            if community.get("verified"):
                trending_score *= 1.2
            if community.get("partnered"):
                trending_score *= 1.3

            # Community type classification
            category = community.get("category", "general")
            focus = community.get("focus", "")

            if "programming" in category or "development" in focus:
                community_type = "programming"
            elif "ai" in category or "machine learning" in focus:
                community_type = "ai_ml"
            elif "game" in category or "gaming" in focus:
                community_type = "gaming"
            elif "design" in category or "ui" in focus:
                community_type = "design"
            elif "security" in category or "cyber" in focus:
                community_type = "security"
            else:
                community_type = "tech_general"

            processed_community = {
                **community,
                "days_since_created": days_since_created,
                "engagement_rate": round(engagement_rate, 2),
                "activity_score": round(activity_score, 2),
                "growth_rate": round(growth_rate, 3),
                "size_category": size_category,
                "activity_level": activity_level,
                "growth_trend": growth_trend,
                "maturity": maturity,
                "trending_score": round(trending_score, 2),
                "community_type": community_type,
                "is_trending": trending_score >= 100,
                "is_verified_or_partnered": community.get("verified", False)
                or community.get("partnered", False),
                "platform": "discord",
                "feature_count": len(community.get("features", [])),
            }

            processed_communities.append(processed_community)

        except Exception as e:
            logger.warning(
                f"Error processing community {community.get('name', 'unknown')}: {e}"
            )
            continue

    # Sort by trending score
    processed_communities.sort(key=lambda x: x.get("trending_score", 0), reverse=True)

    logger.info(
        f"Successfully processed {len(processed_communities)} Discord communities"
    )
    return processed_communities


def save_data(data: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """Save processed data to JSON and CSV files.

    Args:
        data: List of processed Discord communities
        output_dir: Directory to save files

    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # File paths
    json_file = os.path.join(output_dir, f"discord_communities_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"discord_communities_{timestamp}.csv")
    latest_json = os.path.join(output_dir, "discord_communities_latest.json")
    latest_csv = os.path.join(output_dir, "discord_communities_latest.csv")

    # Save JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Save CSV
    if data:
        # Flatten data for CSV
        csv_data = []
        for item in data:
            flat_item = {**item}

            # Convert lists to strings
            if isinstance(flat_item.get("features"), list):
                flat_item["features"] = ", ".join(flat_item["features"])

            csv_data.append(flat_item)

        fieldnames = csv_data[0].keys() if csv_data else []

        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

    logger.info(f"Data saved to {json_file} and {csv_file}")

    return {
        "json_file": json_file,
        "csv_file": csv_file,
        "latest_json": latest_json,
        "latest_csv": latest_csv,
    }


def main():
    """Main function to run the Discord Trending Communities ETL process."""
    logger.info("Starting Discord Trending Communities ETL process")

    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "discord_trending")

        # Generate mock data (in production, replace with actual Discord API calls)
        logger.info("Generating Discord community data")
        communities = generate_mock_discord_communities()

        if not communities:
            logger.warning("No Discord communities data generated. Exiting.")
            return

        # Process data
        logger.info("Processing and enriching Discord community data")
        processed_data = process_discord_communities(communities)

        # Save data
        file_paths = save_data(processed_data, output_dir)

        # Summary
        total_communities = len(processed_data)
        trending_communities = len(
            [c for c in processed_data if c.get("is_trending", False)]
        )
        verified_communities = len(
            [c for c in processed_data if c.get("is_verified_or_partnered", False)]
        )

        logger.info("Discord Trending Communities ETL completed successfully!")
        logger.info(f"Total communities: {total_communities}")
        logger.info(f"Trending communities: {trending_communities}")
        logger.info(f"Verified/Partnered communities: {verified_communities}")
        logger.info(f"Files saved: {list(file_paths.values())}")

        # Print category distribution
        if processed_data:
            categories = [c.get("community_type", "Unknown") for c in processed_data]
            from collections import Counter

            top_categories = Counter(categories).most_common(10)
            logger.info(f"Top community types: {top_categories}")

    except Exception as e:
        logger.error(f"Discord Trending Communities ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
