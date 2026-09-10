"""Configuration models using Pydantic for validation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class LoggingConfig(BaseModel):
    """Logging configuration model."""

    level: LogLevel = Field(default=LogLevel.INFO, description="Default logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    file_enabled: bool = Field(default=True, description="Enable file logging")
    file_path: str = Field(default="logs", description="Log file directory")
    file_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, description="Max log file size in bytes")
    file_backup_count: int = Field(default=5, ge=1, le=50, description="Number of backup log files")
    console_enabled: bool = Field(default=True, description="Enable console logging")
    structured: bool = Field(default=False, description="Use structured JSON logging")


class ScrapingConfig(BaseModel):
    """Web scraping configuration model."""

    user_agent: str = Field(
        default="Watchtower/1.0 (+https://github.com/watchtower)",
        description="User agent string for requests",
    )
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, ge=1, le=60, description="Delay between retries")
    concurrent_limit: int = Field(default=10, ge=1, le=100, description="Max concurrent requests")
    rate_limit: float = Field(default=1.0, ge=0.1, le=60.0, description="Rate limit in requests per second")
    playwright_headless: bool = Field(default=True, description="Run Playwright in headless mode")
    playwright_timeout: int = Field(
        default=30000,
        ge=5000,
        le=300000,
        description="Playwright timeout in milliseconds",
    )
    proxies: list[str] = Field(
        default=[],
        description="List of proxy URLs for rotation",
    )


class APIConfig(BaseModel):
    """API configuration model."""

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, ge=1000, le=65535, description="API port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    workers: int = Field(default=1, ge=1, le=32, description="Number of worker processes")
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:45714",
            "http://127.0.0.1:45714",
            "http://192.168.31.126:45714",
            "http://localhost:7780",
            "http://127.0.0.1:7780",
            "http://192.168.31.126:7780",
            "https://watchtower.josmerod.es",
        ],
        description="CORS allowed origins",
    )
    cors_methods: list[str] = Field(default=["GET"], description="CORS allowed methods")
    news_api_key: str | None = Field(default=None, description="API key for NewsAPI")
    rapidapi_key: str | None = Field(default=None, description="API key for RapidAPI (rapidapi_etl)")
    stackexchange_key: str | None = Field(default=None, description="API key for the Stack Exchange API (stackexchange_etl)")


class ETLConfig(BaseModel):
    """ETL pipeline configuration."""

    batch_size: int = Field(default=1000, ge=10, le=10000, description="Default batch size for processing")
    max_workers: int = Field(default=4, ge=1, le=32, description="Maximum worker threads")
    checkpoint_enabled: bool = Field(default=True, description="Enable ETL checkpointing")
    cleanup_old_data_days: int = Field(default=90, ge=1, le=730, description="Days to keep old data")


class GoogleDriveConfig(BaseModel):
    credentials_file: str = Field(
        default="client_secrets.json",
        description="Path to the Google Drive API credentials JSON file (relative to project root or absolute).",
    )
    backup_folder_id: str = Field(default="", description="Google Drive folder ID for backups.")


class SpanishPublicAidConfig(BaseModel):
    """Spanish Public Aid ETL configuration."""

    enabled_sources: list[str] = Field(
        default=["bdns", "gva", "dogv", "valencia", "burjassot", "labora"],
        description="List of enabled data sources",
    )
    max_aids_per_source: int = Field(default=100, ge=10, le=1000, description="Maximum aids to extract per source")
    data_quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum data quality score to include aid",
    )
    update_frequency_hours: int = Field(default=6, ge=1, le=168, description="Update frequency in hours")
    enable_duplicate_detection: bool = Field(default=True, description="Enable duplicate aid detection")
    max_description_length: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Maximum description length to store",
    )

    # Source-specific settings
    bdns_enabled: bool = Field(default=True, description="Enable BDNS source")
    gva_enabled: bool = Field(default=True, description="Enable GVA source")
    dogv_enabled: bool = Field(default=True, description="Enable DOGV aid notices source")
    valencia_enabled: bool = Field(default=True, description="Enable Valencia source")
    burjassot_enabled: bool = Field(default=True, description="Enable Burjassot local aid source")
    labora_enabled: bool = Field(default=True, description="Enable LABORA source")

    # Scraping settings
    request_delay_seconds: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Delay between requests to be respectful",
    )
    max_retries_per_source: int = Field(default=3, ge=1, le=10, description="Maximum retries per source on failure")

    # Classification settings
    auto_categorize: bool = Field(default=True, description="Enable automatic aid categorization")
    keyword_extraction: bool = Field(default=True, description="Enable automatic keyword extraction")

    # Notification settings
    notify_new_aids: bool = Field(default=False, description="Send notifications for new aids")
    notify_closing_soon: bool = Field(default=False, description="Send notifications for aids closing soon")
    closing_soon_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Days threshold for 'closing soon' notifications",
    )


class LLMConfig(BaseModel):
    """Configuration for Large Language Models."""

    provider: LLMProvider = Field(default=LLMProvider.MOCK, description="LLM Provider to use")
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    openai_base_url: str | None = Field(default=None, description="OpenAI Base URL for compatible APIs")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API Key")
    model: str = Field(default="gpt-4o-mini", description="Model name to use (e.g., gpt-4o-mini, claude-3-opus)")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, le=100000, description="Max tokens in response")
