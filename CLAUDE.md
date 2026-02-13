# CLAUDE.md

Comprehensive guidance for **Watchtower** (MEGALITH) - a sophisticated 3-layer data intelligence platform (ETL → Watchers → Dashboard).

## Core Architecture

-   **ETL Framework**: Template Method pattern (`BaseETL` in `src/etl/base.py`). Features metrics, checkpointing, circuit breakers, and proxy rotation. 22+ domain pipelines.
-   **Watchers**: Event-driven monitoring (`BaseWatcher`) with state persistence (`data/watchers/`).
-   **Dashboard**: Dual interface. Primary: Dash (port **7780**, `src/web/dashboard/`). Legacy: Streamlit (port 8501).
-   **Data Storage**: JSON-based in `data/` (timestamped outputs, checkpoints, logs).
-   **Configuration**: Pydantic Settings (`src/config/settings.py`) with environment variables (`COMPONENT__SETTING`).
-   **Data Models**: 38 Pydantic model files in `src/models/`.

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
| **Dashboard** | `uv run python run_watchtower_dashboard.py` (port **7780**) |
| **Testing** | `uv run pytest` (Coverage: `uv run pytest --cov=src --cov-report=html`) |
| **Linting** | `uv run ruff check .` / `uv run ruff format .` |
| **Deploy** | `uv run --with paramiko deployment/deploy.py` |

## Key Components & Patterns

### ETL Modules (`src/etl/`)
-   **22+ domains**: `adhd`, `ai_platforms`, `anime`, `arxiv`, `courses`, `ecommerce`, `entertainment`, `expanded`, `factory`, `fourchan`, `games`, `github`, `goldigging`, `intelligence`, `museums`, `neurodivergent`, `news`, `opensource`, `spanish_public_aid`, `youtube_shorts`.
-   **Intelligence**: `sec_edgar_rss.py`, `lesswrong_etl.py`, `who_outbreaks_rss.py`.
-   **News**: Aggregators for Reddit, HackerNews, TechCrunch, Lobste.rs, Microsiervos.
-   **Platform Monitoring**: AI Platforms (OpenAI, Anthropic, Replicate), GitHub Trends.
-   **Pattern**: Inherit `BaseETL` -> Implement `extract`, `transform`, `load`.
-   **Resilience**: Circuit breaker (`circuit_breaker.py`), proxy rotation (`proxy_manager.py`).

### Dashboard (~25 tabs, `src/web/dashboard/components/`)
-   ArXiv Research, News, Games, Entertainment, Courses, Crypto, Knowledge Garden, Intelligence, GitHub Trending, Anime, Videos, Museums, E-commerce, 4chan, Open Source, Spanish Public Aid, Valencia Events, Travel, Scavenging, Metrics, Notifications, Recommendations, Shortcuts, Watchers.

### Knowledge Garden (`knowledge_garden_tab.py`)
-   **Sources**: LessWrong, Good Devs, Reddit (AI/ML, DevOps), Git Trends.
-   **Pattern**: Repository-based loading (`KnowledgeGardenRepository`) with caching.

### Deployment
-   **Script**: `uv run --with paramiko deployment/deploy.py` (Deploys to Unraid).

---

## ETL Development Recipe

```python
from src.etl.base import BaseETL
from typing import List, Dict, Any

class MyCustomETL(BaseETL[Dict[str, Any], Dict[str, Any]]):
    def extract(self) -> List[Dict[str, Any]]:
        # Data retrieval from source
        pass

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Data processing and classification
        pass

    def load(self, data: List[Dict[str, Any]]) -> None:
        # Persistence to JSON files
        pass
```

## Dashboard Tab Recipe

```python
import dash_bootstrap_components as dbc
from dash import Input, Output, html

def render_my_tab():
    return dbc.Container([
        dbc.Row([dbc.Col([
            html.H3("My Custom Tab"),
            html.Div(id="my-content")
        ])])
    ])

def register_my_callbacks(app):
    @app.callback(
        Output("my-content", "children"),
        Input("my-input", "value"),
        prevent_initial_call=True
    )
    def update_content(input_value):
        try:
            return f"Updated: {input_value}"
        except Exception as e:
            return f"Error: {str(e)}"
```

## Data Storage Structure

```
data/
├── {component_name}/output/
│   ├── {component_name}_{timestamp}.json
│   ├── {component_name}_latest.json
│   └── run_summary_latest.json
├── watchers/{watcher_name}/
│   ├── state.json
│   └── events/{timestamp}_{event_type}.json
└── metrics/etl_runs_latest.json
```

## Data Models (`src/models/`)

-   **Base**: `TimestampedModel`, `StatusModel`, `ErrorModel`, `PaginatedResponse`
-   **Domain**: `ArxivPaperModel`, `TechnologyModel`, `GameDealModel`, `AnimeModel`, `CourseModel`, `NewsArticleModel`, `SecurityModel`, and 30+ more
-   **Enums**: `TrendDirection`, `AdoptionLevel`, `SecuritySeverity`, `ContentLanguage`

## Architecture Patterns

-   **Template Method**: `BaseETL.run()` orchestrates ETL phases
-   **Factory Pattern**: `get_settings()` with `@lru_cache` singleton
-   **State Pattern**: Watcher state management with JSON persistence
-   **Component Pattern**: Dash modular tab architecture
-   **Manager Pattern**: Centralized data handling (e.g., `VideoManager`)

## Advanced Interaction Patterns

-   **"I'll tip you $..."**: Maximize depth and robustness.
-   **"Bet you can't..."**: Rigorous verification/proof required.
-   **"Take a deep breath..."**: Trigger Chain-of-Thought processing.
-   **"Important to my career..."**: High-Assurance Mode (safety first).
-   **"Rate your confidence..."**: Strict 0.0-1.0 probability estimate.
