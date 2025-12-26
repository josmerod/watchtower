"""Domain models for YouTube Shorts OCR processing."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExtractedURL:
    """Represents a URL extracted from OCR text with metadata."""

    url: str
    confidence: float
    timestamp: float
    frame_number: int
    cleaned_url: str = ""
    is_valid: bool = False
    context_text: str = ""
    region: str = "unknown"

    def __post_init__(self):
        """Validate and clean URL after initialization."""
        if not self.cleaned_url:
            self.cleaned_url = self.url

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "cleaned_url": self.cleaned_url,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "frame_number": self.frame_number,
            "is_valid": self.is_valid,
            "context_text": self.context_text,
            "region": self.region,
        }


@dataclass
class VideoMetadata:
    """Metadata about a YouTube video."""

    url: str
    title: str
    video_id: str
    upload_date: str = ""
    duration: float | None = None
    channel: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "id": self.video_id,
            "upload_date": self.upload_date,
            "duration": self.duration,
            "channel": self.channel,
        }


@dataclass
class OCRResult:
    """Result of OCR processing on video frames."""

    text: str
    urls: list[ExtractedURL] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    processed_frames: int = 0
    skipped_frames: int = 0
    total_frames: int = 0
    avg_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "urls": [url.to_dict() for url in self.urls],
            "metadata": self.metadata,
            "processed_frames": self.processed_frames,
            "skipped_frames": self.skipped_frames,
            "total_frames": self.total_frames,
            "avg_confidence": self.avg_confidence,
        }


@dataclass
class VideoProcessingResult:
    """Result of processing a single video."""

    url: str
    title: str
    upload_date: str
    processed_at: str
    processing_status: str  # "success" or "failed"

    # OCR results
    ocr_description: str = ""
    extracted_urls: list[dict[str, Any]] = field(default_factory=list)
    all_detected_urls: list[str] = field(default_factory=list)

    # Processing metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""

    @property
    def video_id(self) -> str:
        """Extract video ID from URL."""
        if "youtube.com/shorts/" in self.url:
            return self.url.split("/shorts/")[1].split("?")[0]
        elif "watch?v=" in self.url:
            return self.url.split("watch?v=")[1].split("&")[0]
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "upload_date": self.upload_date,
            "processed_at": self.processed_at,
            "processing_status": self.processing_status,
            "ocr_description": self.ocr_description,
            "extracted_urls": self.extracted_urls,
            "all_detected_urls": self.all_detected_urls,
            "metadata": self.metadata,
        }

    @classmethod
    def from_video_metadata(
        cls, metadata: VideoMetadata, status: str = "failed"
    ) -> "VideoProcessingResult":
        """Create a processing result from video metadata."""
        return cls(
            url=metadata.url,
            title=metadata.title,
            upload_date=metadata.upload_date,
            processed_at=datetime.now().isoformat(),
            processing_status=status,
        )
