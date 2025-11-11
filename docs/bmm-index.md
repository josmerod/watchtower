# Watchtower Documentation Index

**Primary AI Retrieval Source for Claude Code and AI-Assisted Development**

**Project:** Watchtower (MEGALITH)
**Type:** Data Processing & ETL Platform
**Generated:** 2025-01-11
**Documentation Version:** 2.1 (BMM Document-Project Workflow)

---

## 🎯 Quick Reference

### Project Overview

- **Name:** Watchtower (also known as MEGALITH)
- **Type:** Python Monolith - Data Processing & ETL Platform
- **Language:** Python 3.10+
- **Package Manager:** UV (recommended) / pip + venv
- **Architecture Pattern:** Template Method (ETL) + Observer (Watchers) + Factory (Config)

### Key Statistics

| Metric | Value |
|--------|-------|
| **ETL Pipelines** | 20+ production domains |
| **Data Models** | 21 total (15 domain + 6 base) |
| **Data Sources** | 50+ platforms |
| **Dashboard Tabs** | 15+ interactive components |
| **Python Files** | 200+ |
| **Test Coverage Target** | ≥80% |
| **Documentation Pages** | 20+ comprehensive guides |

### Tech Stack at a Glance

| Category | Primary Technologies |
|----------|---------------------|
| **Core** | Python 3.10+, UV, Pydantic 2.11.5+ |
| **Data** | pandas 2.2.3+, polars 0.20.0+, numpy 2.2.5+ |
| **Web** | Dash 2.0+, Streamlit 1.45+, Plotly 5.0+ |
| **Scraping** | Playwright 1.51+, BeautifulSoup4 4.13+ |
| **Quality** | ruff, mypy, black, pytest |

---

## 📚 Generated Documentation (This Scan)

### Core Reference Documents

1. **[Project Overview](./project-overview.md)** ⭐ **START HERE**
   - Executive summary and project statistics
   - High-level architecture and design patterns
   - Technology stack details
   - Development workflow and commands
   - Deployment options
   - Security and best practices

2. **[Data Models Reference](./data-models-main.md)** 📊
   - Complete Pydantic model documentation (21 models)
   - Base model hierarchy (BaseModel, TimestampedModel, etc.)
   - 15 domain-specific models (ArXiv, Games, News, Courses, etc.)
   - Validation patterns and best practices
   - Data storage patterns
   - Migration strategy

3. **[Source Tree Analysis](./source-tree-analysis.md)** 🗂️
   - Annotated directory structure (50+ directories)
   - Critical paths explained (etl/, models/, watchers/, web/)
   - Entry points for all components
   - Integration points between modules
   - Navigation guide for common tasks

---

## 📖 Existing Documentation

### Getting Started

- **[Quickstart Guide](./QUICKSTART.md)** ⚡
  - Get up and running in 10 minutes
  - Installation with UV or pip
  - First ETL execution
  - Dashboard launch

- **[FAQ](./FAQ.md)**
  - Frequently asked questions
  - Common troubleshooting
  - Best practices

### Technical Documentation

#### Architecture & Design

- **[Architecture Overview](./technical/ARCHITECTURE_OVERVIEW.md)** 🏗️
  - System architecture and design principles
  - Component interactions and data flow
  - Design patterns in use
  - SOLID principles application

#### Core Components

- **[ETL Development Guide](./technical/ETL_DEVELOPMENT_GUIDE.md)** 🔄
  - BaseETL template method pattern
  - Creating custom ETL pipelines
  - Metrics collection and checkpointing
  - Retry mechanisms and error handling
  - ETL best practices

- **[Watchers Guide](./technical/WATCHERS_GUIDE.md)** 👀
  - BaseWatcher observer pattern
  - Complete watcher development documentation
  - State persistence and event logging
  - Advanced monitoring patterns
  - Deployment and scheduling (systemd, Windows Task Scheduler)

