"""Checkpoint service for resumable video processing."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CheckpointService:
    """Service for managing processing checkpoints."""

    def __init__(self, checkpoint_file: Path, debug: bool = False):
        """Initialize checkpoint service.

        Args:
            checkpoint_file: Path to checkpoint file
            debug: Enable debug logging
        """
        self.checkpoint_file = checkpoint_file
        self.debug = debug

    def load(self) -> dict[str, Any]:
        """Load processing checkpoint to resume from previous state.

        Returns:
            Checkpoint data dictionary
        """
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, encoding="utf-8") as f:
                    checkpoint = json.load(f)
                    processed_count = len(checkpoint.get("processed_videos", []))
                    failed_count = len(checkpoint.get("failed_videos", []))
                    logger.info(f"Loaded checkpoint with {processed_count} processed videos, {failed_count} failed videos")
                    return checkpoint
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Error loading checkpoint: {e}. Starting fresh.")

        # Return default checkpoint structure
        return {
            "processed_videos": [],
            "failed_videos": [],
            "last_processed_date": None,
        }

    def save(self, checkpoint: dict[str, Any]) -> None:
        """Save current processing state to checkpoint file.

        Args:
            checkpoint: Checkpoint data to save
        """
        try:
            # Ensure parent directory exists
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            logger.debug("Checkpoint saved successfully")
        except OSError as e:
            logger.error(f"Error saving checkpoint: {e}")

    def mark_processed(self, checkpoint: dict[str, Any], video_id: str) -> None:
        """Mark a video as successfully processed.

        Args:
            checkpoint: Checkpoint data
            video_id: Video ID to mark as processed
        """
        if "processed_videos" not in checkpoint:
            checkpoint["processed_videos"] = []

        if video_id not in checkpoint["processed_videos"]:
            checkpoint["processed_videos"].append(video_id)

        # Remove from failed if present
        if "failed_videos" in checkpoint and video_id in checkpoint["failed_videos"]:
            checkpoint["failed_videos"].remove(video_id)

        # Update timestamp
        checkpoint["last_processed_date"] = datetime.now().isoformat()

    def mark_failed(self, checkpoint: dict[str, Any], video_id: str) -> None:
        """Mark a video as failed.

        Args:
            checkpoint: Checkpoint data
            video_id: Video ID to mark as failed
        """
        if "failed_videos" not in checkpoint:
            checkpoint["failed_videos"] = []

        if video_id not in checkpoint["failed_videos"]:
            checkpoint["failed_videos"].append(video_id)

    def is_processed(self, checkpoint: dict[str, Any], video_id: str) -> bool:
        """Check if a video has been processed.

        Args:
            checkpoint: Checkpoint data
            video_id: Video ID to check

        Returns:
            True if video has been processed, False otherwise
        """
        return video_id in checkpoint.get("processed_videos", [])

    def is_failed(self, checkpoint: dict[str, Any], video_id: str) -> bool:
        """Check if a video has failed.

        Args:
            checkpoint: Checkpoint data
            video_id: Video ID to check

        Returns:
            True if video has failed, False otherwise
        """
        return video_id in checkpoint.get("failed_videos", [])

    def get_processed_count(self, checkpoint: dict[str, Any]) -> int:
        """Get count of processed videos.

        Args:
            checkpoint: Checkpoint data

        Returns:
            Number of processed videos
        """
        return len(checkpoint.get("processed_videos", []))

    def get_failed_count(self, checkpoint: dict[str, Any]) -> int:
        """Get count of failed videos.

        Args:
            checkpoint: Checkpoint data

        Returns:
            Number of failed videos
        """
        return len(checkpoint.get("failed_videos", []))

    def reset(self) -> None:
        """Reset checkpoint by deleting the checkpoint file."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info("Checkpoint file deleted")
        except OSError as e:
            logger.error(f"Error deleting checkpoint file: {e}")
