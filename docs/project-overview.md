# Watchtower Project Overview

**Project Name:** Watchtower (also known as MEGALITH)
**Type:** Data Processing & ETL Platform
**Architecture:** Python Monolith with Modular Components
**Primary Language:** Python 3.10+
**Package Manager:** UV (recommended) / pip + venv

**Generated:** 2025-01-11
**Documentation Version:** 2.1 (BMM Document-Project Scan)

---

## Executive Summary

Watchtower is a sophisticated **data intelligence and monitoring platform** that aggregates, processes, and visualizes information from 50+ diverse sources including research papers, news feeds, games, courses, AI platforms, and social media. Built on a robust ETL framework with real-time monitoring capabilities, it provides comprehensive insights through dual interactive dashboards.

**Key Differentiators:**
- 🔄 **20+ Production ETL Pipelines** across diverse domains
- 📊 **21 Validated Pydantic Data Models** with runtime validation
- 👀 **Event-Driven Watcher System** for continuous monitoring
- 🌐 **Dual Dashboard Architecture** (Dash primary, Streamlit legacy)
- 📚 **50+ Data Sources** with automated aggregation
- ⚡ **High Performance** with UV package manager (10-100x faster)

---

## Quick Reference

### Project Statistics

| Metric | Value |
|--------|-------|
| **Total Lines of Code** | ~50,000+ |
| **Python Files** | 200+ |
| **ETL Pipelines** | 20+ domains |
| **Data Models** | 21 (15 domain + 6 base) |
| **Dashboard Tabs** | 15+ |
| **Data Sources** | 50+ platforms |
| **Test Coverage** | Target ≥80% |
| **Documentation Pages** | 20+ guides |

### Technology Stack Summary

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.10+ |
| **Package Manager** | UV (primary), pip/venv (fallback) |
| **Data Processing** | pandas ≥2.2.3, polars ≥0.20.0, numpy ≥2.2.5 |
| **Validation** | Pydantic ≥2.11.5 |
| **Web Scraping** | Playwright ≥1.51.0, BeautifulSoup4 ≥4.13.3 |
| **Dashboards** | Dash ≥2.0.0 (primary), Streamlit ≥1.45.0 (legacy) |
| **Visualization** | Plotly ≥5.0.0, Altair ≥5.5.0 |
| **NLP** | NLTK ≥3.9.1, scikit-learn ≥1.6.1 |
| **Testing** | pytest ≥7.0, pytest-cov ≥4.1.0 |
| **Code Quality** | ruff ≥0.2.0, mypy ≥1.7.0, black ≥24.1.0 |
| **Containers** | Docker, Docker Compose |

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Watchtower Platform                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Data Sources │ ───▶ │ ETL Pipeline │ ───▶ │ JSON Storage │
│   (50+)      │      │  Framework   │      │  (data/)     │
└──────────────┘      └──────────────┘      └──────────────┘
                             │                      │
                             │                      │
                             ▼                      ▼
                      ┌─────────────┐      ┌──────────────┐
                      │  Watchers   │      │  Dashboards  │
                      │  (Monitor)  │      │  (Visualize) │
                      └─────────────┘      └──────────────┘
                             │                      │
                             ▼                      ▼
                      ┌──────────────────────────────────┐
                      │     Pydantic Data Models         │
                      │   (Runtime Validation)           │
                      └──────────────────────────────────┘
