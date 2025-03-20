import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

import googleapiclient.discovery
import isodate
import pandas as pd

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

from src.utils.file_system import ensure_directories

# Set up logging
logger = logging.getLogger("goldigging_youtube_posts")
logging.basicConfig(level=logging.INFO)

OUTPUT_DIR = "data/youtube"
MAX_VIDEOS_PER_CHANNEL = 50
DEFAULT_DAYS_LOOKBACK = 14


def get_youtube_client():
    """Initialize and return a YouTube API client."""
    api_service_name = "youtube"
    api_version = "v3"
    api_key = os.environ.get("YOUTUBE_API_KEY")

    if not api_key:
        logger.error("Clave API de YouTube no encontrada en variables de entorno")
        raise ValueError("La variable de entorno YOUTUBE_API_KEY es requerida")

    return googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=api_key
    )


def get_channel_id(youtube, channel_id_or_handle: str) -> str:
    """Convert a channel handle to a channel ID if needed."""
    if channel_id_or_handle.startswith("UC") or channel_id_or_handle.startswith("HC"):
        return channel_id_or_handle

    # If it's a handle, we need to find the channel ID
    handle = channel_id_or_handle.replace("@", "")

    try:
        # Try to find channel by handle
        request = youtube.search().list(
            part="snippet", q=f"@{handle}", type="channel", maxResults=1
        )
        response = request.execute()

        if response.get("items"):
            return response["items"][0]["snippet"]["channelId"]
        else:
            logger.error(f"No se pudo encontrar ID del canal para el handle: {channel_id_or_handle}")
            return None
    except Exception as e:
        logger.error(f"Error al buscar ID del canal para {channel_id_or_handle}: {str(e)}")
        return None


def get_channel_videos_by_id(
    youtube, channel_id_or_handle: str, published_after: str = None
) -> List[Dict]:
    """Fetch videos by a channel ID or handle using YouTube Data API."""
    try:
        channel_id = get_channel_id(youtube, channel_id_or_handle)
        if not channel_id:
            return []

        # Set cutoff date for videos
        if published_after is None:
            published_after = (datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)).isoformat()

        # Get channel uploads playlist ID
        request = youtube.channels().list(part="contentDetails", id=channel_id)
        response = request.execute()

        if not response.get("items"):
            logger.error(f"No se encontró canal para el ID: {channel_id}")
            return []

        uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Get videos from uploads playlist
        videos = []
        next_page_token = None
        remaining_results = MAX_VIDEOS_PER_CHANNEL
        video_ids_batch = []

        while True:
            playlist_request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=min(50, remaining_results),  # API allows max 50 per request
                pageToken=next_page_token,
            )
            playlist_response = playlist_request.execute()

            # Collect video IDs for batch processing
            for item in playlist_response["items"]:
                published_at = item["snippet"]["publishedAt"]
                if published_at >= published_after:
                    video_ids_batch.append(item["contentDetails"]["videoId"])

            next_page_token = playlist_response.get("nextPageToken")
            remaining_results -= len(playlist_response["items"])

            if not next_page_token or remaining_results <= 0:
                break

        # Process video IDs in batches of 50 (API limit)
        for i in range(0, len(video_ids_batch), 50):
            batch = video_ids_batch[i:i+50]
            if not batch:
                continue
                
            video_request = youtube.videos().list(
                part="snippet,contentDetails,statistics", id=",".join(batch)
            )
            video_response = video_request.execute()

            for video in video_response.get("items", []):
                duration = isodate.parse_duration(
                    video["contentDetails"]["duration"]
                ).total_seconds()

                video_info = {
                    "title": video["snippet"]["title"],
                    "url": f"https://www.youtube.com/watch?v={video['id']}",
                    "channel": video["snippet"]["channelTitle"],
                    "published_at": video["snippet"]["publishedAt"],
                    "description": video["snippet"]["description"],
                    "views": int(video["statistics"].get("viewCount", 0)),
                    "length": duration,
                    "metadata": {
                        "api_source": "youtube_data_api",
                        "processed_at": datetime.now().isoformat(),
                    },
                }
                videos.append(video_info)
                logger.debug(f"Video procesado: {video_info['title']}")

        return videos

    except Exception as e:
        logger.error(f"Error al obtener videos para {channel_id_or_handle}: {str(e)}")
        return []


