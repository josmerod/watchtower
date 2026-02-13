# Watchtower Source Tree Analysis

**Generated:** 2025-01-11
**Project Type:** Data Processing & ETL Platform
**Repository Type:** Monolith

---

## Project Overview

Watchtower is organized as a Python monolith with clear separation of concerns across functional domains. The architecture follows the Template Method pattern for ETL pipelines and Observer pattern for watchers.

---

## Annotated Directory Structure

```
watchtower/                          # 🏠 Project root
│
├── src/                             # 📦 Main source code directory
│   ├── etl/                         # 🔄 ETL Pipeline Framework (20+ domains)
│   │   ├── base.py                  # ⭐ BaseETL - Template Method pattern, metrics, checkpointing
│   │   ├── adhd/                    # 🧠 ADHD research papers from PubMed
│   │   ├── ai_platforms/            # 🤖 AI platform monitoring (OpenAI, Anthropic, HuggingFace)
│   │   ├── anime/                   # 📺 MyAnimeList data aggregation
│   │   ├── arxiv/                   # 📚 ArXiv research papers with NLP classification
│   │   ├── courses/                 # 🎓 Course deals (Coursera, DeepLearning.AI, Microsoft)
│   │   ├── deals/                   # 💰 Multi-platform deal aggregation
│   │   ├── ecommerce/               # 🛒 E-commerce deal tracking
│   │   ├── entertainment/           # 🎭 Cinema, meme economics
│   │   ├── fourchan/                # 📋 4chan general thread monitoring
│   │   ├── games/                   # 🎮 Game deals (Steam, Epic, Humble Bundle)
│   │   ├── github/                  # 🐙 GitHub trending repositories
│   │   ├── giveaways/               # 🎁 Free game and item giveaways
│   │   ├── goldigging/              # 🥇 Udemy course discovery and mining
│   │   ├── intelligence/            # 🔍 Advanced data analysis and insights
│   │   ├── museums/                 # 🏛️ Museum exhibitions and cultural events
│   │   ├── neurodivergent/          # 🧩 Neurodivergent-friendly locations
│   │   ├── news/                    # 📰 Multi-source news (HackerNews, Reddit, Medium, DEV)
│   │   │   ├── news_get_ycombinator.py
│   │   │   ├── reddit_unified_etl.py
│   │   │   ├── valencia_events_etl.py
│   │   │   └── ...
│   │   └── spanish_public_aid/      # 🇪🇸 Spanish government aid programs
│   │
│   ├── models/                      # 📊 Pydantic Data Models (21 models)
│   │   ├── base.py                  # ⭐ BaseModel, TimestampedModel, StatusModel, ErrorModel
│   │   ├── arxiv.py                 # ArxivPaperModel with TRL & commercial potential
│   │   ├── anime.py                 # AnimeModel from MyAnimeList
│   │   ├── games.py                 # GameDealModel with pricing
│   │   ├── news.py                  # NewsArticleModel for multi-source aggregation
│   │   ├── course.py                # CourseModel with platform support
│   │   ├── github.py                # GitHubTrendingModel
│   │   ├── security.py              # SecurityAlertModel with CVE tracking
│   │   ├── technology.py            # TechnologyModel with trend analysis
│   │   ├── adhd.py                  # ADHDPublicationModel
│   │   ├── spanish_public_aid.py    # SpanishPublicAidModel
│   │   ├── ecommerce.py             # EcommerceDealModel
│   │   ├── events.py                # EventModel for Valencia events
│   │   ├── giveaways.py             # GiveawayModel
│   │   └── museums.py               # MuseumModel
│   │
│   ├── watchers/                    # 👀 Monitoring & Event System
│   │   ├── base_watcher.py          # ⭐ BaseWatcher - Observer pattern, state persistence
│   │   ├── run_watcher.py           # Watcher orchestration CLI
│   │   └── [domain]_watcher.py      # Domain-specific watchers
│   │
│   ├── web/                         # 🌐 Dashboard & Visualization
│   │   ├── dashboard/               # 📊 Primary Dash dashboard (port 7780)
│   │   │   ├── app.py               # Main dashboard application
│   │   │   ├── components/          # Tab-based modular components
│   │   │   │   ├── videos_tab.py    # YouTube video browser (VideoManager pattern)
│   │   │   │   ├── courses_tab.py
│   │   │   │   ├── games_tab.py
│   │   │   │   ├── news_tab.py
│   │   │   │   └── ...
│   │   │   ├── assets/              # CSS, images, static files
│   │   │   └── utils.py             # Shared dashboard utilities
│   │   └── fullstreamlit/           # 📈 Legacy Streamlit dashboard (port 8501)
│   │       └── app.py               # Streamlit application
│   │
│   ├── analytics/                   # 📈 Data Analysis & Insights
│   │   ├── technology_adoption.py   # Technology trend analysis
│   │   ├── market_analysis.py       # Market and price analysis
│   │   └── performance_analytics.py # System performance monitoring
│   │
│   ├── miners/                      # ⛏️ Advanced Data Mining Tools
│   │   ├── udemy-universal/         # 🎓 Advanced Udemy course discovery & enrollment
│   │   ├── asf-winonly/             # 🎮 ArchiSteamFarm integration
│   │   └── crypto_sentiment/        # 💰 Cryptocurrency sentiment analysis
│   │
│   ├── config/                      # ⚙️ Configuration Management
│   │   ├── settings.py              # ⭐ Pydantic Settings with auto-discovery
│   │   └── models.py                # Configuration models (ETLConfig, WatcherConfig, etc.)
│   │
│   ├── utils/                       # 🔧 Shared Utilities
│   │   ├── nlp_classifier.py        # NLP content categorization
│   │   ├── file_system.py           # Project-wide path resolution
│   │   ├── logging.py               # Structured logging
│   │   ├── backup_utils.py          # Automated backup/recovery
│   │   └── github_utils.py          # Repository analysis
│   │
│   ├── database/                    # 💾 Database Integration (Future)
│   │   └── [planned features]
│   │
│   ├── exceptions/                  # ⚠️ Custom Exception Hierarchy
│   │   └── [domain-specific exceptions]
│   │
│   └── launcher/                    # 🚀 Application Launcher
│       └── [startup scripts]
│
├── data/                            # 💾 JSON Data Storage (50+ sources)
│   ├── arxiv/                       # Research papers
│   ├── anime/                       # Anime data
│   ├── news/                        # News articles from multiple sources
│   ├── games/                       # Game deals and free games
│   ├── courses/                     # Course data
│   ├── youtube/                     # YouTube video metadata
│   ├── github/                      # GitHub trending data
│   ├── adhd_publications/           # ADHD research papers
│   ├── spanish_public_aid/          # Government aid programs
│   ├── watchers/                    # Watcher state and events
│   │   └── [watcher_name]/
│   │       ├── state.json           # Watcher checkpoint
│   │       └── events/              # Change event logs
│   └── shortcuts/                   # Predefined shortcuts
│       └── predefined_shortcuts.json
│
├── docs/                            # 📚 Documentation
│   ├── INDEX.md                     # Documentation index
│   ├── QUICKSTART.md                # Quick start guide
│   ├── CONTRIBUTING.md              # Contribution guidelines
│   ├── FAQ.md                       # Frequently asked questions
│   ├── technical/                   # Technical documentation
│   │   ├── ARCHITECTURE_OVERVIEW.md
│   │   ├── ETL_DEVELOPMENT_GUIDE.md
│   │   ├── WATCHERS_GUIDE.md
│   │   ├── DASHBOARD_DEVELOPMENT_GUIDE.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── ADVANCED_DEPLOYMENT_GUIDE.md
│   │   └── CONFIGURATION_GUIDE.md
│   ├── data-models-main.md          # ⭐ Data models documentation (this scan)
│   └── future/                      # Future planning
│       └── brainstorm-ideas.md
│
├── Tests/                           # 🧪 Test Suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   ├── etl/                         # ETL-specific tests
│   ├── models/                      # Model validation tests
│   ├── web/                         # Dashboard tests
│   ├── performance/                 # Performance tests
│   ├── ETL_TEST_RESULTS.md          # Test results documentation
│   └── GAMES_VALIDATION_REPORT.md   # Games ETL validation
│
├── logs/                            # 📋 Application Logs
│   └── [timestamped log files]
│
├── config/                          # 🔧 Legacy Config Directory
│   └── [configuration files]
│
├── .bmad/                           # 🤖 BMad Method Framework
│   ├── bmm/                         # BMad Method workflows
│   └── core/                        # Core BMAD tasks
│
├── .venv/                           # 🐍 Python Virtual Environment (pip/venv)
├── .git/                            # 📜 Git Repository
├── .vscode/                         # 💻 VSCode Configuration
├── .cursor/                         # ✨ Cursor IDE Configuration
├── .claude/                         # 🧠 Claude Code Configuration
│   └── commands/                    # Custom slash commands
├── .continue/                       # 🔄 Continue.dev Configuration
├── .gemini/                         # ⚡ Gemini Configuration
│
├── pyproject.toml                   # ⭐ Python Project Configuration (UV/pip)
├── uv.lock                          # 🔒 UV dependency lock file
├── setup.py                         # 📦 Python package setup
├── .env                             # 🔐 Environment variables (gitignored)
├── .env.template                    # 📝 Environment template
├── Dockerfile                       # 🐳 Docker container definition
├── docker-compose.yml               # 🐳 Docker Compose orchestration
├── docker-compose.dev.yml           # 🐳 Development Docker Compose
├── docker-compose.enhanced.yml      # 🐳 Enhanced Docker Compose
│
├── run_watchtower_dashboard.py      # 🚀 Dash dashboard entry point
├── run_streamlit_app.py             # 🚀 Streamlit dashboard entry point
├── run_all_etl.sh                   # 🔄 Run all ETL pipelines (Linux/Mac)
├── run_all_etl.bat                  # 🔄 Run all ETL pipelines (Windows)
├── run_all_etl_and_dashboard.sh     # 🔄 Run ETL + dashboard (Linux/Mac)
├── run_all_etl_and_dashboard.bat    # 🔄 Run ETL + dashboard (Windows)
├── run_valencia_etls.py             # 🇪🇸 Valencia-specific ETLs
├── run_new_watchtower_etls.py       # 🆕 New ETL runner
│
├── install_watchtower.py            # 📥 Full installation script
├── install_dev.py                   # 📥 Development environment setup
├── validate_project.py              # ✅ Project validation script
│
├── deploy_linux.sh                  # 🚢 Linux deployment script
├── deploy_mac.sh                    # 🚢 macOS deployment script
├── deploy_windows.bat               # 🚢 Windows deployment script
│
├── README.md                        # 📖 Project README
├── CLAUDE.md                        # 🧠 Claude Code integration guide
├── CLAUDE_ENHANCED.md               # 🧠 Enhanced Claude instructions
├── DASHBOARD_OPTIMIZATION_PLAN.md   # 📊 Dashboard optimization plan
│
├── .gitignore                       # 🚫 Git ignore rules
├── .dockerignore                    # 🚫 Docker ignore rules
├── .cursorrules                     # ✨ Cursor IDE rules
├── .pre-commit-config.yaml          # ✅ Pre-commit hooks
└── .prefectignore                   # 🚫 Prefect ignore rules
```

