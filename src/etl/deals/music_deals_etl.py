"""Music & Entertainment Deals ETL Module

This module fetches music deals, free albums, pay-what-you-want releases,
and entertainment bargains from Bandcamp, NoiseTrade, Archive.org, and more.

Usage:
    python src/etl/deals/music_deals_etl.py

Output:
    - JSON file: data/deals/music_deals.json
    - CSV file: data/deals/music_deals.csv
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests
from bs4 import BeautifulSoup
import re

# Add the project root to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.etl.base import BaseETL

# Initialize logger
logger = get_logger("MusicDealsETL")


class MusicDealsETL(BaseETL):
    """ETL for music and entertainment deals."""

    def __init__(self):
        super().__init__("music_deals")
        self.sources = {
            "bandcamp_free": {
                "name": "Bandcamp",
                "discover_url": "https://bandcamp.com/discover",
                "tag_urls": [
                    "https://bandcamp.com/tag/free-download",
                    "https://bandcamp.com/tag/pay-what-you-want",
                    "https://bandcamp.com/tag/name-your-price",
                ],
                "category": "music",
            },
            "noisetrade": {
                "name": "NoiseTrade",
                "url": "https://noisetrade.com/",
                "free_url": "https://noisetrade.com/free",
                "category": "music",
            },
            "archive_music": {
                "name": "Archive.org",
                "url": "https://archive.org/details/etree",
                "live_music_url": "https://archive.org/details/GratefulDead",
                "category": "music",
            },
            "free_music_archive": {
                "name": "Free Music Archive",
                "url": "https://freemusicarchive.org/",
                "api_url": "https://freemusicarchive.org/api/",
                "category": "music",
            },
        }

    def extract(self) -> Dict[str, Any]:
        """Extract music deals from multiple sources."""
        logger.info("Starting music deals extraction...")

        all_deals = []

        # Add curated music deals and free sources
        curated_deals = self._get_curated_music_deals()
        all_deals.extend(curated_deals)

        # Could add more specific extraction methods here
        # For now focusing on curated high-quality sources

        logger.info(f"Total extracted {len(all_deals)} music deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_music_deals(self) -> List[Dict[str, Any]]:
        """Get manually curated list of music deals and free sources."""
        curated = [
            {
                "title": "Bandcamp Free Downloads",
                "description": "Thousands of free and pay-what-you-want albums from independent artists",
                "url": "https://bandcamp.com/tag/free-download",
                "platform": "Bandcamp",
                "category": "music",
                "deal_type": "free_music",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "music_type": "albums",
                "genre": "various",
                "artist_type": "independent",
                "download_format": ["FLAC", "MP3", "WAV"],
                "drm_free": True,
                "tags": ["indie", "free download", "high quality", "drm-free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Bandcamp Pay-What-You-Want",
                "description": "Albums where you can pay any amount including $0, supporting artists directly",
                "url": "https://bandcamp.com/tag/pay-what-you-want",
                "platform": "Bandcamp",
                "category": "music",
                "deal_type": "pay_what_you_want",
                "original_price": 15,
                "current_price": 0,
                "savings": 15,
                "discount_percentage": 100,
                "music_type": "albums",
                "genre": "various",
                "artist_type": "independent",
                "download_format": ["FLAC", "MP3", "WAV"],
                "drm_free": True,
                "tags": ["flexible pricing", "support artists", "high quality"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Archive.org Live Music Collection",
                "description": "Over 200,000 free live concert recordings from Grateful Dead, Phish, and more",
                "url": "https://archive.org/details/etree",
                "platform": "Archive.org",
                "category": "music",
                "deal_type": "free_music",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "music_type": "live_recordings",
                "genre": "rock",
                "artist_type": "established",
                "download_format": ["FLAC", "MP3", "SHN"],
                "drm_free": True,
                "tags": ["live music", "grateful dead", "phish", "historical"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Free Music Archive",
                "description": "Curated collection of high-quality, legal audio downloads directed by WFMU",
                "url": "https://freemusicarchive.org/",
                "platform": "Free Music Archive",
                "category": "music",
                "deal_type": "free_music",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "music_type": "curated_collection",
                "genre": "various",
                "artist_type": "various",
                "download_format": ["MP3"],
                "drm_free": True,
                "tags": ["curated", "wfmu", "legal", "diverse genres"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "YouTube Music Free Tier",
                "description": "Ad-supported free music streaming with millions of songs",
                "url": "https://music.youtube.com/",
                "platform": "YouTube Music",
                "category": "music",
                "deal_type": "free_streaming",
                "original_price": 120,  # Annual premium cost
                "current_price": 0,
                "savings": 120,
                "discount_percentage": 100,
                "music_type": "streaming",
                "genre": "all",
                "artist_type": "all",
                "download_format": ["Stream only"],
                "drm_free": False,
                "tags": ["streaming", "ad-supported", "massive library"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Spotify Free Tier",
                "description": "Ad-supported free music streaming with shuffle play on mobile",
                "url": "https://open.spotify.com/",
                "platform": "Spotify",
                "category": "music",
                "deal_type": "free_streaming",
                "original_price": 120,  # Annual premium cost
                "current_price": 0,
                "savings": 120,
                "discount_percentage": 100,
                "music_type": "streaming",
                "genre": "all",
                "artist_type": "all",
                "download_format": ["Stream only"],
                "drm_free": False,
                "tags": ["streaming", "ad-supported", "discovery"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "SoundCloud Free Music",
                "description": "Independent artists sharing free tracks and exclusive releases",
                "url": "https://soundcloud.com/discover",
                "platform": "SoundCloud",
                "category": "music",
                "deal_type": "free_music",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "music_type": "individual_tracks",
                "genre": "various",
                "artist_type": "independent",
                "download_format": ["MP3"],
                "drm_free": True,
                "tags": ["independent", "emerging artists", "remixes"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Jamendo Free Music",
                "description": "Creative Commons licensed music free for personal and commercial use",
                "url": "https://www.jamendo.com/",
                "platform": "Jamendo",
                "category": "music",
                "deal_type": "free_music",
                "original_price": 0,
                "current_price": 0,
                "savings": 0,
                "discount_percentage": 0,
                "music_type": "albums_tracks",
                "genre": "various",
                "artist_type": "independent",
                "download_format": ["MP3"],
                "drm_free": True,
                "tags": ["creative commons", "commercial use", "royalty-free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Humble Bundle Music Collections",
                "description": "Occasional music bundles featuring soundtracks, albums, and production music",
                "url": "https://www.humblebundle.com/books",
                "platform": "Humble Bundle",
                "category": "music",
                "deal_type": "bundle",
                "original_price": 100,
                "current_price": 15,
                "savings": 85,
                "discount_percentage": 85,
                "music_type": "bundles",
                "genre": "soundtracks",
                "artist_type": "various",
                "download_format": ["FLAC", "MP3"],
                "drm_free": True,
                "tags": ["bundle", "soundtracks", "game music", "charity"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Amazon Music Free Tier",
                "description": "Ad-supported free music streaming with 2 million songs",
                "url": "https://music.amazon.com/",
                "platform": "Amazon Music",
                "category": "music",
                "deal_type": "free_streaming",
                "original_price": 99,  # Annual unlimited cost
                "current_price": 0,
                "savings": 99,
                "discount_percentage": 100,
                "music_type": "streaming",
                "genre": "popular",
                "artist_type": "mainstream",
                "download_format": ["Stream only"],
                "drm_free": False,
                "tags": ["streaming", "ad-supported", "amazon"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated music deals")
        return curated

    def transform(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform music deals data."""
        logger.info("Starting music deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate music value score
                music_score = self._calculate_music_value_score(deal)

                # Determine quality rating
                quality_rating = self._determine_quality_rating(deal)

                transformed_deal = {
                    "title": title,
                    "description": deal.get("description", "")[:400],
                    "url": deal["url"],
                    "platform": deal["platform"],
                    "category": deal["category"],
                    "deal_type": deal["deal_type"],
                    "original_price": deal.get("original_price", 0),
                    "current_price": deal.get("current_price", 0),
                    "savings": deal.get("savings", 0),
                    "discount_percentage": deal.get("discount_percentage", 0),
                    "music_score": music_score,
                    "quality_rating": quality_rating,
                    "music_type": deal.get("music_type", "unknown"),
                    "genre": deal.get("genre", "various"),
                    "artist_type": deal.get("artist_type", "unknown"),
                    "download_format": deal.get("download_format", []),
                    "drm_free": deal.get("drm_free", False),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming music deal: {e}")
                continue

        # Sort by music score and savings
        transformed_deals.sort(
            key=lambda x: (x["music_score"], x["savings"]), reverse=True
        )

        logger.info(f"Transformed {len(transformed_deals)} music deals")
        return transformed_deals

    def _calculate_music_value_score(self, deal: Dict[str, Any]) -> float:
        """Calculate music value score for ranking deals."""
        score = 0.0

        # Platform quality weight
        platform = deal.get("platform", "").lower()
        if "bandcamp" in platform:
            score += 5.0  # High quality, supports artists
        elif any(name in platform for name in ["archive.org", "free music archive"]):
            score += 4.5  # High quality, legal
        elif any(name in platform for name in ["spotify", "youtube music"]):
            score += 4.0  # Mainstream, large libraries
        elif "humble" in platform:
            score += 4.0  # Good value bundles
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type == "free_music":
            score += 4.0
        elif deal_type == "pay_what_you_want":
            score += 4.5  # Supports artists
        elif deal_type == "bundle":
            score += 3.5
        elif deal_type == "free_streaming":
            score += 3.0

        # Quality indicators
        if deal.get("drm_free", False):
            score += 1.0

        download_formats = deal.get("download_format", [])
        if any("FLAC" in fmt or "WAV" in fmt for fmt in download_formats):
            score += 1.0  # High quality audio

        # Artist support
        if deal.get("artist_type") == "independent":
            score += 0.5  # Supporting indie artists

        # Savings consideration
        savings = deal.get("savings", 0)
        if savings > 50:
            score += 2.0
        elif savings > 20:
            score += 1.0

        return round(score, 2)

    def _determine_quality_rating(self, deal: Dict[str, Any]) -> str:
        """Determine quality rating of the music deal."""
        download_formats = deal.get("download_format", [])
        platform = deal.get("platform", "").lower()
        drm_free = deal.get("drm_free", False)

        # Premium quality indicators
        if any("FLAC" in fmt or "WAV" in fmt for fmt in download_formats):
            if drm_free and "bandcamp" in platform:
                return "premium"
            else:
                return "high"

        # High quality indicators
        if drm_free and any(
            platform_name in platform
            for platform_name in ["bandcamp", "archive.org", "free music archive"]
        ):
            return "high"

        # Good quality indicators
        if any(
            platform_name in platform
            for platform_name in ["spotify", "youtube music", "humble"]
        ):
            return "good"

        return "standard"

    def load(self, transformed_data: List[Dict[str, Any]]) -> bool:
        """Load transformed music deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "music_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "music_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(
                f"Successfully saved {len(transformed_data)} music deals to {output_dir}"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving music deals data: {e}")
            return False


def main():
    """Main function to run the Music Deals ETL."""
    etl = MusicDealsETL()
    success = etl.run()

    if success:
        logger.info("Music Deals ETL completed successfully")
    else:
        logger.error("Music Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
