# Architecture Document - Megalith (Watchtower)

**Project**: megalith
**Author**: Joshi (with Winston, Architect)
**Date**: 2025-01-14
**Version**: 2.0
**Project Type**: Brownfield Web Application (Data Intelligence Platform)

---

## Executive Summary

Megalith's architecture is built on **pragmatic, boring technology that works**. This is a brownfield platform with 50+ operational ETL pipelines and a sophisticated dashboard - our architectural decisions preserve this solid foundation while enabling multi-user expansion, smart notifications, and API integrations.

**Core Architectural Philosophy:**
- **Extensibility First**: The <30-minute source integration capability is the platform's magic - all decisions preserve this
- **Boring Technology**: Battle-tested libraries over cutting-edge frameworks
- **File-Based Performance**: JSON storage remains primary data layer, database only where needed (user management)
- **Incremental Enhancement**: Add capabilities without disrupting existing 50+ ETL pipelines

**Key Architectural Decisions:**
1. **Hybrid Storage**: SQLite for users/preferences, file-based JSON for data sources (preserves existing architecture)
2. **Authentication**: Flask-Login for security-critical user management
3. **Real-Time**: Telegram Bot API for instant alerts (better than email), 60s polling for dashboard updates
4. **API Layer**: FastAPI for external integrations (Epic 9), separate service in same container
5. **Performance**: Built-in Python tools (@lru_cache, difflib) before external dependencies

This architecture supports **10-20 users with 1-3 concurrent** (realistic scale), enables all 9 epics, and maintains the rapid extensibility that makes Megalith special.

---

## Project Context (Brownfield)

**Important**: Megalith is NOT a greenfield project. This architecture document describes:
- **Existing foundation** to preserve (50+ ETL pipelines, Dash dashboard, BaseETL framework)
- **New architectural decisions** for Epics 1-9 (multi-user, notifications, API, intelligence features)
- **Integration patterns** between existing and new components

**No starter template initialization needed** - the platform is operational. New components integrate into existing structure.

---

## Decision Summary

| Category | Decision | Version/Library | Affects Epics | Rationale | Provided By |
|----------|----------|----------------|---------------|-----------|-------------|
| **Data - Users** | SQLite | sqlite3 (built-in) or SQLAlchemy 2.x | 5, 5.5, 8, 9 | User management, preferences, sessions. Scales to 20 users, ACID guarantees, no server overhead | New |
| **Data - Sources** | File-based JSON | Built-in json module | All | Preserves existing architecture, fast reads, simple backup, proven at current scale | Existing |
| **Authentication** | Flask-Login | flask-login 0.6.x | 5, 5.5, 9 | Battle-tested security, session management, CSRF protection, Dash-compatible | New |
| **Password Hashing** | bcrypt | bcrypt 4.x | 5 | Industry standard, 12 rounds minimum, future-proof security | New |
| **Dashboard Framework** | Dash | dash 2.x | All | Existing foundation, Bootstrap components, Plotly integration | Existing |
| **UI Components** | Bootstrap 5 | dash-bootstrap-components 1.x | All | Responsive design, accessible components, familiar patterns | Existing |
| **Data Validation** | Pydantic | pydantic 2.x | All | Type-safe models, automatic validation, FastAPI integration | Existing |
| **Configuration** | Pydantic Settings | pydantic-settings 2.x | All | Environment variables, nested configs, type validation | Existing |
| **ETL Framework** | BaseETL (Custom) | N/A - Internal pattern | All | Template method pattern, checkpointing, metrics, retry logic | Existing |
| **Watcher System** | BaseWatcher (Custom) | N/A - Internal pattern | 3, 4 | State persistence, event logging, configurable intervals | Existing |
| **Real-Time Notifications** | Telegram Bot API | python-telegram-bot 20.x | 3 | Instant delivery, free/unlimited, rich formatting, user-friendly | New |
| **Dashboard Updates** | Dash Interval Polling | dcc.Interval (built-in) | 3 | 60s polling acceptable for intelligence aggregation, zero infrastructure | New |
| **REST API** | FastAPI | fastapi 0.110.x | 9 | Auto-docs, Pydantic integration, modern, async support | New |
| **API Server** | Uvicorn | uvicorn 0.27.x | 9 | ASGI server for FastAPI, production-ready, async support | New |
| **Dashboard Server** | Waitress | waitress 3.x | All | Cross-platform WSGI server, Windows/UnRAID compatible, production-ready | New |
| **Data Processing** | Pandas + Polars | pandas 2.x, polars 0.20.x | All | High-performance data operations, existing patterns | Existing |
| **Web Scraping** | Playwright + BeautifulSoup4 | playwright 1.x, bs4 4.x | All | Browser automation, HTML parsing, existing pipelines | Existing |
| **HTTP Requests** | Requests + Cloudscraper | requests 2.x, cloudscraper 1.x | All | HTTP client, cloudflare bypass, proven reliability | Existing |
| **Search (Current)** | Client-side filtering | JavaScript Array.filter | 1 | Sufficient for 10K items/tab, no dependencies, instant results | New |
| **Search (Future)** | PostgreSQL FTS | N/A - if needed | 1 | Migration path if data exceeds 100K items and client-side becomes slow | Future |
| **Deduplication** | difflib | difflib (built-in) | 4 | Title similarity >80%, no dependencies, sufficient accuracy | New |
| **NLP Classification** | Enhanced keywords | Custom + regex | 4 | Low resource usage, improve existing keyword approach, no heavy models | Enhanced |
| **Caching** | LRU Cache | functools.lru_cache (built-in) | 7 | Zero config, built-in, perfect for function-level caching | New |
| **Task Scheduling** | Cron/systemd | OS-level | All | ETL scheduling, cleanup jobs, proven reliability | Existing |
| **Package Manager** | UV | uv 0.1.x | All | 10-100x faster than pip, existing tooling | Existing |
| **Testing** | pytest | pytest 8.x | All | Unit/integration tests, coverage reporting, existing patterns | Existing |
| **Linting/Formatting** | Ruff | ruff 0.2.x | All | Fast linter/formatter, strict rules, existing config | Existing |
| **Type Checking** | mypy | mypy 1.8.x | All | Static type checking, strict mode, existing config | Existing |
| **Deployment** | Docker + UnRAID | docker 24.x | All | Containerization, UnRAID deployment, existing setup | Existing |