---

## Critical Directories Explained

### 🔄 `src/etl/` - ETL Pipeline Framework

**Purpose:** Core data extraction, transformation, and loading pipelines

**Key Files:**
- `base.py` - **BaseETL** abstract class (Template Method pattern)
- **20+ domain-specific ETL modules** covering research, news, games, courses, etc.

**Architecture:**
- Template Method pattern: `extract() → transform() → load()`
- Built-in metrics collection (`ETLMetrics` model)
- Checkpoint system for resumable operations
- Retry mechanisms with exponential backoff
- Batch processing for memory efficiency

**Entry Points:**
- Individual ETL scripts: `uv run python src/etl/arxiv/arxiv_etl.py`
- Batch execution: `./run_all_etl.sh` or `.\run_all_etl.bat`

### 📊 `src/models/` - Pydantic Data Models

**Purpose:** Runtime type validation and data schemas

**Key Files:**
- `base.py` - Base model hierarchy (TimestampedModel, StatusModel, ErrorModel)
- **15 domain-specific models** for structured data

**Patterns:**
- All models extend `TimestampedModel` (automatic id, created_at, updated_at)
- Enumerations for controlled vocabularies
- Field validators for custom validation
- Computed fields for derived values

**Usage:**
```python
from src.models.arxiv import ArxivPaperModel

paper = ArxivPaperModel(title="...", authors=["..."], ...)
paper.model_dump()  # Serialize to dict
```

