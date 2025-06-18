"""Settings management for Watchtower using Pydantic Settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from config.models import (
    APIConfig,
    DatabaseConfig,
    Environment,
    ETLConfig,
    GoogleDriveConfig,
    LoggingConfig,
    MonitoringConfig,
    NotificationConfig,
    ScrapingConfig,
    SecurityConfig,
    StreamlitConfig,
    WatcherConfig,
)


class Settings(BaseSettings):
    """Main application settings with environment variable support."""

    # Application settings
    app_name: str = Field(default="Watchtower", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Project paths
    project_root: str | None = Field(
        default=None, description="Project root directory"
    )
    data_dir: str = Field(default="data", description="Data directory")
    logs_dir: str = Field(default="logs", description="Logs directory")
    config_dir: str = Field(default="config", description="Config directory")

    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    streamlit: StreamlitConfig = Field(default_factory=StreamlitConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    watchers: WatcherConfig = Field(default_factory=WatcherConfig)
    etl: ETLConfig = Field(default_factory=ETLConfig)
    google_drive: GoogleDriveConfig = Field(default_factory=GoogleDriveConfig)

    class Config:
        """Pydantic configuration."""

        env_file = [".env", ".env.local"]
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields to be ignored instead of causing validation errors

        # Allow environment variables to override nested config
        @classmethod
        def prepare_field_env_vars(cls, field_name: str, field_info) -> dict:
            """Prepare environment variables for nested configs."""
            env_vars = {}

            # Support nested config through environment variables
            # e.g., DATABASE__URL, LOGGING__LEVEL, etc.
            if hasattr(field_info.default_factory, "_fields"):
                for nested_field in field_info.default_factory._fields:
                    env_key = f"{field_name.upper()}__{nested_field.upper()}"
                    env_vars[env_key] = env_key

            return env_vars

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
            if not os.path.isabs(self.config_dir):
                self.config_dir = str(base_path / self.config_dir)

            # Update logging file path
            if not os.path.isabs(self.logging.file_path):
                self.logging.file_path = str(base_path / self.logging.file_path)

    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.data_dir,
            self.logs_dir,
            self.config_dir,
            self.logging.file_path,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING

    def get_data_path(self, *paths: str) -> Path:
        """Get a path relative to the data directory."""
        return Path(self.data_dir) / Path(*paths)

    def get_logs_path(self, *paths: str) -> Path:
        """Get a path relative to the logs directory."""
        return Path(self.logs_dir) / Path(*paths)

    def get_config_path(self, *paths: str) -> Path:
        """Get a path relative to the config directory."""
        return Path(self.config_dir) / Path(*paths)

    def model_dump_env(self) -> dict:
        """Export settings as environment variables format."""

        def _flatten_dict(d: dict, parent_key: str = "", sep: str = "__") -> dict:
            """Flatten nested dictionary with separator."""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(_flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key.upper(), str(v)))
            return dict(items)

        return _flatten_dict(self.dict())


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The cached settings instance.
    """
    return Settings()


def get_settings_for_testing() -> Settings:
    """Get settings configured for testing.

    Returns:
        Settings: Settings instance with testing overrides.
    """
    return Settings(
        environment=Environment.TESTING,
        debug=True,
        database__url="sqlite:///:memory:",
        logging__level="DEBUG",
    )


def reload_settings() -> Settings:
    """Force reload settings (clears cache).

    Returns:
        Settings: New settings instance.
    """
    get_settings.cache_clear()
    return get_settings()
