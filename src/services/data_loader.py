"""Shared data loading services for Watchtower Dashboard and API."""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from src.web.dashboard.utils import get_data_path, parse_date_universal

# Configure logging
logger = logging.getLogger(__name__)

# --- Configuration ---

NEWS_SOURCES_CONFIG = {
    "techcrunch": {
        "path": get_data_path("news", "techcrunch_latest.json"),
        "name": "TechCrunch",
    },
    "venturebeat": {
        "path": get_data_path("news", "venturebeat_latest.json"),
        "name": "VentureBeat",
    },
    "freecodecamp": {
        "path": get_data_path("news", "freecodecamp_latest.json"),
        "name": "freeCodeCamp",
    },
    "google_ai_blog": {
        "path": get_data_path("news", "google_ai_blog_latest.json"),
        "name": "Google AI Blog",
    },
    "lobsters": {
        "path": get_data_path("news", "lobsters_latest.json"),
        "name": "Lobsters",
    },
    "arstechnica": {
        "path": get_data_path("news", "arstechnica_latest.json"),
        "name": "Ars Technica",
    },
    "futuretools": {
        "path": get_data_path("futuretools", "futuretoolsnews.json"),
        "name": "FutureTools",
    },
    "bensbites": {
        "path": get_data_path("bensbites", "bensbites_news.json"),
        "name": "Ben's Bites",
    },
    "hackernews": {
        "path": get_data_path("hackernews", "hackernews.json"),
        "name": "Hacker News",
    },
    "medium_genai": {
        "path": get_data_path("medium_genai", "medium_genai.json"),
        "name": "Medium GenAI",
    },
    "kdnuggets": {
        "path": get_data_path("kdnuggets", "kdnuggets.json"),
        "name": "KDnuggets",
    },
    "meneame_general": {
        "path": get_data_path("meneame", "meneame_general_latest.json"),
        "name": "Meneame General",
    },
    "meneame_tecnologia": {
        "path": get_data_path("meneame", "meneame_tecnologia_latest.json"),
        "name": "Meneame Tech",
    },
    "indiehackers": {
        "path": get_data_path("indie_hackers", "posts.json"),
        "name": "Indie Hackers",
    },
    "kagi_world": {
        "path": get_data_path("kagi_world", "kagi_world.json"),
        "name": "Kagi World",
    },
    "kagi_usa": {
        "path": get_data_path("kagi_usa", "kagi_usa.json"),
        "name": "Kagi USA",
    },
    "kagi_business": {
        "path": get_data_path("kagi_business", "kagi_business.json"),
        "name": "Kagi Business",
    },
    "kagi_science": {
        "path": get_data_path("kagi_science", "kagi_science.json"),
        "name": "Kagi Science",
    },
    "kagi_gaming": {
        "path": get_data_path("kagi_gaming", "kagi_gaming.json"),
        "name": "Kagi Gaming",
    },
    "kagi_ai": {"path": get_data_path("kagi_ai", "kagi_ai.json"), "name": "Kagi AI"},
    "kagi_europe": {
        "path": get_data_path("kagi_europe", "kagi_europe.json"),
        "name": "Kagi Europe",
    },
    "kagi_spain": {
        "path": get_data_path("kagi_spain", "kagi_spain.json"),
        "name": "Kagi Spain",
    },
    "microsiervos": {
        "path": get_data_path("microsiervos", "output", "microsiervos_latest.json"),
        "name": "Microsiervos",
    },
    "spanish_tech": {
        "path": get_data_path("news", "spanish_tech_latest.json"),
        "name": "Spanish Tech (Xataka, Hipertextual, Genbeta)",
    },
    "tldr": {
        "path": get_data_path("tldr", "tldr_news.json"),
        "name": "tldr.tech (Tech/AI/Data)",
    },
}

DEALS_SOURCES_CONFIG = {
    "lifetimo": {
        "path": get_data_path("deals", "lifetimo_deals.json"),
        "name": "Lifetimo Deals",
    },
}