### 👀 `src/watchers/` - Monitoring System

**Purpose:** Event-driven monitoring with state persistence

**Key Files:**
- `base_watcher.py` - **BaseWatcher** abstract class (Observer pattern)
- `run_watcher.py` - Watcher orchestration CLI

**Architecture:**
- Observer pattern: `get_current_value() → check_for_changes() → log_event()`
- State persistence in `data/watchers/{name}/state.json`
- Event logging to `data/watchers/{name}/events/`
- Configurable polling intervals

**Entry Points:**
- Run specific watcher: `uv run python src/watchers/run_watcher.py arxiv_watcher`
- List watchers: `uv run python src/watchers/run_watcher.py --list`

### 🌐 `src/web/` - Dashboard System

**Purpose:** Data visualization and interactive dashboards

**Structure:**
- `dashboard/` - **Primary** Dash dashboard (port 7780)
  - Tab-based modular architecture
  - VideoManager pattern for data handling
  - Single callback pattern prevents conflicts
  - Bootstrap UI with mobile responsiveness
- `fullstreamlit/` - **Legacy** Streamlit dashboard (port 8501)

**Key Patterns:**
- Component-based tab system
- Data manager classes for each domain
- Efficient JSON file reading with caching
- Health API endpoints (`/health`, `/metrics`)

**Entry Points:**
- Dash: `uv run python run_watchtower_dashboard.py`
- Streamlit: `uv run streamlit run src/web/fullstreamlit/app.py`

### 📈 `src/analytics/` - Data Analysis

