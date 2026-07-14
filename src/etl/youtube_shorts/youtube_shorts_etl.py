"""Refactored YouTube Shorts OCR ETL with clean architecture.

This ETL extracts text and URLs from YouTube Shorts using OCR technology.
Following SOLID principles with service layer architecture.
"""

import argparse
import json
import shutil
import time
from typing import Any

from src.utils.logging_utils import get_project_root, setup_logger

from .config import DEFAULT_CONFIG, YouTubeOCRConfig
from .domain.models import VideoProcessingResult
from .services import CheckpointService, OCRService, VideoService

# Setup logging
logger = setup_logger("youtube_shorts_ocr")


class YouTubeShortsETL:
    """Main ETL orchestrator for YouTube Shorts OCR processing."""

    def __init__(self, config: YouTubeOCRConfig):
        """Initialize ETL with configuration.

        Args:
            config: ETL configuration
        """
        self.config = config

        # Ensure directories exist
        self.config.paths.ensure_directories()

        # Initialize services
        self.ocr_service = OCRService(
            settings=self.config.ocr,
            debug=self.config.debug,
        )
        self.video_service = VideoService(
            settings=self.config.video,
            ocr_service=self.ocr_service,
            debug=self.config.debug,
        )
        self.checkpoint_service = CheckpointService(
            checkpoint_file=self.config.paths.checkpoint_file,
            debug=self.config.debug,
        )

        # Verify Tesseract installation
        if not self.ocr_service.verify_tesseract_installation():
            raise RuntimeError("Tesseract OCR is not properly configured. Exiting.")

    def run(
        self,
        limit: int | None = None,
        lookback_days: int | None = None,
        request_delay: float | None = None,
    ) -> list[VideoProcessingResult]:
        """Run the complete ETL pipeline.

        Args:
            limit: Maximum number of shorts to process
            lookback_days: Number of days to look back
            request_delay: Delay between requests in seconds

        Returns:
            List of processing results
        """
        # Use config defaults if not specified
        limit = limit or self.config.video.max_shorts_to_process
        lookback_days = lookback_days or self.config.video.default_lookback_days
        request_delay = request_delay or self.config.video.request_delay

        logger.info("Starting Enhanced YouTube Shorts OCR ETL process...")
        logger.info(f"Project root: {get_project_root()}")
        logger.info(f"Target channel: {self.config.target_channel_url}")
        logger.info(f"Max shorts: {limit}")
        logger.info(f"Lookback: {lookback_days} days")

        # Load checkpoint
        checkpoint = self.checkpoint_service.load()
        processed_ids = set(checkpoint.get("processed_videos", []))
        failed_ids = set(checkpoint.get("failed_videos", []))

        # Fetch video metadata
        try:
            videos_meta = self.video_service.fetch_video_metadata(
                channel_url=self.config.target_channel_url,
                limit=limit,
                lookback_days=lookback_days,
                processed_ids=processed_ids,
                failed_ids=failed_ids,
            )
        except Exception as e:
            logger.error(f"Failed to fetch video URLs after retries: {e}")
            return []

        if not videos_meta:
            logger.info("No new short videos found matching the criteria. Exiting.")
            return []

        logger.info(f"[START] Processing {len(videos_meta)} videos...")

        # Process videos
        all_results = []
        successful_count = 0
        failed_count = 0
        urls_found = 0

        processing_start_time = time.time()

        for i, video_meta in enumerate(videos_meta, 1):
            video_start_time = time.time()

            logger.info(f"[PROGRESS] Processing video {i}/{len(videos_meta)} ({(i / len(videos_meta) * 100):.1f}%)")
            logger.info(f"[CURRENT] {video_meta.title}")

            result = self._process_single_video(video_meta, checkpoint)
            all_results.append(result)

            # Update statistics
            if result.processing_status == "success":
                successful_count += 1
                urls_found += len(result.all_detected_urls)
            else:
                failed_count += 1

            # Calculate timing estimates
            video_duration = time.time() - video_start_time
            if i > 1:
                avg_time = (time.time() - processing_start_time) / i
                remaining = len(videos_meta) - i
                estimated_time = remaining * avg_time
                logger.info(f"[TIMING] Video: {video_duration:.1f}s. Est. remaining: {estimated_time / 60:.1f}min")

            logger.info(f"[PROGRESS] Progress: {successful_count} successful, {failed_count} failed, {urls_found} URLs found")

            # Save checkpoint after each video
            self.checkpoint_service.save(checkpoint)

            # Add delay between videos
            if i < len(videos_meta):
                logger.info(f"[WAIT] Waiting {request_delay}s before next video...")
                time.sleep(request_delay)

        # Final summary
        total_time = time.time() - processing_start_time
        logger.info(f"[COMPLETE] Processing complete! Success: {successful_count}, Failed: {failed_count}, URLs: {urls_found}")
        logger.info(f"[TIMING] Total: {total_time / 60:.1f}min ({total_time / len(videos_meta):.1f}s per video)")

        # Save results
        self._save_results(all_results)

        # Cleanup
        self._cleanup_temp_directory()

        return all_results

    def _process_single_video(self, video_meta, checkpoint: dict[str, Any]) -> VideoProcessingResult:
        """Process a single video: download, OCR, cleanup.

        Args:
            video_meta: Video metadata
            checkpoint: Checkpoint data

        Returns:
            Processing result
        """
        result = VideoProcessingResult.from_video_metadata(video_meta)

        try:
            logger.info(f"[INFO] Processing video {video_meta.video_id}: {video_meta.title}")

            # Download video
            video_path = self.video_service.download_video(
                video_meta.video_id,
                self.config.paths.temp_video_dir,
            )

            if video_path:
                # Add delay before OCR processing
                delay = self.config.video.processing_delay
                logger.info(f"[WAIT] Waiting {delay}s before OCR processing...")
                time.sleep(delay)

                # Extract text and URLs
                logger.info("[INFO] Starting OCR analysis of video frames...")
                ocr_result = self.video_service.process_video_frames(video_path)

                result.ocr_description = ocr_result.text if ocr_result.text else "No high-quality text found in video"
                result.extracted_urls = ocr_result.urls
                result.all_detected_urls = [url.get("cleaned_url", url.get("url", "")) for url in ocr_result.urls]
                result.metadata = ocr_result.metadata
                result.processing_status = "success"

                # Log success
                if result.all_detected_urls:
                    logger.info(f"[OK] Successfully processed {video_meta.video_id} - Found {len(result.all_detected_urls)} URLs")
                else:
                    logger.info(f"[OK] Successfully processed {video_meta.video_id} - No URLs detected")

                # Clean up immediately
                self.video_service.cleanup_video(video_path, self.config.paths.temp_video_dir)

                # Update checkpoint
                self.checkpoint_service.mark_processed(checkpoint, video_meta.video_id)

            else:
                logger.warning(f"[ERROR] Skipping OCR for {video_meta.video_id} as download failed")
                result.ocr_description = "Download failed"
                result.error_message = "Download failed"
                self.checkpoint_service.mark_failed(checkpoint, video_meta.video_id)

        except Exception as e:
            logger.error(f"[ERROR] Error processing video {video_meta.video_id}: {e}")
            result.ocr_description = f"Processing error: {e}"
            result.error_message = str(e)
            self.checkpoint_service.mark_failed(checkpoint, video_meta.video_id)

        return result

    def _save_results(self, results: list[VideoProcessingResult]) -> None:
        """Save processing results to JSON file.

        Args:
            results: List of processing results
        """
        output_file = self.config.paths.output_dir / "youtube_shorts_ocr_results.json"

        try:
            # Load existing results if they exist
            existing_results = []
            if output_file.exists():
                try:
                    with open(output_file, encoding="utf-8") as f:
                        existing_results = json.load(f)
                except (OSError, json.JSONDecodeError):
                    pass

            # Combine with new results
            all_results = [r.to_dict() for r in results] + existing_results

            # Remove duplicates based on URL
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result["url"] not in seen_urls:
                    unique_results.append(result)
                    seen_urls.add(result["url"])

            # Save to file
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(unique_results, f, indent=4, ensure_ascii=False)

            logger.info(f"Successfully saved {len(unique_results)} results to {output_file}")

        except OSError as e:
            logger.error(f"Error saving results to {output_file}: {e}")

    def _cleanup_temp_directory(self) -> None:
        """Clean up empty temporary directory."""
        try:
            temp_dir = self.config.paths.temp_video_dir
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                shutil.rmtree(temp_dir)
                logger.info(f"Successfully removed empty temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error removing temporary directory {self.config.paths.temp_video_dir}: {e}")