**Version Note**: All versions are current as of January 2025 and will be verified during implementation.

---

## Project Structure

```
watchtower/
├── .bmad/                          # BMAD methodology artifacts
│   ├── bmm/                        # BMM workflow files
│   └── templates/                  # Code generation templates
├── data/                           # Data storage layer
│   ├── megalith.db                 # SQLite database (NEW - Epic 5)
│   │   ├── users                   # User accounts
│   │   ├── sessions                # User sessions
│   │   ├── preferences             # User preferences
│   │   └── alert_rules             # Notification rules
│   ├── users/                      # Per-user data (NEW - Epic 5.5)
│   │   └── {user_id}/
│   │       ├── preferences.json    # Dashboard customization
│   │       ├── alerts/             # Alert events
│   │       ├── sources/            # Personal data sources
│   │       └── activity_log.json   # Usage tracking (Epic 8)
│   ├── shared/                     # Shared data sources (EXISTING - all 50+ sources)
│   │   ├── youtube/
│   │   │   └── youtube_videos.json
│   │   ├── arxiv/
│   │   │   └── arxiv_papers.json
│   │   ├── news/
│   │   ├── games/
│   │   ├── courses/
│   │   └── ... (50+ other sources)
│   ├── watchers/                   # Watcher state (EXISTING)
│   │   └── {watcher_name}/
│   │       ├── state.json
│   │       └── events/
│   ├── metrics/                    # ETL performance metrics (NEW - Epic 1)
│   │   ├── {etl_name}/
│   │   └── profiling/              # Performance profiling (Epic 7)
│   └── backups/                    # Data backups
├── src/
│   ├── api/                        # FastAPI REST API (NEW - Epic 9)
│   │   ├── main.py                 # API entry point
│   │   ├── routers/                # API route modules
│   │   │   ├── sources.py
│   │   │   ├── content.py
│   │   │   ├── users.py
│   │   │   └── alerts.py
│   │   ├── auth.py                 # API authentication
│   │   └── models.py               # API response models
│   ├── auth/                       # Authentication system (NEW - Epic 5)
│   │   ├── login_manager.py        # Flask-Login setup
│   │   ├── models.py               # User model
│   │   └── utils.py                # Password hashing, session management
│   ├── alerts/                     # Notification system (NEW - Epic 3)
│   │   ├── engine.py               # Alert rule engine
│   │   ├── telegram_bot.py         # Telegram bot integration
│   │   └── models.py               # AlertRule, AlertEvent models
│   ├── analytics/                  # Intelligence features (NEW - Epic 8)
│   │   ├── trends.py               # Trend detection
│   │   ├── recommendations.py      # Usage-based recommendations
│   │   └── related.py              # Related content engine
│   ├── config/
│   │   ├── settings.py             # Pydantic settings (EXISTING)
│   │   └── models.py               # Config models (EXISTING)
│   ├── data_quality/               # Data quality pipeline (NEW - Epic 4)
│   │   ├── deduplication.py        # Duplicate detection (difflib)
│   │   ├── classification.py       # Enhanced NLP classification
│   │   ├── relevance.py            # Relevance scoring
│   │   ├── retention.py            # Retention policies
│   │   └── migration.py            # Data migration utilities
│   ├── etl/                        # ETL pipelines (EXISTING)
│   │   ├── base.py                 # BaseETL framework
│   │   ├── arxiv/
│   │   ├── news/
│   │   ├── games/
│   │   ├── courses/
│   │   └── ... (50+ sources)
│   ├── models/                     # Pydantic data models (EXISTING)
│   │   ├── base.py
│   │   ├── arxiv_model.py
│   │   ├── game_deal_model.py
│   │   └── ... (50+ models)
│   ├── registry/                   # Source registry (NEW - Epic 6)
│   │   └── registry.py             # Source metadata catalog
│   ├── utils/
│   │   ├── nlp_classifier.py       # NLP classification (EXISTING, Enhanced in Epic 4)
│   │   ├── file_system.py          # Path resolution (EXISTING)
│   │   └── logging.py              # Structured logging (EXISTING)
│   ├── watchers/                   # Watcher system (EXISTING)
│   │   ├── base_watcher.py         # BaseWatcher framework
│   │   └── run_watcher.py          # Watcher orchestration
│   ├── web/
│   │   ├── dashboard/              # Main Dash dashboard (EXISTING)
│   │   │   ├── app.py              # Dashboard entry point
│   │   │   ├── components/         # Tab components
│   │   │   │   ├── videos_tab.py
│   │   │   │   ├── papers_tab.py
│   │   │   │   ├── news_tab.py
│   │   │   │   ├── metrics_tab.py  # NEW - Epic 1
│   │   │   │   └── ... (15+ tabs)
│   │   │   ├── assets/             # CSS, JavaScript
│   │   │   └── utils.py            # Shared utilities
│   │   └── fullstreamlit/          # Legacy Streamlit (EXISTING - compatibility)
│   ├── exceptions/                 # Custom exceptions (EXISTING)
│   └── miners/                     # Advanced data mining tools (EXISTING)
├── tests/                          # Test suite (EXISTING)
│   ├── unit/
│   ├── integration/
│   ├── etl/
│   └── models/
├── logs/                           # Application logs (EXISTING)
├── docs/                           # Documentation
│   ├── architecture.md             # This file
│   ├── PRD.md                      # Product requirements
│   ├── epics.md                    # Epic breakdown
│   ├── CLAUDE.md                   # Development guide (EXISTING)
│   └── bmm-workflow-status.yaml    # BMM workflow tracking
├── .env                            # Environment variables (gitignored)
├── .cursorrules                    # Cursor IDE rules (EXISTING)
├── pyproject.toml                  # UV project config (EXISTING)
├── requirements.txt                # Python dependencies (EXISTING)
├── docker-compose.yml              # Docker orchestration (EXISTING)
├── Dockerfile                      # Container definition (EXISTING)
├── run_watchtower_dashboard.py    # Dashboard launcher (EXISTING)
├── run_all_etl.sh                  # ETL orchestration script (EXISTING)
└── README.md                       # Project overview (EXISTING)
```

