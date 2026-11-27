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

-   **Automated Data Collection**: 22 ETL domains (98 scripts in the ETL orchestrator's list) scraping data from ArXiv, GitHub, Reddit, game stores, course platforms, AI platforms, security feeds, and more.
-   **Change Detection**: Event-driven watchers monitor web pages for content changes with state persistence.
-   **Interactive Dashboard**: Modern Dash-based interface with 18 tabs, Bootstrap styling, and real-time data loading.
-   **JSON API**: A read-only FastAPI service serving the collected feeds under `/api/v1`.
-   **Resilience**: `BaseETL` bundles circuit breakers, proxy rotation, retry logic, and checkpointing.

## Features

### ETL Pipelines (23 Domains)
-   **Research & Intelligence**: ArXiv papers, Hugging Face daily papers, AI platforms (Replicate, Ollama), LessWrong, NVD CVEs, OpenAlex, Kaggle, ADHD research
-   **News & Social**: HackerNews, Reddit, TechCrunch, Lobste.rs, Medium, 4chan, and about 40 more feeds
-   **Gaming**: Game deals, GOG, Humble Bundles, itch.io, IsThereAnyDeal, Metacritic
-   **Education**: AWS Skill Builder, Coursera, DeepLearning.AI, GCP Skills Boost, Microsoft Applied Skills, Pluralsight, Udemy
-   **Deals & E-commerce**: Lifetimo, Gumroad, Audible releases, Humble Books, Viajeros Piratas
-   **Security & Markets**: CISA KEV, security news, OSV advisories, CoinGecko crypto quotes
-   **Benchmarks & Open Source**: LLM leaderboards and model feeds, GitHub trending, releases and end-of-life dates for a self-hosted stack, open-source projects, package registries, Stack Exchange, Hashnode, Substack, Trendshift
-   **Regional**: Spanish public aid (BDNS), Valencia events and local news

### Watchers
-   Extensible `BaseWatcher` system for continuous monitoring
-   Four watchers today: `ArxivWatcher`, `MSAppliedSkillsWatcher`, `CoursesWatcher`, `DataFreshnessWatcher`
-   JSON state persistence and event logging

### Dashboard (18 Tabs)
-   **Dash** (port **7780**) with Bootstrap styling
-   Tabs: News, Knowledge Garden, Videos, Learning, 4chan Generals, Scavenging, Valencia Events, Ayudas Públicas, ArXiv Research, Deals, Benchmarks, Markets, Security, Tech Radar, Games, Notifications, Metrics, Digest

### API
-   FastAPI service (port **45714**) with 20 GET routes: 19 under `/api/v1` plus `/health`

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.10+ |
| **Package Manager** | UV (10-100x faster than pip) |
| **Data Processing** | pandas, NumPy, scikit-learn |
| **Web Dashboard** | Dash + Bootstrap |
| **API** | FastAPI + Uvicorn |
| **Web Scraping** | Playwright, BeautifulSoup4, feedparser, cloudscraper |
| **Configuration** | Pydantic Settings with nested validation |
| **Data Models** | 19 Pydantic model modules |
| **Storage** | JSON files (timestamped, file-based) |
| **Quality** | Ruff (lint/format), mypy (types, advisory), pytest (testing), pre-commit (hooks) |
| **Containerization** | Docker + docker-compose |

## Project Structure

```
watchtower/
├── src/
│   ├── config/              # Pydantic settings management
│   ├── etl/                 # 23 ETL pipeline domains
│   │   ├── base.py          # BaseETL framework (Template Method)
│   │   ├── circuit_breaker.py  # Failure isolation
│   │   ├── proxy_manager.py    # IP rotation
│   │   ├── arxiv/           # Research papers
│   │   ├── ai_platforms/    # Replicate, Ollama
│   │   ├── news/            # HackerNews, Reddit, TechCrunch, etc.
│   │   ├── games/           # Game deals and bundles
│   │   ├── intelligence/    # LessWrong, NVD CVEs
│   │   ├── benchmarks/      # LLM leaderboards and model feeds
│   │   ├── security/        # CISA KEV, security news, OSV advisories
│   │   ├── goldigging/      # Courses (Coursera, Pluralsight, etc.) and scavenging
│   │   └── ...              # courses, deals, ecommerce, markets, spanish_public_aid, etc.
│   ├── models/              # 19 Pydantic model modules
│   ├── watchers/            # Event-driven monitoring
│   ├── api/                 # FastAPI REST API (/api/v1, /health)
│   ├── repositories/        # Cached data access for dashboard tabs
│   ├── web/
│   │   └── dashboard/       # Dash dashboard (port 7780)
│   │       ├── app.py       # Main app with tab container
│   │       └── components/  # Tab components
│   ├── miners/              # Specialized scrapers (Udemy course miner, crypto sentiment)
│   ├── intelligence/        # AI enrichment engine
│   └── utils/               # Shared utilities (NLP, file system, logging)
├── data/                    # JSON data storage (timestamped outputs)
├── docs/                    # Project documentation
├── Tests/                   # pytest test suite
├── deployment/              # Unraid deployment (Dockerfile, deploy.py, supervisord.conf)
├── run_watchtower_dashboard.py  # Dashboard entry point
├── run_all_etl.sh           # Batch ETL execution (runs run_all_etl_orchestrator.py)
└── pyproject.toml           # Project config and dependencies
```

## Installation

### Prerequisites

-   Python 3.10+
-   [UV](https://github.com/astral-sh/uv) (recommended package manager)

### Setup

```bash
# Clone
git clone https://github.com/josmerod/watchtower.git
cd watchtower

# Install UV (if needed)
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (includes the dev tools: ruff, pytest, mypy, pre-commit)
uv sync

# Install the git hooks (commit and push stages). Mandatory before you commit.
uv run pre-commit install --hook-type pre-commit --hook-type pre-push

# Install Playwright browsers (only needed by the browser-backed ETLs)
uv run playwright install
```

## Usage

### Dashboard

```bash
# Dash dashboard
uv run python run_watchtower_dashboard.py
# → http://localhost:7780
```

### API

```bash
# FastAPI service
uv run uvicorn src.api.main:app --port 45714
# → http://localhost:45714/docs (interactive docs), /health, /api/v1/*
```

### ETL Pipelines

```bash
# Run all ETL pipelines (4 workers; needs Bash)
./run_all_etl.sh

# Run a specific ETL
uv run python src/etl/arxiv/arxiv_etl.py
uv run python src/etl/news/news_get_ycombinator.py
```

### Watchers

```bash
# List the watchers the runner can launch (today: ms_applied_skills)
uv run python src/watchers/run_watcher.py --list

# Run a specific watcher once
uv run python src/watchers/run_watcher.py ms_applied_skills --once

# Run every registered watcher continuously
uv run python src/watchers/run_watcher.py
```

`MSAppliedSkillsWatcher`, `CoursesWatcher` and `DataFreshnessWatcher` each run once per invocation and are steps of the ETL cycle; `ArxivWatcher` is a component of the ArXiv ETL.

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

No credentials required for a base deploy — all API keys are optional (affected ETLs fail soft / fall back).

```bash
git clone https://github.com/josmerod/watchtower.git && cd watchtower
cp .env.example .env   # defaults work; add API keys later for more sources
# or: touch .env

# Compose (dashboard :7777 + API :45714)
docker compose up -d --build

# Plain docker
docker build -t watchtower-app .
docker run -p 7780:7780 -p 45714:45714 --env-file .env watchtower-app
```

The container starts the dashboard, the API and the ETL scheduler together; the scheduler runs every ETL as soon as it starts and then every 2 hours by default (`WATCHTOWER_ETL_INTERVAL`, in seconds).

Secrets differ between the two Docker paths. The root `Dockerfile` (used by both `docker compose` and the plain `docker build` above) copies `./secrets/` into the image, and `docker-compose.yml` also mounts `./secrets` read-only. The Unraid path below (`deployment/Dockerfile` + `deploy.py`) ships no secrets as files: `.env` and `secrets/` are not part of the deploy archive, and only the `data` and `logs` volumes are mounted. API keys reach that container only through the allowlist `CONTAINER_ENV_KEYS` in `deployment/deploy.py` — the ones set in `.env` are passed with `docker run --env-file` (names in `.env.example`), and nothing else from `.env` travels.

### Unraid

```bash
# Deploy to the Unraid server (connection settings come from .env: UNRAID_HOST, UNRAID_USER, UNRAID_PASSWORD or an SSH key)
uv run --with paramiko python deployment/deploy.py
```

`deploy.py` archives the working tree, uploads it, builds the image on the server, starts the container and waits for its health check; if the new container does not become healthy it rolls back to the previous image.

Volume mappings used by `deploy.py`:
```yaml
volumes:
  - /mnt/user/appdata/watchtower/data:/app/data
  - /mnt/user/appdata/watchtower/logs:/app/logs
```

## Development Standards

-   **UV First**: Always use `uv run` — never `pip install` or bare `python`
-   **Type Hints**: Full Python 3.10+ annotations required
-   **Code Style**: PEP 8 via Ruff, Google-style docstrings
-   **Pydantic**: All data structures and configuration use Pydantic models
-   **Dash UI**: Single Callback Pattern, Bootstrap components, error boundaries
-   **Testing**: pytest with focus on ETL logic and data processing
-   **AI agents**: `AGENTS.md` holds the commands and conventions for AI coding agents working in this repository

### Architecture Patterns

-   **Template Method**: `BaseETL.run()` orchestrates extract → transform → load
-   **Singleton**: `get_settings()` with `@lru_cache`
-   **State Pattern**: Watcher state management with JSON persistence
-   **Component Pattern**: Modular Dash tab architecture
-   **Repository Pattern**: Cached data loading in six dashboard components (see `docs/REPOSITORY_PATTERN.md`)

## Contributing

1.  Fork the repository
2.  Create a branch: `git checkout -b feat/your-feature` (prefixes: `feat/`, `fix/`, `chore/`, `docs/`)
3.  Follow [Development Standards](#development-standards)
4.  Write tests for new code
5.  Run `uv run pre-commit run --all-files` and `uv run pytest`
6.  Submit a Pull Request

Read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for the full workflow. Open work is tracked in [docs/TASK_BOARD.md](docs/TASK_BOARD.md).

## Troubleshooting

-   **Dashboard not loading**: Check that port 7780 is free. Run `uv run python run_watchtower_dashboard.py` and check console output.
-   **Playwright issues**: Run `uv run playwright install` to install browser binaries.
-   **Dependency conflicts**: Delete `.venv/` and run `uv sync` for a clean install.
-   **ETL failures**: Check `data/{etl_name}/output/` for error logs and `logs/` for detailed output.

## License

`pyproject.toml` declares an MIT license, but the repository does not include a `LICENSE` file.
