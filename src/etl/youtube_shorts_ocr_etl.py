import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

import yt_dlp
from moviepy.editor import VideoFileClip
from PIL import Image
import pytesseract

# Add project root to Python path
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    if project_root not in sys.path:
        sys.path.append(project_root)
except NameError: # Fallback for environments where __file__ is not defined
    project_root = os.path.abspath(".")
    if project_root not in sys.path:
        sys.path.append(project_root)


from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("youtube_shorts_ocr_etl")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration
TARGET_CHANNEL_URL = "https://youtube.com/@setupsaitony/shorts"
OUTPUT_DIR = os.path.join(get_project_root(), "data", "youtube_shorts_ocr")
TEMP_VIDEO_DIR = os.path.join(OUTPUT_DIR, "temp_videos")
MAX_SHORTS_TO_PROCESS = 10  # Limiting for development/testing
DEFAULT_DAYS_LOOKBACK = 90 # Process shorts from the last 90 days

def get_short_video_urls(channel_url: str, limit: int, lookback_days: int) -> List[Dict[str, str]]:
    """
    Fetches URLs and titles of short videos from a given YouTube channel URL.
    Only fetches videos published within the lookback period.
    """
    logger.info(f"Fetching short video information from {channel_url}...")
    ydl_opts = {
        "extract_flat": "discard_in_playlist", # Get individual video info
        "playlistend": limit, # Max videos to retrieve metadata for
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "dateafter": (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d'),
    }

    videos_info = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            if result and "entries" in result:
                for entry in result["entries"]:
                    if entry: # Ensure entry is not None
                        video_id = entry.get("id")
                        title = entry.get("title", "N/A")
                        if video_id:
                            videos_info.append({
                                "url": f"https://www.youtube.com/shorts/{video_id}",
                                "title": title,
                                "id": video_id
                            })
                        else:
                            logger.warning(f"Could not get video ID for an entry in {channel_url}")
            else:
                logger.warning(f"No entries found for channel {channel_url}. Result: {result}")


    except Exception as e:
        logger.error(f"Error fetching video URLs from {channel_url}: {e}")

    logger.info(f"Found {len(videos_info)} shorts from the last {lookback_days} days (up to limit of {limit}).")
    return videos_info


def extract_text_from_video_frames(video_path: str, frame_interval_seconds: int = 1) -> str:
    """
    Extracts text from video frames using OCR.
    A frame is processed every `frame_interval_seconds`.
    """
    logger.info(f"Starting OCR for video: {video_path}")
    extracted_texts = set() # Use a set to store unique text snippets

    try:
        video_clip = VideoFileClip(video_path)
        duration = video_clip.duration

        if duration is None:
            logger.warning(f"Could not get duration for video {video_path}. Skipping OCR.")
            return ""

        for i in range(0, int(duration), frame_interval_seconds):
            try:
                frame = video_clip.get_frame(i) # Get frame at time 'i' seconds
                pil_image = Image.fromarray(frame)

                # Perform OCR
                # Adding config for better results with potentially sparse text or varied languages
                # '--psm 6' assumes a single uniform block of text.
                # Try to specify language if known, otherwise, Tesseract will attempt to detect.
                # For general use, 'eng' is a common default.
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(pil_image, config=custom_config)

                cleaned_text = text.strip()
                if cleaned_text: # Add text only if it's not empty
                    extracted_texts.add(cleaned_text)
            except Exception as e:
                logger.error(f"Error processing frame at {i}s for {video_path}: {e}")
                continue # Continue to next frame

        video_clip.close() # Release resources

    except Exception as e:
        logger.error(f"Error opening or processing video file {video_path} with MoviePy: {e}")
        return "" # Return empty string if video processing fails

    if not extracted_texts:
        logger.info(f"No text extracted from OCR for video: {video_path}")
        return ""

    full_description = " ".join(sorted(list(extracted_texts))) # Sort for consistent ordering
    logger.info(f"OCR completed for {video_path}. Extracted text length: {len(full_description)}")
    return full_description


def download_video(video_id: str, output_path: str) -> str | None:
    """
    Downloads a single YouTube video using its ID to the specified output path.
    Returns the path to the downloaded video file or None if download fails.
    """
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    logger.info(f"Attempting to download video: {video_url}")

    # Ensure the specific video's directory exists (e.g., TEMP_VIDEO_DIR/video_id/video.mp4)
    # This helps keep downloads organized if multiple files are associated with one video later.
    # For shorts, it's usually one file.
    video_specific_dir = os.path.join(output_path, video_id)
    ensure_directories([video_specific_dir])

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", # Standard MP4 format
        "outtmpl": os.path.join(video_specific_dir, '%(id)s.%(ext)s'), # Save as video_id.mp4
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "nocheckcertificate": True, # Add this to bypass SSL certificate verification if needed
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Assuming download is successful, construct the expected file path
        # yt-dlp might save with a different extension if mp4 isn't available,
        # but we requested mp4. For simplicity, we'll assume video_id.mp4.
        # A more robust solution would be to capture the exact filename from yt-dlp's output or hooks.
        downloaded_file_path = os.path.join(video_specific_dir, f"{video_id}.mp4")
        if os.path.exists(downloaded_file_path):
            logger.info(f"Successfully downloaded video to {downloaded_file_path}")
            return downloaded_file_path
        else:
            # Check for other possible extensions if mp4 wasn't strictly enforced or available
            for ext_attempt in ['mkv', 'webm', 'flv', 'avi']: # Common video extensions
                alt_path = os.path.join(video_specific_dir, f"{video_id}.{ext_attempt}")
                if os.path.exists(alt_path):
                    logger.info(f"Successfully downloaded video to {alt_path} (as .{ext_attempt})")
                    return alt_path
            logger.error(f"Download reported success, but file not found at expected path for {video_id}")
            return None

    except Exception as e:
        logger.error(f"Error downloading video {video_id}: {e}")
        return None


def main(args):
    """Main function to orchestrate the ETL process."""
    logger.info("Starting YouTube Shorts OCR ETL process...")
    ensure_directories([OUTPUT_DIR, TEMP_VIDEO_DIR])

    logger.info(f"Targeting channel: {TARGET_CHANNEL_URL}")
    logger.info(f"Max shorts to process: {args.limit}")
    logger.info(f"Lookback period: {args.days} days")

    short_videos_meta = get_short_video_urls(TARGET_CHANNEL_URL, args.limit, args.days)

    if not short_videos_meta:
        logger.info("No short videos found matching the criteria. Exiting.")
        return

    all_results = []

    # Placeholder for OCR processing steps (will be implemented in subsequent plan steps)
    for video_meta in short_videos_meta:
        logger.info(f"Processing: {video_meta['title']} ({video_meta['url']})")

        video_path = download_video(video_meta["id"], TEMP_VIDEO_DIR)

        if video_path:
            logger.info(f"Video downloaded to: {video_path}")
            ocr_text = extract_text_from_video_frames(video_path, frame_interval_seconds=1)

            all_results.append({
                "url": video_meta["url"],
                "title": video_meta["title"],
                "ocr_description": ocr_text if ocr_text else "OCR processing failed or no text found."
                # "downloaded_video_path": video_path # Removed from final output
            })

            # Clean up the downloaded video file immediately after processing
            try:
                # The video is inside a folder named by its ID. Delete the whole folder.
                video_folder_path = os.path.dirname(video_path)
                if os.path.commonpath([TEMP_VIDEO_DIR, video_folder_path]) == TEMP_VIDEO_DIR: # Safety check
                    shutil.rmtree(video_folder_path)
                    logger.info(f"Cleaned up temporary video folder: {video_folder_path}")
                else:
                    logger.warning(f"Skipping cleanup for {video_folder_path} as it's outside TEMP_VIDEO_DIR")
            except Exception as e:
                logger.error(f"Error cleaning up video folder {video_folder_path}: {e}")

        else:
            logger.warning(f"Skipping OCR for {video_meta['title']} as download failed.")
            all_results.append({
                "url": video_meta["url"],
                "title": video_meta["title"],
                "ocr_description": "Download Failed",
                "downloaded_video_path": None
            })

    # Step 4: Store results (will be refined)
    output_file_path = os.path.join(OUTPUT_DIR, "youtube_shorts_ocr_results.json")
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved results to {output_file_path}")
    except IOError as e:
        logger.error(f"Error saving results to {output_file_path}: {e}")

    # Clean up temporary video directory if it's empty
    try:
        if os.path.exists(TEMP_VIDEO_DIR) and not os.listdir(TEMP_VIDEO_DIR):
            shutil.rmtree(TEMP_VIDEO_DIR)
            logger.info(f"Successfully removed empty temporary directory: {TEMP_VIDEO_DIR}")
        elif os.path.exists(TEMP_VIDEO_DIR):
            logger.warning(f"Temporary directory {TEMP_VIDEO_DIR} is not empty. Manual cleanup might be needed.")
    except Exception as e:
        logger.error(f"Error removing temporary directory {TEMP_VIDEO_DIR}: {e}")

    logger.info("YouTube Shorts OCR ETL process completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Shorts OCR ETL")
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_SHORTS_TO_PROCESS,
        help=f"Maximum number of shorts to process (default: {MAX_SHORTS_TO_PROCESS})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS_LOOKBACK,
        help=f"Number of past days to look for shorts (default: {DEFAULT_DAYS_LOOKBACK})",
    )
    args = parser.parse_args()

    main(args)