**Key Architectural Boundaries:**
- `src/etl/` - Data ingestion layer (50+ sources, BaseETL pattern)
- `src/watchers/` - Real-time monitoring layer (BaseWatcher pattern)
- `data/` - Persistence layer (hybrid: SQLite + JSON files)
- `src/web/dashboard/` - Presentation layer (Dash + Bootstrap)
- `src/api/` - Integration layer (FastAPI - NEW in Epic 9)
- `src/auth/` - Security layer (Flask-Login - NEW in Epic 5)
- `src/alerts/` - Notification layer (Telegram - NEW in Epic 3)

---

## Epic to Architecture Mapping

| Epic | Primary Architecture Components | Data Storage | Key Technologies |
|------|--------------------------------|--------------|------------------|
| **Epic 1: Observability** | `src/metrics/`, `data/metrics/`, `web/dashboard/components/metrics_tab.py` | `data/metrics/{etl_name}/*.json` | BaseETL metrics, Plotly charts, health API endpoints |
| **Epic 2: Personalization** | `src/auth/preferences.py`, `web/dashboard/` (enhanced) | Browser localStorage (Phase 1) → `data/users/{user_id}/preferences.json` (Phase 2) | Dash callbacks, JSON storage |
| **Epic 3: Notifications** | `src/alerts/`, `data/alerts/` | `data/alerts/{user_id}/rules.json`, `data/alerts/{user_id}/events/*.json` | Telegram Bot API, Dash Interval polling, Alert rule engine |
| **Epic 4: Data Quality** | `src/data_quality/`, `src/utils/nlp_classifier.py` | Enhanced data files with `duplicate_group_id`, `relevance_score` | difflib, enhanced keyword NLP, retention policies |
| **Epic 5: Multi-User Auth** | `src/auth/`, `data/megalith.db` | SQLite tables: `users`, `sessions` | Flask-Login, bcrypt, SQLite |
| **Epic 5.5: Per-User Prefs** | `src/auth/preferences.py`, `data/users/{user_id}/` | `data/users/{user_id}/preferences.json`, `data/users/{user_id}/sources/` | User-scoped data, migration from localStorage |
| **Epic 6: Integration Tools** | `src/registry/`, `src/templates/` | `data/registry/sources.json` | CLI scaffolding, source metadata |
| **Epic 7: Tech Debt** | All `src/etl/` (refactored), `tests/` (expanded) | `data/metrics/profiling/` | pytest, coverage, cProfile, @lru_cache |
| **Epic 8: Intelligence** | `src/analytics/`, `web/dashboard/components/insights_tab.py` | `data/users/{user_id}/activity_log.json`, `data/analytics/trends/` | Heuristic algorithms, Plotly visualizations |
| **Epic 9: Ecosystem** | `src/api/`, webhooks, browser extension | API uses existing `data/` sources | FastAPI, Uvicorn, OpenAPI docs, Telegram webhooks |

---

## Technology Stack Details

### Core Technologies

**Backend Framework:**
- **Dash 2.x**: Reactive dashboard framework (existing)
  - Built on Flask (enables Flask-Login integration)
  - Component-based architecture with callbacks
  - Single-callback pattern per component to prevent conflicts
  - Bootstrap styling via dash-bootstrap-components

**API Framework (NEW - Epic 9):**
- **FastAPI 0.110.x**: Modern Python API framework
  - Automatic OpenAPI/Swagger documentation
  - Pydantic integration for request/response validation
  - Async support for performance
  - Separate service on port 8000

**Authentication (NEW - Epic 5):**
- **Flask-Login 0.6.x**: Session management and authentication
  - Integrates with Dash's Flask server
  - Secure session cookies (HTTP-only, secure flag)
  - Remember-me functionality
  - CSRF protection

**Data Layer:**
- **SQLite** (built-in or SQLAlchemy 2.x): User management
  - Tables: users, sessions, preferences, alert_rules
  - ACID transactions for auth operations
  - File-based (`data/megalith.db`)
  - No server overhead

- **File-based JSON**: Data sources (existing)
  - Fast read performance
  - Simple backup (copy files)
  - `data/{source}/output/*.json` pattern
  - Latest file symlinks for quick access

**Data Processing:**
- **Pandas 2.x**: Primary data manipulation (existing)
- **Polars 0.20.x**: High-performance alternative (existing)
- **Pydantic 2.x**: Data validation and models (existing)

**Notification System (NEW - Epic 3):**
- **python-telegram-bot 20.x**: Telegram Bot API client
  - Instant push notifications
  - Rich message formatting
  - Free and unlimited
  - User-friendly onboarding

**Production Servers:**
- **Waitress 3.x**: WSGI server for Dash dashboard
  - Cross-platform (Windows/UnRAID compatible)
  - Production-ready
  - Port 7780

- **Uvicorn 0.27.x**: ASGI server for FastAPI
  - High-performance async support
  - Production-ready
  - Port 8000

