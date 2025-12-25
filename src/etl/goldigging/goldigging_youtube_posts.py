import concurrent.futures
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yt_dlp

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("goldigging_youtube_posts")
logging.basicConfig(level=logging.INFO)

BASE_OUTPUT_DIR = "data/youtube"
MAX_VIDEOS_PER_CHANNEL = 50
DEFAULT_DAYS_LOOKBACK = 42  # 6 weeks

# Performance optimization constants
MAX_WORKERS_PER_CHANNEL = 8  # Max concurrent video fetches per channel
RATE_LIMIT_DELAY = 0.1  # Delay between API calls in seconds
CACHE_TTL = 300  # Cache TTL in seconds (5 minutes)
CHANNEL_CACHE: dict[str, tuple[dict, float]] = {}  # Cache for channel info
VIDEO_CACHE: dict[str, tuple[dict, float]] = {}  # Cache for video details


# Load channel topics from JSON file
def load_channel_topics() -> dict[str, Any]:
    """Load the channel topics configuration from the JSON file."""
    # Get the directory this file is in
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "channels.json")

    with open(json_path) as json_file:
        return json.load(json_file)


# Channel configurations by topic
CHANNEL_TOPICS = load_channel_topics()


def get_cached_channel_info(channel_handle: str, ydl: yt_dlp.YoutubeDL) -> dict | None:
    """Get cached channel info or fetch fresh data with caching."""
    current_time = time.time()

    # Check cache first
    if channel_handle in CHANNEL_CACHE:
        cached_data, cache_time = CHANNEL_CACHE[channel_handle]
        if current_time - cache_time < CACHE_TTL:
            logger.debug(f"Using cached channel info for {channel_handle}")
            return cached_data

    # Fetch fresh data
    channel_urls = [
        f"https://www.youtube.com/@{channel_handle}/videos",
        f"https://www.youtube.com/c/{channel_handle}/videos",
        f"https://www.youtube.com/channel/{channel_handle}/videos",
    ]

    for url in channel_urls:
        try:
            channel_info = ydl.extract_info(url, download=False)
            if channel_info:
                # Cache the result
                CHANNEL_CACHE[channel_handle] = (channel_info, current_time)
                logger.debug(f"Fetched and cached channel info for {channel_handle}")
                return channel_info
        except Exception as e:
            logger.debug(f"Failed URL {url} for {channel_handle}: {e!s}")
            continue

    logger.warning(f"No channel info found for {channel_handle}")
    return None


def get_cached_video_info(video_id: str, ydl: yt_dlp.YoutubeDL) -> dict | None:
    """Get cached video info or fetch fresh data with caching."""
    current_time = time.time()

    # Check cache first
    if video_id in VIDEO_CACHE:
        cached_data, cache_time = VIDEO_CACHE[video_id]
        if current_time - cache_time < CACHE_TTL:
            logger.debug(f"Using cached video info for {video_id}")
            return cached_data

    # Fetch fresh data
    try:
        video_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        if video_info:
            # Cache the result
            VIDEO_CACHE[video_id] = (video_info, current_time)
            logger.debug(f"Fetched and cached video info for {video_id}")
            return video_info
    except Exception as e:
        logger.debug(f"Failed to fetch video info for {video_id}: {e!s}")

    return None


def rate_limited_fetch(url: str, ydl: yt_dlp.YoutubeDL, delay: float = RATE_LIMIT_DELAY) -> dict | None:
    """Fetch data with rate limiting."""
    try:
        result = ydl.extract_info(url, download=False)
        if delay > 0:
            time.sleep(delay)
        return result
    except Exception as e:
        logger.debug(f"Rate limited fetch failed for {url}: {e!s}")
        if delay > 0:
            time.sleep(delay)
        return None


