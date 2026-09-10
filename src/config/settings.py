"""Settings management for Watchtower using Pydantic Settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.models import (
    APIConfig,
    Environment,
    ETLConfig,
    GoogleDriveConfig,
    LLMConfig,
    LoggingConfig,
    ScrapingConfig,
    SpanishPublicAidConfig,
)


class Settings(BaseSettings):
    """Main application settings with environment variable support."""

    # Application settings
    app_name: str = Field(default="Watchtower", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Project paths
    project_root: str | None = Field(default=None, description="Project root directory")
    data_dir: str = Field(default="data", description="Data directory")
    logs_dir: str = Field(default="logs", description="Logs directory")

    # Component configurations
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    etl: ETLConfig = Field(default_factory=ETLConfig)
    google_drive: GoogleDriveConfig = Field(default_factory=GoogleDriveConfig)
    spanish_public_aid: SpanishPublicAidConfig = Field(default_factory=SpanishPublicAidConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    class Config:
        """Pydantic configuration."""

        env_file = [".env", ".env.local"]
        env_prefix = "WATCHTOWER_"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields to be ignored instead of causing validation errors

    def __init__(self, **kwargs):
        """Initialize settings with automatic project root detection."""
        super().__init__(**kwargs)

        # Auto-detect project root if not provided
        if not self.project_root:
            self.project_root = self._find_project_root()

        # Update relative paths to absolute paths
        self._update_paths()

    def _find_project_root(self) -> str:
        """Find the project root directory."""
        current_path = Path(__file__).resolve()

        # Look for project markers
        markers = ["pyproject.toml", "README.md", ".git", "requirements.txt"]

        for parent in current_path.parents:
            if any((parent / marker).exists() for marker in markers):
                return str(parent)

        # Fallback to current working directory
        return os.getcwd()

    def _update_paths(self) -> None:
        """Update relative paths to absolute paths based on project root."""
        if self.project_root:
            base_path = Path(self.project_root)

            # Update directory paths
            if not os.path.isabs(self.data_dir):
                self.data_dir = str(base_path / self.data_dir)
            if not os.path.isabs(self.logs_dir):
                self.logs_dir = str(base_path / self.logs_dir)

            # Update logging file path
            if not os.path.isabs(self.logging.file_path):
                self.logging.file_path = str(base_path / self.logging.file_path)

    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.data_dir,
            self.logs_dir,
            self.logging.file_path,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The cached settings instance.
    """
    return Settings()