### Integration Points

**Dashboard ↔ Data Layer:**
```python
# VideoManager pattern (existing)
class VideoManager:
    @lru_cache(maxsize=128)  # NEW - Epic 7 caching
    def load_videos(self, channel: str) -> List[Video]:
        # Read from data/youtube/{channel}/youtube_videos.json
        pass
```

**ETL Pipeline ↔ Watchers:**
```python
# BaseETL writes data → BaseWatcher monitors changes
# Watcher detects new content → Alert engine evaluates → Telegram notification
```

**Dashboard ↔ Authentication (NEW - Epic 5):**
```python
from flask_login import login_required, current_user

@app.callback(...)
@login_required
def protected_callback():
    user_prefs = load_preferences(current_user.id)
    # Return user-specific data
```

**Dashboard ↔ Notifications (NEW - Epic 3):**
```python
# Dash Interval polls every 60s
dcc.Interval(id='notification-poll', interval=60*1000)

@app.callback(Output('notifications', 'children'), Input('notification-poll', 'n_intervals'))
def check_notifications():
    # Read data/alerts/{user_id}/events/*.json
    # Return new alerts for display
```

**FastAPI ↔ Data Sources (NEW - Epic 9):**
```python
from fastapi import FastAPI, Depends
from src.api.auth import get_current_user

@app.get("/api/content/{domain}")
def get_content(domain: str, user: User = Depends(get_current_user)):
    # Load from data/shared/{domain}/*.json
    # Apply user's personalization filters
    return content
```

**Telegram Bot ↔ Alert Engine (NEW - Epic 3):**
```python
# Alert rule matches → Generate event → Send Telegram message
from telegram import Bot

bot = Bot(token=settings.telegram_bot_token)
bot.send_message(
    chat_id=user.telegram_chat_id,
    text=f"🔔 New free course: {course.title}",
    parse_mode="Markdown"
)
```

---

## Implementation Patterns

These patterns ensure consistency across all AI agents implementing features.

### Naming Conventions

**Files and Directories:**
- Python files: `snake_case.py` (e.g., `arxiv_etl.py`, `user_preferences.py`)
- Test files: `test_{module}.py` (e.g., `test_arxiv_etl.py`)
- Directories: `snake_case/` (e.g., `data_quality/`, `alert_rules/`)
- Models: `{name}_model.py` (e.g., `arxiv_model.py`, `user_model.py`)