- **[Dashboard Development Guide](./technical/DASHBOARD_DEVELOPMENT_GUIDE.md)** 📊
  - Dash dashboard architecture (primary, port 7777)
  - Component-based tab system
  - VideoManager and data manager patterns
  - Single callback pattern (prevents conflicts)
  - Performance optimization
  - Bootstrap UI and mobile responsiveness

- **[Configuration Guide](./technical/CONFIGURATION_GUIDE.md)** ⚙️
  - Pydantic Settings system
  - Environment variable management
  - Nested configuration models
  - Auto-discovery patterns

### Deployment & Operations

- **[Deployment Guide](./technical/DEPLOYMENT_GUIDE.md)** 🚀
  - Local development setup
  - Docker deployment
  - Basic deployment strategies

- **[Advanced Deployment Guide](./technical/ADVANCED_DEPLOYMENT_GUIDE.md)** 🚢
  - Production deployment with Docker/Podman
  - Unraid server configuration
  - Systemd services
  - Performance tuning

### Community & Contributing

- **[Contributing Guide](./CONTRIBUTING.md)** 🤝
  - How to contribute to the project
  - Code style and conventions
  - PR process
  - Testing requirements

---

## 🗺️ Project Structure

### Repository Type: Monolith

Single cohesive codebase with modular organization.

```
watchtower/
├── src/                    # Main source code
│   ├── etl/               # ETL pipelines (20+ domains) ⭐
│   ├── models/            # Pydantic data models (21 models) ⭐
│   ├── watchers/          # Monitoring system ⭐
│   ├── web/               # Dashboards (Dash + Streamlit) ⭐
│   ├── analytics/         # Data analysis
│   ├── miners/            # Advanced mining tools
│   ├── config/            # Configuration management
│   ├── utils/             # Shared utilities
│   └── exceptions/        # Custom exceptions
│
├── data/                   # JSON data storage (50+ sources) ⭐
│   ├── arxiv/
│   ├── news/
│   ├── games/
│   ├── courses/
│   └── watchers/
│
├── docs/                   # Documentation ⭐
├── Tests/                  # Test suite
└── [config files]          # pyproject.toml, docker-compose.yml, etc.
```

**⭐ = Critical directories for development**

---

## 🔧 Development Quick Commands

### Setup

```bash
# UV (Recommended - 10-100x faster)
uv sync --all-extras
uv run playwright install

# Traditional pip/venv
pip install -r requirements.txt
playwright install
```

### Running ETLs

```bash
# All ETLs
./run_all_etl.sh              # Linux/Mac
.\run_all_etl.bat             # Windows

# Specific ETL
uv run python src/etl/arxiv/arxiv_etl.py
uv run python src/etl/news/news_get_ycombinator.py
```

### Dashboards

```bash
# Dash (Primary) - Port 7777
uv run python run_watchtower_dashboard.py

# Streamlit (Legacy) - Port 8501
uv run streamlit run src/web/fullstreamlit/app.py
```

### Watchers

```bash
# List watchers
uv run python src/watchers/run_watcher.py --list

# Run specific watcher
uv run python src/watchers/run_watcher.py arxiv_watcher

# Run once (no loop)
uv run python src/watchers/run_watcher.py arxiv_watcher --once
```

### Testing

```bash
# All tests with coverage
uv run pytest --cov=src --cov-report=html

# Specific test categories
uv run pytest Tests/etl/
uv run pytest Tests/models/
uv run pytest Tests/integration/
```

### Code Quality

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/
```

---

## 🎨 Architecture Patterns

### Design Patterns

| Pattern | Location | Purpose | Key Classes |
|---------|----------|---------|-------------|
| **Template Method** | `src/etl/base.py` | ETL lifecycle | `BaseETL` |
| **Observer** | `src/watchers/base_watcher.py` | Event monitoring | `BaseWatcher` |
| **Factory** | `src/config/settings.py` | Config creation | `get_settings()` |
| **Manager** | `src/web/dashboard/components/` | Data handling | `VideoManager`, etc. |
| **Repository** | `data/` directories | Data persistence | JSON files |

### Data Flow

```
External Source → ETL.extract() → ETL.transform() → Pydantic Validation
                                                           ↓