**Purpose:** Advanced data analysis and trend identification

**Features:**
- Technology adoption lifecycle tracking
- Market and price analysis algorithms
- Performance monitoring and optimization

### ⛏️ `src/miners/` - Advanced Mining Tools

**Purpose:** Specialized data mining with automation

**Components:**
- **udemy-universal** - Advanced course discovery and enrollment
- **asf-winonly** - ArchiSteamFarm integration for game collection
- **crypto_sentiment** - Multi-platform cryptocurrency sentiment

### ⚙️ `src/config/` - Configuration Management

**Purpose:** Centralized configuration with validation

**Key Files:**
- `settings.py` - Pydantic Settings with auto-discovery
- `models.py` - Configuration models (ETLConfig, WatcherConfig, DatabaseConfig)

**Features:**
- Environment variable support (double underscore delimiter)
- Automatic project root detection
- Type validation with Pydantic
- Nested configuration models

### 💾 `data/` - JSON Data Storage

**Purpose:** File-based data storage for all ETL outputs

**Structure:**
- One directory per ETL domain
- Timestamped outputs: `{etl_name}_{timestamp}.json`
- Latest symlinks or direct files
- Watcher state and event logs

**Advantages:**
- No database setup required
- Fast read operations with pandas/polars
- Easy backup and version control
- Human-readable JSON format

### 🧪 `Tests/` - Test Suite

**Purpose:** Comprehensive testing framework

**Categories:**
- `unit/` - Unit tests for individual functions
- `integration/` - Integration tests for ETL workflows
- `etl/` - ETL-specific tests
- `models/` - Pydantic model validation
- `web/` - Dashboard component tests
- `performance/` - Performance and load tests

**Entry Point:** `uv run pytest --cov=src --cov-report=html`

---

## Integration Points

### ETL → Data Storage

```
BaseETL.load() → JSON files → data/{etl_name}/ → Dashboard reads
```

### Watchers → Event Logs

```
BaseWatcher.check_for_changes() → Events → data/watchers/{name}/events/
```

### Dashboard → Data Storage

```
Tab components → Data managers → Read JSON → Display in UI
```

### Models → All Components

```
Pydantic models ← ETL, Watchers, Dashboard, Analytics
```

---

## Entry Points Summary

| Purpose | Entry Point | Port/Output |
|---------|-------------|-------------|
| **Dash Dashboard** | `run_watchtower_dashboard.py` | Port 7780 |
| **Streamlit Dashboard** | `run_streamlit_app.py` | Port 8501 |
| **All ETLs (Linux/Mac)** | `run_all_etl.sh` | `data/` directory |
| **All ETLs (Windows)** | `run_all_etl.bat` | `data/` directory |
| **Specific ETL** | `uv run python src/etl/{domain}/{etl}.py` | `data/{domain}/` |
| **Watcher** | `uv run python src/watchers/run_watcher.py {name}` | `data/watchers/{name}/` |
| **Tests** | `uv run pytest` | Test reports |
| **Validation** | `uv run python validate_project.py` | Console output |

---

## Navigation Guide

### For New Features (ETL)

1. **Create Model:** `src/models/{domain}.py` (extend `TimestampedModel`)
2. **Create ETL:** `src/etl/{domain}/{etl_name}.py` (extend `BaseETL`)
3. **Add Dashboard Tab:** `src/web/dashboard/components/{domain}_tab.py`
4. **Write Tests:** `Tests/etl/test_{domain}.py`

### For Data Analysis

1. **Read Data:** Load JSON from `data/{domain}/`
2. **Use Models:** Validate with Pydantic models
3. **Analyze:** Use pandas/polars for analysis
4. **Visualize:** Create Plotly charts in dashboard tabs

### For Monitoring

1. **Create Watcher:** `src/watchers/{domain}_watcher.py` (extend `BaseWatcher`)
2. **Implement Methods:** `get_current_value()`, `check_for_changes()`
3. **Run Watcher:** `uv run python src/watchers/run_watcher.py {domain}_watcher`

---

## Related Documentation

- [Data Models Reference](./data-models-main.md) - Complete model documentation
- [ETL Development Guide](./technical/ETL_DEVELOPMENT_GUIDE.md) - ETL patterns and best practices
- [Watchers Guide](./technical/WATCHERS_GUIDE.md) - Monitoring system documentation
- [Dashboard Development Guide](./technical/DASHBOARD_DEVELOPMENT_GUIDE.md) - UI development
- [Architecture Overview](./technical/ARCHITECTURE_OVERVIEW.md) - System architecture

---

**Last Updated:** 2025-01-11
**Total Directories:** 50+ (excluding node_modules, .venv, .git)
**Critical Paths:** etl/, models/, watchers/, web/, analytics/, miners/
**Data Sources:** 50+ domains in `data/` directory
