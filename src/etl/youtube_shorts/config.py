"""Configuration for YouTube Shorts OCR processing."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OCRSettings:
    """OCR processing configuration."""

    # Quality thresholds
    min_confidence: float = 10.0  # Minimum confidence score (0-100)
    min_text_length: int = 4  # Minimum text length to consider valid

    # Image preprocessing
    use_enhancement: bool = True
    use_binarization: bool = True
    use_denoising: bool = True
    use_thresholding: bool = True

    # Processing limits
    max_retries: int = 3
    timeout_seconds: int = 30

    # Frame processing
    frame_similarity_threshold: float = 0.85  # Threshold for duplicate frame detection
    frame_interval_seconds: int = 2  # Default interval between frames

    # Tesseract configuration
    tesseract_config: str = r"--oem 3 --psm 6"
    tesseract_lang: str = "eng"


@dataclass
class VideoSettings:
    """Video processing configuration."""

    # Processing limits
    max_shorts_to_process: int = 10
    default_lookback_days: int = 30
    max_lookback_days: int = 365
    max_request_limit: int = 1000

    # Delays (in seconds)
    request_delay: float = 2.0
    download_delay: float = 1.0
    processing_delay: float = 0.5

    # Download settings
    video_quality: str = "worst"  # Use worst quality for faster download
    socket_timeout: int = 60
    download_retries: int = 2
    fragment_retries: int = 2

    # yt-dlp options
    extract_flat: bool = True
    quiet_mode: bool = True
    ignore_errors: bool = True


@dataclass
class PathSettings:
    """File system paths configuration."""

    # Output directories
    output_dir: Path = field(default_factory=lambda: Path("data/youtube_shorts_ocr"))
    temp_video_dir: Path = field(default_factory=lambda: Path("data/temp_youtube_videos"))
    checkpoint_file: Path = field(default_factory=lambda: Path("data/youtube_shorts_ocr/checkpoint.json"))

    def ensure_directories(self) -> None:
        """Create all necessary directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_video_dir.mkdir(parents=True, exist_ok=True)

        # Ensure checkpoint file directory exists
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class YouTubeOCRConfig:
    """Complete configuration for YouTube Shorts OCR processing."""

    ocr: OCRSettings = field(default_factory=OCRSettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    paths: PathSettings = field(default_factory=PathSettings)

    # Target channel
    target_channel_url: str = ""

    # Logging
    debug: bool = False
    log_level: str = "INFO"

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.target_channel_url:
            errors.append("target_channel_url is required")

        if self.ocr.min_confidence < 0 or self.ocr.min_confidence > 100:
            errors.append("min_confidence must be between 0 and 100")

        if self.ocr.min_text_length < 1:
            errors.append("min_text_length must be at least 1")

        if self.video.max_shorts_to_process < 1:
            errors.append("max_shorts_to_process must be at least 1")

        if self.video.default_lookback_days < 1:
            errors.append("default_lookback_days must be at least 1")

        if self.video.default_lookback_days > self.video.max_lookback_days:
            errors.append("default_lookback_days cannot exceed max_lookback_days")

        if self.video.request_delay < 0:
            errors.append("request_delay cannot be negative")

        if self.ocr.frame_similarity_threshold < 0 or self.ocr.frame_similarity_threshold > 1:
            errors.append("frame_similarity_threshold must be between 0 and 1")

        return errors

    def __post_init__(self):
        """Validate configuration after initialization."""
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")


# Default configuration instance
DEFAULT_CONFIG = YouTubeOCRConfig(
    target_channel_url="https://www.youtube.com/@AIwithaut",
)