JSON Storage (data/) ← ETL.load()                     Model
                                                           ↓
Dashboard Components ← Read JSON ← Data Manager
```

---

## 📊 Data Models Summary

### Base Model Hierarchy

1. **BaseModel** - Core Pydantic configuration
2. **TimestampedModel** - Adds id, created_at, updated_at (most domain models extend this)
3. **StatusModel** - Operation status tracking
4. **ErrorModel** - Structured error information
5. **PaginationModel** - Pagination support
6. **PaginatedResponse** - Generic paginated response

### Domain Models (15 Total)

| Model | File | Purpose |
|-------|------|---------|
| `ArxivPaperModel` | `arxiv.py` | Research papers with TRL & commercial potential |
| `AnimeModel` | `anime.py` | MyAnimeList data |
| `NewsArticleModel` | `news.py` | Multi-source news aggregation |
| `GameDealModel` | `games.py` | Game deals with pricing |
| `CourseModel` | `course.py` | Course data from multiple platforms |
| `GitHubTrendingModel` | `github.py` | GitHub trending repositories |
| `GiveawayModel` | `giveaways.py` | Giveaways and free items |
| `SecurityAlertModel` | `security.py` | CVE tracking and security |
| `TechnologyModel` | `technology.py` | Technology trend analysis |
| `ADHDPublicationModel` | `adhd.py` | ADHD research papers |
| `SpanishPublicAidModel` | `spanish_public_aid.py` | Government aid programs |
| `EcommerceDealModel` | `ecommerce.py` | E-commerce deals |
| `EventModel` | `events.py` | Valencia events |
| `MuseumModel` | `museums.py` | Museum exhibitions |
| `GitHubRepositoryModel` | `arxiv.py` | GitHub repo metadata |

**See:** [Data Models Reference](./data-models-main.md) for complete documentation

---

## 🔄 ETL Pipelines Summary

### Active Pipelines (20+ Domains)

| Domain | Location | Output | Primary Models |
|--------|----------|--------|----------------|
| **ArXiv** | `src/etl/arxiv/` | `data/arxiv/` | `ArxivPaperModel` |
| **News** | `src/etl/news/` | `data/news/` | `NewsArticleModel` |
| **Games** | `src/etl/games/` | `data/games/` | `GameDealModel` |
| **Courses** | `src/etl/courses/` | `data/courses/` | `CourseModel` |
| **Anime** | `src/etl/anime/` | `data/anime/` | `AnimeModel` |
| **GitHub** | `src/etl/github/` | `data/github/` | `GitHubTrendingModel` |
| **AI Platforms** | `src/etl/ai_platforms/` | `data/ai_platforms/` | Various |
| **ADHD** | `src/etl/adhd/` | `data/adhd_publications/` | `ADHDPublicationModel` |
| **Giveaways** | `src/etl/giveaways/` | `data/giveaways/` | `GiveawayModel` |
| **Museums** | `src/etl/museums/` | `data/museums/` | `MuseumModel` |
| **Valencia Events** | `src/etl/news/valencia_events_etl.py` | `data/valencia_events/` | `EventModel` |
| **Spanish Aid** | `src/etl/spanish_public_aid/` | `data/spanish_public_aid/` | `SpanishPublicAidModel` |
| **4chan** | `src/etl/fourchan/` | `data/4chan_generals/` | Custom |
| **Deals** | `src/etl/deals/` | `data/deals/` | `EcommerceDealModel` |
| **Entertainment** | `src/etl/entertainment/` | `data/entertainment/` | Various |
| **Intelligence** | `src/etl/intelligence/` | `data/intelligence/` | Various |
| **Neurodivergent** | `src/etl/neurodivergent/` | `data/neurodivergent/` | Custom |
| **E-commerce** | `src/etl/ecommerce/` | `data/ecommerce/` | `EcommerceDealModel` |
| **Gold Digging** | `src/etl/goldigging/` | `data/goldigging/` | `CourseModel` |
| **Miners** | `src/miners/` | Various | Multiple |

**All ETLs extend `BaseETL`** from `src/etl/base.py`

---

## 🌐 Dashboard Components

### Dash Dashboard (Primary - Port 7777)

**Tab Components** (`src/web/dashboard/components/`):
- `videos_tab.py` - YouTube video browser (VideoManager, 48 videos/view)
- `courses_tab.py` - Course deals browser
- `games_tab.py` - Game deals tracker
- `news_tab.py` - News aggregation viewer
- `arxiv_tab.py` - Research papers explorer
- `anime_tab.py` - Anime listings
- [15+ total tabs]

**Key Patterns:**
- Single callback per output (prevents conflicts)
- Data manager classes for data loading
- Bootstrap UI with mobile responsiveness
- Error boundaries for graceful degradation

**Health Endpoints:**
- `GET /health` - System health status
- `GET /metrics` - Performance metrics

### Streamlit Dashboard (Legacy - Port 8501)

Maintained for compatibility, simpler component structure.

---

## 🔍 Common Development Tasks

### Adding New ETL Pipeline

**Steps:**
1. Create model: `src/models/{domain}.py` (extend `TimestampedModel`)
2. Create ETL: `src/etl/{domain}/{etl_name}.py` (extend `BaseETL`)
3. Implement methods: `extract()`, `transform()`, `load()`
4. Add tests: `Tests/etl/test_{domain}.py`
5. Add dashboard tab: `src/web/dashboard/components/{domain}_tab.py`

**Example:**
```python
from src.etl.base import BaseETL
from src.models.{domain} import {DomainModel}

