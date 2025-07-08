import concurrent.futures
import json
import logging
import os
import sys
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


def get_channel_videos_by_id(
    channel_handle: str,
    published_after: str = (
        datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)
    ).isoformat(),
) -> list[dict]:
    """Fetch videos from a channel using yt-dlp."""
    try:
        ydl_opts = {
            "extract_flat": True,  # Do not download videos
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "playlist_items": f"1-{MAX_VIDEOS_PER_CHANNEL}",  # Limit number of videos to fetch
        }

        videos = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get channel URL - try both @ handle and direct channel URL formats
            channel_urls = [
                f"https://www.youtube.com/@{channel_handle}/videos",
                f"https://www.youtube.com/c/{channel_handle}/videos",
                f"https://www.youtube.com/channel/{channel_handle}/videos",
            ]

            channel_info = None
            for url in channel_urls:
                try:
                    channel_info = ydl.extract_info(url, download=False)
                    if channel_info:
                        break
                except Exception:
                    continue

            if not channel_info:
                logger.error(f"No se pudo encontrar el canal: {channel_handle}")
                return []

            # Process videos
            for entry in channel_info.get("entries", []):
                try:
                    if not entry:
                        continue

                    # Get detailed video information
                    video_info = ydl.extract_info(
                        f"https://www.youtube.com/watch?v={entry['id']}", download=False
                    )

                    if not video_info:
                        continue

                    # Convert timestamp to ISO format
                    published_at = (
                        datetime.fromtimestamp(
                            video_info.get("timestamp", 0)
                        ).isoformat()
                        + "Z"
                    )

                    # Skip if video is older than published_after or newer than published_before
                    if published_at < published_after:
                        break

                    video_data = {
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
                                (
                                    t["url"]
                                    for t in reversed(video_info.get("thumbnails", []))
                                    if "url" in t
                                ),
                                "",
                            ),
                        ),
                        "metadata": {
                            "api_source": "yt_dlp",
                            "processed_at": datetime.now().isoformat(),
                        },
                    }
                    videos.append(video_data)
                    logger.debug(f"Video procesado: {video_data['title']}")

                except Exception as e:
                    logger.error(
                        f"Error processing video {entry.get('id', 'unknown')}: {e!s}"
                    )
                    continue

        return videos

    except Exception as e:
        logger.error(f"Error al obtener videos para {channel_handle}: {e!s}")
        return []


def process_youtube_channels(
    channel_handles: list[str], published_after: str = None
) -> list[dict]:
    """Process multiple YouTube channels concurrently and combine their videos."""
    all_videos = []
    # Determine a reasonable number of workers, e.g., based on CPU cores or a fixed number
    # Let's start with a sensible default, adjust as needed based on performance
    max_workers = min(10, os.cpu_count() + 4)  # Example: Use up to 10 workers

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for each channel processing task
        future_to_channel = {
            executor.submit(get_channel_videos_by_id, handle, published_after): handle
            for handle in channel_handles
        }

        for future in concurrent.futures.as_completed(future_to_channel):
            handle = future_to_channel[future]
            try:
                channel_videos = future.result()
                if channel_videos:
                    all_videos.extend(channel_videos)
                    logger.info(
                        f"Processed successfully {len(channel_videos)} videos from {handle}"
                    )
                else:
                    logger.info(f"No new videos found for {handle}")
            except Exception as e:
                logger.error(f"Error processing channel {handle}: {e!s}")
                continue  # Continue with other channels even if one fails

    logger.info(
        f"Finished processing all channels. Total videos collected: {len(all_videos)}"
    )
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
        logger.warning(
            f"No se recuperaron videos para el tema {topic}, el proceso ETL no puede continuar"
        )
        return

    # Order by published_at descending (newest first)
    processed_videos = sorted(
        processed_videos, key=lambda x: x["published_at"], reverse=True
    )

    # Save to JSON file
    json_file = os.path.join(output_dir, "youtube_videos.json")
    with open(json_file, "w") as f:
        json.dump(processed_videos, f, indent=2)
    logger.debug(f"Datos JSON guardados en {json_file}")

    # Also save as CSV for easier viewing (drop description to avoid CSV formatting issues)
    csv_file = os.path.join(output_dir, "youtube_videos.csv")
    pd.DataFrame(processed_videos).drop(columns=["description"]).to_csv(
        csv_file, index=False
    )
    logger.debug(f"Datos CSV guardados en {csv_file}")

    logger.info(
        f"Guardados {len(processed_videos)} videos del tema {topic} en {json_file} y {csv_file}"
    )


def main(topics: list[str] = None):
    """Main function to fetch and process YouTube channel videos by topic."""
    logger.info("Iniciando proceso ETL de canales de YouTube")

    try:
        # Ensure base output directory exists
        ensure_directories([BASE_OUTPUT_DIR])

        # Define date range for videos
        published_after = (
            datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)
        ).isoformat()

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
