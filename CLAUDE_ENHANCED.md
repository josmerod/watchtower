# CLAUDE.md - Enhanced Documentation

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

# Install Playwright browsers for web scraping
uv run playwright install

# Run any Python script with UV
uv run python src/script.py

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/
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

#### Research & Intelligence
- **ArXiv ETL** (`src/etl/arxiv/`): RSS parsing, NLP classification, research trend analysis
- **AI Platforms ETL** (`src/etl/ai_platforms/`): OpenAI, Anthropic, HuggingFace, Papers with Code monitoring
- **ADHD Research** (`src/etl/adhd/`): PubMed research paper collection and analysis

#### News & Social Media
- **News ETL** (`src/etl/news/`): Multi-source aggregation (HackerNews, Reddit, Medium, ProductHunt)
- **4chan ETL** (`src/etl/fourchan/`): General thread monitoring and sentiment analysis
- **Reddit Unified** (`src/etl/news/reddit_unified_etl.py`): 30+ subreddits with category classification

#### Gaming & Entertainment
- **Games ETL** (`src/etl/games/`): Deal aggregation, free games, metacritic reviews, new releases
- **Anime ETL** (`src/etl/anime/`): MyAnimeList data with recommendation engine
- **Entertainment ETL** (`src/etl/entertainment/`): Cinema listings, Spotify, Trakt trending

#### Education & Professional
- **Course ETL** (`src/etl/goldigging/`): Udemy, Coursera, educational content mining
- **GitHub ETL** (`src/etl/github/`): Trending repositories, release monitoring, star tracking
- **Spanish Public Aid** (`src/etl/spanish_public_aid/`): Government assistance programs

#### E-commerce & Deals
- **Deal Aggregation** (`src/etl/deals/`): 12 categories of deals across multiple platforms
- **Giveaways ETL** (`src/etl/giveaways/`): Free games, courses, Reddit giveaways

## Data Models Architecture

Located in `src/models/`, follows strict Pydantic BaseModel patterns:

### Base Models (`src/models/base.py`)
- **TimestampedModel**: Automatic ID generation, created_at, updated_at fields
- **StatusModel**: Status tracking with message and details
- **ErrorModel**: Comprehensive error context with traceback
- **PaginationModel**: Automatic page calculation and navigation
- **PaginatedResponse**: Generic container for API responses

### Domain-Specific Models
- **ArxivPaperModel** (`arxiv.py`): Research paper metadata with classification
- **TechnologyModel** (`technology.py`): Tech trend tracking with adoption metrics
- **GameDealModel** (`games.py`): Game pricing and availability data
- **AnimeModel** (`anime.py`): Anime series with ratings and recommendations
- **CourseModel** (`course.py`): Educational content with pricing and reviews
- **NewsArticleModel** (`news.py`): Article content with source attribution
- **SecurityModel** (`security.py`): Vulnerability data with CVSS scores

### Enum Classifications
- **TrendDirection**: UP, DOWN, STABLE, VOLATILE
- **AdoptionLevel**: EXPERIMENTAL, EMERGING, MAINSTREAM, DECLINING
- **SecuritySeverity**: LOW, MEDIUM, HIGH, CRITICAL
- **ContentLanguage**: EN, ES, FR, DE, IT, PT, RU, ZH, JA, KO

## File Organization Patterns

### ETL Development Best Practices
When creating new ETL processes:

1. **Inherit from BaseETL**: Use `src/etl/base.py` for all new ETL implementations
2. **Implement Required Methods**: 
   - `extract()`: Data retrieval from source
   - `transform()`: Data processing and classification
   - `load()`: Persistence to JSON files
3. **Use ETLMetrics**: Built-in performance tracking and success rate monitoring
4. **Enable Checkpointing**: For resumable long-running operations
5. **JSON Output Structure**: `data/{etl_name}/output/{timestamp}.json` and `_latest.json`

```python
from src.etl.base import BaseETL
from typing import List, Dict, Any

class MyCustomETL(BaseETL[Dict[str, Any], Dict[str, Any]]):
    def extract(self) -> List[Dict[str, Any]]:
        # Implement data extraction
        pass
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Implement data transformation
        pass
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        # Implement data loading
        pass
```

### Watcher Development
For continuous monitoring capabilities:

1. **Inherit from BaseWatcher**: Use `src/watchers/base_watcher.py`
2. **Implement Abstract Methods**:
   - `extract_value()`: Get current value from source
   - `has_changed()`: Determine if change is significant
3. **State Management**: Automatic handling in `data/watchers/{name}/state.json`
4. **Event Logging**: Changes recorded in `data/watchers/{name}/events/`

```python
from src.watchers.base_watcher import BaseWatcher

class MyWatcher(BaseWatcher):
    def extract_value(self, html_content: str) -> Any:
        # Extract the value to monitor
        pass
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        # Determine if change is significant
        pass
```

### Dashboard Component Development
For interactive web interfaces:

1. **Tab Structure**: Create component in `src/web/dashboard/components/`
2. **Single Callback Pattern**: Use one callback per output to avoid conflicts
3. **Error Boundaries**: Include try-catch blocks with user-friendly messages
4. **Data Loading**: Use VideoManager pattern for complex data handling
5. **Bootstrap CSS**: Consistent styling with `dbc` components