class {Domain}ETL(BaseETL):
    def extract(self):
        # Fetch data from source
        pass

    def transform(self, raw_data):
        # Clean and validate
        return [DomainModel(**item) for item in raw_data]

    def load(self, data):
        # Write to data/{domain}/
        pass
```

### Adding New Watcher

**Steps:**
1. Create watcher: `src/watchers/{domain}_watcher.py` (extend `BaseWatcher`)
2. Implement: `get_current_value()`, `check_for_changes()`
3. Run: `uv run python src/watchers/run_watcher.py {domain}_watcher`

### Adding Dashboard Component

**Steps:**
1. Create tab: `src/web/dashboard/components/{name}_tab.py`
2. Create data manager class
3. Register tab in dashboard app
4. Follow single callback pattern

---

## 🧪 Testing Strategy

### Test Organization

```
Tests/
├── unit/           # Unit tests (70%)
├── integration/    # Integration tests (20%)
├── etl/           # ETL-specific tests
├── models/        # Model validation tests
├── web/           # Dashboard tests
└── performance/   # Performance tests (10%)
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific category
uv run pytest Tests/etl/ -v
uv run pytest Tests/models/ -v
```

**Coverage Target:** ≥80% for `src/`

---

## 🚀 Deployment Options

### Local Development

```bash
# Dashboard only
uv run python run_watchtower_dashboard.py

# ETL + Dashboard
./run_all_etl_and_dashboard.sh
```

### Docker

```bash
# Production
docker-compose up -d

# Development
docker-compose -f docker-compose.dev.yml up