**Python Code:**
- Classes: `PascalCase` (e.g., `BaseETL`, `VideoManager`, `AlertEngine`)
- Functions/methods: `snake_case` (e.g., `load_videos()`, `check_notifications()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- Private methods: `_leading_underscore` (e.g., `_validate_config()`)

**Database (SQLite):**
- Tables: `snake_case` plural (e.g., `users`, `sessions`, `alert_rules`)
- Columns: `snake_case` (e.g., `user_id`, `created_at`, `password_hash`)
- Foreign keys: `{table}_id` (e.g., `user_id` references `users.id`)

**API Endpoints:**
- REST paths: `/api/{resource}` lowercase (e.g., `/api/sources`, `/api/users/{id}`)
- Query parameters: `snake_case` (e.g., `?source_filter=arxiv&limit=50`)

### Code Organization Patterns

**ETL Modules:**
```python
# All ETL classes inherit from BaseETL
class ArxivETL(BaseETL):
    def extract(self) -> List[Dict]:
        """Fetch data from external source."""
        pass

    def transform(self, raw_data: List[Dict]) -> List[ArxivPaperModel]:
        """Validate and transform data."""
        pass

    def load(self, data: List[ArxivPaperModel]) -> None:
        """Save to data/arxiv/output/*.json."""
        pass
```

**Dashboard Components:**
```python
# Tab function + Manager class pattern
def videos_tab():
    """Render videos tab layout."""
    return html.Div([...])

class VideoManager:
    """Handle video data loading and filtering."""

    @lru_cache(maxsize=128)
    def load_videos(self, channel: str) -> List[Video]:
        """Load and cache video data."""
        pass

# Single callback per tab (prevents conflicts)
@app.callback(
    Output('videos-display', 'children'),
    Input('channel-dropdown', 'value')
)
def update_videos(channel: str):
    manager = VideoManager()
    videos = manager.load_videos(channel)
    return render_video_cards(videos)
```

**API Modules:**
```python
# FastAPI router pattern
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/sources", tags=["sources"])

@router.get("/")
def list_sources(user: User = Depends(get_current_user)):
    """List all data sources."""
    return {"sources": load_source_registry()}
```

### Error Handling Patterns

**ETL Pipelines:**
```python
# Use custom exception hierarchy
from src.exceptions import ETLError, ValidationError, NetworkError

try:
    data = self.extract()
except NetworkError as e:
    logger.error(f"Network failure: {e}")
    raise  # Let retry mechanism handle
except ValidationError as e:
    logger.warning(f"Invalid data: {e}")
    # Skip invalid items, continue processing
```

**Dashboard Callbacks:**
```python
# Graceful degradation with user feedback
@app.callback(...)
def callback_with_error_handling():
    try:
        result = process_data()
        return result
    except Exception as e:
        logger.exception("Callback failed")
        return html.Div([
            html.P("⚠️ Error loading data", className="text-danger"),
            html.P(str(e), className="text-muted")
        ])
```

**API Endpoints:**
```python
# Consistent error responses
from fastapi import HTTPException

@router.get("/content/{domain}")
def get_content(domain: str):
    if domain not in VALID_DOMAINS:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")

    try:
        data = load_content(domain)
        return {"data": data}
    except Exception as e:
        logger.exception(f"Failed to load {domain}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Logging Patterns

**Structured Logging:**
```python
import logging

logger = logging.getLogger(__name__)

# Always include context
logger.info("ETL started", extra={
    "etl_name": "arxiv",
    "start_time": datetime.now().isoformat(),
    "config": {"batch_size": 100}
})

# Error context preservation
try:
    process_data()
except Exception as e:
    logger.exception("Processing failed", extra={
        "etl_name": "arxiv",
        "error_type": type(e).__name__,
        "input_data": data_sample  # Never log full data
    })
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information (development only)
- `INFO`: General informational messages (ETL start/complete, user actions)
- `WARNING`: Unexpected but handled situations (data validation failures, retries)
- `ERROR`: Error events that require attention (ETL failures, API errors)
- `CRITICAL`: Critical failures requiring immediate action (database corruption, auth failures)

### Data Persistence Patterns

**File Writes (Atomic):**
```python
import json
from pathlib import Path

def save_data(data: List[Dict], output_path: Path):
    """Atomic file write using temp file + rename."""
    temp_path = output_path.with_suffix('.tmp')

    # Write to temp file
    with temp_path.open('w') as f:
        json.dump(data, f, indent=2)

    # Atomic rename
    temp_path.rename(output_path)
```

**SQLite Transactions:**
```python
import sqlite3

def update_user_preferences(user_id: int, preferences: dict):
    """Update preferences with transaction."""
    conn = sqlite3.connect('data/megalith.db')
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE preferences SET value = ? WHERE user_id = ?",
            (json.dumps(preferences), user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### Testing Patterns

**Unit Tests:**
```python
import pytest
from src.etl.arxiv.arxiv_etl import ArxivETL

def test_arxiv_transform_valid_data():
    """Test transform with valid data."""
    etl = ArxivETL()
    raw_data = [{"title": "Test Paper", "authors": ["Author 1"]}]

    result = etl.transform(raw_data)

    assert len(result) == 1
    assert result[0].title == "Test Paper"

def test_arxiv_transform_invalid_data():
    """Test transform with invalid data."""
    etl = ArxivETL()
    raw_data = [{"invalid": "data"}]

    with pytest.raises(ValidationError):
        etl.transform(raw_data)
```

**Integration Tests:**
```python
def test_arxiv_etl_end_to_end(tmp_path):
    """Test complete ETL pipeline."""
    etl = ArxivETL(output_dir=tmp_path)

    etl.run()

    # Verify output file created
    output_files = list(tmp_path.glob("*.json"))
    assert len(output_files) == 1

    # Verify data validity
    with output_files[0].open() as f:
        data = json.load(f)
        assert len(data) > 0
        assert all('title' in item for item in data)
```

---

## Consistency Rules

### Date/Time Handling

**Format:** ISO 8601 strings for storage, timezone-aware datetime objects in code
```python
from datetime import datetime, timezone

# Storage
timestamp = datetime.now(timezone.utc).isoformat()  # "2025-01-14T10:30:00+00:00"

# Parsing
dt = datetime.fromisoformat(timestamp)

# Display (dashboard)
display_time = dt.strftime("%Y-%m-%d %H:%M")  # "2025-01-14 10:30"
```

**Consistency:**
- All timestamps stored in UTC
- Display in user's local time (browser handles conversion)
- File timestamps in format: `{name}_{YYYYMMDD_HHMMSS}.json`

### API Response Format

**Success Response:**
```json
{
  "data": [...],
  "meta": {
    "count": 150,
    "page": 1,
    "total_pages": 15
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid source filter",
    "details": {
      "field": "source_filter",
      "allowed_values": ["arxiv", "news", "games"]
    }
  }
}
```

### Configuration Precedence

1. Environment variables (highest priority)
2. `.env` file
3. Config file (`src/config/settings.py` defaults)
4. Code defaults (lowest priority)

```python
# Example
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/megalith.db")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Required, no default
```

---

## Data Architecture

### Database Schema (SQLite)

**users table:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    telegram_chat_id TEXT,  -- For Telegram notifications
    created_at TEXT NOT NULL,
    last_login TEXT
);
```

**sessions table:**
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,  -- Session ID
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**preferences table:**
```sql
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,  -- JSON string
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, key)
);
```

**alert_rules table:**
```sql
CREATE TABLE alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    conditions TEXT NOT NULL,  -- JSON: {sources, keywords, categories}
    channels TEXT NOT NULL,    -- JSON: ["telegram", "email"]
    active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### File-Based Data Models

**Shared Data Sources:**
```
data/shared/
├── youtube/{channel}/youtube_videos.json
├── arxiv/arxiv_papers.json
├── news/hackernews.json
├── games/free_games.json
└── ... (50+ sources)
```

**Per-User Data:**
```
data/users/{user_id}/
├── preferences.json              # Dashboard customization
├── alerts/
│   ├── rules.json               # Alert rules (also in SQLite)
│   └── events/
│       └── {timestamp}_alert.json
├── sources/                     # Personal data sources
│   └── {source_name}/*.json
└── activity_log.json            # Usage tracking for recommendations
```

**Metrics Data:**
```
data/metrics/
├── {etl_name}/
│   └── {timestamp}_metrics.json
└── profiling/
    └── {etl_name}_profile.json
```

### Data Relationships

```
User (SQLite)
  ├─ 1:N → Sessions (SQLite)
  ├─ 1:N → Preferences (SQLite + JSON)
  ├─ 1:N → AlertRules (SQLite)
  ├─ 1:N → AlertEvents (JSON files)
  ├─ 1:1 → ActivityLog (JSON file)
  └─ 1:N → PersonalSources (JSON files)

Shared Sources (JSON files)
  ├─ Read by all users
  ├─ Written by ETL pipelines
  └─ Filtered by user preferences
```

---

## API Contracts

### Authentication Endpoints

**POST /api/auth/login**
```json
Request:
{
  "username": "joshi",
  "password": "secure_password"
}

Response (200):
{
  "token": "eyJ...",
  "user": {
    "id": 1,
    "username": "joshi",
    "email": "joshi@example.com"
  }
}
```