def main():
    """Main entry point for CLI execution."""
    parser = argparse.ArgumentParser(description="Enhanced YouTube Shorts OCR ETL with clean architecture")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONFIG.video.max_shorts_to_process,
        help=f"Maximum number of shorts to process (default: {DEFAULT_CONFIG.video.max_shorts_to_process})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_CONFIG.video.default_lookback_days,
        help=f"Number of past days to look for shorts (default: {DEFAULT_CONFIG.video.default_lookback_days})",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=DEFAULT_CONFIG.video.request_delay,
        help=f"Delay between requests in seconds (default: {DEFAULT_CONFIG.video.request_delay})",
    )
    parser.add_argument(
        "--channel",
        type=str,
        default=DEFAULT_CONFIG.target_channel_url,
        help="YouTube channel URL to process",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Create configuration
    config = YouTubeOCRConfig(
        target_channel_url=args.channel,
        debug=args.debug,
    )

    # Run ETL
    etl = YouTubeShortsETL(config)
    results = etl.run(
        limit=args.limit,
        lookback_days=args.days,
        request_delay=args.request_delay,
    )

    # Log summary
    if results:
        successful = len([r for r in results if r.processing_status == "success"])
        failed = len(results) - successful
        total_urls = sum(len(r.all_detected_urls) for r in results)
        videos_with_urls = len([r for r in results if r.all_detected_urls])

        logger.info(f"ETL process completed. Success: {successful}, Failed: {failed}")
        logger.info(f"URL Extraction Summary: {total_urls} URLs found across {videos_with_urls} videos")

        # Show extracted URLs
        if total_urls > 0:
            logger.info("[RESULTS] EXTRACTED URLS:")
            for i, result in enumerate(results, 1):
                if result.all_detected_urls:
                    print(f"\n[VIDEO] Video {i}: {result.title}")
                    for url_data in result.extracted_urls:
                        print(f"   [URL] {url_data.get('cleaned_url', url_data.get('url', 'Unknown'))}")
                        print(f"      Confidence: {url_data.get('confidence', 0):.1f}% | Time: {url_data.get('timestamp', 0):.1f}s")
                        context = url_data.get("context_text", "")
                        if context:
                            print(f"      Context: {context[:100]}...")
                    print()
            print("=" * 60)


if __name__ == "__main__":
    main()
