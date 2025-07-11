# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Package Management (UV - Recommended)
```bash
# Install dependencies and set up virtual environment
uv sync --all-extras

# Install Playwright browsers
uv run playwright install

# Run any Python script
uv run python src/script.py

# Run tests
uv run pytest

# Run linting and formatting
uv run ruff check .
uv run ruff format .
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
# Run all ETL pipelines
./run_all_etl.sh          # Linux/Mac
.\run_all_etl.bat         # Windows

# Run specific ETL
uv run python src/etl/arxiv/arxiv_etl.py
uv run python src/etl/news/news_get_ycombinator.py

# Run watchers
uv run python src/watchers/run_watcher.py
uv run python src/watchers/run_watcher.py --list
uv run python src/watchers/run_watcher.py ms_applied_skills --once
```

### Dashboard Operations
```bash
# Main dashboard (Dash-based, recommended)
uv run python run_watchtower_dashboard.py
# Available at http://localhost:7777

# Legacy Streamlit dashboard
uv run streamlit run src/web/fullstreamlit/app.py
# Available at http://localhost:8501

# Run both ETL and dashboard
./run_all_etl_and_dashboard.sh    # Linux/Mac
.\run_all_etl_and_dashboard.bat   # Windows
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test category
uv run pytest Tests/etl/
uv run pytest Tests/models/
uv run pytest Tests/unit/

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## High-Level Architecture

### Core Framework Pattern
MEGALITH follows a sophisticated ETL + Watcher + Dashboard architecture:

1. **BaseETL Framework** (`src/etl/base.py`):
   - Template method pattern with extract/transform/load phases
   - Built-in metrics collection (ETLMetrics model)
   - Checkpoint system for resumable operations
   - Retry mechanisms with exponential backoff
   - Comprehensive error handling and logging

2. **BaseWatcher System** (`src/watchers/base_watcher.py`):
   - State persistence with JSON checkpoints
   - Event-driven change detection
   - Configurable polling intervals
   - Automatic directory structure creation

3. **Pydantic Settings Management** (`src/config/settings.py`):
   - Nested configuration models with environment variable support
   - Auto-discovery of project root directory
   - Component-specific configs (DatabaseConfig, ETLConfig, etc.)
   - Double underscore delimiter for nested env vars (e.g., `DATABASE__URL`)

4. **Modular Streamlit Dashboard** (`src/web/fullstreamlit/`):
   - Tab-based component architecture
   - Ultra-optimized data service with TTL caching
   - Performance-focused design with lazy loading
   - Error boundaries for graceful degradation

### Data Processing Flow
```
External APIs/RSS → ETL Pipelines → JSON Storage → Dashboard Components
     ↓                   ↓              ↓              ↓
- ArXiv RSS          Extract         File-based      Tab Components
- Course APIs        Transform       Event logs      Data Services
- News Feeds         Classify        Checkpoints     Interactive UI
- Game Deals         Load            Metrics         Cached Views
```

### Domain-Specific ETL Modules
- **ArXiv ETL** (`src/etl/arxiv/`): RSS parsing, NLP classification, research trend analysis
- **News ETL** (`src/etl/news/`): Multi-source aggregation (HackerNews, Reddit, etc.)
- **Games ETL** (`src/etl/games/`): Deal aggregation, free games, new releases
- **Course ETL** (`src/etl/goldigging/`): Udemy, Coursera, educational content mining
- **AI Platforms ETL** (`src/etl/ai_platforms/`): OpenAI, Anthropic, HuggingFace monitoring

### Data Models Architecture
Located in `src/models/`, follows Pydantic BaseModel pattern:
- **Base Models** (`base.py`): TimestampedModel, StatusModel with common fields
- **Domain Models**: ArxivPaperModel, TechnologyModel, GameDealModel, etc.
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

### Streamlit Components
- Create tab functions in `src/web/fullstreamlit/components/`
- Use `data_service.py` for optimized data loading with caching
- Implement error handling with `render_tab_safely` pattern
- Follow performance optimization patterns from existing components

### Configuration Management
- Use nested Pydantic Settings models in `src/config/models.py`
- Environment variables with double underscore delimiter
- Component-specific configurations (ETLConfig, WatcherConfig, etc.)
- Auto-discovery of project root directory

## Development Standards from .cursorrules

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
- **Component Pattern**: Streamlit modular tab architecture
- **Observer Pattern**: Event logging in watchers and ETL processes

### Performance Optimization
- **Caching**: Streamlit @st.cache_data with TTL configuration
- **Batch Processing**: Configurable batch_size in ETL operations
- **JSON Storage**: Fast read operations with pandas/polars
- **Memory Management**: Ultra-optimized data services
- **Lazy Loading**: On-demand data loading in dashboard components

## Important Implementation Details

### UV Package Manager Integration
- Project uses UV for extremely fast dependency management
- All Python commands should use `uv run` prefix
- `uv sync --all-extras` for complete setup
- No manual virtual environment activation needed

### Data Storage Pattern
- **Primary Format**: JSON files in `data/` directory
- **Structure**: `data/{component_name}/output/` for processed data
- **Checkpoints**: `data/{component_name}/checkpoints/` for state
- **Events**: `data/watchers/{name}/events/` for change tracking

### Error Handling Strategy
- Custom exception classes in `src/exceptions/`
- Retry mechanisms with exponential backoff
- Graceful degradation in dashboard components
- Comprehensive logging with structured formats

### Testing Approach
- Tests in `Tests/` directory (note capital T)
- Unit tests for utilities and models
- Integration tests for ETL processes
- Performance testing for dashboard components
- Run with `uv run pytest` for best performance

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
- **Web Framework**: Streamlit (dashboard), Dash (new dashboard)
- **Scraping**: requests, BeautifulSoup4, Playwright
- **Configuration**: Pydantic Settings with nested models

### Development Tools
- **Linting/Formatting**: Ruff (configured in pyproject.toml)
- **Testing**: pytest with coverage reporting
- **Type Checking**: mypy (configured for strict typing)
- **Documentation**: Google-style docstrings

### External APIs
- **ArXiv**: RSS feeds and paper metadata
- **GitHub**: Repository trends and API monitoring
- **News Sources**: RSS feeds from multiple tech sites
- **Course Platforms**: Udemy, Coursera APIs
- **Game Platforms**: Steam, Epic Games, deal aggregators

This architecture enables rapid development of new ETL processes and monitoring capabilities while maintaining high code quality and performance standards.