**POST /api/auth/logout**
```json
Request: (authenticated)

Response (200):
{
  "message": "Logged out successfully"
}
```

### Content Endpoints

**GET /api/sources**
```json
Response:
{
  "data": [
    {
      "id": "arxiv",
      "name": "ArXiv Papers",
      "type": "RSS",
      "update_frequency": "daily",
      "item_count": 1250,
      "last_updated": "2025-01-14T10:00:00Z"
    }
  ],
  "meta": {
    "count": 52
  }
}
```

**GET /api/content/{domain}?limit=50&offset=0**
```json
Response:
{
  "data": [
    {
      "id": "arxiv_2501_12345",
      "title": "Advanced AI Paper",
      "source": "arxiv",
      "date": "2025-01-14",
      "url": "https://arxiv.org/...",
      "preview": "Abstract text..."
    }
  ],
  "meta": {
    "count": 50,
    "total": 1250,
    "page": 1,
    "total_pages": 25
  }
}
```

### User Preferences Endpoints

**GET /api/user/preferences**
```json
Response:
{
  "data": {
    "tab_visibility": {
      "videos": true,
      "papers": true,
      "news": false
    },
    "tab_order": ["videos", "papers", "deals"],
    "items_per_page": 48
  }
}
```

**PUT /api/user/preferences**
```json
Request:
{
  "tab_visibility": {
    "videos": true,
    "papers": true
  }
}

Response (200):
{
  "message": "Preferences updated",
  "data": { ... }
}
```

### Alert Endpoints

**GET /api/alerts?unread_only=true**
```json
Response:
{
  "data": [
    {
      "id": "alert_123",
      "title": "New free course detected",
      "source": "udemy",
      "timestamp": "2025-01-14T10:30:00Z",
      "read": false,
      "content_url": "https://..."
    }
  ],
  "meta": {
    "count": 5,
    "unread_count": 3
  }
}
```

### Webhook Payloads

**content.new event:**
```json
{
  "event": "content.new",
  "timestamp": "2025-01-14T10:30:00Z",
  "data": {
    "source": "arxiv",
    "items": [
      {
        "id": "arxiv_2501_12345",
        "title": "New Paper",
        "url": "https://..."
      }
    ]
  },
  "signature": "sha256=..."
}
```

---

## Security Architecture

### Authentication Flow

**User Registration:**
1. User submits username, email, password
2. Validate password strength (min 12 characters)
3. Hash password with bcrypt (12 rounds)
4. Store in SQLite `users` table
5. Create initial preferences record

**Login Flow:**
1. User submits credentials
2. Lookup user by username/email
3. Verify password with bcrypt
4. Create session (Flask-Login)
5. Store session in SQLite `sessions` table
6. Return secure HTTP-only cookie

**Session Management:**
- Session timeout: 7 days (remember-me) or 30 minutes (default)
- HTTP-only cookies (prevent XSS)
- Secure flag (HTTPS only in production)
- SameSite=Lax (CSRF protection)
- Server-side session storage (SQLite)

### Password Security

**Requirements:**
- Minimum 12 characters
- No complexity requirements (passphrase-friendly)
- Bcrypt hashing with 12 rounds

**Password Reset (Future):**
- Email-based reset tokens
- Token expiration: 1 hour
- Single-use tokens

### API Security

**Authentication:**
- API keys stored in user profile
- Bearer token authentication: `Authorization: Bearer {api_key}`
- Rate limiting: 100 requests/hour per user

**Rate Limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/sources")
@limiter.limit("100/hour")
def get_sources():
    pass
```

**CORS Configuration:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7780"],  # Dashboard only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Data Security

**Sensitive Configuration:**
- All API keys, tokens, passwords in environment variables or `.env` file
- `.env` file gitignored
- No secrets committed to version control

**Input Validation:**
- All external data validated via Pydantic models
- SQL injection prevention: parameterized queries (SQLite/SQLAlchemy)
- Path traversal prevention: validate file paths, use absolute paths only

**File Permissions:**
- `data/` directory: read/write for app user only
- `data/megalith.db`: 600 (owner read/write only)
- Log files: 644 (owner read/write, others read)

---

## Performance Considerations

### Dashboard Performance

**Current State:**
- Initial page load: ~2 seconds
- Tab switching: ~500ms
- Filter application: ~300ms

**Optimization Targets (Epic 7):**
- Initial load: <1 second
- Tab switching: <300ms
- Filter application: <200ms

**Optimization Strategies:**

1. **Lazy Loading:**
```python
# Only load data for active tab
@app.callback(Output('tab-content', 'children'), Input('tabs', 'value'))
def render_tab(active_tab):
    if active_tab == 'videos':
        return load_videos_tab()  # Loads data only when tab accessed
    # Other tabs not loaded
```

2. **Function-Level Caching:**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def load_videos(channel: str) -> List[Video]:
    """Cache video data for 128 unique channel queries."""
    with open(f'data/youtube/{channel}/youtube_videos.json') as f:
        return json.load(f)
```

3. **Client-Side Filtering:**
```javascript
// Filter in browser for instant response (<200ms)
const filtered = videos.filter(v =>
    v.channel === selectedChannel &&
    v.title.includes(searchQuery)
);
```

4. **Pagination:**
```python
# Display 48 items per page (configurable)
items_per_page = user_preferences.get('items_per_page', 48)
page_data = all_items[offset:offset+items_per_page]
```

### ETL Performance

**Current State:**
- Single pipeline: ~2-5 minutes
- All 50+ pipelines: ~2 hours sequential

**Optimization Strategies:**

1. **Batch Processing:**
```python
def process_batch(items: List[Dict], batch_size: int = 100):
    """Process items in batches to manage memory."""
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        yield transform_batch(batch)
```