```

### Core Components

#### 1. **ETL Framework** (`src/etl/`)

**Pattern:** Template Method + Metrics Collection

**BaseETL Lifecycle:**
```python
run() → extract() → transform() → load() → metrics.report()
```

**Features:**
- Checkpoint system for resumable operations
- Retry mechanisms with exponential backoff
- Batch processing for memory efficiency
- Built-in metrics collection (ETLMetrics model)
- Automatic timestamped outputs

**Domains:**
- Research: ArXiv, ADHD publications
- News: HackerNews, Reddit, Medium, DEV
- Games: Steam, Epic, Humble Bundle
- Courses: Udemy, Coursera, Microsoft, Cloud providers
- AI: GitHub, OpenAI, Anthropic, HuggingFace
- Entertainment: Anime, Cinema, Museums
- Local: Valencia events, Spanish public aid

#### 2. **Data Models** (`src/models/`)

**Pattern:** Pydantic BaseModel Hierarchy

**Base Classes:**
- `BaseModel` - Core Pydantic configuration
- `TimestampedModel` - Adds id, created_at, updated_at
- `StatusModel` - Operation status tracking
- `ErrorModel` - Structured error information
- `PaginationModel` - Pagination support

**Domain Models:** 15 specialized models covering all data sources

**Validation:**
- Runtime type validation
- Field constraints (min/max, regex patterns)
- Custom validators (@field_validator)
- Computed fields (@computed_field)

#### 3. **Watcher System** (`src/watchers/`)

**Pattern:** Observer + State Persistence

**BaseWatcher Lifecycle:**
```python
loop:
    current_value = get_current_value()
    if check_for_changes(current_value):
        log_event(changes)
    persist_state()
    sleep(interval)
```

**Features:**
- State persistence in `data/watchers/{name}/state.json`
- Event logging to `data/watchers/{name}/events/`
- Configurable polling intervals (default: 1 hour)
- Automatic directory creation

#### 4. **Dashboard System** (`src/web/`)

**Primary: Dash Dashboard** (Port 7777)
- Tab-based modular architecture
- VideoManager pattern for data handling
- Single callback pattern (prevents conflicts)
- Bootstrap UI with mobile responsiveness
- Health API endpoints (`/health`, `/metrics`)

**Legacy: Streamlit Dashboard** (Port 8501)
- Maintained for compatibility
- Simpler component structure

**Key Patterns:**
- Component-based tabs
- Data manager classes per domain
- Efficient JSON file reading with caching
- Error boundaries for graceful degradation

#### 5. **Data Storage** (`data/`)

**Pattern:** File-based JSON Storage

**Advantages:**
- No database setup required
- Fast read operations (pandas/polars)
- Easy backup and version control
- Human-readable format

**Structure:**
```
data/
├── {domain}/
│   └── {etl_name}_{timestamp}.json
└── watchers/
    └── {watcher_name}/
        ├── state.json
        └── events/
```

---

## Architecture Patterns

### Design Patterns in Use

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Template Method** | `src/etl/base.py` | ETL lifecycle orchestration |
| **Observer** | `src/watchers/base_watcher.py` | Event-driven monitoring |
| **Factory** | `src/config/settings.py` | Configuration creation |
| **Manager** | `src/web/dashboard/components/` | Data handling |
| **Repository** | `data/` directories | Data persistence |

### SOLID Principles Application

✅ **Single Responsibility**: Each ETL handles one domain, each model one entity
✅ **Open/Closed**: BaseETL extensible without modification
✅ **Liskov Substitution**: All ETLs interchangeable via BaseETL interface
✅ **Interface Segregation**: Minimal interfaces (extract, transform, load)
✅ **Dependency Inversion**: Depend on BaseETL/BaseWatcher abstractions

---

## Data Flow

### ETL Pipeline Flow

```
1. External API/RSS Feed
   ↓
2. ETL.extract() - Fetch raw data
   ↓
3. ETL.transform() - Clean, validate, classify
   ↓
4. Pydantic Model Validation
   ↓
5. ETL.load() - Write JSON to data/{domain}/
   ↓
6. Dashboard reads JSON → Display in UI
```

### Watcher Flow

```
1. BaseWatcher.get_current_value()
   ↓
2. Compare with previous state
   ↓
3. If changed:
   - Log event to data/watchers/{name}/events/
   - Update state.json
   - (Optional) Trigger notification