ARXIV_SOURCES_CONFIG = {
    "hf_trending": {
        "path": get_data_path("arxiv", "hf_daily_papers_latest.json"),
        "name": "🔥 HF Trending",
    },
    "all_arxiv": {
        "path": get_data_path("arxiv", "arxiv_papers_latest.json"),
        "name": "All Papers",
    },
    "machine_learning": {
        "path": get_data_path("arxiv", "arxiv_machine_learning_latest.json"),
        "name": "Machine Learning",
    },
    "computer_vision": {
        "path": get_data_path("arxiv", "arxiv_computer_vision_latest.json"),
        "name": "Computer Vision",
    },
    "nlp": {
        "path": get_data_path("arxiv", "arxiv_natural_language_latest.json"),
        "name": "NLP",
    },
    "neural_networks": {
        "path": get_data_path("arxiv", "arxiv_neural_networks_latest.json"),
        "name": "Neural Networks",
    },
    "robotics": {
        "path": get_data_path("arxiv", "arxiv_robotics_latest.json"),
        "name": "Robotics",
    },
    "reinforcement_learning": {
        "path": get_data_path("arxiv", "arxiv_reinforcement_learning_latest.json"),
        "name": "RL & AI",
    },
    "security": {
        "path": get_data_path("arxiv", "arxiv_security_latest.json"),
        "name": "Security & Privacy",
    },
    "systems_cloud": {
        "path": get_data_path("arxiv", "arxiv_systems_cloud_latest.json"),
        "name": "Systems & Cloud",
    },
    "quantum": {
        "path": get_data_path("arxiv", "arxiv_quantum_latest.json"),
        "name": "Quantum Computing",
    },
    "data_engineering": {
        "path": get_data_path("arxiv", "arxiv_data_engineering_latest.json"),
        "name": "Data Engineering",
    },
}

KNOWLEDGE_SOURCES_CONFIG = {
    "opensource": {
        "path": get_data_path("open_source_intelligence", "output", "latest.json"),
        "name": "Open Source Projects",
    },
    "reddit_opensource": {
        "path": get_data_path("reddit_unified", "reddit_opensource_latest.json"),
        "name": "Reddit Open Source",
    },
    "gooddevs": {
        "path": get_data_path("gooddevs", "gooddevs_latest.json"),
        "name": "Good Devs",
    },
    "podcasts": {
        "path": get_data_path("podcasts", "podcasts_latest.json"),
        "name": "Podcasts",
    },
    "product_hunt": {
        "path": get_data_path("product_hunt", "product_hunt_latest.json"),
        "name": "Product Hunt",
    },
    "gittrends": {
        "path": get_data_path("github_trends", "github_trends_latest.json"),
        "name": "Git Trends",
    },
    "hackernews_ask": {
        "path": get_data_path("hackernews_ask", "hackernews_ask_latest.json"),
        "name": "HN Ask",
    },
    "stackoverflow_trends": {
        "path": get_data_path("stackoverflow_trends", "stackoverflow_trends_latest.json"),
        "name": "Stack Overflow",
    },
    "reddit_unified": {
        "path": get_data_path("reddit_unified", "reddit_unified_latest.json"),
        "name": "Reddit All",
    },
    "reddit_ai_ml": {
        "path": get_data_path("reddit_unified", "reddit_ai_ml_latest.json"),
        "name": "Reddit AI/ML",
    },
    "reddit_programming": {
        "path": get_data_path("reddit_unified", "reddit_programming_latest.json"),
        "name": "Reddit Programming",
    },
    "reddit_tech": {
        "path": get_data_path("reddit_unified", "reddit_tech_latest.json"),
        "name": "Reddit Tech",
    },
    "reddit_devops": {
        "path": get_data_path("reddit_unified", "reddit_devops_latest.json"),
        "name": "Reddit DevOps",
    },
    "devto": {"path": get_data_path("devto", "devto.json"), "name": "Dev.to"},
    "hypeurls": {"path": get_data_path("reddit_unified", "reddit_news_latest.json"), "name": "HypeURLs"},
    "lesswrong": {
        "path": get_data_path("lesswrong", "lesswrong_latest.json"),
        "name": "LessWrong",
    },
    "substack": {
        "path": get_data_path("substack", "output", "latest.json"),
        "name": "Substack",
    },
    "trendshift": {
        "path": get_data_path("trendshift", "output", "latest.json"),
        "name": "TrendShift",
    },
    "rss_feeds": {
        "path": get_data_path("rss_feeds", "output", "latest.json"),
        "name": "RSS Feeds",
    },
}