def process_video_batch(video_ids: list[str], ydl: yt_dlp.YoutubeDL) -> list[dict]:
    """Process a batch of videos concurrently."""
    video_data_list = []

    def fetch_video_details(video_id: str) -> dict | None:
        """Fetch detailed information for a single video."""
        video_info = get_cached_video_info(video_id, ydl)
        if not video_info:
            return None

        # Convert timestamp to ISO format
        timestamp = video_info.get("timestamp")
        if timestamp:
            published_at = datetime.fromtimestamp(timestamp).isoformat() + "Z"
        else:
            # Fallback to upload_date if timestamp is missing
            upload_date = video_info.get("upload_date")
            if upload_date:
                try:
                    published_at = datetime.strptime(upload_date, "%Y%m%d").isoformat() + "Z"
                except ValueError:
                    published_at = datetime.fromtimestamp(0).isoformat() + "Z"
            else:
                published_at = datetime.fromtimestamp(0).isoformat() + "Z"

        return {
            "title": video_info.get("title", ""),
            "url": video_info.get("webpage_url", ""),
            "channel": video_info.get("channel", ""),
            "published_at": published_at,
            "description": video_info.get("description", ""),
            "views": video_info.get("view_count", 0),
            "length": video_info.get("duration", 0),
            "thumbnail": video_info.get(
                "thumbnail",
                # Try to get the highest quality thumbnail available
                next(
                    (t["url"] for t in reversed(video_info.get("thumbnails", [])) if "url" in t),
                    "",
                ),
            ),
            "metadata": {
                "api_source": "yt_dlp",
                "processed_at": datetime.now().isoformat(),
            },
        }

    # Use ThreadPoolExecutor for concurrent video processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_PER_CHANNEL) as executor:
        # Submit all video fetch tasks
        future_to_video_id = {executor.submit(fetch_video_details, video_id): video_id for video_id in video_ids}

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_video_id):
            video_id = future_to_video_id[future]
            try:
                video_data = future.result()
                if video_data:
                    video_data_list.append(video_data)
                    logger.debug(f"Processed video: {video_data['title']}")
                else:
                    logger.debug(f"Failed to process video: {video_id}")
            except Exception as e:
                logger.error(f"Error processing video {video_id}: {e!s}")

    return video_data_list


