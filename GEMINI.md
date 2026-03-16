# GEMINI.md

This file provides comprehensive guidance to **Gemini** when working with the **Watchtower** (MEGALITH) project.

## Project Overview

**Watchtower** is a sophisticated data intelligence platform that aggregates, processes, and monitors information from diverse sources (ArXiv, GitHub, Reddit, YouTube, museums, e-commerce, etc.). It uses a **3-Layer Architecture**:
1.  **ETL Framework**: Extracts, transforms, and loads data from 22+ domain pipelines.
2.  **Watchers**: Event-driven monitoring with state persistence.
3.  **Dashboard**: Dual interface (Dash + legacy Streamlit) for visualization with ~25 interactive tabs.

## Core Technologies & Standards

-   **Package Manager**: **`uv`** is the standard. ALWAYS use `uv run <command>` for Python scripts.
-   **Language**: Python 3.10+ (Strict type hints required).
-   **Configuration**: Pydantic Settings (`src/config/settings.py`).
-   **Data Models**: Pydantic BaseModels (`src/models/`) — 38 model files across all domains.
-   **Storage**: JSON files in `data/` (efficient, file-based).
-   **Testing**: `pytest` (run via `uv run pytest`).
-   **Resilience**: Circuit breaker (`src/etl/circuit_breaker.py`) and proxy rotation (`src/etl/proxy_manager.py`).

## Development Commands (UV)

**Always use `uv` for these operations:**

```bash
# Install dependencies
uv sync --all-extras

# Run Tests
uv run pytest
uv run pytest Tests/etl/  # Specific category

# Run Linting/Formatting
uv run ruff check .
uv run ruff format .

# Run Dashboard (Dash - Recommended)
uv run python run_watchtower_dashboard.py
# Access at http://localhost:7780

# Run Legacy Dashboard (Streamlit)
uv run streamlit run src/web/fullstreamlit/app.py
# Access at http://localhost:8501

# Run ETL Pipelines
./run_all_etl.sh          # Linux/Mac
.\run_all_etl.bat         # Windows
uv run python src/etl/arxiv/arxiv_etl.py  # Specific ETL

# Deploy to Unraid
uv run --with paramiko deployment/deploy.py
```

## BMM Methodology (Agentic Workflow)

This project uses the **BMad Method (BMM)** for agile development.
-   **Configuration**: `.bmad/bmm/config.yaml`
-   **Agents**: `.bmad/bmm/agents/` (e.g., `pm.md`, `dev.md`)
-   **Workflows**: `.bmad/bmm/workflows/`

**To adopt a persona:**
1.  Read the agent file (e.g., `read_file .bmad/bmm/agents/dev.md`).
2.  Follow the "Activation" steps in the file.
3.  Use the defined menu commands (e.g., `*develop-story`).

**Key Workflows:**
-   **Development**: Use the `dev` agent and `*develop-story`.
-   **Planning**: Use the `pm` agent and `*create-prd`.


## Architecture Details

### 1. ETL Framework (`src/etl/base.py`)
-   **Pattern**: Template Method (`extract` -> `transform` -> `load`).
-   **Features**: Metrics (`ETLMetrics`), Checkpointing, Retry Logic, Circuit Breaker, Proxy Rotation.
-   **Output**: `data/{etl_name}/output/`.
-   **Domains** (22+ subdirectories): `adhd`, `ai_platforms`, `anime`, `arxiv`, `courses`, `ecommerce`, `entertainment`, `expanded`, `factory`, `fourchan`, `games`, `github`, `goldigging`, `intelligence`, `museums`, `neurodivergent`, `news`, `opensource`, `spanish_public_aid`, `youtube_shorts`, and more.

### 2. Watchers (`src/watchers/base_watcher.py`)
-   **Pattern**: Event-driven loop.
-   **State**: `data/watchers/{name}/state.json`.
-   **Events**: `data/watchers/{name}/events/`.

### 3. Dashboard (`src/web/dashboard/`)
-   **Framework**: Dash + Bootstrap (port **7780**).
-   **Key Rule**: **Single Callback Pattern** (one callback per output to avoid conflicts).
-   **Data**: Loads from JSON files (lazy loading + caching).
-   **Tabs** (~25): ArXiv Research, News, Games, Entertainment, Courses, Crypto, Knowledge Garden, Intelligence, GitHub Trending, Anime, Videos, Museums, E-commerce, 4chan, Open Source, Spanish Public Aid, Valencia Events, Travel, Scavenging, Metrics, Notifications, Recommendations, Shortcuts, and more.
-   **Feature**: **Knowledge Garden** (`knowledge_garden_tab.py`) aggregates dev communities (LessWrong, Reddit, etc.) using Repository pattern.

## Critical Rules for Gemini

1.  **UV First**: Never suggest `pip install` or `python script.py` directly. Always use `uv run`.
2.  **Pydantic**: Use Pydantic for all data structures and configuration.
3.  **Type Hints**: Enforce strict type hints in all new code.
4.  **File Paths**: Use absolute paths or project-relative paths carefully. The project root is auto-detected.
5.  **Aesthetics**: When touching the UI (Dash), ensure it looks premium and modern (Bootstrap). Keep layouts minimalist, semantic, and highly responsive.
6.  **Dash Pattern Strictness**: STRICT adherence to the Single-Callback Pattern. Never have two callbacks target the same React prop/output to avoid conflicts.
7.  **Resilient ETLs**: Always subclass `BaseETL`, implement retry logic, checkpointing, and handle rate limits. Pydantic is strictly enforced.
8.  **Dashboard Port**: The Dash dashboard runs on port **7780**.

## Workflows

### 1. Run All ETLs
Executes all configured ETL pipelines to refresh data.
-   **Command**: `.\run_all_etl.bat` (Windows) or `./run_all_etl.sh` (Linux/Mac)

### 2. Start Dashboard
Starts the main Dash interface.
-   **Command**: `uv run python run_watchtower_dashboard.py`

### 3. Run Tests
Executes the test suite.
-   **Command**: `uv run pytest`

### 4. Add New ETL
1.  Create class inheriting from `BaseETL`.
2.  Implement `extract`, `transform`, `load`.
3.  Add to `run_all_etl` scripts if needed.

### 5. Deploy to Unraid
-   **Command**: `uv run --with paramiko deployment/deploy.py`

## Advanced Interaction Patterns

The following user patterns represent specific intent signals. Recognize and adapt behavior accordingly:

1.  **Incentive Signal** ("I'll tip you $..."): Interpret as a request for **maximum depth and thoroughness**. Explore edge cases and provide the most robust solution possible.
2.  **Challenge Protocol** ("Bet you can't..."): Interpret as a request for **rigorous verification**. Provide proof of correctness and explicitly validate assumptions.
3.  **Cognitive Decompression** ("Take a deep breath..."): Trigger **Chain-of-Thought processing**. Break down the problem into atomic steps and reason through each before generating code.
4.  **Criticality Marker** ("Important to my career..."): Activate **High-Assurance Mode**. Prioritize safety, check for destructive side effects, and warn about potential risks.
5.  **Confidence Calibration** ("Rate your confidence..."): Provide a strict **0.0-1.0 probability estimate**. If <0.9, list specific risk factors and alternative approaches.
