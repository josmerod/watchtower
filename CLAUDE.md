# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with the **Watchtower** (MEGALITH) project - a sophisticated data intelligence and monitoring platform.

## Project Overview

**Watchtower** is a comprehensive data intelligence platform that aggregates, processes, and monitors information from diverse sources including research papers, news feeds, games, courses, AI platforms, and social media. It follows a sophisticated ETL + Watcher + Dashboard architecture with advanced features like NLP classification, GitHub repository analysis, and real-time monitoring.

### Key Capabilities
- **Multi-source Data Aggregation**: 50+ different data sources including ArXiv, GitHub, Reddit, YouTube, game stores, course platforms
- **Advanced ETL Framework**: Template method pattern with metrics collection, checkpointing, and retry mechanisms
- **Real-time Monitoring**: Event-driven watchers with state persistence and change detection
- **Interactive Dashboards**: Dual dashboard system (Dash + legacy Streamlit) with modular tab architecture
- **NLP Classification**: Automated content categorization and trend analysis
- **Performance Optimization**: File-based JSON storage, caching, and efficient data loading

## Common Development Commands

### Package Management (UV - Recommended)
UV provides 10-100x faster dependency management compared to pip/venv:
```bash
# Install dependencies and set up virtual environment
uv sync --all-extras

# Install Playwright browsers
uv run playwright install

# Run any Python script
uv run python src/script.py

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/
```

### Alternative Commands (Legacy)
```bash
# Using pip/venv
pip install -r requirements.txt
playwright install
python src/script.py
pytest
ruff check .
ruff format .
```

### ETL Operations
```bash
# Run all ETL pipelines (recommended for full data refresh)
./run_all_etl.sh          # Linux/Mac (uses UV by default)
.\run_all_etl.bat         # Windows (uses UV by default)

# Run specific ETL pipelines
uv run python src/etl/arxiv/arxiv_etl.py
uv run python src/etl/news/news_get_ycombinator.py
uv run python src/etl/games/enhanced_free_games_etl.py
uv run python src/etl/ai_platforms/anthropic_etl.py

# Run watchers for continuous monitoring
uv run python src/watchers/run_watcher.py
uv run python src/watchers/run_watcher.py --list
uv run python src/watchers/run_watcher.py arxiv_watcher --once

# Run category-specific ETLs
uv run python src/etl/deals/run_all_deals.py
uv run python src/etl/giveaways/run_all_giveaways.py
```

### Dashboard Operations
```bash
# Main Dash-based dashboard (recommended)
uv run python run_watchtower_dashboard.py
# Available at http://localhost:7777

# Legacy Streamlit dashboard (compatibility mode)
uv run streamlit run src/web/fullstreamlit/app.py
# Available at http://localhost:8501

# Run ETL and dashboard together
./run_all_etl_and_dashboard.sh    # Linux/Mac
.\run_all_etl_and_dashboard.bat   # Windows
```

### Testing and Quality Assurance
```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest Tests/etl/
uv run pytest Tests/models/
uv run pytest Tests/unit/
uv run pytest Tests/integration/

# Run with coverage and generate HTML report
uv run pytest --cov=src --cov-report=html --cov-report=term

# Performance testing
uv run pytest Tests/performance/ -v
```

## High-Level Architecture

