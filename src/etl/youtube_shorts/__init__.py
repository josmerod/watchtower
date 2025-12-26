"""YouTube Shorts OCR ETL module.

This module provides tools for extracting text and URLs from YouTube Shorts
using OCR (Optical Character Recognition) technology.

Main components:
- Domain models (ExtractedURL, VideoMetadata, OCRResult, VideoProcessingResult)
- Services (OCRService, VideoService, CheckpointService, URLExtractor)
- Configuration (centralized settings management)
- ETL orchestrator (YouTubeShortsETL)
"""

from .config import DEFAULT_CONFIG, OCRSettings, PathSettings, VideoSettings, YouTubeOCRConfig
from .domain import ExtractedURL, OCRResult, VideoMetadata, VideoProcessingResult
from .services import CheckpointService, OCRService, URLExtractor, VideoService
from .youtube_shorts_etl import YouTubeShortsETL

__version__ = "2.0.0"

__all__ = [
    # Configuration
    "DEFAULT_CONFIG",
    "OCRSettings",
    "PathSettings",
    "VideoSettings",
    "YouTubeOCRConfig",
    # Domain models
    "ExtractedURL",
    "OCRResult",
    "VideoMetadata",
    "VideoProcessingResult",
    # Services
    "CheckpointService",
    "OCRService",
    "URLExtractor",
    "VideoService",
    # Main ETL
    "YouTubeShortsETL",
]