```python
import dash_bootstrap_components as dbc
from dash import Input, Output, html

def render_my_tab():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H3("My Custom Tab"),
                html.Div(id="my-content")
            ])
        ])
    ])

def register_my_callbacks(app):
    @app.callback(
        Output("my-content", "children"),
        Input("my-input", "value"),
        prevent_initial_call=True
    )
    def update_content(input_value):
        try:
            # Process and return content
            return f"Updated: {input_value}"
        except Exception as e:
            return f"Error: {str(e)}"
```

## Configuration Management

### Settings System
- **Main Settings**: `src/config/settings.py` with `get_settings()` singleton
- **Component Models**: Individual config classes in `src/config/models.py`
- **Environment Variables**: Use `COMPONENT__SETTING` format for nested configs
- **Auto-Discovery**: Automatic project root detection and path resolution

### Environment Variable Examples
```bash
# Database configuration
DATABASE__URL=postgresql://user:pass@localhost:5432/watchtower
DATABASE__POOL_SIZE=10

# ETL configuration
ETL__BATCH_SIZE=100
ETL__MAX_RETRIES=5

# Logging configuration
LOGGING__LEVEL=DEBUG
LOGGING__FILE_ENABLED=true
```

## Development Standards

### Code Quality Requirements
- **Type Hints**: Full Python 3.10+ type annotations required
- **Error Handling**: Custom exception hierarchy in `src/exceptions/`
- **Logging**: Structured logging with component-specific loggers
- **Testing**: pytest with focus on ETL and data processing logic
- **Documentation**: Google-style docstrings with examples

### Architecture Patterns in Use
- **Template Method**: BaseETL.run() orchestrates ETL phases
- **Factory Pattern**: get_settings() with @lru_cache singleton
- **State Pattern**: Watcher state management with JSON persistence
- **Component Pattern**: Dash modular tab architecture
- **Observer Pattern**: Event logging in watchers and ETL processes
- **Manager Pattern**: VideoManager for centralized data handling

### Performance Optimization Techniques
- **Caching**: Component-level data caching with efficient rendering
- **Batch Processing**: Configurable batch_size in ETL operations
- **JSON Storage**: Fast read operations optimized for dashboard loading
- **Memory Management**: Efficient data services with lazy loading
- **Concurrent Processing**: Parallel ETL execution in run scripts

## Data Storage Patterns

### Primary Storage Structure
```
data/
├── {component_name}/
│   ├── output/
│   │   ├── {component_name}_{timestamp}.json
│   │   ├── {component_name}_latest.json
│   │   └── run_summary_latest.json
│   └── checkpoints/
│       └── latest.json
├── watchers/
│   └── {watcher_name}/
│       ├── state.json
│       └── events/
│           └── {timestamp}_{event_type}.json
└── metrics/
    └── etl_runs_latest.json
```

### File Naming Conventions
- **Timestamped Files**: `{component}_{YYYYMMDD_HHMMSS}.json`
- **Latest Files**: `{component}_latest.json` (always current)
- **State Files**: `state.json` in component directories
- **Event Files**: `{timestamp}_{event_type}.json` in events directories

### Data Retention Policy
- **Automatic Cleanup**: Configurable retention via `ETL.cleanup_old_data_days`
- **Latest File Preservation**: `*_latest.*` files never deleted
- **Event Archival**: Watcher events preserved indefinitely
- **Metrics Aggregation**: Global ETL run metrics in centralized location

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

## Key Dependencies and External Integrations

### Core Stack
- **Python**: 3.10+ (required for modern type hints and performance)
- **Package Manager**: UV (10-100x faster than pip) or pip + venv (fallback)
- **Data Processing**: pandas (primary), polars (performance-critical), numpy
- **Web Framework**: Dash (modern UI) + Streamlit (legacy compatibility)
- **HTTP/Scraping**: requests, BeautifulSoup4, Playwright (browser automation)
- **Configuration**: Pydantic Settings with nested validation

### Development Tools
- **Linting/Formatting**: Ruff (configured in pyproject.toml)
- **Testing**: pytest with coverage reporting and benchmarking
- **Type Checking**: mypy with strict configuration
- **Documentation**: Google-style docstrings with Sphinx support

### External APIs and Services
- **Research**: ArXiv RSS, PubMed, Papers with Code
- **Developer Tools**: GitHub API, Stack Overflow trends
- **News Sources**: HackerNews, Reddit JSON, RSS aggregators
- **Education**: Udemy API, Coursera, DeepLearning.AI
- **Gaming**: Steam API, Epic Games, Humble Bundle, AllKeyShop
- **AI Platforms**: OpenAI API, Anthropic, HuggingFace Models
- **Entertainment**: MyAnimeList, Cinema listings, Spotify API
- **Social Media**: Reddit (30+ subreddits), 4chan archives

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

## Important Implementation Details

### Dashboard Callback Best Practices
1. **Single Callback Pattern**: One callback per output prevents conflicts
2. **Prevent Initial Call**: Use `prevent_initial_call=True` when appropriate
3. **Error Boundaries**: Always include try-catch with user feedback
4. **Unique Component IDs**: Descriptive, conflict-free identifiers
5. **Context Usage**: Use `dash.callback_context` for multi-input callbacks

### UV Package Manager Benefits
- **Performance**: 10-100x faster than pip for dependency resolution
- **Reliability**: Consistent dependency locking and resolution
- **Compatibility**: Drop-in replacement for pip workflows
- **Modern Python**: Full support for Python 3.10+ features

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

This enhanced documentation provides a comprehensive foundation for understanding and extending the Watchtower platform. The architecture is designed for scalability, maintainability, and high performance while processing large volumes of diverse data sources.