GAMES_SOURCES_CONFIG = {
    "deals": {
        "path": get_data_path("games", "deals.json"),
        "name": "Game Deals",
    },
    "bundles": {
        "path": get_data_path("games", "bundles.json"),
        "name": "Game Bundles",
    },
    "trending": {
        "path": get_data_path("games", "itchio_trending.json"),
        "name": "Trending Games",
    },
}

BENCHMARKS_SOURCES_CONFIG = {
    "overall": {
        "path": get_data_path("benchmarks", "bridgebench_overall.json"),
        "name": "Overall Rankings",
    },
    "security": {
        "path": get_data_path("benchmarks", "bridgebench_security.json"),
        "name": "Security Benchmark",
    },
    "debugging": {
        "path": get_data_path("benchmarks", "bridgebench_debugging.json"),
        "name": "Debugging Benchmark",
    },
    "refactoring": {
        "path": get_data_path("benchmarks", "bridgebench_refactoring.json"),
        "name": "Refactoring Benchmark",
    },
    "hallucination": {
        "path": get_data_path("benchmarks", "bridgebench_hallucination.json"),
        "name": "Hallucination Benchmark",
    },
    "reasoning": {
        "path": get_data_path("benchmarks", "bridgebench_reasoning.json"),
        "name": "Reasoning Benchmark",
    },
}

# --- AI Platform Models ---

AI_PLATFORMS_SOURCES_CONFIG = {
    "replicate": {
        "path": get_data_path("ai_platforms", "replicate_explore_latest.json"),
        "name": "Replicate Models",
    },
}

# --- Expanded Intelligence (GitHub, StackExchange, OpenAlex, etc.) ---

EXPANDED_SOURCES_CONFIG = {
    "github_analytics": {
        "path": get_data_path("github_analytics", "output", "github_analytics_latest.json"),
        "name": "GitHub Trending",
    },
    "stackexchange": {
        "path": get_data_path("stackexchange", "output", "stackexchange_latest.json"),
        "name": "Stack Exchange",
    },
    "openalex": {
        "path": get_data_path("openalex", "output", "openalex_latest.json"),
        "name": "OpenAlex Research",
    },
    "package_registry": {
        "path": get_data_path("package_registry", "output", "packages_latest.json"),
        "name": "Package Registry",
    },
    "kaggle": {
        "path": get_data_path("kaggle", "output", "kaggle_latest.json"),
        "name": "Kaggle Datasets",
    },
}

# --- Spanish Public Aid ---

SPANISH_AID_SOURCES_CONFIG = {
    "public_aid": {
        "path": get_data_path("spanish_public_aid", "output", "spanish_public_aid_latest.json"),
        "name": "Spanish Public Aid",
    },
}

# --- Cloud Provider Updates ---

CLOUD_UPDATES_SOURCES_CONFIG = {
    "cloud_updates": {
        "path": get_data_path("cloud_updates", "cloud_updates_latest.json"),
        "name": "Cloud Updates (AWS, CNCF, GitHub)",
    },
}

# --- Valencia Local Feeds ---

