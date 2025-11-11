# MEGALITH - Continue Development Guide

## Project Overview

MEGALITH is a comprehensive monitoring and ETL framework for scraping, aggregating, and visualizing data from diverse online sources. The project automates data collection from news sites, game deal aggregators, online course platforms, and provides intelligent monitoring of web content changes through robust ETL pipelines, watchers, and an interactive dashboard.

### Key Technologies

- **Core Language**: Python 3.10+
- **Package Management**: UV (recommended) with Poetry-style `pyproject.toml`
- **Data Processing**: Polars (primary), Pandas (secondary), NumPy
- **Web Scraping**: Playwright, Beautiful Soup, Feedparser, yt-dlp
- **Web Dashboard**: Dash (primary) with Streamlit (legacy)
- **Data Validation**: Pydantic with comprehensive type hints
- **Orchestration**: Prefect for workflow management
- **Containerization**: Docker with multi-stage builds
- **Code Quality**: Ruff, pytest, mypy

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │     ETL/Pipes   │    │   Storage/DB    │
│                 │───▶│                 │───▶│                 │
│ • News Sites    │    │ • BaseETL       │    │ • JSON Files    │
│ • APIs          │    │ • DataFrameETL  │    │ • CSV/Parquet   │
│ • Web Pages     │    │ • Transformers  │    │ • Checkpoints   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Watchers    │    │   Orchestrator  │    │    Dashboard    │
│                 │    │                 │    │                 │
│ • BaseWatcher   │    │ • Prefect Flows │    │ • Dash App      │
│ • Change Detect │    │ • Scheduling    │    │ • Data Viz      │
│ • Alerts        │    │ • Monitoring    │    │ • Management    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [UV](https://github.com/astral-sh/uv) package manager (recommended)
- Git
- Docker (optional, for containerization)

### Quick Setup with UV

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd megalith
   ```

2. **Install dependencies and setup**:
   ```bash
   # Install all dependencies automatically
   uv sync --all-extras
   
   # Install Playwright browsers
   uv run playwright install
   ```

3. **Set up environment**:
   ```bash
   # Copy environment template and configure
   cp .env.template .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the dashboard**:
   ```bash
   uv run python run_watchtower_dashboard.py
   ```

### Alternative Setup Methods

#### Development Setup Script
```bash
python install_dev.py
```

#### Traditional Setup (Not Recommended)
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt
playwright install
```

### First Run

1. **Start the main dashboard**:
   ```bash
   uv run python run_watchtower_dashboard.py
   # Visit: http://localhost:7777
   ```

2. **Run ETL pipelines**:
   ```bash
   # Run all ETLs
   bash run_all_etl.sh  # Linux/Mac
   # or
   .\run_all_etl.bat    # Windows
   ```

3. **Start watchers**:
   ```bash
   uv run python src/watchers/run_watcher.py
   ```

## Project Structure

### Core Directories

```
megalith/
├── src/                      # Main source code
│   ├── etl/                  # ETL pipelines by data source
│   │   ├── base.py          # BaseETL abstract classes
│   │   ├── news/            # News aggregation ETLs
│   │   ├── games/           # Game deals ETLs
│   │   ├── arxiv/           # Academic papers ETL
│   │   ├── courses/         # Online courses ETL
│   │   └── ...
│   ├── watchers/            # Web content monitoring
│   │   ├── base_watcher.py  # BaseWatcher abstract class
│   │   ├── run_watcher.py   # Watcher orchestration
│   │   └── ...
│   ├── web/                 # Web applications
│   │   └── dashboard/       # Dash-based main dashboard
│   ├── config/              # Configuration management
│   │   ├── settings.py      # Pydantic-based settings
│   │   └── models.py        # Configuration data models
│   ├── utils/               # Shared utilities
│   ├── models/              # Pydantic data models
│   └── launcher/            # Application launchers
├── Tests/                   # Test suite (pytest)
├── data/                    # Runtime data storage
├── logs/                    # Application logs
├── .continue/rules/         # Continue AI assistant rules
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # Container definition
└── pyproject.toml          # Project configuration
```

### Key Files

- **`src/etl/base.py`**: Core `BaseETL` and `DataFrameETL` classes with checkpointing, retry logic, and metrics
- **`src/config/settings.py`**: Pydantic-based configuration with environment variable support
- **`src/watchers/base_watcher.py`**: Base watcher class for web content monitoring
- **`run_watchtower_dashboard.py`**: Main dashboard launcher
- **`src/web/dashboard/app.py`**: Dash-based main dashboard application
- **`pyproject.toml`**: Complete project configuration and dependencies

### Configuration System

The project uses a hierarchical configuration system:

1. **Environment Variables**: Primary method for sensitive data
   - Copy `.env.template` to `.env`
   - Use format `SECTION__SUBSECTION__KEY=value`
   - Example: `DATABASE__URL=postgresql://...`

2. **Settings Classes**: Located in `src/config/`
   - `Settings`: Main configuration class
   - Individual config classes for each component
   - Type validation and defaults

## Development Workflow

### Code Standards

1. **Type Safety**:
   - Full type hints required (Python 3.10+ syntax)
   - Pydantic models for data validation
   - mypy checking enabled

2. **Code Style**:
   - Ruff for linting and formatting (88 character line length)
   - Google-style docstrings
   - Follow PEP 8 conventions

3. **Architecture Patterns**:
   - Base classes for extensible components (BaseETL, BaseWatcher)
   - Dependency injection through settings
   - Error handling with custom exceptions
   - Comprehensive logging and metrics

### Adding New ETL Pipelines

1. **Create ETL Class**:
   ```python
   # src/etl/mysource/my_etl.py
   from src.etl.base import BaseETL
   
   class MySourceETL(BaseETL[dict, MyDataModel]):
       def __init__(self):
           super().__init__("my_source", description="My data source")
       
       def extract(self) -> List[dict]:
           # Implement data extraction
           pass
       
       def transform(self, data: List[dict]) -> List[MyDataModel]:
           # Implement data transformation
           pass
       
       def load(self, data: List[MyDataModel]) -> None:
           # Implement data loading
           pass
   ```

2. **Add Data Models**:
   ```python
   # src/models/mysource.py
   from pydantic import BaseModel
   
   class MyDataModel(BaseModel):
       title: str
       url: str
       timestamp: datetime
       # ... other fields
   ```

3. **Register with Orchestration**:
   - Add to Prefect flows in `prefect_flows/`
   - Update deployment configurations
   - Add to run scripts if needed

### Adding New Watchers

1. **Create Watcher Class**:
   ```python
   # src/watchers/my_watcher.py
   from src.watchers.base_watcher import BaseWatcher
   from bs4 import BeautifulSoup
   
   class MyWatcher(BaseWatcher):
       def extract_value(self, html_content: str) -> Any:
           soup = BeautifulSoup(html_content, 'html.parser')
           # Extract the value to monitor
           return soup.find('specific-element').text
       
       def has_changed(self, old_value: Any, new_value: Any) -> bool:
           return old_value != new_value
   ```

2. **Register Watcher**:
   - Add to `src/watchers/run_watcher.py` registry
   - Configure in settings if needed

### Testing Strategy

1. **Unit Tests**:
   - Located in `Tests/unit/`
   - Test individual ETL and watcher components
   - Mock external dependencies

2. **Integration Tests**:
   - Located in `Tests/integration/`
   - Test end-to-end ETL pipelines
   - Use test databases/files

3. **Run Tests**:
   ```bash
   # Run all tests
   uv run pytest
   
   # Run with coverage
   uv run pytest --cov=src --cov-report=html
   ```

### Code Quality Tools

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check . --fix

# Type checking
uv run mypy src/

# Full quality check
uv run ruff format . && uv run ruff check . --fix && uv run mypy src/
```

## Key Concepts

### ETL Architecture

The ETL system uses a template method pattern:

- **BaseETL**: Abstract base class with common functionality
  - Checkpointing for resumable operations
  - Retry logic with exponential backoff
  - Metrics collection and logging
  - Batch processing support

- **DataFrameETL**: Specialized for data processing
  - Built-in Pandas integration
  - CSV/Parquet export capabilities
  - DataFrame-based transformations

### Data Flow

1. **Extraction**: Raw data from sources (APIs, web scraping)
2. **Transformation**: Clean, normalize, and structure data
3. **Loading**: Save to appropriate format (JSON, CSV, Parquet)
4. **Checkpointing**: Save progress for resilience
5. **Metrics**: Track performance and success rates

### Watcher System

Watchers monitor web content for changes:

- **Polling**: Regular checks at configurable intervals
- **State Management**: Persistent tracking of previous values
- **Event Recording**: Timestamped change events
- **Extensible**: Easy to create new watchers for any web content

### Configuration Management

- **Hierarchical**: Environment → Settings → Component Config
- **Typed**: Full Pydantic validation
- **Environment-aware**: Different configs for dev/prod/test
- **Hot-reloadable**: Settings can be reloaded at runtime

## Common Tasks

### Running ETL Pipelines

1. **Run Individual ETL**:
   ```bash
   uv run python src/etl/news/news_get_ycombinator.py
   ```

2. **Run All ETLs**:
   ```bash
   # Cross-platform scripts provided
   bash run_all_etl.sh     # Linux/Mac
   .\run_all_etl.bat       # Windows
   ```

3. **Run with Prefect**:
   ```bash
   # Start Prefect server
   prefect server start
   
   # Run specific flow
   uv run python prefect_flows/news_flow.py
   ```

### Managing Watchers

1. **List Available Watchers**:
   ```bash
   uv run python src/watchers/run_watcher.py --list
   ```

2. **Run Single Watcher**:
   ```bash
   uv run python src/watchers/run_watcher.py ms_applied_skills --once
   ```

3. **Run All Watchers Continuously**:
   ```bash
   uv run python src/watchers/run_watcher.py
   ```

### Dashboard Operations

1. **Start Main Dashboard**:
   ```bash
   uv run python run_watchtower_dashboard.py
   # Visit: http://localhost:7777
   ```

2. **Start Legacy Streamlit**:
   ```bash
   uv run streamlit run src/web/fullstreamlit/app.py
   # Visit: http://localhost:8501
   ```

### Data Management

1. **View ETL Results**:
   ```bash
   # Results are stored in data/{etl_name}/output/
   ls data/news/output/
   ```

2. **Check Metrics**:
   ```bash
   # ETL run summaries in data/metrics/
   cat data/metrics/etl_runs_latest.json
   ```

3. **Clean Old Data**:
   - Configured via `ETL_CONFIG__CLEANUP_OLD_DATA_DAYS`
   - Automatic cleanup after successful ETL runs

### Deployment

1. **Docker Build**:
   ```bash
   docker build -t megalith .
   ```

2. **Docker Run**:
   ```bash
   docker run -p 7777:7777 --env-file .env megalith
   ```

3. **Docker Compose**:
   ```bash
   docker-compose up -d
   ```

## Troubleshooting

### Common Issues

1. **Playwright Browser Issues**:
   ```bash
   # Reinstall browsers
   uv run playwright install
   
   # Install system dependencies (if needed)
   uv run playwright install-deps
   ```

2. **Import Path Issues**:
   ```bash
   # Ensure running from project root
   # Use 'uv run' prefix for all commands
   
   # Check PYTHONPATH if needed
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

3. **Permission Issues**:
   ```bash
   # Fix data directory permissions
   chmod -R 755 data/
   chmod -R 755 logs/
   ```

4. **Memory Issues**:
   - Reduce batch size in settings
   - Enable checkpointing for large datasets
   - Monitor with performance logs

5. **Network/Scraping Issues**:
   - Check rate limits and retry configurations
   - Verify user-agent strings
   - Consider VPN for geo-restricted content

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export LOGGING__LEVEL=DEBUG

# Or edit .env file
LOGGING__LEVEL=DEBUG
```

### Health Checks

- **Dashboard Health**: `http://localhost:7777/health`
- **ETL Status**: Check `data/metrics/etl_runs_latest.json`
- **Logs**: All logs in `logs/` directory with timestamp rotation

### Performance Monitoring

1. **ETL Performance**:
   - Check run summaries for duration metrics
   - Monitor memory usage in logs
   - Use performance logger outputs

2. **Dashboard Performance**:
   - Monitor browser console for errors
   - Check data loading times
   - Review caching strategies

## References

### Internal Documentation

- **ETL Development**: `src/etl/base.py` docstrings
- **Watcher Development**: `src/watchers/README.md`
- **Configuration**: `src/config/models.py` field definitions
- **API Documentation**: Auto-generated from type hints and docstrings

### External Resources

- **UV Documentation**: https://github.com/astral-sh/uv
- **Playwright**: https://playwright.dev/python/
- **Dash Documentation**: https://dash.plotly.com/
- **Prefect**: https://docs.prefect.io/
- **Pydantic**: https://pydantic-docs.helpmanual.io/
- **Polars**: https://pola-rs.github.io/polars/

### Best Practices

- Always use UV for dependency management
- Implement comprehensive error handling
- Add metrics for all operations
- Use checkpoints for long-running processes
- Follow type hinting conventions
- Write tests for new components
- Document custom watchers and ETLs
- Use environment variables for configuration

---

## Contributing to This Guide

This CONTINUE.md file is designed to help AI assistants and developers understand and work with the MEGALITH project. When making changes:

1. Keep it up-to-date with architectural changes
2. Add examples for new features
3. Update troubleshooting sections based on common issues
4. Maintain the consistent structure and formatting

For additional component-specific documentation, create separate `rules.md` files in relevant subdirectories within `.continue/rules/`.