# Enhanced
docker-compose -f docker-compose.enhanced.yml up
```

### Production Scripts

- **Linux:** `./deploy_linux.sh`
- **macOS:** `./deploy_mac.sh`
- **Windows:** `deploy_windows.bat`

---

## 🔐 Security & Configuration

### Environment Variables

Sensitive data in `.env` (gitignored):
- API keys (OpenAI, Anthropic, GitHub, etc.)
- Database credentials
- Configuration secrets

**Template:** `.env.template`

### Configuration Management

**Pydantic Settings** (`src/config/settings.py`):
- Environment variable support (`COMPONENT__SETTING` format)
- Auto-discovery of project root
- Nested configuration models
- Type validation

---

## 📈 Performance Characteristics

### ETL Performance

| Pipeline | Runtime | Data Volume |
|----------|---------|-------------|
| ArXiv | 2-5 min | 100-500 papers |
| News | 5-10 min | 1000-2000 articles |
| Games | 3-7 min | 500-1000 deals |
| Courses | 2-5 min | 200-500 courses |
| **Full Run** | **30-60 min** | **All sources** |

### Dashboard Performance

- **Load Time:** <2s (initial)
- **Tab Switch:** <500ms
- **Data Refresh:** <1s
- **Concurrent Users:** ~50-100 (tested)

---

## 🆘 Support & Resources

### Documentation

- **This Index:** Primary AI retrieval source
- **Project Overview:** `./project-overview.md`
- **Technical Guides:** `./technical/`
- **Main README:** `../README.md`

### Getting Help

- **FAQ:** `./FAQ.md`
- **Contributing:** `./CONTRIBUTING.md`
- **Issues:** GitHub Issues (when public)

### Key Files for Reference

- **Configuration:** `pyproject.toml`, `.env.template`
- **Entry Points:** `run_watchtower_dashboard.py`, `run_all_etl.sh`
- **Base Classes:** `src/etl/base.py`, `src/watchers/base_watcher.py`
- **Models:** `src/models/base.py`

---

## 📝 Document Status

### Generated Documentation (This Scan)

| Document | Status | Last Updated |
|----------|--------|--------------|
| **bmm-index.md** (this file) | ✅ Complete | 2025-01-11 |
| project-overview.md | ✅ Complete | 2025-01-11 |
| data-models-main.md | ✅ Complete | 2025-01-11 |
| source-tree-analysis.md | ✅ Complete | 2025-01-11 |

### Existing Documentation

| Document | Status | Notes |
|----------|--------|-------|
| Quickstart Guide | ✅ Complete | 2025-01-10 |
| Watchers Guide | ✅ Complete | 2025-01-10 |
| Architecture Overview | ✅ Complete | Previous |
| ETL Development Guide | ✅ Complete | Previous |
| Dashboard Development | ✅ Complete | Previous |
| Deployment Guide | ✅ Complete | Previous |
| Advanced Deployment | ✅ Complete | Previous |
| Configuration Guide | ✅ Complete | Previous |
| Contributing Guide | ✅ Complete | 2025-01-10 |
| FAQ | ✅ Complete | 2025-01-10 |

---

## 🎯 AI-Assisted Development Guide

**For Claude Code and AI Tools:**

1. **Start Here:** Read this index for project overview
2. **Architecture:** See [Project Overview](./project-overview.md) and [Architecture Overview](./technical/ARCHITECTURE_OVERVIEW.md)
3. **Data Models:** See [Data Models Reference](./data-models-main.md) for schema
4. **Directory Structure:** See [Source Tree Analysis](./source-tree-analysis.md) for navigation
5. **Specific Guides:** Use technical guides for ETL, Watchers, Dashboard development

**When implementing features:**
- Always extend appropriate base class (`BaseETL`, `TimestampedModel`, etc.)
- Follow existing patterns (see architecture docs)
- Use Pydantic for validation
- Write tests (target ≥80% coverage)
- Follow code quality standards (ruff, mypy)

**When troubleshooting:**
- Check logs in `logs/` directory
- Use health endpoints (`/health`, `/metrics`)
- Review ETL metrics in output JSON
- Check watcher state in `data/watchers/{name}/state.json`

---

**Last Updated:** 2025-01-11
**Documentation Version:** 2.1
**Primary Maintainer:** Claude Code (BMM Document-Project Workflow)
**For:** AI-Assisted Development with Watchtower Platform

---

**🧠 This index is optimized for AI retrieval and should be the first reference for any AI-assisted development work on the Watchtower project.**
