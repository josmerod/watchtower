"""ETL constants and configuration values.

Centralized constants for ETL processes to eliminate magic numbers
and improve maintainability.
"""

from __future__ import annotations

# --- Base ETL Constants ---
DEFAULT_BATCH_SIZE: int = 100
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_DELAY_SECONDS: int = 5
DEFAULT_CHECKPOINT_ENABLED: bool = True
DEFAULT_DEDUPLICATION_ENABLED: bool = True
DEFAULT_TITLE_SIMILARITY_THRESHOLD: float = 0.8

# --- Circuit Breaker Constants ---
CIRCUIT_BREAKER_DEFAULT_FAILURE_THRESHOLD: int = 5
CIRCUIT_BREAKER_DEFAULT_RECOVERY_TIMEOUT_SECONDS: int = 1800  # 30 minutes
CIRCUIT_BREAKER_DEFAULT_HALF_OPEN_MAX_CALLS: int = 3

# --- Proxy Manager Constants ---
PROXY_MANAGER_DEFAULT_MAX_RETRIES: int = 3
PROXY_MANAGER_DEFAULT_BACKOFF_FACTOR: float = 0.5
PROXY_MANAGER_DEFAULT_TIMEOUT_SECONDS: int = 30

# --- Checkpoint Constants ---
CHECKPOINT_FILE_EXTENSION: str = ".json"
CHECKPOINT_TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"

# --- Deduplication Constants ---
DEDUPLICATION_DEFAULT_SIMILARITY_THRESHOLD: float = 0.85
DEDUPLICATION_MIN_TITLE_LENGTH: int = 10
DEDUPLICATION_CACHE_SIZE: int = 1000

# --- Retry Constants ---
RETRY_EXPONENTIAL_BACKOFF_BASE: int = 2
RETRY_MAX_DELAY_SECONDS: int = 300  # 5 minutes
RETRY_JITTER_ENABLED: bool = True

# --- Logging Constants ---
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
PERFORMANCE_LOG_FORMAT: str = "%(asctime)s [PERF] %(message)s"

# --- File System Constants ---
DEFAULT_DATA_DIR: str = "data"
DEFAULT_OUTPUT_DIR: str = "output"
DEFAULT_CHECKPOINT_DIR: str = "checkpoints"
JSON_INDENT: int = 2
JSON_DEFAULT_DATETIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%fZ"

# --- Web Scraping Constants ---
SCRAPER_DEFAULT_TIMEOUT_SECONDS: int = 30
SCRAPER_DEFAULT_MAX_RETRIES: int = 5
SCRAPER_DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
SCRAPER_DEFAULT_REQUEST_DELAY_SECONDS: float = 1.0
SCRAPER_DEFAULT_CONCURRENT_REQUESTS: int = 5

# --- Content Processing Constants ---
VIDEO_TITLE_MAX_LENGTH: int = 75
VIDEO_DESCRIPTION_MAX_LENGTH: int = 500
ARTICLE_TITLE_MAX_LENGTH: int = 200
ARTICLE_SUMMARY_MAX_LENGTH: int = 500

# --- Dashboard Constants ---
DASHBOARD_PAGE_SIZE: int = 15
DASHBOARD_MAX_RESULTS: int = 1000
DASHBOARD_REFRESH_INTERVAL_SECONDS: int = 300  # 5 minutes
DASHBOARD_CACHE_TTL_SECONDS: int = 3600  # 1 hour

# --- Date Parsing Constants ---
DATE_ISO_FORMAT: str = "%Y-%m-%dT%H:%M:%S"
DATE_ISO_FORMAT_WITH_TZ: str = "%Y-%m-%dT%H:%M:%S%z"
DATE_COMMON_FORMATS: list[str] = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y-%m-%d %H:%M:%S",
]

# --- NLP Classification Constants ---
NLP_DEFAULT_MODEL: str = "en_core_web_sm"
NLP_SIMILARITY_THRESHOLD: float = 0.75
NLP_MIN_TEXT_LENGTH: int = 50
NLP_MAX_TEXT_LENGTH: int = 10000

# --- Technology Adoption Constants ---
TECH_ADOPTION_MIN_REPOS: int = 10
TECH_ADOPTION_MIN_STARS: int = 100
TECH_ADOPTION_TREND_WINDOW_DAYS: int = 90
TECH_ADOPTION_PREDICTION_HORIZON_DAYS: int = 30

# --- Performance Constants ---
PERFORMANCE_WARNING_THRESHOLD_SECONDS: float = 5.0
PERFORMANCE_CRITICAL_THRESHOLD_SECONDS: float = 30.0
MEMORY_WARNING_THRESHOLD_MB: int = 500
MEMORY_CRITICAL_THRESHOLD_MB: int = 1000

# --- Testing Constants ---
TEST_TIMEOUT_SECONDS: int = 60
TEST_RETRY_ATTEMPTS: int = 3
TEST_CLEANUP_ENABLED: bool = True

# --- API Constants ---
API_DEFAULT_TIMEOUT_SECONDS: int = 30
API_MAX_RETRIES: int = 3
API_RETRY_DELAY_SECONDS: int = 2
API_BACKOFF_FACTOR: float = 1.5

# --- Database Constants ---
DB_DEFAULT_POOL_SIZE: int = 5
DB_MAX_OVERFLOW: int = 10
DB_POOL_TIMEOUT_SECONDS: int = 30
DB_CONNECTION_TIMEOUT_SECONDS: int = 10

# --- Validation Constants ---
VALIDATION_MIN_TITLE_LENGTH: int = 5
VALIDATION_MAX_TITLE_LENGTH: int = 500
VALIDATION_MIN_URL_LENGTH: int = 10
VALIDATION_MAX_URL_LENGTH: int = 2000
VALIDATION_REQUIRED_FIELDS: list[str] = ["title", "url"]

# --- Error Handling Constants ---
ERROR_MAX_STACK_TRACE_LENGTH: int = 1000
ERROR_MAX_CONTEXT_LENGTH: int = 500
ERROR_NOTIFICATION_ENABLED: bool = False
ERROR_LOG_TO_FILE: bool = True

# --- Security Constants ---
SECURE_SSL_VERIFY: bool = True
SECURE_CERT_FILE: str | None = None  # Will use certifi by default
SECURE_MAX_REDIRECTS: int = 5
SECURE_COOKIE_ENABLED: bool = True

# --- Feature Flags ---
FEATURE_CHECKPOINTING_ENABLED: bool = True
FEATURE_CIRCUIT_BREAKER_ENABLED: bool = True
FEATURE_PROXY_ROTATION_ENABLED: bool = False  # Disabled by default
FEATURE_DEDUPLICATION_ENABLED: bool = True
FEATURE_ENRICHMENT_ENABLED: bool = False

# --- Version Constants ---
VERSION: str = "2.5.1"
BUILD_DATE: str = "2025-12-25"
API_VERSION: str = "v1"