2. **Parallel Execution (Future):**
```bash
# Run independent ETLs in parallel
python src/etl/arxiv/arxiv_etl.py &
python src/etl/news/news_etl.py &
wait
```

3. **Incremental Updates:**
```python
# Only fetch new items since last run
last_run = load_checkpoint()
new_items = fetch_since(last_run.timestamp)
```

### Database Performance

**SQLite Optimization:**
```sql
-- Indexes for common queries
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_preferences_user_id ON preferences(user_id);
CREATE INDEX idx_alert_rules_user_id ON alert_rules(user_id);

-- PRAGMA settings for performance
PRAGMA journal_mode = WAL;  -- Write-Ahead Logging for concurrency
PRAGMA synchronous = NORMAL;  -- Balance safety vs performance
PRAGMA cache_size = -64000;  -- 64MB cache
```

**Connection Pooling (if using SQLAlchemy):**
```python
from sqlalchemy import create_engine

engine = create_engine(
    'sqlite:///data/megalith.db',
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

---

## Deployment Architecture

### Docker Container Structure

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Copy project files
WORKDIR /app
COPY . /app

# Install Python dependencies
RUN uv sync --all-extras

# Install Playwright browsers
RUN uv run playwright install --with-deps chromium

# Create data directories
RUN mkdir -p data/shared data/users data/metrics data/watchers logs

# Expose ports
EXPOSE 7780 8000

# Start both services
CMD ["./start.sh"]
```

**start.sh:**
```bash
#!/bin/bash
set -e

# Start FastAPI (Epic 9)
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &

# Start Dash dashboard
uv run waitress-serve --host=0.0.0.0 --port=7780 run_watchtower_dashboard:server &

# Wait for both processes
wait
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  watchtower:
    build: .
    container_name: megalith
    ports:
      - "7780:7780"  # Dashboard
      - "8000:8000"  # API
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./.env:/app/.env
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

### UnRAID Deployment

**Current Setup:**
- Docker container deployment
- Data persistence via volume mounts
- Port mapping: 7780 (dashboard), 8000 (API - future)

**Environment Variables:**
```bash
# .env file (not committed)
DATABASE_PATH=data/megalith.db
TELEGRAM_BOT_TOKEN=your_bot_token_here
SECRET_KEY=your_flask_secret_key_here
```

### Production Checklist

**Security:**
- [ ] HTTPS enabled (reverse proxy)
- [ ] Secure cookie flags set
- [ ] Environment variables configured
- [ ] Database file permissions set (600)
- [ ] API rate limiting enabled

**Performance:**
- [ ] Waitress/Uvicorn configured for production
- [ ] SQLite WAL mode enabled
- [ ] Log rotation configured
- [ ] Caching enabled

**Monitoring:**
- [ ] Health check endpoints responding
- [ ] Metrics collection active
- [ ] Log aggregation configured
- [ ] Backup strategy implemented

---

## Development Environment

### Prerequisites

**System Requirements:**
- Python 3.10+
- UV package manager (recommended) or pip/venv
- Git
- Docker (for containerized deployment)

**Operating System Support:**
- Linux (Ubuntu 20.04+, Debian 11+)
- macOS (11+)
- Windows 10+

### Setup Commands

**Using UV (Recommended):**
```bash
# Clone repository
git clone https://github.com/josmerod/watchtower.git
cd watchtower

# Install dependencies
uv sync --all-extras

# Install Playwright browsers
uv run playwright install

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
uv run python src/scripts/init_database.py

# Run dashboard
uv run python run_watchtower_dashboard.py

# Run all ETL pipelines
./run_all_etl.sh  # Linux/Mac
.\run_all_etl.bat  # Windows
```

**Using pip/venv:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
playwright install

# Same steps as above for .env, database, running
```

### Development Workflow

**Running Services:**
```bash
# Dashboard only (development mode)
uv run python run_watchtower_dashboard.py

# FastAPI only (when implementing Epic 9)
uv run uvicorn src.api.main:app --reload --port 8000

# Both services (production-like)
docker-compose up
```

**Running Tests:**
```bash
# All tests
uv run pytest

# Specific test category
uv run pytest tests/etl/
uv run pytest tests/models/

# With coverage
uv run pytest --cov=src --cov-report=html --cov-report=term
```

**Code Quality:**
```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy src/
```

**ETL Development:**
```bash
# Run single ETL pipeline
uv run python src/etl/arxiv/arxiv_etl.py

# Run with profiling (Epic 7)
uv run python -m cProfile -o profile.stats src/etl/arxiv/arxiv_etl.py

# Generate new ETL scaffold (Epic 6)
uv run python src/scripts/new_source.py --name crypto_news --type rss
```

---

## Architecture Decision Records (ADRs)

### ADR-001: SQLite for User Management

**Context**: Epic 5 requires multi-user support with authentication, session management, and user preferences. Need to choose between file-based storage (consistent with existing architecture) vs. database.

**Decision**: Use SQLite for user management, keep file-based JSON for data sources.

**Rationale:**
- User operations require ACID transactions (auth, sessions)
- SQLite handles 10-20 users with 1-3 concurrent easily
- No server overhead (embedded database)
- Migration path to PostgreSQL if scale exceeds expectations
- Keeps existing file-based ETL architecture untouched

**Consequences:**
- Hybrid architecture (SQLite + JSON files)
- Need database migration tooling
- Introduces SQLAlchemy or raw sqlite3 dependency

**Status**: Accepted

---

### ADR-002: Flask-Login for Authentication

**Context**: Multi-user system needs secure authentication. Options: custom auth (full control) vs. Flask-Login (battle-tested library).

**Decision**: Use Flask-Login for session management and authentication.

