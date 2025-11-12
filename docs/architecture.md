# Architecture Document - Megalith (Watchtower)

**Project**: Megalith (Watchtower)
**Author**: Joshi
**Date**: 2025-01-12
**Version**: 1.0.0
**Type**: Brownfield Project (Existing Codebase)
**Complexity Level**: High - Multi-domain data aggregation platform

---

## Executive Summary

**Megalith (Watchtower)** is a comprehensive data intelligence and monitoring platform that aggregates, processes, and monitors information from 50+ diverse sources including research papers, news feeds, games, courses, AI platforms, and social media.

**Core Architectural Philosophy**: **Extensibility through Patterns**

The architecture prioritizes **rapid source integration** (<30min per new source) through well-defined framework patterns (BaseETL, BaseWatcher) while maintaining high performance and data quality.

**Key Metrics**:
- **50+ Active Data Sources** (target: 100+)
- **<30 minute** source integration time (via scaffolding tools)
- **<2 second** dashboard load time with 10K+ items
- **File-based JSON** storage (no database) for simplicity and performance
- **Template Method Pattern** as core extensibility mechanism

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [System Architecture](#2-system-architecture)
3. [Project Structure](#3-project-structure)
4. [Core Framework Patterns](#4-core-framework-patterns)
5. [Cross-Cutting Concerns](#5-cross-cutting-concerns)
6. [Epic-to-Architecture Mapping](#6-epic-to-architecture-mapping)
7. [Implementation Patterns for AI Agents](#7-implementation-patterns-for-ai-agents)
8. [Performance & Scalability](#8-performance--scalability)
9. [Security](#9-security)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment](#11-deployment)

---

## 1. Technology Stack

### Core Technologies

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Language** | Python 3.10+ | Modern type hints, match statements, async support |
| **Package Manager** | UV | 10-100x faster than pip, consistent dependency resolution |
| **Web Framework** | Dash + Flask | Python-native reactive framework, no separate frontend |
| **UI Components** | dash-bootstrap-components | Bootstrap 5 styling, responsive design |
| **Data Visualization** | Plotly | Interactive charts, dashboard integration |
| **Data Validation** | Pydantic v2 | Type-safe models, settings management |
| **Data Processing** | Pandas + Polars | Pandas for compatibility, Polars for performance |
| **Web Scraping** | BeautifulSoup4, Playwright, Requests, Cloudscraper | Multi-strategy scraping for different site types |
| **Testing** | pytest + pytest-cov | Standard Python testing with coverage |
| **Code Quality** | Ruff (linting + formatting), mypy (type checking) | Fast, modern tooling |
| **Logging** | Python logging + custom StructuredFormatter | JSON structured logs, performance tracking |

### Data Storage Decision: **File-Based JSON**

**Choice**: File-based JSON storage in `data/` directory

**Rationale**:
1. **Simplicity**: No database setup, migrations, or ORM complexity
2. **Performance**: Direct file reads are fast for read-heavy workloads
3. **Version Control**: Data files can be backed up easily
4. **Portability**: Works across environments without database dependencies
5. **Inspection**: JSON files are human-readable and debuggable

**Trade-offs**:
- ❌ No ACID transactions (acceptable for read-heavy, append-mostly workloads)
- ❌ No complex queries (mitigated by Pandas/Polars for filtering)
- ✅ Perfect for 10K-50K items per domain (current scale)
- ✅ Dashboard caching makes file reads negligible

**Future Migration Path** (if needed at 100K+ items):
- PostgreSQL with SQLAlchemy for transactional data
- Keep file-based storage for archival and cold data

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Data Sources                     │
│  ArXiv │ GitHub │ Reddit │ News │ Games │ Courses │ AI Platforms│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ETL Framework Layer                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  BaseETL   │  │ ArXiv ETL  │  │ News ETL   │ ... (50+ ETLs) │
│  │ (Template) │  │ (Concrete) │  │ (Concrete) │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│       │                │                │                        │
│       ▼                ▼                ▼                        │
│  [Extract] ──▶ [Transform] ──▶ [Load] ──▶ JSON Files           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Storage Layer                           │
│  data/{source}/output/{source}_{timestamp}.json                │
│  data/{source}/output/{source}_latest.json                     │
│  data/{source}/checkpoints/latest.json                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
┌────────────────────────┐  ┌────────────────────────┐
│   Watcher System       │  │  Dashboard Layer       │
│  (Real-time Monitor)   │  │  (Dash + Bootstrap)    │
│                        │  │                        │
│  ┌──────────────┐      │  │  ┌──────────────┐     │
│  │ BaseWatcher  │      │  │  │ Tab Manager  │     │
│  │ (Template)   │      │  │  │  Pattern     │     │
│  └──────────────┘      │  │  └──────────────┘     │
│  • State Persistence   │  │  • Single Callback    │
│  • Event Logging       │  │  • Lazy Loading       │
│  • Change Detection    │  │  • Bootstrap UI       │
└────────────────────────┘  └────────────────────────┘
```

### 2.2 Data Flow

```
External API/RSS ──▶ ETL Pipeline ──▶ JSON Storage ──▶ Dashboard
     │                   │               │                │
     ▼                   ▼               ▼                ▼
┌──────────┐      ┌──────────┐    ┌──────────┐    ┌──────────┐
│ • HTTP   │      │ • Extract│    │ • File   │    │ • Manager│
│ • RSS    │      │ • Trans  │    │ • Cached │    │ • Filter │
│ • API    │      │ • Valida │    │ • Events │    │ • Display│
│ • Scrape │      │ • Load   │    │ • Latest │    │ • Search │
└──────────┘      └──────────┘    └──────────┘    └──────────┘
```

### 2.3 Three-Layer Pattern

**Layer 1: Data Acquisition** (ETL Pipelines)
- Inherit from `BaseETL`
- Implement: `extract()`, `transform()`, `load()`
- Automatic: metrics, checkpointing, retry logic, validation

**Layer 2: Data Storage** (File System + JSON)
- Timestamped files for history: `{name}_{YYYYmmdd_HHMMSS}.json`
- Latest symlinks for fast access: `{name}_latest.json`
- Checkpoints for resumability: `checkpoints/latest.json`
- Metrics for monitoring: `data/metrics/etl_runs_latest.json`

**Layer 3: Data Presentation** (Dash Dashboard)
- Manager classes (VideoManager pattern) for data handling
- Single callback pattern to prevent Dash conflicts
- Component-based tabs with filters, search, pagination
- Real-time health monitoring via `/health` and `/metrics` endpoints

---

## 3. Project Structure

```
watchtower/
├── .bmad/                        # BMAD workflow system (dev tooling)
│   └── bmm/                      # BMad Method workflows
│       ├── agents/               # Specialized AI agents (Architect, Dev, etc.)
│       ├── workflows/            # Multi-step workflows (PRD, Architecture, etc.)
│       └── config.yaml           # BMad configuration
│
├── src/                          # Source code (primary development)
│   ├── etl/                      # ETL pipelines (50+ sources)
│   │   ├── base.py               # BaseETL framework ⭐
│   │   ├── arxiv/                # ArXiv research papers
│   │   ├── news/                 # News aggregation (HN, Reddit, Medium)
│   │   ├── games/                # Game deals (Steam, Epic, Humble)
│   │   ├── goldigging/           # Educational courses (Udemy, Coursera)
│   │   ├── ai_platforms/         # AI platform monitoring (OpenAI, Anthropic)
│   │   ├── entertainment/        # Cinema, meme economy
│   │   ├── deals/                # Deal aggregation
│   │   ├── anime/                # MyAnimeList data
│   │   ├── adhd/                 # PubMed research papers
│   │   ├── fourchan/             # 4chan general threads
│   │   ├── spanish_public_aid/   # Government aid programs
│   │   └── intelligence/         # Advanced data analysis
│   │
│   ├── watchers/                 # Real-time monitoring
│   │   ├── base_watcher.py       # BaseWatcher framework ⭐
│   │   └── run_watcher.py        # Watcher orchestration
│   │
│   ├── web/                      # Web interfaces
│   │   ├── dashboard/            # Main Dash dashboard ⭐ (port 7777)
│   │   │   ├── app.py            # Dash application entry point
│   │   │   ├── components/       # Tab components (videos_tab.py, etc.)
│   │   │   ├── assets/           # CSS, JS, images
│   │   │   └── utils.py          # Dashboard utilities
│   │   └── fullstreamlit/        # Legacy Streamlit dashboard (port 8501)
│   │
│   ├── models/                   # Pydantic data models
│   │   ├── base.py               # TimestampedModel, StatusModel
│   │   ├── arxiv.py              # ArxivPaperModel
│   │   ├── technology.py         # TechnologyModel
│   │   ├── games.py              # GameDealModel
│   │   └── ...                   # 20+ domain models
│   │
│   ├── config/                   # Configuration management
│   │   ├── settings.py           # Pydantic Settings ⭐
│   │   └── models.py             # Configuration models
│   │
│   ├── exceptions/               # Custom exception hierarchy
│   │   ├── base.py               # WatchtowerError (root)
│   │   ├── etl.py                # ETL-specific exceptions
│   │   ├── scraping.py           # Scraping exceptions
│   │   └── watcher.py            # Watcher exceptions
│   │
│   ├── utils/                    # Shared utilities
│   │   ├── logging.py            # Structured logging ⭐
│   │   ├── nlp_classifier.py     # NLP classification
│   │   ├── file_system.py        # Path resolution
│   │   └── github_utils.py       # GitHub repository analysis
│   │
│   ├── miners/                   # Advanced data mining tools
│   │   ├── udemy-universal/      # Udemy course automation
│   │   ├── asf-winonly/          # Steam game automation
│   │   └── crypto_sentiment/     # Crypto sentiment analysis
│   │
│   └── analytics/                # Data analysis and trends
│       ├── trends.py             # Trend analysis
│       └── performance.py        # Performance analytics
│
├── data/                         # Data storage (gitignored)
│   ├── {source_name}/            # Per-source directories
│   │   ├── output/               # Processed data files
│   │   │   ├── {source}_{timestamp}.json
│   │   │   └── {source}_latest.json
│   │   └── checkpoints/          # Resumability state
│   │       └── latest.json
│   ├── watchers/                 # Watcher state and events
│   │   └── {watcher_name}/
│   │       ├── state.json
│   │       └── events/
│   ├── metrics/                  # System-wide metrics
│   │   └── etl_runs_latest.json
│   └── shortcuts/                # Dashboard shortcuts
│
├── docs/                         # Documentation
│   ├── PRD.md                    # Product Requirements Document
│   ├── epics.md                  # Epic breakdown (48 stories, 9 epics)
│   ├── architecture.md           # THIS FILE ⭐
│   └── research-technical-*.md   # Technical research notes
│
├── Tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   ├── etl/                      # ETL-specific tests
│   ├── models/                   # Model validation tests
│   └── performance/              # Performance tests
│
├── logs/                         # Application logs (gitignored)
│   └── watchtower.log            # Rotating log file
│
├── run_watchtower_dashboard.py  # Dashboard entry point
├── run_all_etl.sh|.bat           # Run all ETL pipelines
├── pyproject.toml                # UV project configuration
├── .env                          # Environment variables (gitignored)
└── README.md                     # Project README

⭐ = Core architectural components
```

---

## 4. Core Framework Patterns

### 4.1 BaseETL: Template Method Pattern

**Purpose**: Provide consistent ETL pipeline structure with built-in error handling, metrics, checkpointing, and retry logic.

**Pattern**: Template Method (Gang of Four)

**Abstract Interface**:
```python
class BaseETL(ABC, Generic[InputType, OutputType]):
    @abstractmethod
    def extract(self) -> List[InputType]:
        """Extract raw data from source."""
        pass

    @abstractmethod
    def transform(self, data: List[InputType]) -> List[OutputType]:
        """Transform raw data into validated Pydantic models."""
        pass

    @abstractmethod
    def load(self, data: List[OutputType]) -> None:
        """Load transformed data to JSON files."""
        pass

    def run(self) -> ETLMetrics:
        """Template method: orchestrates extract → transform → load."""
        # Handles: checkpointing, retries, metrics, logging, errors
```

**Built-in Features**:
- ✅ **ETLMetrics**: Automatic performance tracking (start_time, duration, records_extracted, success_rate)
- ✅ **Checkpointing**: Resume from last successful point (`ETLCheckpoint` model)
- ✅ **Retry Logic**: Exponential backoff for transient failures (max 3 retries)
- ✅ **Batch Processing**: Configurable batch sizes for memory efficiency
- ✅ **Data Validation**: Pydantic model validation with error reporting
- ✅ **Retention Management**: Auto-cleanup of old timestamped files (configurable days)
- ✅ **Structured Logging**: Component-specific loggers with performance metrics

**Concrete Implementation Example**:
```python
from src.etl.base import BaseETL
from src.models.arxiv import ArxivPaperModel

class ArxivETL(BaseETL[dict, ArxivPaperModel]):
    def extract(self) -> List[dict]:
        # Fetch from ArXiv RSS feed
        return raw_papers

    def transform(self, data: List[dict]) -> List[ArxivPaperModel]:
        # Validate using Pydantic model
        return self.validate_data(data, ArxivPaperModel)

    def load(self, data: List[ArxivPaperModel]) -> None:
        # Save to data/arxiv/output/arxiv_{timestamp}.json
        # Save to data/arxiv/output/arxiv_latest.json
```

**Key Decisions**:
- `Generic[InputType, OutputType]` for type safety
- Automatic metrics collection (no manual tracking)
- Checkpoint files in `data/{etl_name}/checkpoints/latest.json`
- Output files in `data/{etl_name}/output/`

---

### 4.2 BaseWatcher: Event-Driven Monitoring

**Purpose**: Monitor data sources for changes and trigger events.

**Pattern**: Observer Pattern + State Machine

**Abstract Interface**:
```python
class BaseWatcher(ABC):
    @abstractmethod
    def get_current_value(self) -> Any:
        """Get current state from source."""
        pass

    @abstractmethod
    def check_for_changes(self, old_value: Any, new_value: Any) -> bool:
        """Determine if change is significant."""
        pass

    def run(self, once: bool = False) -> None:
        """Main monitoring loop with state persistence."""
```

**Built-in Features**:
- ✅ **State Persistence**: JSON-based checkpoint in `data/watchers/{name}/state.json`
- ✅ **Event Logging**: Timestamped change events in `data/watchers/{name}/events/`
- ✅ **Configurable Intervals**: Flexible polling frequencies (default: 1 hour)
- ✅ **Exception Resilience**: Continues operation despite individual failures
- ✅ **Automatic Directory Creation**: Self-managing file system structure

**Typical Use Case**: Monitor ArXiv for new papers, trigger notifications

---

### 4.3 Pydantic Models: Data Validation & Settings

**Purpose**: Type-safe data models and settings management.

**Pattern**: Data Transfer Object (DTO) + Settings Object

**Model Hierarchy**:
```python
class TimestampedModel(BaseModel):
    """Base for all data models with timestamp tracking."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ArxivPaperModel(TimestampedModel):
    """Domain-specific model with validation."""
    title: str
    authors: List[str]
    abstract: str
    published: datetime
    url: str
    categories: List[str]
```

**Settings Management**:
```python
from src.config.settings import get_settings

settings = get_settings()  # Singleton with @lru_cache
data_path = settings.get_data_path("arxiv", "output")
```

**Key Features**:
- ✅ **Environment Variable Support**: Double underscore delimiter (`DATABASE__URL`)
- ✅ **Nested Configurations**: Component-specific configs (ETLConfig, WatcherConfig)
- ✅ **Auto-discovery**: Automatic project root detection via markers
- ✅ **Type Validation**: Full Pydantic validation with custom validators
- ✅ **Path Management**: Automatic conversion to absolute paths

---

### 4.4 Dashboard Manager Pattern

**Purpose**: Centralized data handling and filtering for dashboard tabs.

**Pattern**: Manager Pattern + Single Callback

**VideoManager Example** (from `videos_tab.py`):
```python
class VideoManager:
    """Manages video data loading and filtering."""

    def __init__(self):
        self.video_data = {}  # Channel -> DataFrame
        self.loaded = False

    def load_data(self):
        """Load all video data from JSON files."""
        for channel_dir in youtube_path.iterdir():
            json_file = channel_dir / "youtube_videos.json"
            df = pd.read_json(json_file)
            self.video_data[channel_dir.name] = df

    def get_videos(self, channel=None, search_term=None, days_filter=None, limit=200):
        """Get filtered videos with caching."""
        # Apply filters, return results
```

**Single Callback Pattern**:
```python
@app.callback(
    Output("videos-display", "children"),
    Input("channel-dropdown", "value"),
    Input("search-input", "value"),
    prevent_initial_call=True
)
def update_videos(channel, search_term):
    """Single callback updates entire video display."""
    videos = video_manager.get_videos(channel, search_term)
    return create_video_cards(videos)
```

**Key Decisions**:
- ✅ **One Manager per Tab**: VideoManager, PapersManager, NewsManager, etc.
- ✅ **One Callback per Output**: Prevents "Duplicate callback outputs" errors
- ✅ **Lazy Loading**: Data loaded on first access, cached thereafter
- ✅ **Thread-Safe**: Manager instances are module-level singletons

---

## 5. Cross-Cutting Concerns

### 5.1 Error Handling

**Custom Exception Hierarchy**:
```
WatchtowerError (root)
├── ConfigurationError
├── ValidationError
├── AuthenticationError
├── AuthorizationError
├── ETLError
│   ├── CheckpointError
│   ├── ExtractionError
│   ├── TransformationError
│   ├── LoadError
│   ├── DataSourceError
│   ├── DataValidationError
│   ├── ETLTimeoutError
│   └── ETLConfigurationError
├── ScrapingError
│   ├── RequestError
│   ├── ParsingError
│   ├── RateLimitError
│   └── TimeoutError
└── WatcherError
    ├── WatcherConfigurationError
    ├── WatcherRuntimeError
    ├── WatcherTimeoutError
    ├── WatcherValidationError
    └── WatcherConnectionError
```

**Error Handling Strategy**:
1. **Context Preservation**: All exceptions carry context dicts
2. **handle_exception()**: Centralized error handling utility
3. **Graceful Degradation**: Dashboard continues functioning despite errors
4. **Structured Logging**: Errors logged with full context and stack traces
5. **Retry Logic**: Exponential backoff for transient failures

**Example**:
```python
try:
    data = extract_from_api()
except RequestError as e:
    logger.error(f"API request failed: {e}", exc_info=True)
    raise DataSourceError(
        "Failed to fetch data from API",
        context={"url": api_url, "attempt": retry_count},
        cause=e
    ) from e
```

---

### 5.2 Logging Strategy

**Structured Logging with JSON**:
```python
from src.utils.logging import get_logger, get_performance_logger

logger = get_logger("ETL.ArXiv")
perf_logger = get_performance_logger("ETL.ArXiv")

logger.info("Starting ArXiv ETL", extra={"source": "arxiv", "batch_size": 100})

perf_logger.start("ETL_ArXiv")
# ... do work ...
perf_logger.end(success=True, extra_data={"records": 150})
```

**Log Output Format** (JSON):
```json
{
  "timestamp": "2025-01-12T10:30:45.123456",
  "level": "INFO",
  "logger": "ETL.ArXiv",
  "message": "Starting ArXiv ETL",
  "module": "arxiv_etl",
  "function": "extract",
  "line": 42,
  "source": "arxiv",
  "batch_size": 100,
  "process_id": 12345,
  "thread_id": 67890
}
```

**Log Levels**:
- **DEBUG**: Detailed diagnostic information (development only)
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (operation failed, but app continues)
- **CRITICAL**: Critical errors (app may crash)

**Log Rotation**:
- File: `logs/watchtower.log`
- Max size: 10MB per file
- Backup count: 5 files
- Encoding: UTF-8

---

### 5.3 Date & Time Handling

**Standard Practice**: **Always use UTC timestamps**

```python
from datetime import datetime

# ✅ CORRECT: UTC timestamps
created_at = datetime.utcnow()
timestamp_str = datetime.utcnow().isoformat()

# ✅ CORRECT: Parsing with timezone awareness
df["published_date"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)

# ❌ INCORRECT: Local time (ambiguous across timezones)
created_at = datetime.now()  # Don't use this!
```

**File Naming Convention**:
```python
# Timestamped files
filename = f"{source_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
# Example: arxiv_20250112_103045.json
```

**JSON Serialization**:
```python
# Store as ISO 8601 strings
{"created_at": "2025-01-12T10:30:45.123456"}

# Parse back
created_at = datetime.fromisoformat(data["created_at"])
```

---

### 5.4 Data Persistence Patterns

**File Naming Convention**:
```
data/{source_name}/output/{source}_{YYYYmmdd_HHMMSS}.json  # Timestamped
data/{source_name}/output/{source}_latest.json             # Latest copy
data/{source_name}/checkpoints/latest.json                 # Checkpoint
data/{source_name}/output/run_summary_{timestamp}.json     # Metrics
data/{source_name}/output/run_summary_latest.json          # Latest metrics
```

**Directory Structure Rules**:
1. Each ETL/Watcher creates `data/{name}/` automatically
2. Subdirectories: `output/`, `checkpoints/`, `events/`
3. Retention: Auto-delete timestamped files older than N days (configurable)
4. `*_latest.*` files are NEVER deleted

**JSON Format**:
```python
{
    "generated_at": "2025-01-12T10:30:45",
    "source": "arxiv",
    "items": [
        {
            "id": "2501.12345",
            "title": "Paper Title",
            "created_at": "2025-01-12T09:00:00",
            # ... more fields
        }
    ],
    "metadata": {
        "count": 150,
        "etl_version": "1.0.0"
    }
}
```

---

### 5.5 API Response Formats

**Health Check Endpoint** (`/health`):
```json
{
    "status": "ok",           // "ok" | "degraded" | "down"
    "timestamp": "2025-01-12T10:30:45",
    "version": "0.1.0",
    "uptime_seconds": 86400,
    "etl_health": {
        "total_sources": 52,
        "failed_last_run": 2,
        "success_rate": 96.15
    }
}
```

**Metrics Endpoint** (`/metrics`):
```json
{
    "generated_at": "2025-01-12T10:30:45",
    "runs": {
        "arxiv": {
            "etl_name": "arxiv",
            "start_time": "2025-01-12T09:00:00",
            "duration_seconds": 45.2,
            "records_loaded": 150,
            "success": true,
            "last_updated": "2025-01-12T09:00:45"
        },
        "news": {
            "etl_name": "news",
            "start_time": "2025-01-12T09:05:00",
            "duration_seconds": 32.1,
            "records_loaded": 420,
            "success": true,
            "last_updated": "2025-01-12T09:05:32"
        }
    }
}
```

---

### 5.6 Testing Approach

**Test Organization**:
```
Tests/
├── unit/           # Unit tests for individual functions
├── integration/    # Integration tests for ETL workflows
├── etl/           # ETL-specific tests
├── models/        # Pydantic model validation tests
├── web/           # Dashboard component tests
└── performance/   # Performance and load tests
```

**Testing Patterns**:

**1. ETL Testing**:
```python
import pytest
from src.etl.arxiv.arxiv_etl import ArxivETL

def test_arxiv_extract(mock_arxiv_api):
    """Test ArXiv extraction with mocked API."""
    etl = ArxivETL(name="test_arxiv")
    data = etl.extract()
    assert len(data) > 0
    assert all("title" in item for item in data)

def test_arxiv_transform():
    """Test ArXiv transformation and validation."""
    etl = ArxivETL(name="test_arxiv")
    raw_data = [{"title": "Test", "authors": ["Alice"], ...}]
    models = etl.transform(raw_data)
    assert all(isinstance(m, ArxivPaperModel) for m in models)
```

**2. Model Testing**:
```python
def test_arxiv_model_validation():
    """Test Pydantic model validation."""
    valid_data = {
        "title": "Test Paper",
        "authors": ["Alice", "Bob"],
        "abstract": "Test abstract",
        "published": "2025-01-12T10:00:00",
        "url": "https://arxiv.org/abs/2501.12345",
        "categories": ["cs.AI"]
    }
    model = ArxivPaperModel(**valid_data)
    assert model.title == "Test Paper"

def test_arxiv_model_invalid():
    """Test validation errors."""
    with pytest.raises(ValidationError):
        ArxivPaperModel(title="Test", authors=[])  # Missing required fields
```

**3. Dashboard Testing**:
```python
def test_video_manager_load():
    """Test VideoManager data loading."""
    manager = VideoManager()
    manager.load_data()
    assert len(manager.get_channels()) > 0

def test_video_filtering():
    """Test video filtering logic."""
    manager = VideoManager()
    videos = manager.get_videos(channel="ai-news", search_term="GPT")
    assert all("gpt" in v["title"].lower() for v in videos)
```

**Coverage Targets** (from Epic 7.2):
- **Overall**: 70% minimum
- **BaseETL**: 90% target
- **Models**: 80% target
- **Dashboard**: 60% target

**Test Execution**:
```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test categories
uv run pytest Tests/etl/ -v
uv run pytest Tests/models/ -v
uv run pytest Tests/integration/ -v
```

---

## 6. Epic-to-Architecture Mapping

This section maps the 9 epics from `docs/epics.md` to architectural components and patterns.

### Epic 1: Observability Infrastructure
**Architectural Components**:
- **ETLMetrics Model**: Already implemented in `src/etl/base.py`
- **Health Check API**: Add Flask endpoints `/health` and `/metrics` to `src/web/dashboard/app.py`
- **Metrics Dashboard Tab**: New component `src/web/dashboard/components/metrics_tab.py`
- **Structured Logging**: Already implemented in `src/utils/logging.py`

**Patterns Used**:
- Template Method (BaseETL provides automatic metrics)
- Singleton (Settings for metrics configuration)
- REST API (Health check endpoints)

**Key Decisions**:
- Metrics stored in `data/metrics/etl_runs_latest.json` (aggregated)
- Per-ETL metrics in `data/{etl}/output/run_summary_latest.json`
- Search implemented client-side (Dash callbacks) for <1s response

---

### Epic 2: Personalized Intelligence Hub
**Architectural Components**:
- **Browser LocalStorage**: Preferences stored client-side initially
- **PreferencesManager**: New manager class for preference handling
- **Dashboard Tab Customization**: Modify `src/web/dashboard/app.py` layout generation
- **Responsive CSS**: Bootstrap responsive breakpoints

**Patterns Used**:
- Manager Pattern (PreferencesManager)
- Strategy Pattern (Filter presets)
- Observer Pattern (Real-time filter updates)

**Key Decisions**:
- Preferences stored in browser `localStorage` initially (single-user)
- Migration to server-side storage in Epic 5.5 (multi-user)
- Items-per-page: 12, 24, 48, 96 options
- Tab customization: visibility + order

---

### Epic 3: Smart Notifications & Alerts
**Architectural Components**:
- **AlertEngine**: New class in `src/alerts/engine.py`
- **AlertRule Model**: Pydantic model with conditions
- **Web Notifications API**: Browser push notifications
- **Watcher Integration**: BaseWatcher triggers alert evaluation

**Patterns Used**:
- Rule Engine Pattern (Alert conditions)
- Observer Pattern (Watcher → Alert Engine)
- Event Sourcing (Alert events stored as JSON)

**Key Decisions**:
- Alert rules in `data/alerts/{user_id}/rules.json`
- Alert events in `data/alerts/{user_id}/events/`
- Deduplication: Content hash + 1-hour time window
- Channels: Browser notifications, Email (future)

---

### Epic 4: Intelligent Data Quality
**Architectural Components**:
- **DeduplicationEngine**: New class in `src/data_quality/deduplication.py`
- **Enhanced NLP Classifier**: Improve `src/utils/nlp_classifier.py`
- **RelevanceScorer**: New class in `src/data_quality/relevance.py`
- **RetentionManager**: New class in `src/data_quality/retention.py`

**Patterns Used**:
- Strategy Pattern (Multiple deduplication strategies)
- Pipeline Pattern (Dedup → Classify → Score → Store)
- Scheduled Job Pattern (Daily cleanup)

**Key Decisions**:
- Title similarity: `difflib.SequenceMatcher` (ratio > 0.8)
- Multi-label classification supported
- Relevance score: `(recency * 0.4) + (source_rep * 0.3) + (category_match * 0.3)`
- Retention policies per source type (news: 30d, papers: 1y, deals: 7d)

---

### Epic 5: Multi-User Foundation
**Architectural Components**:
- **User Model**: Pydantic model in `src/models/user.py`
- **AuthenticationService**: New class in `src/auth/service.py`
- **SessionManager**: Flask-Login or custom session management
- **User Storage**: `data/users/users.json` or SQLite

**Patterns Used**:
- Singleton Pattern (AuthenticationService)
- Decorator Pattern (Login required decorators)
- Factory Pattern (User creation)

**Key Decisions**:
- Password hashing: bcrypt (12 rounds)
- Session storage: Secure HTTP-only cookies
- Session timeout: 30 minutes inactive, 7 days absolute
- Rate limiting: 5 failed attempts per 15 minutes per IP

**Future Migration Path**:
- If users >100: Migrate to PostgreSQL with SQLAlchemy
- If distributed: Add Redis for session storage

---

### Epic 5.5: Per-User Personalization
**Architectural Components**:
- **UserPreferencesModel**: Pydantic model
- **Per-User Storage**: `data/users/{user_id}/preferences.json`
- **PreferencesMigration**: Data migration from localStorage to server

**Patterns Used**:
- Repository Pattern (User preferences CRUD)
- Migration Pattern (Single-user → Multi-user data migration)

**Key Decisions**:
- Preferences: `{tab_visibility, tab_order, items_per_page, saved_filters, shortcuts}`
- Shared sources: `data/{source}/` (global)
- Personal sources: `data/users/{user_id}/sources/` (per-user)

---

### Epic 6: Source Integration Acceleration
**Architectural Components**:
- **SourceRegistry**: New class in `src/registry/registry.py`
- **CLI Scaffolding Tool**: `src/scripts/new_source.py` (Click or argparse)
- **Templates**: Source templates in `src/templates/` or `.bmad/templates/`

**Patterns Used**:
- Registry Pattern (Central source catalog)
- Template Method (Source code generation)
- Decorator Pattern (`@source` metadata decorator)

**Key Decisions**:
- CLI: `megalith new-source <name> --type <rss|api|scraper>`
- Generated files: Model, ETL, Tab, Test
- Auto-register in `data/registry/sources.json`

---

### Epic 7: Technical Debt & Performance Sprint
**Architectural Components**:
- **BaseETL v2.0**: Enhanced ETL framework
- **DataMigrator**: Migration tool in `src/data_quality/migration.py`
- **Performance Profiler**: cProfile + custom analysis

**Patterns Used**:
- Refactoring Patterns (Extract Method, Extract Class)
- Migration Pattern (Schema version migrations)

**Key Decisions**:
- Target: 10 oldest ETLs refactored to BaseETL v2.0
- Test coverage: 40% → 70% (BaseETL: 90%, Models: 80%)
- Dashboard load time: 2s → 1s (via lazy loading, virtual scrolling)
- Complexity: Cyclomatic complexity <10 per function

---

### Epic 8: Simple Intelligence Features
**Architectural Components**:
- **RecommendationEngine**: New class in `src/analytics/recommendations.py`
- **TrendAnalyzer**: New class in `src/analytics/trends.py`
- **RelatedContentEngine**: New class in `src/analytics/related.py`
- **Activity Tracker**: User interaction logging

**Patterns Used**:
- Strategy Pattern (Multiple recommendation algorithms)
- Observer Pattern (User activity tracking)

**Key Decisions**:
- Recommendations: Top 5 sources by clicks + Top 3 categories + Similar content
- Trends: 7-day rolling window, >30% increase = trending
- Insights: Bar charts (Plotly), Pie charts, Line charts, Heatmaps

---

### Epic 9: Platform Ecosystem & Integrations
**Architectural Components**:
- **REST API**: Flask-RESTX or FastAPI in `src/api/`
- **Webhook System**: Webhook delivery in `src/webhooks/`
- **Browser Extension**: Manifest V3 extension

**Patterns Used**:
- REST API Pattern (Resource-based endpoints)
- Webhook Pattern (Event-driven notifications)
- API Gateway Pattern (Rate limiting, auth)

**Key Decisions**:
- API framework: Flask-RESTX (integrated with Dash) or FastAPI (performance)
- Rate limiting: 100 requests/hour per user
- Webhook retry: 3 attempts (30s, 5m, 30m delays)
- OpenAPI documentation at `/api/docs`

---

## 7. Implementation Patterns for AI Agents

This section defines **naming conventions, structure patterns, and coding standards** to ensure AI-assisted development (e.g., Claude Code, GitHub Copilot) produces **consistent, maintainable code**.

### 7.1 File and Directory Naming

**General Rules**:
- **Python files**: `snake_case.py` (e.g., `arxiv_etl.py`, `video_manager.py`)
- **Test files**: `test_{module}.py` (e.g., `test_arxiv_etl.py`)
- **Data directories**: `{source_name}/` (e.g., `arxiv/`, `news/`, `youtube/`)
- **Markdown docs**: `kebab-case.md` (e.g., `architecture.md`, `epic-breakdown.md`)

**ETL Module Naming**:
```
src/etl/{domain}/{domain}_etl.py
src/models/{domain}.py
src/web/dashboard/components/{domain}_tab.py
tests/etl/test_{domain}_etl.py
```

**Example**:
```
src/etl/arxiv/arxiv_etl.py          # ArxivETL class
src/models/arxiv.py                 # ArxivPaperModel
src/web/dashboard/components/papers_tab.py  # Papers tab (displays ArXiv + others)
tests/etl/test_arxiv_etl.py         # Test suite
```

---

### 7.2 Class and Function Naming

**Class Names**: `PascalCase`
- ETL classes: `{Domain}ETL` (e.g., `ArxivETL`, `NewsETL`, `GamesETL`)
- Models: `{Domain}Model` (e.g., `ArxivPaperModel`, `GameDealModel`)
- Managers: `{Domain}Manager` (e.g., `VideoManager`, `PapersManager`)
- Services: `{Purpose}Service` (e.g., `AuthenticationService`, `NotificationService`)

**Function Names**: `snake_case`
- Public methods: `get_videos()`, `load_data()`, `extract()`, `transform()`, `load()`
- Private methods: `_ensure_directories()`, `_load_checkpoint()`, `_retry_operation()`
- Test functions: `test_{functionality}()` (e.g., `test_arxiv_extract()`)

**Constants**: `UPPER_SNAKE_CASE`
```python
MAX_RETRIES = 3
DEFAULT_BATCH_SIZE = 100
API_BASE_URL = "https://api.example.com"
```

---

### 7.3 Code Structure Standards

**Import Order** (PEP 8 + isort):
```python
# 1. Standard library
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

# 2. Third-party libraries
import pandas as pd
from pydantic import BaseModel, Field

# 3. Local imports
from src.config.settings import get_settings
from src.etl.base import BaseETL
from src.models.arxiv import ArxivPaperModel
from src.utils.logging import get_logger
```

**Type Hints**: **ALWAYS required**
```python
def get_videos(
    self,
    channel: Optional[str] = None,
    search_term: Optional[str] = None,
    days_filter: Optional[int] = None,
    limit: int = 200
) -> List[dict[str, Any]]:
    """Get filtered videos with type-safe parameters."""
    pass
```

**Docstrings**: **Google Style**
```python
def extract(self) -> List[dict]:
    """Extract papers from ArXiv RSS feed.

    Fetches the latest papers from cs.AI, cs.LG, and stat.ML categories.

    Returns:
        List[dict]: Raw paper dictionaries with keys: title, authors, abstract,
                    published, url, categories.

    Raises:
        DataSourceError: If ArXiv API is unreachable or returns invalid data.

    Example:
        >>> etl = ArxivETL(name="arxiv")
        >>> papers = etl.extract()
        >>> len(papers)
        150
    """
    pass
```

---

### 7.4 Pydantic Model Standards

**Base Model Pattern**:
```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class TimestampedModel(BaseModel):
    """Base model with automatic timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ArxivPaperModel(TimestampedModel):
    """ArXiv research paper data model."""
    id: str = Field(..., description="ArXiv paper ID (e.g., 2501.12345)")
    title: str = Field(..., min_length=1, max_length=500)
    authors: List[str] = Field(..., min_items=1)
    abstract: str = Field(..., min_length=10)
    published: datetime
    url: HttpUrl
    categories: List[str] = Field(default_factory=list)

    @validator("id")
    def validate_arxiv_id(cls, v):
        """Ensure ArXiv ID format is correct."""
        if not v.startswith("2"):  # Simple check
            raise ValueError("Invalid ArXiv ID format")
        return v
```

**Field Naming**: `snake_case`
**Validation**: Use `@validator` decorators for custom validation
**Config**: Always specify `json_encoders` for datetime serialization

---

### 7.5 ETL Implementation Pattern

**Standard ETL Structure**:
```python
from typing import List
from src.etl.base import BaseETL
from src.models.arxiv import ArxivPaperModel
from src.utils.logging import get_logger

logger = get_logger(__name__)

class ArxivETL(BaseETL[dict, ArxivPaperModel]):
    """ArXiv research papers ETL pipeline."""

    def __init__(self, **kwargs):
        super().__init__(
            name="arxiv",
            description="ArXiv research papers ETL",
            batch_size=100,
            enable_checkpointing=True,
            **kwargs
        )
        self.api_url = "https://export.arxiv.org/rss/cs"

    def extract(self) -> List[dict]:
        """Extract papers from ArXiv RSS feed."""
        logger.info(f"Fetching papers from {self.api_url}")
        # Implementation
        return raw_papers

    def transform(self, data: List[dict]) -> List[ArxivPaperModel]:
        """Transform raw papers into validated models."""
        return self.validate_data(data, ArxivPaperModel)

    def load(self, data: List[ArxivPaperModel]) -> None:
        """Save papers to JSON files."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Timestamped file
        output_file = self.output_dir / f"arxiv_{timestamp}.json"
        output_file.write_text(
            json.dumps(
                [p.model_dump() for p in data],
                ensure_ascii=False,
                indent=2,
                default=str
            ),
            encoding="utf-8"
        )

        # Latest file
        latest_file = self.output_dir / "arxiv_latest.json"
        latest_file.write_text(output_file.read_text(), encoding="utf-8")

        logger.info(f"Saved {len(data)} papers to {output_file}")

# Entry point
if __name__ == "__main__":
    etl = ArxivETL()
    metrics = etl.run()
    print(f"ETL completed: {metrics.success_rate:.1f}% success rate")
```

---

### 7.6 Dashboard Component Pattern

**Tab Component Structure**:
```python
# src/web/dashboard/components/papers_tab.py
import logging
from pathlib import Path
import pandas as pd
import dash_bootstrap_components as dbc
from dash import Input, Output, html, dcc

from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)

class PapersManager:
    """Manages papers data loading and filtering."""

    def __init__(self):
        self.papers_data = pd.DataFrame()
        self.loaded = False

    def load_data(self):
        """Load papers from ArXiv JSON files."""
        arxiv_path = Path(get_data_path("arxiv", "output", "arxiv_latest.json"))
        if arxiv_path.exists():
            self.papers_data = pd.read_json(arxiv_path)
            logger.info(f"Loaded {len(self.papers_data)} papers")
        self.loaded = True

    def get_papers(self, category=None, search_term=None, days_filter=None, limit=100):
        """Get filtered papers."""
        if not self.loaded:
            self.load_data()
        # Apply filters
        return filtered_papers

# Singleton instance
papers_manager = PapersManager()

def create_papers_tab():
    """Create Papers tab layout."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                # Filters
                dcc.Dropdown(id="papers-category-dropdown", ...),
                dcc.Input(id="papers-search-input", ...),
            ], width=3),
            dbc.Col([
                # Content display
                html.Div(id="papers-display")
            ], width=9)
        ])
    ])

def register_callbacks(app):
    """Register Dash callbacks (SINGLE CALLBACK PATTERN)."""

    @app.callback(
        Output("papers-display", "children"),
        Input("papers-category-dropdown", "value"),
        Input("papers-search-input", "value"),
        prevent_initial_call=True
    )
    def update_papers(category, search_term):
        """Update papers display based on filters."""
        papers = papers_manager.get_papers(category, search_term)
        return create_paper_cards(papers)

def create_paper_cards(papers):
    """Create Bootstrap cards for papers."""
    cards = []
    for paper in papers:
        card = dbc.Card([
            dbc.CardBody([
                html.H5(paper["title"]),
                html.P(f"Authors: {', '.join(paper['authors'])}"),
                html.P(paper["abstract"][:200] + "..."),
                dbc.Button("Read More", href=paper["url"], external_link=True)
            ])
        ])
        cards.append(card)
    return cards
```

**Key Patterns**:
- ✅ One Manager per tab (singleton instance)
- ✅ `create_{tab}_tab()` function returns layout
- ✅ `register_callbacks(app)` function for callback registration
- ✅ Single callback per output (prevents conflicts)
- ✅ Lazy loading (`if not self.loaded: self.load_data()`)

---

### 7.7 Testing Patterns

**Test File Structure**:
```python
# tests/etl/test_arxiv_etl.py
import pytest
from unittest.mock import Mock, patch
from src.etl.arxiv.arxiv_etl import ArxivETL
from src.models.arxiv import ArxivPaperModel

@pytest.fixture
def arxiv_etl():
    """Fixture for ArxivETL instance."""
    return ArxivETL(name="test_arxiv")

@pytest.fixture
def sample_arxiv_data():
    """Fixture for sample ArXiv data."""
    return [
        {
            "id": "2501.12345",
            "title": "Test Paper",
            "authors": ["Alice", "Bob"],
            "abstract": "Test abstract content",
            "published": "2025-01-12T10:00:00",
            "url": "https://arxiv.org/abs/2501.12345",
            "categories": ["cs.AI"]
        }
    ]

def test_arxiv_extract_success(arxiv_etl):
    """Test successful extraction from ArXiv."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<rss>...</rss>"

        data = arxiv_etl.extract()
        assert len(data) > 0
        assert all("title" in item for item in data)

def test_arxiv_transform_valid_data(arxiv_etl, sample_arxiv_data):
    """Test transformation with valid data."""
    models = arxiv_etl.transform(sample_arxiv_data)
    assert len(models) == 1
    assert isinstance(models[0], ArxivPaperModel)
    assert models[0].title == "Test Paper"

def test_arxiv_transform_invalid_data(arxiv_etl):
    """Test transformation with invalid data."""
    invalid_data = [{"title": "Test"}]  # Missing required fields
    models = arxiv_etl.transform(invalid_data)
    assert len(models) == 0  # Invalid data filtered out
    assert arxiv_etl.metrics.records_failed == 1

def test_arxiv_load(arxiv_etl, sample_arxiv_data, tmp_path):
    """Test loading data to JSON files."""
    arxiv_etl.output_dir = tmp_path
    models = [ArxivPaperModel(**sample_arxiv_data[0])]

    arxiv_etl.load(models)

    # Check latest file exists
    latest_file = tmp_path / "arxiv_latest.json"
    assert latest_file.exists()

    # Check timestamped file exists
    timestamped_files = list(tmp_path.glob("arxiv_*.json"))
    assert len(timestamped_files) >= 2  # latest + timestamped
```

---

### 7.8 Error Messages and Logging Standards

**Error Messages**:
```python
# ❌ BAD: Vague error
raise ValueError("Invalid data")

# ✅ GOOD: Specific, actionable error
raise DataValidationError(
    f"ArXiv paper missing required field 'authors': {paper['id']}",
    context={"paper_id": paper["id"], "missing_fields": ["authors"]}
)
```

**Logging Standards**:
```python
# ❌ BAD: No context
logger.info("Data loaded")

# ✅ GOOD: Rich context
logger.info(
    f"Loaded {len(data)} papers from ArXiv",
    extra={"source": "arxiv", "count": len(data), "duration_seconds": 12.3}
)

# ❌ BAD: No exception context
try:
    data = fetch_data()
except Exception as e:
    logger.error(f"Error: {e}")

# ✅ GOOD: Full exception context
try:
    data = fetch_data()
except RequestError as e:
    logger.error(
        f"Failed to fetch ArXiv data: {e}",
        exc_info=True,
        extra={"url": api_url, "retry_count": retry_count}
    )
    raise
```

---

## 8. Performance & Scalability

### 8.1 Current Performance Baseline

**Measured Performance** (from PRD NFRs):
- **Dashboard Load Time**: ~2 seconds (target: <2s)
- **ETL Run Time**: <5 minutes per source (50+ sources in parallel)
- **Data Volume**: 10K-50K items per domain
- **Concurrent Users**: 1 (single-user, expanding to 3-5 in Epic 5)

### 8.2 Performance Optimization Strategies

**Dashboard Optimization** (Epic 7.3):
1. **Lazy Loading**: Only load active tab data
2. **Virtual Scrolling**: For lists with 1,000+ items
3. **Client-Side Caching**: Manager classes cache loaded data
4. **Optimized JSON Parsing**: Use `orjson` or `ijson` for large files
5. **Service Worker**: Cache static assets and API responses

**ETL Optimization**:
1. **Batch Processing**: Configurable batch sizes (default: 100 items)
2. **Parallel Execution**: Multiple ETLs run concurrently via shell scripts
3. **Checkpointing**: Resume from last successful point on failures
4. **Incremental Loading**: Only fetch new items (where supported by source)

**Data Storage Optimization**:
1. **Retention Policies**: Auto-cleanup old timestamped files (configurable days)
2. **Compression**: Future: gzip for archived data
3. **Indexing**: Future: JSON-based indices for fast lookups

### 8.3 Scalability Targets

**Near-Term** (Epics 1-7):
- ✅ 100+ data sources (from 50+)
- ✅ 100K items per domain (from 10K-50K)
- ✅ 3-5 concurrent users (from 1)
- ✅ <1 second dashboard load (from ~2s)

**Long-Term** (Epics 8-9):
- ⏳ PostgreSQL migration for 1M+ items
- ⏳ Redis caching for multi-user sessions
- ⏳ Horizontal scaling with load balancing
- ⏳ CDN for static assets

---

## 9. Security

### 9.1 Current Security Posture

**Single-User Security** (Current State):
- ✅ **Local Network Only**: No public exposure
- ✅ **Environment Variables**: Sensitive config in `.env` (gitignored)
- ✅ **Input Validation**: Pydantic models validate all external data
- ✅ **Path Security**: Secure file path handling (no traversal attacks)

**Authentication** (Epic 5):
- ✅ **Password Hashing**: bcrypt with 12 rounds
- ✅ **Session Management**: HTTP-only, secure cookies
- ✅ **CSRF Protection**: Flask-WTF or custom token generation
- ✅ **Rate Limiting**: 5 failed attempts per 15 minutes per IP

### 9.2 Security Best Practices

**Data Handling**:
1. **Never Log Sensitive Data**: Passwords, API keys, tokens
2. **Sanitize User Input**: Validate all input with Pydantic
3. **Secure API Keys**: Store in environment variables, never commit

**Web Security**:
1. **HTTPS Only**: Enforce HTTPS in production (Epic 5)
2. **Secure Cookies**: `HttpOnly`, `Secure`, `SameSite=Lax` flags
3. **CSRF Tokens**: Validate on all state-changing operations
4. **XSS Prevention**: Escape all user-generated content in dashboard

**API Security** (Epic 9):
1. **Authentication**: API keys or OAuth2
2. **Rate Limiting**: 100 requests/hour per user
3. **Input Validation**: Pydantic models for all API payloads
4. **CORS Configuration**: Whitelist allowed origins

### 9.3 Future Security Enhancements

- ⏳ **2FA Support**: Two-factor authentication for admin users
- ⏳ **Audit Logging**: Track user actions and data access
- ⏳ **Encryption at Rest**: Encrypt sensitive data files
- ⏳ **Security Scanning**: Automated dependency vulnerability scanning

---

## 10. Testing Strategy

See [Section 5.6](#56-testing-approach) for detailed testing patterns.

**Summary**:
- **Framework**: pytest + pytest-cov
- **Coverage Target**: 70% overall (BaseETL: 90%, Models: 80%, Dashboard: 60%)
- **Test Types**: Unit, Integration, ETL, Model Validation, Performance
- **Mocking**: Mock external APIs to keep tests fast (<5 min total suite)
- **CI/CD**: Future: Fail build if coverage drops below 70%

---

## 11. Deployment

### 11.1 Current Deployment (Local Development)

**Setup**:
```bash
# 1. Install dependencies with UV (10-100x faster than pip)
uv sync --all-extras

# 2. Install Playwright browsers
uv run playwright install

# 3. Configure environment
cp .env.example .env
# Edit .env with API keys, settings

# 4. Run ETL pipelines
./run_all_etl.sh          # Linux/Mac
.\run_all_etl.bat         # Windows

# 5. Start dashboard
uv run python run_watchtower_dashboard.py
# Available at http://localhost:7777
```

**Directory Creation**:
- Automatic via `Settings.create_directories()`
- Creates: `data/`, `logs/`, `config/` on first run

### 11.2 Production Deployment (Future)

**Docker** (already configured):
- ✅ Dockerfile exists in project root
- ✅ Docker Compose for multi-container setup
- ⏳ Production configuration needed (Epic 5, 7)

**unRAID Deployment** (already configured):
- ✅ Branch: `unraid-deployment-setup`
- ✅ Docker support configured

**Environment Variables** (Production):
```bash
# Application
APP_NAME=Watchtower
ENVIRONMENT=production
DEBUG=false

# Database (if migrating from JSON)
DATABASE__URL=postgresql://user:pass@localhost:5432/watchtower

# Security
SECRET_KEY=<random-32-char-string>
SESSION_TIMEOUT=1800  # 30 minutes

# API Keys (External Services)
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>
```

### 11.3 Monitoring & Observability

**Health Checks**:
- Endpoint: `/health` (status, uptime, ETL health)
- Endpoint: `/metrics` (ETL run summaries, success rates)

**Logging**:
- File: `logs/watchtower.log` (rotating, 10MB max, 5 backups)
- Format: Structured JSON (production), human-readable (development)

**Performance Monitoring**:
- ETL Metrics: Automatic collection in `data/metrics/etl_runs_latest.json`
- Dashboard: Metrics tab (Epic 1.4)

---

## Appendix A: Decision Log

| Decision | Rationale | Trade-offs | Date |
|----------|-----------|-----------|------|
| **File-based JSON Storage** | Simplicity, performance for read-heavy workloads, no database setup | No ACID transactions, limited query capabilities | 2024-Q4 |
| **UV Package Manager** | 10-100x faster than pip, consistent dependency resolution | Newer tool, smaller ecosystem than pip | 2024-Q4 |
| **Dash over Streamlit** | Better component control, production-ready, Bootstrap integration | Steeper learning curve than Streamlit | 2024-Q4 |
| **Template Method Pattern** | Enforces consistent ETL structure, reduces boilerplate | Less flexibility for non-standard ETLs | 2024-Q4 |
| **Single Callback Pattern** | Prevents Dash callback conflicts, easier debugging | May require larger callbacks for complex interactions | 2024-Q4 |
| **Pydantic Everywhere** | Type safety, automatic validation, settings management | Performance overhead for large data volumes (acceptable) | 2024-Q4 |
| **Structured JSON Logging** | Machine-readable, better for log aggregation | Harder to read directly (use log viewers) | 2024-Q4 |
| **UTC Timestamps** | Avoids timezone ambiguity, global consistency | Requires timezone conversion for display | 2024-Q4 |
| **BaseETL Checkpointing** | Resumability, fault tolerance | Additional I/O overhead (minimal) | 2024-Q4 |
| **Manager Pattern (Dashboard)** | Centralized data handling, caching, thread-safe | Singleton instances (acceptable for current scale) | 2024-Q4 |

---

## Appendix B: Future Architectural Decisions

**Pending Decisions** (Epics 8-9):
1. **Database Migration**: If/when to migrate from JSON to PostgreSQL
2. **API Framework**: Flask-RESTX vs. FastAPI for REST API
3. **Caching Layer**: Redis vs. in-memory caching for multi-user sessions
4. **Message Queue**: Celery vs. RQ for background jobs (email digests, etc.)
5. **Frontend Framework**: Keep Dash vs. migrate to React/Vue (if needed)

**Evaluation Criteria**:
- Performance impact
- Development velocity
- Maintenance complexity
- Team expertise
- Cost (hosting, licensing)

---

## Appendix C: Architectural Principles

**Core Principles**:
1. **Simplicity Over Complexity**: Choose boring tech that works
2. **Extensibility Through Patterns**: Template method enables rapid source integration
3. **Performance by Design**: File-based storage, lazy loading, caching
4. **Type Safety**: Python 3.10+ type hints, Pydantic models
5. **Observability**: Structured logging, metrics collection, health checks
6. **Developer Productivity**: UV, Ruff, mypy, pytest for fast iteration
7. **AI-First Development**: Clear patterns and documentation for AI-assisted coding

**SOLID Principles**:
- ✅ **Single Responsibility**: Each ETL handles one source
- ✅ **Open/Closed**: BaseETL open for extension, closed for modification
- ✅ **Liskov Substitution**: All ETLs substitutable for BaseETL
- ✅ **Interface Segregation**: Minimal abstract methods (extract, transform, load)
- ✅ **Dependency Inversion**: Depend on abstractions (BaseETL, BaseWatcher)

---

## Document Metadata

**Version History**:
- v1.0.0 (2025-01-12): Initial architecture document (Joshi, Winston)

**Related Documents**:
- [PRD.md](./PRD.md): Product Requirements Document
- [epics.md](./epics.md): Epic and story breakdown
- [CLAUDE.md](../CLAUDE.md): Claude Code instructions
- [.cursorrules](../.cursorrules): Cursor IDE rules

**Approval Status**: ✅ Approved for implementation

**Next Review Date**: 2025-02-12 (after Epic 1 completion)