def get_channel_videos_by_id(
    channel_handle: str,
    published_after: str = (datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)).isoformat(),
) -> list[dict]:
    """Fetch videos from a channel using yt-dlp with optimized parallel processing."""
    try:
        ydl_opts = {
            "extract_flat": True,  # Do not download videos
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "playlist_items": f"1-{MAX_VIDEOS_PER_CHANNEL}",  # Limit number of videos to fetch
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get channel info with caching
            channel_info = get_cached_channel_info(channel_handle, ydl)

            if not channel_info:
                logger.error(f"No se pudo encontrar el canal: {channel_handle}")
                return []

            # Extract video IDs and filter by date
            video_ids = []
            entries = channel_info.get("entries", [])

            for entry in entries:
                if not entry:
                    continue

                # Convert timestamp to ISO format for comparison
                entry_timestamp = entry.get("timestamp")
                if entry_timestamp:
                    published_at = datetime.fromtimestamp(entry_timestamp).isoformat() + "Z"

                    # Skip if video is older than published_after
                    if published_at < published_after:
                        logger.info(f"Reached old content (published {published_at}), stopping fetch for channel")
                        break
                else:
                    # If timestamp is missing, we can't determine age in flat extraction.
                    # Assume it might be new and verify later during detail fetch.
                    logger.debug(f"Timestamp missing for {entry.get('id')}, queuing for detail verification")

                video_ids.append(entry["id"])

            if not video_ids:
                logger.info(f"No recent videos found for {channel_handle}")
                return []

            logger.info(f"Processing {len(video_ids)} videos from {channel_handle}")

            # Process videos in parallel batches
            video_data_list = process_video_batch(video_ids, ydl)

            # Filter out videos that are too old (double-check after fetching details)
            filtered_videos = []
            for video_data in video_data_list:
                if video_data and video_data["published_at"] >= published_after:
                    filtered_videos.append(video_data)

            logger.info(f"Successfully processed {len(filtered_videos)} recent videos from {channel_handle}")
            return filtered_videos

    except Exception as e:
        logger.error(f"Error al obtener videos para {channel_handle}: {e!s}")
        return []


def process_youtube_channels(channel_handles: list[str], published_after: str = None) -> list[dict]:
    """Process multiple YouTube channels concurrently and combine their videos."""
    all_videos = []
    # Determine a reasonable number of workers, e.g., based on CPU cores or a fixed number
    # Let's start with a sensible default, adjust as needed based on performance
    max_workers = min(10, os.cpu_count() + 4)  # Example: Use up to 10 workers

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for each channel processing task
        future_to_channel = {executor.submit(get_channel_videos_by_id, handle, published_after): handle for handle in channel_handles}

        for future in concurrent.futures.as_completed(future_to_channel):
            handle = future_to_channel[future]
            try:
                channel_videos = future.result()
                if channel_videos:
                    all_videos.extend(channel_videos)
                    logger.info(f"Processed successfully {len(channel_videos)} videos from {handle}")
                else:
                    logger.info(f"No new videos found for {handle}")
            except Exception as e:
                logger.error(f"Error processing channel {handle}: {e!s}")
                continue  # Continue with other channels even if one fails

    logger.info(f"Finished processing all channels. Total videos collected: {len(all_videos)}")
    return all_videos


def process_topic(topic: str, channels: list[str], published_after: str = None):
    """Process a specific topic and save its results to separate files."""
    logger.info(f"Procesando tema: {topic}")

    # Create topic-specific output directory
    project_root = get_project_root()
    output_dir = os.path.join(project_root, BASE_OUTPUT_DIR, topic)
    ensure_directories([os.path.join(BASE_OUTPUT_DIR, topic)])

    # Process channels for this topic
    processed_videos = process_youtube_channels(channels, published_after)

    if not processed_videos:
        logger.warning(f"No se recuperaron videos para el tema {topic}, el proceso ETL no puede continuar")
        return

    # Order by published_at descending (newest first)
    processed_videos = sorted(processed_videos, key=lambda x: x["published_at"], reverse=True)

    # Save to JSON file
    json_file = os.path.join(output_dir, "youtube_videos.json")
    with open(json_file, "w") as f:
        json.dump(processed_videos, f, indent=2)
    logger.debug(f"Datos JSON guardados en {json_file}")

    # Also save as CSV for easier viewing (drop description to avoid CSV formatting issues)
    csv_file = os.path.join(output_dir, "youtube_videos.csv")
    pd.DataFrame(processed_videos).drop(columns=["description"]).to_csv(csv_file, index=False)
    logger.debug(f"Datos CSV guardados en {csv_file}")

    logger.info(f"Guardados {len(processed_videos)} videos del tema {topic} en {json_file} y {csv_file}")


def main(topics: list[str] = None):
    """Main function to fetch and process YouTube channel videos by topic."""
    logger.info("Iniciando proceso ETL de canales de YouTube")

    try:
        # Ensure base output directory exists
        ensure_directories([BASE_OUTPUT_DIR])

        # Define date range for videos
        published_after = (datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)).isoformat()

        # If topics is None or empty, process all topics
        if not topics:
            topics = CHANNEL_TOPICS.keys()

        # Process each specified topic
        for topic in topics:
            if topic in CHANNEL_TOPICS:
                process_topic(topic, CHANNEL_TOPICS[topic]["channels"], published_after)
            else:
                logger.warning(f"Tema no reconocido: {topic}")

    except Exception as e:
        logger.error(f"Error en el proceso ETL de YouTube: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Script ETL de YouTube iniciado")

    # Parse command line arguments for topics if provided
    import argparse

    parser = argparse.ArgumentParser(description="Process YouTube channels by topic")
    parser.add_argument("--topics", nargs="+", help="Topics to process (default: all)")
    args = parser.parse_args()

    main(args.topics)
    logger.info("Script ETL de YouTube completado")