VALENCIA_LOCAL_SOURCES_CONFIG = {
    "valencia_local": {
        "path": get_data_path("valencia_local", "valencia_local_latest.json"),
        "name": "Valencia Local (20minutos CV, Metro VLC)",
    },
}

# --- Shared Logic ---


def _normalize_dedupe_text(value: Any) -> str:
    """Normalize text/URLs for lightweight display-time deduplication."""
    if value is None:
        return ""

    normalized = str(value).strip().lower()
    normalized = re.sub(r"^https?://(www\.)?", "", normalized)
    normalized = re.sub(r"[#?].*$", "", normalized)
    normalized = normalized.rstrip("/")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def get_item_dedupe_key(item: dict[str, Any]) -> tuple[str, str] | None:
    """Return a stable key for exact/near-exact duplicate feed items.

    Prefer URL because titles can legitimately repeat in sources such as travel deals.
    Fall back to title only when there is no URL-like field.
    """
    url = _normalize_dedupe_text(item.get("url") or item.get("link") or item.get("html_url") or item.get("website"))
    if url:
        return ("url", url)

    title = _normalize_dedupe_text(item.get("title") or item.get("name") or item.get("full_name") or item.get("model"))
    if title:
        return ("title", title)

    return None


def deduplicate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate feed items while preserving first-seen order.

    This is intentionally conservative: URL matches are removed across the board;
    title-only matches are only used when an item has no URL at all. That avoids
    collapsing legitimate repeated titles with different links/prices.
    """
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    removed = 0

    for item in items:
        key = get_item_dedupe_key(item)
        if key and key in seen:
            removed += 1
            continue
        if key:
            seen.add(key)
        deduped.append(item)

    if removed:
        logger.info("Deduplicated %s duplicate items from %s loaded records", removed, len(items))

    return deduped


def load_data_from_file(file_path: str) -> list[dict[str, Any]]:
    """Loads items from a JSON file, handling various formats."""
    try:
        if not os.path.exists(file_path):
            # logger.warning(f"File not found: {file_path}")
            return []

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Ensure data is a list of records
        if isinstance(data, dict):
            if "articles" in data and isinstance(data["articles"], list):
                return deduplicate_items(data["articles"])
            elif "items" in data and isinstance(data["items"], list):
                return deduplicate_items(data["items"])
            elif "models" in data and isinstance(data["models"], list):
                return deduplicate_items(data["models"])
            # Single item heuristic
            elif all(k in data for k in ["title", "url"]):
                return [data]
            else:
                logger.warning(f"Data in {file_path} is a dict but not a recognized list structure.")
                return []
        elif isinstance(data, list):
            return deduplicate_items(data)
        else:
            logger.warning(f"Data in {file_path} is not a list or dict. Type: {type(data)}")
            return []

    except json.JSONDecodeError:
        logger.warning(f"Could not decode JSON from {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        return []


def parse_date(date_str: Any) -> datetime | None:
    """Wrapper around universal date parser."""
    return parse_date_universal(date_str, "DataLoader")


def get_sortable_date(article: dict[str, Any]) -> datetime:
    """Get a sortable datetime object from an article dictionary."""
    date_str = (
        article.get("published_at")
        or article.get("published")
        or article.get("published_date")
        or article.get("publication_date")
        or article.get("created_at")
        or article.get("created_utc")
        or article.get("updated_at")
        or article.get("updated")
        or article.get("time")
        or article.get("pubDate")
        or article.get("release_date")
        or article.get("fetched_at")
        or article.get("extracted_at")
        or article.get("first_seen")
        or article.get("date")
    )
    parsed = parse_date(date_str)
    return parsed if parsed else datetime.min.replace(tzinfo=timezone.utc)


def format_article_date(article: dict[str, Any]) -> str:
    """Formats the date for display."""
    parsed_dt = get_sortable_date(article)
    if parsed_dt == datetime.min.replace(tzinfo=timezone.utc):
        return "Date N/A"
    return parsed_dt.strftime("%Y-%m-%d %H:%M UTC")