```

---

## Project Structure

### Repository Type: **Monolith**

Single cohesive codebase with clear module separation.

**Benefits:**
- Simplified deployment
- Shared utilities and models
- Consistent patterns across domains
- Easy code reuse

**Organization:**
```
src/
├── etl/          # Data pipelines (20+ domains)
├── models/       # Data models (21 models)
├── watchers/     # Monitoring system
├── web/          # Dashboards (Dash + Streamlit)
├── analytics/    # Data analysis
├── miners/       # Advanced mining tools
├── config/       # Configuration management
├── utils/        # Shared utilities
├── database/     # Database integration (future)
├── exceptions/   # Custom exceptions
└── launcher/     # Application launcher
```

---

## Development Workflow

### Getting Started

```bash
# 1. Clone repository
git clone <repository-url>
cd watchtower

# 2. Install dependencies (UV - recommended)
uv sync --all-extras

# 3. Install Playwright browsers
uv run playwright install

# 4. Configure environment
cp .env.template .env
# Edit .env with your API keys

# 5. Run ETL pipelines
./run_all_etl.sh          # Linux/Mac
.\run_all_etl.bat         # Windows

# 6. Launch dashboard
uv run python run_watchtower_dashboard.py
# Visit: http://localhost:7777
```

### Development Commands

```bash
# Run specific ETL
uv run python src/etl/arxiv/arxiv_etl.py

# Run watcher
uv run python src/watchers/run_watcher.py arxiv_watcher

# Run tests
uv run pytest --cov=src --cov-report=html

# Code quality
uv run ruff check .
uv run ruff format .
uv run mypy src/

# Type checking
uv run mypy src/
```

### Testing Strategy

**Test Pyramid:**
- **Unit Tests** (70%): Individual functions, model validation
- **Integration Tests** (20%): ETL workflows, data flow
- **E2E Tests** (10%): Dashboard interactions, full workflows

**Coverage Target:** ≥80% for src/

**Test Locations:**
- `Tests/unit/` - Unit tests
- `Tests/integration/` - Integration tests
- `Tests/etl/` - ETL-specific tests
- `Tests/models/` - Model validation tests
- `Tests/web/` - Dashboard tests
- `Tests/performance/` - Performance tests

---

## Deployment Options

### Local Development
```bash
# Dashboard only
uv run python run_watchtower_dashboard.py

# With ETL execution
./run_all_etl_and_dashboard.sh
```

### Docker Deployment
```bash
# Build and run
docker-compose up -d

# Development mode
docker-compose -f docker-compose.dev.yml up