### Core Framework Pattern
Watchtower implements a sophisticated three-layer architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  ETL Framework  │───▶│   Dashboard     │
│                 │    │                 │    │                 │
│ • ArXiv RSS     │    │ • BaseETL       │    │ • Dash Tabs     │
│ • GitHub API    │    │ • Checkpointing │    │ • Real-time     │
│ • Reddit JSON   │    │ • Retry Logic   │    │ • Interactive   │
│ • News Feeds    │    │ • Metrics       │    │ • Filterable    │
│ • Game Stores   │    │ • NLP Classify  │    │ • Bootstrap UI  │
│ • Course APIs   │    │ • Validation    │    │ • Mobile Ready │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Watchers      │    │  JSON Storage   │    │   Health APIs   │
│                 │    │                 │    │                 │
│ • BaseWatcher   │    │ • data/*/       │    │ • /health       │
│ • State Mgmt    │    │ • Timestamped   │    │ • /metrics      │
│ • Event Logs    │    │ • Latest Files  │    │ • Status Check  │
│ • Continuous    │    │ • Checkpoints   │    │ • Data Summary  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1. BaseETL Framework (`src/etl/base.py`)
The cornerstone of the data processing architecture:

- **Template Method Pattern**: Orchestrates extract → transform → load phases
- **Built-in Metrics Collection**: ETLMetrics model tracks performance, success rates, and error counts
- **Checkpoint System**: Resumable operations with automatic state persistence
- **Retry Mechanisms**: Exponential backoff for transient failures
- **Error Handling**: Custom exception hierarchy with context preservation
- **Data Validation**: Pydantic model validation with detailed error reporting
- **Batch Processing**: Configurable batch sizes for memory efficiency
- **Retention Management**: Automatic cleanup of old timestamped files

### 2. BaseWatcher System (`src/watchers/base_watcher.py`)
Event-driven monitoring infrastructure:

- **State Persistence**: JSON-based checkpoint system in `data/watchers/{name}/state.json`
- **Event Logging**: Timestamped change events in `data/watchers/{name}/events/`
- **Configurable Intervals**: Flexible polling frequencies (default: 1 hour)
- **Abstract Interface**: `extract_value()` and `has_changed()` for custom implementations
- **Automatic Directory Creation**: Self-managing file system structure
- **Exception Resilience**: Continues operation despite individual failures

### 3. Pydantic Settings Management (`src/config/settings.py`)
Centralized configuration with environment variable support:

- **Nested Configuration**: Component-specific configs (DatabaseConfig, ETLConfig, etc.)
- **Auto-discovery**: Automatic project root detection via markers
- **Environment Variables**: Double underscore delimiter support (e.g., `DATABASE__URL`)
- **Type Validation**: Full Pydantic validation with custom validators
- **Path Management**: Automatic conversion to absolute paths

### 4. Dash Dashboard Architecture (`src/web/dashboard/`)
Modern web interface with performance focus:

- **Tab-based Components**: Modular architecture with Bootstrap styling
- **Single Callback Pattern**: Prevents "Duplicate callback outputs" errors
- **Real-time Data Loading**: Efficient JSON file reading with caching
- **VideoManager Pattern**: Centralized data handling for complex components
- **Error Boundaries**: Graceful degradation with user-friendly error messages
- **Mobile Responsive**: Bootstrap CSS with fluid containers
- **Health API Endpoints**: `/health` and `/metrics` for monitoring

## Data Processing Flow

The complete data pipeline follows this sophisticated flow:

```
External APIs/RSS ──▶ ETL Pipelines ──▶ JSON Storage ──▶ Dashboard Components
     │                    │               │               │
     ▼                    ▼               ▼               ▼
┌─────────────┐    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ • ArXiv RSS │    │ • Extract   │ │ • File-based│ │ • Tab Comps │
│ • Course APIs│    │ • Transform │ │ • Event logs│ │ • Data Svcs │
│ • News Feeds │    │ • Classify  │ │ • Checkpts  │ │ • Interactv │
│ • Game Deals │    │ • Validate  │ │ • Metrics   │ │ • Cached    │
│ • GitHub API │    │ • Load      │ │ • Latest    │ │ • Realtime  │
└─────────────┘    └─────────────┘ └─────────────┘ └─────────────┘
```

### Domain-Specific ETL Modules
- **ArXiv ETL** (`src/etl/arxiv/`): RSS parsing, NLP classification, research trend analysis
- **News ETL** (`src/etl/news/`): Multi-source aggregation (HackerNews, Reddit, Medium, etc.)
- **Games ETL** (`src/etl/games/`): Deal aggregation, free games, new releases
- **Course ETL** (`src/etl/goldigging/`): Udemy, Coursera, educational content mining  
- **AI Platforms ETL** (`src/etl/ai_platforms/`): OpenAI, Anthropic, HuggingFace monitoring
- **Entertainment ETL** (`src/etl/entertainment/`): Cinema listings, meme economics
- **Deal Aggregation** (`src/etl/deals/`): Comprehensive deal tracking across multiple categories
- **Anime ETL** (`src/etl/anime/`): MyAnimeList data aggregation
- **ADHD Research** (`src/etl/adhd/`): PubMed research paper collection and analysis
- **4chan ETL** (`src/etl/fourchan/`): General thread monitoring and analysis
- **Spanish Public Aid** (`src/etl/spanish_public_aid/`): Government aid programs monitoring
- **Valencia Events** (`src/etl/news/valencia_events_etl.py`): Local event aggregation
- **Intelligence Mining** (`src/etl/intelligence/`): Advanced data analysis and insights

### Data Models Architecture
Located in `src/models/`, follows Pydantic BaseModel pattern:
- **Base Models** (`base.py`): TimestampedModel, StatusModel with common fields
- **Domain Models**: ArxivPaperModel, TechnologyModel, GameDealModel, AnimeModel, CourseModel, etc.
- **Specialized Models**: ADHDModel, MuseumModel, SecurityModel, EcommerceModel
- **Enum Classifications**: TrendDirection, AdoptionLevel, SecuritySeverity
- **Validation Methods**: Built-in data validation and serialization

## File Organization Patterns

### ETL Development
- Inherit from `BaseETL` in `src/etl/base.py`
- Implement `extract()`, `transform()`, `load()` methods
- Use `ETLMetrics` for performance tracking
- Store outputs in `data/{etl_name}/` with JSON format
- Enable checkpointing for resumable operations

### Watcher Development
- Inherit from `BaseWatcher` in `src/watchers/base_watcher.py`
- Implement `get_current_value()` and `check_for_changes()` methods
- State files automatically managed in `data/watchers/{name}/state.json`
- Events logged to `data/watchers/{name}/events/`

### Dashboard Components
- **Main Dashboard**: Dash-based dashboard in `src/web/dashboard/`
- **Component Structure**: Tab functions in `src/web/dashboard/components/`
- **Data Manager Pattern**: Each tab implements a manager class for data loading and filtering
- **Styling**: CSS and assets in `src/web/dashboard/assets/`
- **Utilities**: Use `utils.py` for shared utilities and data path resolution
- **Legacy Support**: Streamlit components in `src/web/fullstreamlit/` for compatibility
- **Interactive Features**: Implement Dash callbacks for real-time updates
- **Health Monitoring**: Built-in health checks and metrics endpoints

#### Videos Tab Implementation (`videos_tab.py`)
- **VideoManager Class**: Handles YouTube video data loading and filtering
- **Data Source**: `data/youtube/{channel_name}/youtube_videos.json` files
- **Display Capacity**: Shows 48 videos per view (increased from 12 for better browsing)
- **Channel Organization**: Categories (`aa-`, `zz-` prefixes) listed first, then alphabetical
- **Automatic Filtering**: Channel dropdown triggers immediate video updates via single callback
- **Error Handling**: Fallback cards for individual video loading failures
- **Performance**: Thread-safe data loading with caching for 1,500+ videos across 16+ channels
- **UI Components**: Bootstrap cards with thumbnails, titles, channels, and publication dates
- **Callback Design**: Single callback prevents duplicate output conflicts with other dashboard tabs

### Configuration Management
- **Settings System**: Pydantic Settings in `src/config/settings.py`
- **Models**: Configuration models in `src/config/models.py`
- **Environment Variables**: Use double underscore delimiter (e.g., `DATABASE__URL`)
- **Component Configs**: ETLConfig, WatcherConfig, DatabaseConfig, etc.
- **Auto-Discovery**: Automatic project root directory detection
- **Validation**: Built-in validation with Pydantic models

## Development Standards

### Code Quality Requirements
- **Type Hints**: All functions must use Python 3.10+ type annotations
- **Error Handling**: Custom exception hierarchy (`src/exceptions/`)
- **Logging**: Structured logging with component-specific loggers
- **Testing**: pytest with focus on ETL and data processing logic
- **Documentation**: Google-style docstrings with examples

### Architecture Patterns in Use
- **Template Method**: BaseETL.run() orchestrates ETL phases
- **Factory Pattern**: get_settings() with @lru_cache singleton
- **State Pattern**: Watcher state management with JSON persistence
- **Component Pattern**: Dash modular tab architecture with single-callback design
- **Observer Pattern**: Event logging in watchers and ETL processes
- **Manager Pattern**: VideoManager for centralized video data handling and filtering

### Performance Optimization
- **Caching**: Component-level data caching and efficient rendering
- **Batch Processing**: Configurable batch_size in ETL operations
- **JSON Storage**: Fast read operations with pandas/polars
- **Memory Management**: Ultra-optimized data services
- **Lazy Loading**: On-demand data loading in dashboard components

## Important Implementation Details

### Dashboard Callback Best Practices
1. **Single Callback Pattern**: One callback per output prevents conflicts
2. **Prevent Initial Call**: Use `prevent_initial_call=True` when appropriate
3. **Error Boundaries**: Always include try-catch with user feedback
4. **Unique Component IDs**: Descriptive, conflict-free identifiers
5. **Context Usage**: Use `dash.callback_context` for multi-input callbacks
6. **Data Manager Integration**: Use manager classes for complex data handling

### UV Package Manager Benefits
- **Performance**: 10-100x faster than pip for dependency resolution
- **Reliability**: Consistent dependency locking and resolution
- **Compatibility**: Drop-in replacement for pip workflows
- **Modern Python**: Full support for Python 3.10+ features
- **Usage**: All Python commands should use `uv run` prefix
- **Setup**: `uv sync --all-extras` for complete installation

### Data Storage Pattern
- **Primary Format**: JSON files in `data/` directory
- **Structure**: `data/{component_name}/output/` for processed data
- **Checkpoints**: `data/{component_name}/checkpoints/` for state
- **Events**: `data/watchers/{name}/events/` for change tracking

### Error Handling Strategy
1. **Custom Exception Hierarchy**: Domain-specific exceptions in `src/exceptions/`
2. **Retry Mechanisms**: Exponential backoff for transient failures
3. **Graceful Degradation**: Dashboard continues functioning despite errors
4. **Contextual Logging**: Structured error context for debugging

### Performance Optimization Techniques
1. **Lazy Loading**: Data loaded on-demand in dashboard components
2. **Caching Strategies**: Multiple levels of caching for frequently accessed data
3. **Batch Processing**: Configurable batch sizes for memory efficiency
4. **Concurrent Execution**: Parallel processing in ETL scripts
5. **JSON Optimization**: Efficient serialization and deserialization

## Testing Strategy

### Test Organization
```
Tests/
├── unit/           # Unit tests for individual functions
├── integration/    # Integration tests for ETL workflows
├── etl/           # ETL-specific tests
├── models/        # Pydantic model validation tests
├── web/           # Dashboard component tests
└── performance/   # Performance and load tests
```

### Key Testing Patterns
- **ETL Testing**: Mock external APIs, test transform logic, validate output schemas
- **Model Testing**: Pydantic validation, serialization, field constraints
- **Dashboard Testing**: Component rendering, callback functionality
- **Performance Testing**: Memory usage, execution time, data loading speed

### Test Execution
```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest Tests/etl/ -v
uv run pytest Tests/models/ -v
uv run pytest Tests/integration/ -v

# Performance testing
uv run pytest Tests/performance/ --benchmark-only
```

### Configuration Best Practices
- Use `.env` files for sensitive configuration
- Nested config models for component separation
- Environment variables with `COMPONENT__SETTING` format
- Auto-discovery of project paths and settings

## Key Dependencies and Tools

### Core Stack
- **Python**: 3.10+ (required for modern type hints)
- **Package Manager**: UV (recommended) or pip + venv
- **Data Processing**: pandas (primary), polars (performance), numpy
- **Web Framework**: Dash (dashboard), Streamlit (legacy)
- **Scraping**: requests, BeautifulSoup4, Playwright, cloudscraper
- **Configuration**: Pydantic Settings with nested models
- **UI Components**: dash-bootstrap-components, plotly for charts

### Development Tools
- **Linting/Formatting**: Ruff (configured in pyproject.toml)
- **Testing**: pytest with coverage reporting
- **Type Checking**: mypy (configured for strict typing)
- **Documentation**: Google-style docstrings

### External APIs
- **ArXiv**: RSS feeds and paper metadata
- **GitHub**: Repository trends and API monitoring
- **News Sources**: RSS feeds from multiple tech sites (HackerNews, Reddit, Medium)
- **Course Platforms**: Udemy, Coursera, DeepLearning.AI APIs
- **Game Platforms**: Steam, Epic Games, Humble Bundle
- **AI Platforms**: OpenAI, Anthropic, HuggingFace APIs
- **Entertainment**: MyAnimeList, Cinema listings
- **Research**: PubMed for ADHD research papers

## Specialized Components

### Miners (`src/miners/`)
Advanced data mining tools with specialized functionality:

- **Udemy Universal** (`udemy-universal/`): Advanced course discovery and enrollment automation
- **Steam ASF** (`asf-winonly/`): ArchiSteamFarm integration for game collection automation
- **Crypto Sentiment**: Multi-platform cryptocurrency sentiment analysis

### Analytics (`src/analytics/`)
Data analysis and trend identification:

- **Technology Adoption**: Trend analysis with adoption lifecycle tracking
- **Performance Analytics**: System performance monitoring and optimization
- **Market Analysis**: Price tracking and deal identification algorithms

### Utilities (`src/utils/`)
Shared functionality across the platform:

- **NLP Classifier**: Content categorization with machine learning
- **File System**: Project-wide path resolution and directory management
- **Logging**: Structured logging with performance metrics
- **Backup Utils**: Automated backup and recovery systems
- **GitHub Utils**: Repository analysis and metadata extraction

This architecture enables rapid development of new ETL processes and monitoring capabilities while maintaining high code quality and performance standards.

## Cursor Rules Integration

The project includes comprehensive development standards in `.cursorrules`:

### Key Standards
- **UV-first development**: All Python operations use `uv run` prefix
- **Dash dashboard architecture**: Primary framework with Bootstrap styling
- **Template method patterns**: BaseETL and BaseWatcher provide consistent interfaces
- **Data manager pattern**: Component-level data handling with caching
- **Single callback pattern**: Prevents dashboard callback conflicts
- **Pydantic everywhere**: Models, settings, and validation use Pydantic
- **Domain-specific ETL modules**: Organized by data source and purpose
- **Performance optimization**: Caching, lazy loading, and efficient rendering

### Development Workflow
1. Use UV for all package management and script execution
2. Follow Dash component patterns for dashboard development
3. Implement data managers for complex data handling
4. Use single callbacks to prevent dashboard conflicts
5. Apply comprehensive error handling with graceful degradation

## Important Project Context

### Project Name and Identity
The project is called **Watchtower** (also referenced as MEGALITH in some documentation). It's a comprehensive data intelligence and monitoring platform.

### Key Architecture Decisions
- **UV Package Manager**: Preferred over pip/venv for 10-100x faster dependency management
- **Dual Dashboard System**: Main Dash dashboard (port 7777) + Legacy Streamlit (port 8501)
- **File-based Storage**: JSON files in `data/` directory for performance and simplicity
- **Pydantic Everything**: Models, configuration, and validation all use Pydantic
- **Template Method Pattern**: BaseETL and BaseWatcher provide consistent interfaces

### Development Workflow
1. **Setup**: Always use `uv sync --all-extras` for fastest setup
2. **Running Code**: Prefix all Python commands with `uv run`
3. **Testing**: Use `uv run pytest` with coverage reporting
4. **Linting**: `uv run ruff check .` and `uv run ruff format .`
5. **Type Checking**: `uv run mypy src/` (configured in pyproject.toml)

### Data Flow Patterns
- **ETL Output**: `data/{etl_name}/output/` for processed data
- **Checkpoints**: `data/{etl_name}/checkpoints/` for resumable state
- **Watcher Events**: `data/watchers/{name}/events/` for change tracking
- **Logs**: Centralized in `logs/` with component-specific files
- **Health Data**: Dashboard health metrics and status information
- **Shortcuts**: Predefined shortcuts in `data/shortcuts/predefined_shortcuts.json`

### Security and Best Practices
- **Environment Variables**: Use `.env` files for sensitive data
- **Exception Handling**: Custom hierarchy in `src/exceptions/`
- **Logging**: Structured with performance metrics
- **Type Safety**: Full type annotations with Python 3.10+ syntax
- **Documentation**: Google-style docstrings required
- **API Key Management**: Secure storage and environment-based configuration
- **Input Validation**: Pydantic models validate all external data
- **Path Security**: Secure file path handling prevents traversal attacks