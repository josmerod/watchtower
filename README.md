# Watchtower (MEGALITH)

**A comprehensive data intelligence platform for scraping, aggregating, and visualizing data from 50+ diverse online sources.**

Watchtower automates data collection from news sites, research platforms, game stores, course providers, AI platforms, and more. It features robust ETL pipelines, event-driven watchers, and a modern Dash-based dashboard for real-time visualization.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Docker & Unraid Deployment](#docker--unraid-deployment)
- [Development Standards](#development-standards)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

Watchtower is an integrated solution for automated data acquisition, processing, and monitoring:

-   **Automated Data Collection**: 22+ ETL pipelines scraping data from ArXiv, GitHub, Reddit, YouTube, game stores, course platforms, AI platforms, museums, and more.
-   **Change Detection**: Event-driven watchers monitor web pages for content changes with state persistence.
-   **Interactive Dashboard**: Modern Dash-based interface with ~25 tabs, Bootstrap styling, and real-time data loading.
-   **Resilience**: Circuit breakers, proxy rotation, retry logic, and checkpointing for reliable operation.

## Features

### ETL Pipelines (22+ Domains)
-   **Research & Intelligence**: ArXiv papers, AI platforms (OpenAI, Anthropic, HuggingFace, Replicate), ADHD research, SEC filings, WHO outbreaks, LessWrong
-   **News & Social**: HackerNews, Reddit (30+ subreddits), TechCrunch, Lobste.rs, Medium, 4chan
-   **Gaming & Entertainment**: Game deals, free games, Metacritic, cinema, anime, Spotify, Trakt, YouTube Shorts
-   **Education**: Udemy, Coursera, DeepLearning.AI, Pluralsight
-   **E-commerce & Deals**: Multi-platform deal aggregation, museum exhibitions, scavenging
-   **Regional**: Spanish public aid, Valencia events

### Watchers
-   Extensible `BaseWatcher` system for continuous monitoring
-   JSON state persistence and event logging

### Dashboard (~25 Tabs)
-   Primary: **Dash** (port **7780**) with Bootstrap styling
-   Legacy: Streamlit (port 8501)
-   Tabs: ArXiv, News, Games, Entertainment, Courses, Crypto, Knowledge Garden, Intelligence, GitHub Trending, Anime, Videos, Museums, E-commerce, 4chan, Open Source, Spanish Public Aid, Valencia Events, Travel, Scavenging, Metrics, Notifications, Recommendations, Shortcuts, Watchers

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.10+ |
| **Package Manager** | UV (10-100x faster than pip) |
| **Data Processing** | pandas, polars, NumPy, scikit-learn |
| **Web Dashboard** | Dash + Bootstrap (primary), Streamlit (legacy) |
| **Web Scraping** | Playwright, BeautifulSoup4, feedparser, cloudscraper |
| **Configuration** | Pydantic Settings with nested validation |
| **Data Models** | 38 Pydantic model files |
| **Storage** | JSON files (timestamped, file-based) |
| **Quality** | Ruff (lint/format), mypy (types), pytest (testing) |
| **Containerization** | Docker + docker-compose |

## Project Structure

```
watchtower/
├── src/
│   ├── config/              # Pydantic settings management
│   ├── etl/                 # 22+ ETL pipeline domains
│   │   ├── base.py          # BaseETL framework (Template Method)
│   │   ├── circuit_breaker.py  # Failure isolation
│   │   ├── proxy_manager.py    # IP rotation
│   │   ├── arxiv/           # Research papers
│   │   ├── ai_platforms/    # OpenAI, Anthropic, Replicate, etc.
│   │   ├── news/            # HackerNews, Reddit, TechCrunch, etc.
│   │   ├── games/           # Game deals and releases
│   │   ├── intelligence/    # SEC, LessWrong, WHO, startups, etc.
│   │   ├── entertainment/   # Cinema, Spotify, Trakt
│   │   ├── goldigging/      # Courses (Udemy, Coursera, etc.)
│   │   ├── ecommerce/       # E-commerce deals
│   │   ├── museums/         # Museum exhibitions
│   │   ├── youtube_shorts/  # YouTube video processing
│   │   └── ...              # adhd, anime, fourchan, opensource, etc.
│   ├── models/              # 38 Pydantic data models
│   ├── watchers/            # Event-driven monitoring
│   ├── web/
│   │   ├── dashboard/       # Dash dashboard (primary, port 7780)
│   │   │   ├── app.py       # Main app with tab container
│   │   │   └── components/  # ~25 tab components
│   │   └── fullstreamlit/   # Legacy Streamlit dashboard
│   ├── miners/              # Specialized scrapers (Udemy, Steam ASF)
│   ├── intelligence/        # AI enrichment engine
│   ├── recommendations/     # Content recommendation system
│   └── utils/               # Shared utilities (NLP, file system, logging)
├── data/                    # JSON data storage (timestamped outputs)
├── docs/                    # Project documentation
├── Tests/                   # pytest test suite
├── deployment/              # Unraid deployment scripts
├── run_watchtower_dashboard.py  # Dashboard entry point
├── run_all_etl.bat/.sh      # Batch ETL execution
└── pyproject.toml           # Project config and dependencies
```

## Installation

### Prerequisites

-   Python 3.10+
-   [UV](https://github.com/astral-sh/uv) (recommended package manager)

### Setup

```bash
# Clone
git clone https://github.com/yourusername/watchtower.git
cd watchtower

# Install UV (if needed)
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync --all-extras

# Install Playwright browsers (for web scraping)
uv run playwright install
```

## Usage

### Dashboard

```bash
# Main Dash dashboard (recommended)
uv run python run_watchtower_dashboard.py
# → http://localhost:7780

# Legacy Streamlit dashboard
uv run streamlit run src/web/fullstreamlit/app.py
# → http://localhost:8501
```

### ETL Pipelines

```bash
# Run all ETL pipelines
.\run_all_etl.bat         # Windows
./run_all_etl.sh          # Linux/Mac

# Run a specific ETL
uv run python src/etl/arxiv/arxiv_etl.py
uv run python src/etl/news/news_get_ycombinator.py
```

### Watchers

```bash
# Run all watchers continuously
uv run python src/watchers/run_watcher.py

# Run a specific watcher once
uv run python src/watchers/run_watcher.py arxiv_watcher --once

# List available watchers
uv run python src/watchers/run_watcher.py --list
```

### Testing & Quality

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Lint and format
uv run ruff check .
uv run ruff format .
```

## Docker & Unraid Deployment

### Docker

```bash
# Build
docker build -t watchtower-app .

# Run
docker run -p 7780:7780 --env-file .env watchtower-app
```

### Unraid

```bash
# Deploy to Unraid server
uv run --with paramiko deployment/deploy.py
```

Pre-configured volume mappings:
```yaml
volumes:
  - /mnt/user/appdata/watchtower/data:/app/data
  - /mnt/user/appdata/watchtower/logs:/app/logs
  - /mnt/user/appdata/watchtower/secrets:/app/secrets:ro
```

## Development Standards

-   **UV First**: Always use `uv run` — never `pip install` or bare `python`
-   **Type Hints**: Full Python 3.10+ annotations required
-   **Code Style**: PEP 8 via Ruff, Google-style docstrings
-   **Pydantic**: All data structures and configuration use Pydantic models
-   **Dash UI**: Single Callback Pattern, Bootstrap components, error boundaries
-   **Testing**: pytest with focus on ETL logic and data processing

### Architecture Patterns

-   **Template Method**: `BaseETL.run()` orchestrates extract → transform → load
-   **Factory Pattern**: `get_settings()` with `@lru_cache` singleton
-   **State Pattern**: Watcher state management with JSON persistence
-   **Component Pattern**: Modular Dash tab architecture
-   **Repository Pattern**: Knowledge Garden data loading

## Contributing

1.  Fork the repository
2.  Create a feature branch: `git checkout -b feature/your-feature`
3.  Follow [Development Standards](#development-standards)
4.  Write tests for new code
5.  Run quality checks: `uv run ruff check . && uv run pytest`
6.  Submit a Pull Request

## Troubleshooting

-   **Dashboard not loading**: Check that port 7780 is free. Run `uv run python run_watchtower_dashboard.py` and check console output.
-   **Playwright issues**: Run `uv run playwright install` to install browser binaries.
-   **Dependency conflicts**: Delete `.venv/` and run `uv sync --all-extras` for a clean install.
-   **ETL failures**: Check `data/{etl_name}/output/` for error logs and `logs/` for detailed output.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
