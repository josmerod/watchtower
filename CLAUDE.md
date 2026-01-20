# CLAUDE.md

Comprehensive guidance for **Watchtower** (MEGALITH) - a sophisticated 3-layer data intelligence platform (ETL → Watchers → Dashboard).

## Core Architecture

-   **ETL Framework**: Template Method pattern (`BaseETL` in `src/etl/base.py`). Features metrics, checkpointing, circuit breakers, and proxy rotation.
-   **Watchers**: Event-driven monitoring (`BaseWatcher`) with state persistence (`data/watchers/`).
-   **Dashboard**: Dual interface. Primary: Dash (port 7778, `src/web/dashboard/`). Legacy: Streamlit (port 8501).
-   **Data Storage**: JSON-based in `data/` (timestamped outputs, checkpoints, logs).
-   **Configuration**: Pydantic Settings (`src/config/settings.py`) with environment variables (`COMPONENT__SETTING`).

## Development Standards (Critical)

1.  **UV First**: ALWAYS use `uv run <command>` (e.g., `uv run python script.py`, `uv run pytest`).
2.  **Type Hints**: Strict Python 3.10+ typing required.
3.  **Code Style**: Ruff for linting/formatting. Google-style docstrings.
4.  **UI Design**: Dash components must look premium (Bootstrap). Use **Single Callback Pattern** to avoid conflicts.
5.  **Pathing**: Use `src.utils.file_system.get_project_root()` for robust path resolution.

## Common Interface Commands

| Action | Command |
| :--- | :--- |
| **All ETLs** | `./run_all_etl.sh` / `.\run_all_etl.bat` |
| **Dashboard** | `uv run python run_watchtower_dashboard.py` |
| **Testing** | `uv run pytest` (Coverage: `uv run pytest --cov=src --cov-report=html`) |
| **Linting** | `uv run ruff check .` / `uv run ruff format .` |

## Key Components & Patterns

### ETL Modules (`src/etl/`)
-   **Intelligence**: `sec_edgar_rss.py`, `lesswrong_etl.py`, `who_outbreaks_rss.py`.
-   **News**: Aggregators for Reddit, HackerNews, TechCrunch, etc.
-   **Platform Monitoring**: AI Platforms (OpenAI, Anthropic), GitHub Trends.
-   **Pattern**: Inherit `BaseETL` -> Implement `extract`, `transform`, `load`.

### Knowledge Garden (`src/web/dashboard/components/knowledge_garden_tab.py`)
-   **Sources**: LessWrong, Good Devs, Reddit (AI/ML, DevOps), Git Trends.
-   **Pattern**: Repository-based loading (`KnowledgeGardenRepository`) with caching.

### Deployment
-   **Script**: `uv run --with paramiko deployment/deploy.py` (Deploys to Unraid).

## Advanced Interaction Patterns

-   **"I'll tip you $..."**: Maximize depth and robustness.
-   **"Bet you can't..."**: Rigorous verification/proof required.
-   **"Take a deep breath..."**: Trigger Chain-of-Thought processing.
-   **"Important to my career..."**: High-Assurance Mode (safety first).
-   **"Rate your confidence..."**: Strict 0.0-1.0 probability estimate.