**Rationale:**
- Security-critical code should not be DIY
- Flask-Login is industry standard (13+ years, millions of deployments)
- Seamless Dash integration (Dash runs on Flask)
- Handles sessions, remember-me, CSRF protection automatically
- Time-to-market: focus on features, not building auth from scratch

**Consequences:**
- Adds flask-login dependency
- Requires bcrypt for password hashing
- Must follow Flask-Login patterns for protected routes

**Status**: Accepted

---

### ADR-003: Telegram Bot API for Notifications

**Context**: Epic 3 requires real-time alerts. Options: email (SMTP/Resend), browser notifications (WebSockets/polling), Telegram.

**Decision**: Use Telegram Bot API for instant alerts, 60-second polling for dashboard updates.

**Rationale:**
- **User preference**: Explicit request for Telegram over email
- Instant delivery (better than email or 60s polling)
- Free and unlimited (no rate limits or costs)
- Rich notifications (formatted messages, links, inline buttons)
- Simple API with excellent Python library (python-telegram-bot)
- Tech-savvy users already have Telegram

**Consequences:**
- Users must link Telegram account to Megalith profile
- Requires Telegram bot setup via @BotFather
- Email digests (Epic 9.6) still need SMTP later

**Status**: Accepted

---

### ADR-004: FastAPI for REST API

**Context**: Epic 9 requires REST API for external integrations, browser extension, webhooks. Options: extend Dash with Flask routes, Flask-RESTX, or FastAPI.

**Decision**: Use FastAPI as separate service (port 8000), run alongside Dash (port 7780) in same Docker container.

**Rationale:**
- Auto-generated OpenAPI/Swagger documentation (Epic 9.5 requirement)
- Pydantic integration (reuse existing models)
- Modern, async-capable for future scale
- Clean separation of concerns (dashboard vs. API)
- Light usage expected - no need for complex infrastructure
- Single container deployment keeps complexity manageable

**Consequences:**
- Two services to manage (Dash + FastAPI)
- Need reverse proxy or expose both ports
- Slightly more complex deployment (mitigated by Docker)

**Status**: Accepted

---

### ADR-005: Client-Side Search Initially

**Context**: Story 1.3 requires full-text search. Options: client-side filtering, PostgreSQL FTS, Elasticsearch.

**Decision**: Start with client-side JavaScript filtering, migrate to PostgreSQL FTS if data exceeds 100K items.

**Rationale:**
- Current scale: 10K items per tab - client-side is instant (<1 second)
- Zero infrastructure (no search server needed)
- Simple implementation (Array.filter in JavaScript)
- Migration path exists if scale demands it
- Boring technology: works today, upgrade only if needed

**Consequences:**
- Performance degrades if data grows beyond 100K items
- Limited to simple substring/keyword matching
- No advanced features (fuzzy search, relevance ranking) initially

**Status**: Accepted

---

### ADR-006: LRU Cache for Performance

**Context**: Epic 7 requires dashboard performance optimization (2s → 1s load time). Options: Redis cache, in-memory cache, file-based cache, @lru_cache.

**Decision**: Use Python's built-in @lru_cache decorator for function-level caching.

**Rationale:**
- Zero configuration (built-in Python)
- Perfect for function memoization (load_videos, load_papers)
- No external dependencies
- Sufficient for 10-20 concurrent users
- Can add Redis later if cross-process caching needed

**Consequences:**
- Cache lost on application restart
- Per-process cache (not shared across workers)
- Need to manage cache invalidation (TTL or manual)

**Status**: Accepted

---

### ADR-007: Enhanced Keywords for NLP Classification

**Context**: Epic 4 improves NLP classification for better categorization. Options: spaCy (heavy models), NLTK (lighter), enhanced keyword approach.

**Decision**: Enhance existing keyword-based classification with regex patterns and confidence scoring, defer spaCy unless accuracy becomes critical.

**Rationale:**
- Low resource usage (no 100MB+ models to load)
- Existing keyword approach works reasonably well
- Improvements possible without heavy dependencies (regex, better keyword lists, confidence scores)
- Can add spaCy later if accuracy demands it

**Consequences:**
- Limited accuracy vs. ML-based approaches
- Manual keyword list maintenance
- No contextual understanding

**Status**: Accepted

---

## Appendix: Technology Versions

**As of January 2025** (verify during implementation):

| Technology | Version | Notes |
|------------|---------|-------|
| Python | 3.10+ | Existing requirement |
| UV | 0.1.x | Existing package manager |
| Dash | 2.14.x | Verify latest stable |
| dash-bootstrap-components | 1.5.x | Verify latest |
| Plotly | 5.18.x | Bundled with Dash |
| FastAPI | 0.110.x | Verify latest stable |
| Uvicorn | 0.27.x | ASGI server for FastAPI |
| Waitress | 3.0.x | WSGI server for Dash |
| Flask-Login | 0.6.x | Verify latest stable |
| bcrypt | 4.1.x | Password hashing |
| python-telegram-bot | 20.x | Verify latest v20 |
| Pydantic | 2.5.x | Existing v2 |
| pydantic-settings | 2.1.x | Config management |
| SQLAlchemy | 2.0.x | If using ORM (optional) |
| Pandas | 2.1.x | Existing |
| Polars | 0.20.x | Existing |
| Playwright | 1.41.x | Existing |
| BeautifulSoup4 | 4.12.x | Existing |
| Requests | 2.31.x | Existing |
| cloudscraper | 1.2.x | Existing |
| pytest | 8.0.x | Testing |
| pytest-cov | 4.1.x | Coverage |
| Ruff | 0.2.x | Linting/formatting |
| mypy | 1.8.x | Type checking |

---

**End of Architecture Document**

_Generated by BMAD Decision Architecture Workflow v1.3.2_
_Date: 2025-01-14_
_For: Joshi_
_Agent: Winston (Architect)_