def process_youtube_channels(channel_ids_or_handles: List[str]) -> List[Dict]:
    """Process multiple YouTube channels and combine their videos."""
    all_videos = []
    youtube = get_youtube_client()

    for channel_id_or_handle in channel_ids_or_handles:
        try:
            channel_videos = get_channel_videos_by_id(youtube, channel_id_or_handle)
            all_videos.extend(channel_videos)
            logger.info(
                f"Procesados con éxito {len(channel_videos)} videos de {channel_id_or_handle}"
            )
        except Exception as e:
            logger.error(f"Error al procesar el canal {channel_id_or_handle}: {str(e)}")
            continue

    return all_videos


def main():
    """Main function to fetch and process YouTube channel videos."""
    logger.info("Iniciando proceso ETL de canales de YouTube")

    try:
        # Ensure output directory exists
        ensure_directories([OUTPUT_DIR])

        # List of channels to process
        channels = [
            # Popular Programming Tutorials
            "Fireship",
            "TechWithTim",
            "TraversyMedia",
            "CoreySchafer",
            "freecodecamp",
            "ArjanCodes",
            "t3dotgg",
            "ishaqhamin",
            "james-willett",
            # AI/ML Focus
            "AICodeKing",
            "Sentdex",
            "TwoMinutePapers",
            "YannicKilcher",
            "CodeEmporium",

            # GenAI Focus

            "mreflow",
            "DaveShap",
            "Deeplearningai",
            "Augmented_AI",

            
            # Software Architecture/Design
            "CodeOpinion",
            "markrichards5014",
            "CodingTech",
            
            # Advanced Programming
            "EmilyBache-tech-coach",
            "CodeAesthetic",
            "NoBoilerplate",
            
            # Spanish Programming Content
            "mouredev",
            "FaztCode",
            "midudev",
            "midulive",
            "PeladoNerd",

            # Spanish dissertions
            "jfcalero",
            "jfcaleroMANUAL",
            "VisualEconomik",
            "VisualPolitik",

            # English economics, politics and enterprises
            "PolyMatter",
            "slow_start",
            "companyman114",            

            # Data Science / aData Engineering / Databricks
            "SeattleDataGuy",
            "nataindata",
            "DataWithBaraa",
            "DecisionForest",

            # Cloud Architecture / Solution Architecture / Enterprise Architecture / DevOps
            "ByteByteGo",
            "TechLead",
            "techwithsoleyman",
            #"amazonwebservices", # This channel sends a lot of videos, we need to filter them...

        ]

        processed_videos = process_youtube_channels(channels)

        if not processed_videos:
            logger.warning("No se recuperaron videos, el proceso ETL no puede continuar")
            return

        # Order by published_at descending (newest first)
        processed_videos = sorted(
            processed_videos, key=lambda x: x["published_at"], reverse=True
        )

        # Filter out videos that are older than the lookback period
        cutoff_date = (datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)).isoformat()
        processed_videos = [
            video for video in processed_videos if video["published_at"] > cutoff_date
        ]

        # Save to JSON file
        json_file = f"{OUTPUT_DIR}/youtube_videos.json"
        with open(json_file, "w") as f:
            json.dump(processed_videos, f, indent=2)
        logger.debug(f"Datos JSON guardados en {json_file}")

        # Also save as CSV for easier viewing (drop description to avoid CSV formatting issues)
        csv_file = f"{OUTPUT_DIR}/youtube_videos.csv"
        pd.DataFrame(processed_videos).drop(columns=["description"]).to_csv(
            csv_file, index=False
        )
        logger.debug(f"Datos CSV guardados en {csv_file}")

        logger.info(
            f"Guardados {len(processed_videos)} videos procesados en {json_file} y {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error en el proceso ETL de YouTube: {str(e)}", exc_info=True)


if __name__ == "__main__":
    logger.info("Script ETL de YouTube iniciado")
    main()
    logger.info("Script ETL de YouTube completado")