# Enhanced configuration
docker-compose -f docker-compose.enhanced.yml up
```

### Production Deployment

**Linux:**
```bash
./deploy_linux.sh
```

**macOS:**
```bash
./deploy_mac.sh
```

**Windows:**
```cmd
deploy_windows.bat
```

**Systemd Service (Linux):**
See `docs/technical/WATCHERS_GUIDE.md` for systemd configuration

**Windows Task Scheduler:**
See `docs/technical/WATCHERS_GUIDE.md` for Windows scheduling

---

## Security & Best Practices

### Environment Variables

All sensitive data stored in `.env` (gitignored):
- API keys (OpenAI, Anthropic, GitHub, etc.)
- Database credentials (if used)
- Configuration secrets

**Template:** `.env.template`

### Input Validation

- All external data validated through Pydantic models
- Runtime type checking
- Field constraints (min/max, regex)
- Custom validators for complex logic

### Error Handling

- Custom exception hierarchy in `src/exceptions/`
- Structured error logging
- Graceful degradation in dashboards
- Error context preservation

### Code Quality

- **Linting:** ruff with Google-style docstrings
- **Type Checking:** mypy with strict configuration
- **Formatting:** black (via ruff format)
- **Pre-commit Hooks:** `.pre-commit-config.yaml`

---

## Performance Characteristics

### ETL Performance

| Pipeline | Typical Runtime | Data Volume |
|----------|----------------|-------------|
| ArXiv | 2-5 minutes | ~100-500 papers |
| News Aggregation | 5-10 minutes | ~1000-2000 articles |
| Games | 3-7 minutes | ~500-1000 deals |
| Courses | 2-5 minutes | ~200-500 courses |
| Full Run | 30-60 minutes | All sources |

### Dashboard Performance

| Metric | Value |
|--------|-------|
| **Load Time** | <2s (initial load) |
| **Tab Switch** | <500ms |
| **Data Refresh** | <1s |
| **Concurrent Users** | ~50-100 (tested) |

### Optimization Strategies

- Lazy loading of dashboard components
- JSON file caching with TTL
- Batch processing in ETL pipelines
- Efficient pandas/polars operations
- UV package manager for fast installs

---

## Monitoring & Observability

### Health Checks

**Dashboard Health API:**
- `GET /health` - System health status
- `GET /metrics` - Performance metrics

### Logging

**Structured Logging:**
- Component-specific loggers
- Timestamped entries
- Error context preservation
- Performance metrics

**Log Location:** `logs/` directory

### Metrics Collection

**ETL Metrics** (`ETLMetrics` model):
- Execution duration
- Records processed
- Success/failure counts
- Error rates
- Retry attempts

---

## Extensibility

### Adding New ETL Pipeline

1. **Create Model:** `src/models/{domain}.py`
2. **Create ETL:** `src/etl/{domain}/{etl_name}.py`
3. **Extend BaseETL:** Implement `extract()`, `transform()`, `load()`
4. **Add Tests:** `Tests/etl/test_{domain}.py`
5. **Add Dashboard Tab:** `src/web/dashboard/components/{domain}_tab.py`

### Adding New Watcher

1. **Create Watcher:** `src/watchers/{domain}_watcher.py`
2. **Extend BaseWatcher:** Implement `get_current_value()`, `check_for_changes()`
3. **Run:** `uv run python src/watchers/run_watcher.py {domain}_watcher`

### Adding Dashboard Component

1. **Create Tab:** `src/web/dashboard/components/{name}_tab.py`
2. **Create Manager:** Data manager class for data loading
3. **Register Tab:** Add to dashboard app routing
4. **Test:** Verify single callback pattern compliance

---

## Known Limitations & Future Enhancements

### Current Limitations

- File-based storage (no database)
- Single-machine deployment
- No real-time streaming (polling-based watchers)
- No multi-user authentication

### Planned Enhancements

- Database integration (PostgreSQL, TimescaleDB)
- Distributed task queue (Celery, Redis)
- Real-time streaming (WebSockets)
- Multi-user authentication (OAuth)
- API layer (FastAPI)
- Enhanced ML features (LangGraph, ChromaDB)

**See:** `docs/future/brainstorm-ideas.md` for detailed roadmap

---

## Related Documentation

### Core Documentation
- [Data Models Reference](./data-models-main.md) - Complete model documentation
- [Source Tree Analysis](./source-tree-analysis.md) - Directory structure guide
- [Architecture Overview](./technical/ARCHITECTURE_OVERVIEW.md) - Detailed architecture

### Technical Guides
- [ETL Development Guide](./technical/ETL_DEVELOPMENT_GUIDE.md) - ETL patterns
- [Watchers Guide](./technical/WATCHERS_GUIDE.md) - Monitoring system
- [Dashboard Development Guide](./technical/DASHBOARD_DEVELOPMENT_GUIDE.md) - UI development
- [Configuration Guide](./technical/CONFIGURATION_GUIDE.md) - Settings management

### Operational Guides
- [Quickstart Guide](./QUICKSTART.md) - Get started in 10 minutes
- [Deployment Guide](./technical/DEPLOYMENT_GUIDE.md) - Deployment options
- [Advanced Deployment Guide](./technical/ADVANCED_DEPLOYMENT_GUIDE.md) - Production deployment

### Community
- [Contributing Guide](./CONTRIBUTING.md) - How to contribute
- [FAQ](./FAQ.md) - Frequently asked questions

---

## Support & Contact

- **Issues:** GitHub Issues (when repository is public)
- **Documentation:** This directory (`docs/`)
- **Main README:** `../README.md`

---

**Last Updated:** 2025-01-11
**Version:** 2.1
**Maintained By:** Watchtower Development Team
