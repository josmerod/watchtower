"""Video service for downloading and processing YouTube videos."""

import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import yt_dlp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

from ..config import VideoSettings
from ..domain.models import OCRResult, VideoMetadata
from .ocr_service import OCRService

logger = logging.getLogger(__name__)


class VideoService:
    """Service for video downloading, metadata extraction, and frame processing."""

    def __init__(self, settings: VideoSettings, ocr_service: OCRService, debug: bool = False):
        """Initialize video service.

        Args:
            settings: Video configuration settings
            ocr_service: OCR service for text extraction
            debug: Enable debug logging
        """
        self.settings = settings
        self.ocr_service = ocr_service
        self.debug = debug

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def fetch_video_metadata(
        self,
        channel_url: str,
        limit: int,
        lookback_days: int,
        processed_ids: set[str],
        failed_ids: set[str],
    ) -> list[VideoMetadata]:
        """Fetch metadata for short videos from a YouTube channel.

        Args:
            channel_url: YouTube channel URL
            limit: Maximum number of videos to fetch
            lookback_days: Number of days to look back
            processed_ids: Set of already processed video IDs
            failed_ids: Set of previously failed video IDs

        Returns:
            List of video metadata
        """
        logger.info(f"Fetching short video information from {channel_url}...")

        # Apply reasonable limits
        limit = min(limit, self.settings.max_request_limit)
        lookback_days = min(lookback_days, self.settings.max_lookback_days)

        # Add delay before making request
        time.sleep(self.settings.request_delay)

        # Progress tracking
        last_progress_time = time.time()

        def progress_hook(d):
            nonlocal last_progress_time
            current_time = time.time()
            if current_time - last_progress_time > 10:
                logger.info(f"[PROGRESS] yt-dlp is working... (status: {d.get('status', 'unknown')})")
                last_progress_time = current_time

        # Configure yt-dlp options
        ydl_opts = {
            "extract_flat": "discard_in_playlist",
            "playlistend": min(limit * 2, 500),
            "quiet": self.settings.quiet_mode,
            "no_warnings": self.settings.quiet_mode,
            "ignoreerrors": self.settings.ignore_errors,
            "dateafter": (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d"),
            "socket_timeout": self.settings.socket_timeout,
            "fragment_retries": self.settings.fragment_retries,
            "retries": self.settings.download_retries,
            "progress_hooks": [progress_hook],
            "sleep_interval": 1.0,
            "max_sleep_interval": 5,
        }

        videos_info = []

        logger.info(f"[INFO] Checkpoint status: {len(processed_ids)} already processed, {len(failed_ids)} failed")
        logger.info(f"[INFO] Searching for videos from the last {lookback_days} days (limit: {limit})...")

        try:
            logger.info("[INFO] Connecting to YouTube to fetch video metadata...")
            start_time = time.time()

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("[PROGRESS] Starting metadata extraction...")
                result = ydl.extract_info(channel_url, download=False)

            fetch_time = time.time() - start_time
            logger.info(f"[OK] Metadata fetched successfully in {fetch_time:.1f}s")

            if result and "entries" in result:
                total_entries = len(result["entries"])
                logger.info(f"[INFO] Found {total_entries} total videos, filtering for shorts...")

                if total_entries == 0:
                    logger.warning("No videos found in the channel or time range")
                    return []

                processed_count = 0
                skipped_processed = 0
                skipped_failed = 0

                for entry in result["entries"]:
                    if entry and len(videos_info) < limit:
                        video_id = entry.get("id")
                        title = entry.get("title", "N/A")
                        upload_date = entry.get("upload_date", "")

                        processed_count += 1

                        # Log progress
                        progress_interval = 50 if total_entries > 200 else 10
                        if processed_count % progress_interval == 0:
                            logger.info(f"[PROGRESS] Processing video {processed_count}/{total_entries} - Found {len(videos_info)} valid shorts so far...")

                        # Skip already processed or failed videos
                        if video_id in processed_ids:
                            logger.debug(f"Skipping already processed video: {video_id}")
                            skipped_processed += 1
                            continue
                        if video_id in failed_ids:
                            logger.debug(f"Skipping previously failed video: {video_id}")
                            skipped_failed += 1
                            continue

                        if video_id:
                            videos_info.append(
                                VideoMetadata(
                                    url=f"https://www.youtube.com/shorts/{video_id}",
                                    title=title,
                                    video_id=video_id,
                                    upload_date=upload_date,
                                )
                            )
                            logger.debug(f"[OK] Added video {len(videos_info)}/{limit}: {title[:50]}...")

                    elif len(videos_info) >= limit:
                        logger.info(f"[INFO] Reached limit of {limit} videos, stopping search...")
                        break

                logger.info(f"[INFO] Filter summary: {len(videos_info)} new videos, {skipped_processed} already processed, {skipped_failed} previously failed")

            else:
                logger.warning(f"No entries found for channel {channel_url}")

        except Exception as e:
            logger.error(f"Error fetching video URLs from {channel_url}: {e}")
            if "timed out" in str(e).lower():
                logger.info("[HINT] This might be due to a very large request. Try reducing --limit or --days")
            raise

        logger.info(f"[OK] Successfully found {len(videos_info)} new shorts to process")
        return videos_info

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def download_video(self, video_id: str, output_path: Path) -> Path | None:
        """Download a YouTube video to the specified path.

        Args:
            video_id: YouTube video ID
            output_path: Directory to save the video

        Returns:
            Path to downloaded video file, or None if download fails
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Create a directory for this specific video
        video_specific_dir = output_path / video_id
        video_specific_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": self.settings.video_quality + "[ext=mp4]/" + self.settings.video_quality,
            "outtmpl": str(video_specific_dir / "%(id)s.%(ext)s"),
            "quiet": self.settings.quiet_mode,
            "no_warnings": self.settings.quiet_mode,
            "ignoreerrors": self.settings.ignore_errors,
            "nocheckcertificate": True,
            "socket_timeout": 30,
            "retries": self.settings.download_retries,
        }

        try:
            logger.info(f"[INFO] Downloading video {video_id} ({self.settings.video_quality} quality)...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Check for downloaded file with common extensions
            for ext in ["mp4", "mkv", "webm", "flv", "avi"]:
                downloaded_file_path = video_specific_dir / f"{video_id}.{ext}"
                if downloaded_file_path.exists():
                    file_size = downloaded_file_path.stat().st_size / 1024 / 1024  # Size in MB
                    logger.info(f"[OK] Successfully downloaded: {video_id}.{ext} ({file_size:.1f} MB)")
                    return downloaded_file_path

            logger.error(f"Download reported success, but file not found for {video_id}")
            return None

        except Exception as e:
            logger.error(f"Error downloading video {video_id}: {e}")
            raise

    def process_video_frames(self, video_path: Path) -> OCRResult:
        """Extract text and URLs from video frames using OCR.

        Args:
            video_path: Path to video file

        Returns:
            OCR result with text, URLs, and metadata
        """
        logger.info(f"Starting OCR with URL extraction for video: {video_path.name}")

        all_extracted_text = []
        all_urls = []
        capture = None
        previous_frame = None

        try:
            # Load video with OpenCV instead of MoviePy. This keeps the OCR path
            # lightweight and avoids MoviePy's Pillow<12 dependency cap.
            capture = cv2.VideoCapture(str(video_path))
            if not capture.isOpened():
                logger.warning(f"Could not open video {video_path}. Skipping OCR.")
                return OCRResult(text="")

            fps = capture.get(cv2.CAP_PROP_FPS) or 0
            frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            duration = frame_count / fps if fps > 0 else 0

            if duration <= 0:
                logger.warning(f"Could not get duration for video {video_path}. Skipping OCR.")
                return OCRResult(text="")

            # Calculate frame interval based on video duration
            if duration <= 10:
                interval = max(0.5, self.ocr_service.settings.frame_interval_seconds / 2)
            elif duration <= 30:
                interval = self.ocr_service.settings.frame_interval_seconds
            else:
                interval = self.ocr_service.settings.frame_interval_seconds * 2

            # Generate frame timestamps
            frame_times = []
            current_time = 0.0
            while current_time < duration:
                frame_times.append(current_time)
                current_time += interval

            logger.info(f"Processing {len(frame_times)} frames from {duration:.1f}s video")

            processed_frames = 0
            skipped_frames = 0

            for i, frame_time in enumerate(frame_times):
                try:
                    # Log progress for longer videos
                    if len(frame_times) > 10 and (i + 1) % 5 == 0:
                        logger.info(f"[PROGRESS] OCR: {i + 1}/{len(frame_times)} frames ({((i + 1) / len(frame_times) * 100):.1f}%)")

                    # Get frame at specified time (OpenCV returns BGR; OCR expects RGB).
                    capture.set(cv2.CAP_PROP_POS_MSEC, frame_time * 1000)
                    ok, frame_bgr = capture.read()
                    if not ok or frame_bgr is None:
                        logger.warning(f"Invalid frame at {frame_time}s, skipping")
                        continue
                    frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                    # Ensure frame is valid
                    if frame is None or not isinstance(frame, np.ndarray):
                        logger.warning(f"Invalid frame at {frame_time}s, skipping")
                        continue

                    # Skip very similar frames
                    if previous_frame is not None and self.ocr_service.are_frames_similar(frame, previous_frame):
                        skipped_frames += 1
                        continue

                    # Extract text and URLs
                    ocr_result = self.ocr_service.extract_text_from_frame(frame, frame_time, i)

                    # Check confidence threshold
                    if ocr_result["confidence"] >= self.ocr_service.settings.min_confidence and len(ocr_result["text"]) >= self.ocr_service.settings.min_text_length:
                        cleaned_text = self.ocr_service.clean_extracted_text(ocr_result["text"])
                        if cleaned_text:
                            all_extracted_text.append(
                                {
                                    "text": cleaned_text,
                                    "confidence": ocr_result["confidence"],
                                    "timestamp": frame_time,
                                    "method": ocr_result["method"],
                                }
                            )
                            logger.debug(f"OCR @{frame_time:.1f}s (conf: {ocr_result['confidence']:.1f}): {cleaned_text[:100]}...")

                    # Collect URLs
                    if ocr_result["urls"]:
                        all_urls.extend(ocr_result["urls"])
                        logger.info(f"[INFO] Found {len(ocr_result['urls'])} URLs in frame {i + 1} at {frame_time:.1f}s")

                    previous_frame = frame
                    processed_frames += 1

                    # Add small delay between frames
                    time.sleep(0.05)

                except Exception as e:
                    logger.error(f"Error processing frame at {frame_time}s: {e}")
                    continue

            logger.info(f"[OK] OCR complete: processed {processed_frames} frames, skipped {skipped_frames} similar frames")

        except Exception as e:
            logger.error(f"Error opening or processing video file {video_path}: {e}")
            return OCRResult(text="")

        finally:
            # Always close the video capture.
            if capture is not None:
                try:
                    capture.release()
                except Exception as e:
                    logger.warning(f"Error closing video capture: {e}")

        # Process text results
        final_text = ""
        if all_extracted_text:
            # Sort by confidence
            all_extracted_text.sort(key=lambda x: x["confidence"], reverse=True)

            # Create summary with unique text
            unique_texts = []
            seen_texts = set()

            for item in all_extracted_text:
                text_lower = item["text"].lower()
                if text_lower not in seen_texts:
                    unique_texts.append(item["text"])
                    seen_texts.add(text_lower)

            final_text = " | ".join(unique_texts[:10])  # Limit to top 10

        # Process URL results (deduplicate)
        unique_urls = {}
        for url_dict in all_urls:
            key = url_dict.get("cleaned_url", url_dict.get("url", ""))
            if key and (key not in unique_urls or url_dict.get("confidence", 0) > unique_urls[key].get("confidence", 0)):
                unique_urls[key] = url_dict

        final_urls = list(unique_urls.values())

        # Calculate metadata
        metadata = {
            "duration": duration,
            "processed_frames": processed_frames,
            "skipped_frames": skipped_frames,
            "total_frames": len(frame_times),
            "text_results": len(all_extracted_text),
            "url_count": len(final_urls),
        }

        if all_extracted_text:
            avg_confidence = sum(item["confidence"] for item in all_extracted_text) / len(all_extracted_text)
            metadata["avg_confidence"] = avg_confidence
            logger.info(f"Average confidence: {avg_confidence:.1f}%")

        if final_urls:
            logger.info(f"Unique URLs found: {len(final_urls)}")

        logger.info(f"OCR completed for {video_path.name}")
        logger.info(f"Final text length: {len(final_text)}, URLs found: {len(final_urls)}")

        return OCRResult(
            text=final_text,
            urls=final_urls,
            metadata=metadata,
            processed_frames=processed_frames,
            skipped_frames=skipped_frames,
            total_frames=len(frame_times),
        )

    def cleanup_video(self, video_path: Path, temp_dir: Path) -> None:
        """Clean up temporary video files.

        Args:
            video_path: Path to video file
            temp_dir: Temporary directory root
        """
        try:
            video_folder_path = video_path.parent
            if temp_dir in video_folder_path.parents or video_folder_path == temp_dir:
                shutil.rmtree(video_folder_path)
                logger.debug(f"[CLEANUP] Removed temporary video folder: {video_folder_path}")
        except Exception as e:
            logger.error(f"Error cleaning up video folder {video_path.parent}: {e}")
