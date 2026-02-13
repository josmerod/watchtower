"""YouTube Shorts Metadata ETL

This module fetches metadata for YouTube Shorts from specified channels.
It replaces the previous OCR-heavy implementation with a lightweight version that 
only fetches titles, thumbnails, and metadata, as the dashboard does not use OCR data.

Usage:
    python src/etl/youtube_shorts_ocr_etl.py

Output:
    - JSON file: data/youtube/{channel_name}/youtube_videos.json
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import yt_dlp
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("youtube_shorts_etl")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configuration
# Default target channel (can be overridden or expanded in variables)
TARGET_CHANNEL_URL = "https://youtube.com/@setupsaitony/shorts"

MAX_SHORTS_TO_PROCESS = 50
DEFAULT_DAYS_LOOKBACK = 30
MAX_RETRIES = 3


def get_channel_name(channel_url: str) -> str:
    """Extract suitable directory name from channel URL."""
    try:
        parsed = urlparse(channel_url)
        path_parts = parsed.path.strip("/").split("/")
        
        # Handle @username format
        for part in path_parts:
            if part.startswith("@"):
                return part[1:]
        
        # Handle /channel/ID format
        if "channel" in path_parts:
            idx = path_parts.index("channel")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]
                
        # Handle /c/name format
        if "c" in path_parts:
            idx = path_parts.index("c")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]
                
        return "unknown_channel"
    except Exception:
        return "unknown_channel"


def get_video_metadata(channel_url: str, limit: int, lookback_days: int) -> list[dict]:
    """Fetches metadata for videos from a given YouTube channel URL."""
    
    logger.info(f"Fetching video metadata from {channel_url}...")
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "extract_flat": True,  # Don't download, just list
        "dateafter": (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d"),
        "playlistend": limit,
    }

    videos = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            
            if not result:
                logger.warning("No result from yt-dlp")
                return []
                
            entries = result.get("entries", [])
            if not entries:
                entries = [result] if "id" in result else []
                
            logger.info(f"Found {len(entries)} entries")
            
            for entry in entries:
                if not entry:
                    continue
                    
                video_id = entry.get("id")
                title = entry.get("title", "No Title")
                url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
                
                # Check for shorts URL pattern if not explicit
                if "shorts" in channel_url and "/shorts/" not in url:
                    url = f"https://www.youtube.com/shorts/{video_id}"

                # Calculate published date
                upload_date = entry.get("upload_date")
                published_at = ""
                if upload_date:
                    try:
                        dt = datetime.strptime(upload_date, "%Y%m%d")
                        published_at = dt.isoformat()
                    except ValueError:
                        pass
                
                video_data = {
                    "id": video_id,
                    "title": title,
                    "url": url,
                    "thumbnail": entry.get("thumbnail"),
                    "published_at": published_at,
                    "description": entry.get("description", ""),
                    "views": entry.get("view_count", 0),
                    "length": entry.get("duration", 0),
                    "channel": result.get("uploader", get_channel_name(channel_url)),
                    "fetched_at": datetime.now().isoformat()
                }
                
                videos.append(video_data)
                
    except Exception as e:
        logger.error(f"Error fetching metadata: {e}")
        
    return videos


def main(args):
    """Main function to run the ETL."""
    logger.info("Starting YouTube Shorts Metadata ETL")
    
    project_root = get_project_root()
    base_output_dir = os.path.join(project_root, "data", "youtube")
    
    # Extract channel name for directory
    channel_name = get_channel_name(TARGET_CHANNEL_URL)
    output_dir = os.path.join(base_output_dir, channel_name)
    ensure_directories([output_dir])
    
    # Fetch videos
    videos = get_video_metadata(TARGET_CHANNEL_URL, args.limit, args.days)
    
    if not videos:
        logger.warning("No videos found.")
        return

    # Save to JSON
    output_file = os.path.join(output_dir, "youtube_videos.json")
    
    # Merge with existing if needed, or just overwrite? 
    # Usually overwrite is cleaner for a "latest state" view, but appending new ones is good for history.
    # The dashboard loads this JSON. Let's merge by ID.
    
    existing_videos = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_videos = json.load(f)
        except Exception:
            pass
            
    # Create dict by ID
    video_map = {v["id"]: v for v in existing_videos}
    
    # Update/Add new videos
    for v in videos:
        video_map[v["id"]] = v
        
    # Convert back to list and sort
    final_list = list(video_map.values())
    final_list.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(final_list)} videos to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Shorts Metadata ETL")
    parser.add_argument("--limit", type=int, default=MAX_SHORTS_TO_PROCESS, help="Max videos to fetch")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS_LOOKBACK, help="Lookback days")
    
    args = parser.parse_args()
    main(args)
