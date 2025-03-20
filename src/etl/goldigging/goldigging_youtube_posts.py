import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

import yt_dlp
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


def get_channel_videos_by_id(channel_handle: str, published_after: str = (datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)).isoformat()) -> List[Dict]:
    """Fetch videos from a channel using yt-dlp."""
    try:
        ydl_opts = {
            'extract_flat': True,  # Do not download videos
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'playlist_items': f'1-{MAX_VIDEOS_PER_CHANNEL}'  # Limit number of videos to fetch
        }
        
        videos = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get channel URL - try both @ handle and direct channel URL formats
            channel_urls = [
                f"https://www.youtube.com/@{channel_handle}/videos",
                f"https://www.youtube.com/c/{channel_handle}/videos",
                f"https://www.youtube.com/channel/{channel_handle}/videos"
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
            for entry in channel_info.get('entries', []):
                try:
                    if not entry:
                        continue
                        
                    # Get detailed video information
                    video_info = ydl.extract_info(
                        f"https://www.youtube.com/watch?v={entry['id']}", 
                        download=False
                    )
                    
                    if not video_info:
                        continue
                    
                    # Convert timestamp to ISO format
                    published_at = datetime.fromtimestamp(
                        video_info.get('timestamp', 0)
                    ).isoformat() + "Z"
                    
                    # Skip if video is older than published_after or newer than published_before
                    if published_at < published_after:
                        break
                        
                    video_data = {
                        "title": video_info.get('title', ''),
                        "url": video_info.get('webpage_url', ''),
                        "channel": video_info.get('channel', ''),
                        "published_at": published_at,
                        "description": video_info.get('description', ''),
                        "views": video_info.get('view_count', 0),
                        "length": video_info.get('duration', 0),
                        "metadata": {
                            "api_source": "yt_dlp",
                            "processed_at": datetime.now().isoformat(),
                        },
                    }
                    videos.append(video_data)
                    logger.debug(f"Video procesado: {video_data['title']}")
                    
                except Exception as e:
                    logger.error(f"Error processing video {entry.get('id', 'unknown')}: {str(e)}")
                    continue
                    
        return videos

    except Exception as e:
        logger.error(f"Error al obtener videos para {channel_handle}: {str(e)}")
        return []


def process_youtube_channels(channel_handles: List[str], published_after: str = None) -> List[Dict]:
    """Process multiple YouTube channels and combine their videos."""
    all_videos = []

    for handle in channel_handles:
        try:
            logger.info(f"Procesando canal {handle}")
            channel_videos = get_channel_videos_by_id(handle, published_after)
            all_videos.extend(channel_videos)
            logger.info(
                f"Procesados con éxito {len(channel_videos)} videos de {handle}"
            )
        except Exception as e:
            logger.error(f"Error al procesar el canal {handle}: {str(e)}")
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

            # Data Science / Data Engineering / Databricks
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

        # Define date range for videos
        published_after = (datetime.now() - timedelta(days=DEFAULT_DAYS_LOOKBACK)).isoformat()
        published_before = datetime.now().isoformat()

        processed_videos = process_youtube_channels(channels, published_after)

        if not processed_videos:
            logger.warning("No se recuperaron videos, el proceso ETL no puede continuar")
            return

        # Order by published_at descending (newest first)
        processed_videos = sorted(
            processed_videos, key=lambda x: x["published_at"], reverse=True
        )

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
