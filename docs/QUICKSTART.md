# Watchtower Quickstart Guide

Get up and running with Watchtower in 10 minutes.

## Prerequisites

- Python 3.10 or higher
- Git
- 5-10 GB free disk space

## Quick Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/josmerod/watchtower.git
cd watchtower

# Install UV package manager (10-100x faster than pip)
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates virtual environment automatically)
# The dev tools (ruff, pytest, mypy, pre-commit) are included
uv sync

# Install the git hooks (commit and push stages). Mandatory before you commit.
uv run pre-commit install --hook-type pre-commit --hook-type pre-push

# Install browser dependencies
uv run playwright install
```

### 2. Configure (Optional)

```bash
# Copy example environment file (if exists)
cp .env.example .env

# Edit .env with your API keys (optional for basic usage)
# nano .env
```

### 3. Run Your First ETL

```bash
# Collect Hacker News stories
uv run python src/etl/news/news_get_ycombinator.py

# Collect ArXiv research papers
uv run python src/etl/arxiv/arxiv_etl.py

# Collect game deals
uv run python src/etl/games/games_get_deals.py
```

### 4. Launch the Dashboard

```bash
# Start the main Watchtower dashboard
uv run python run_watchtower_dashboard.py

# Open browser to: http://localhost:7780
```

## What's Next?

### Run All ETL Pipelines

```bash
# Needs Bash
./run_all_etl.sh
```

### Start Watchers

```bash
# List available watchers
uv run python src/watchers/run_watcher.py --list

# Run specific watcher once
uv run python src/watchers/run_watcher.py ms_applied_skills --once

# Run all watchers continuously
uv run python src/watchers/run_watcher.py
```

### Explore the Data

All collected data is stored in `data/` directory:

```bash
# View the Hacker News output (written by the first ETL above)
ls data/hackernews/

# View ArXiv papers
ls data/arxiv/

# View game deals
ls data/games/
```

## Common First Tasks

### 1. Customize Your News Sources

Edit `src/etl/news/` to add or remove news sources.

### 2. Set Up Scheduling

In production the container's scheduler (`deployment/etl_scheduler.py`) runs all ETLs on start and then every 2 hours. Locally, schedule `./run_all_etl.sh` with cron or Task Scheduler.

### 3. Configure Watchers

Set up continuous monitoring for important sources (see [Watchers Guide](technical/WATCHERS_GUIDE.md)).

### 4. Explore the Dashboard

The dashboard provides interactive views of all collected data with filtering and search capabilities.

## Need Help?

- **Documentation Index**: [INDEX.md](INDEX.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Technical Docs**: [docs/technical/](technical/)
- **FAQ**: [FAQ.md](FAQ.md)
- **Issues**: [GitHub Issues](https://github.com/josmerod/watchtower/issues)

## Troubleshooting Quick Fixes

### UV Command Not Found

Restart your terminal after UV installation to update PATH.

### Playwright Install Fails

```bash
# Install system dependencies (Linux)
sudo apt-get install -y libgbm1 libnss3 libnspr4 libatk1.0-0

# Try install again
uv run playwright install
```

### Dashboard Won't Start

```bash
# Check if port 7780 is in use
# Windows
netstat -ano | findstr :7780

# Linux/macOS
lsof -i :7780

# Use a different port (the port is read from the WATCHTOWER_DASHBOARD_PORT environment variable)
WATCHTOWER_DASHBOARD_PORT=8888 uv run python run_watchtower_dashboard.py
```

### No Data Appears

Run ETL pipelines first to collect data:

```bash
./run_all_etl.sh
```

## Next Steps

Once you have the basics running:

1. Read the [Contributing Guide](CONTRIBUTING.md) for the development workflow
2. Explore [ETL Development Guide](technical/ETL_DEVELOPMENT_GUIDE.md) to create custom pipelines
3. Deploy it: see [Docker & Unraid Deployment](../README.md#docker--unraid-deployment) in the README
4. Configure [watchers](technical/WATCHERS_GUIDE.md) for change detection

Happy monitoring! 🎯
