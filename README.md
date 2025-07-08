# MEGALITH

**A comprehensive monitoring and ETL framework for scraping, aggregating, and visualizing data from diverse online sources.**

MEGALITH is designed to automate the collection of information from news sites, game deal aggregators, online course platforms, and other web content. It features robust ETL (Extract, Transform, Load) pipelines, intelligent watchers for monitoring content changes, an orchestrator for managing and scheduling tasks, and a user-friendly Streamlit web dashboard for real-time data visualization and interaction.

## Table of Contents

- [MEGALITH](#megalith)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
  - [Technologies Used](#technologies-used)
  - [Project Structure](#project-structure)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Clone the Repository](#clone-the-repository)
    - [Set up Development Environment](#set-up-development-environment)
      - [Using Poetry (Recommended)](#using-poetry-recommended)
      - [Using venv (Alternative)](#using-venv-alternative)
    - [Install Dependencies](#install-dependencies)
    - [Install Playwright Browsers](#install-playwright-browsers)
  - [Configuration](#configuration)
  - [Usage](#usage)
    - [Running ETL Pipelines](#running-etl-pipelines)
    - [Running Watchers](#running-watchers)
    - [Running Workflows with Prefect](#running-workflows-with-prefect)
    - [Decommissioning the Old Orchestration System](#decommissioning-the-old-orchestration-system)
    - [Launching the Web Dashboard](#launching-the-web-dashboard)
  - [Docker](#docker)
  - [Scheduling and Automation (Legacy)](#scheduling-and-automation-legacy)
  - [Automated Backups](#automated-backups)
  - [Important Notes \& Known Issues (Prefect Implementation)](#important-notes--known-issues-prefect-implementation)
  - [Development Standards](#development-standards)
  - [Contributing](#contributing)
    - [Adherence to Development Standards](#adherence-to-development-standards)
    - [Code Style](#code-style)
    - [Testing](#testing)
    - [Issue Reporting](#issue-reporting)
    - [Pull Request Process](#pull-request-process)
  - [Troubleshooting](#troubleshooting)
  - [License](#license)
  - [Contact](#contact)

## Overview

MEGALITH is an integrated solution for automated data acquisition, processing, and monitoring. Its core capabilities include:

-   **Automated Data Collection**: Regularly scrapes data from various websites, including news portals, e-learning platforms, and gaming sites.
-   **Change Detection**: Monitors specified web pages for any changes in content, providing alerts or updates.
-   **Process Management**: Orchestrates multiple data collection and monitoring tasks, ensuring they run reliably and efficiently with fault tolerance.
-   **Data Visualization**: Presents aggregated data through an interactive web interface built with Streamlit, allowing for easy exploration and analysis.

This project is ideal for users who need to stay updated on specific topics, track website changes, or aggregate data for analysis, reporting, and decision-making.

## Features

-   **ETL Pipelines**:
    -   Comprehensive news scraping: Hacker News, Future Tools, Bensbites, GoodDevs, Valencia Events, Medium GenAI, arXiv papers, and more.
    -   Game Deals: Aggregates deals, bundles, and free game offerings.
    -   New Game Releases: Fetches and filters recent and upcoming game releases from RAWG.io based on Metacritic score.
    -   Online Courses: Tracks courses from platforms like Coursera and content from sources like DeepLearning.AI.
    -   **ADHD Research**: Collects and processes research papers related to ADHD from PubMed.
-   **Watchers**:
    -   Monitors web pages for content changes (e.g., Microsoft Applied Skills credentials, new arXiv submissions).
    -   Extensible `BaseWatcher` class for straightforward creation of custom watchers.
-   **Orchestration (New)**:
    -   Uses **Prefect** for defining, scheduling, and monitoring data workflows.
    -   Flow definitions are located in the `prefect_flows/` directory.
    -   Example flows like `prefect_flows/news_flow.py` (for daily news aggregation) and `prefect_flows/data_collection_flow.py` (for ArXiv and game deals) serve as templates.
-   **Web Dashboard**:
    -   Interactive Streamlit application providing a holistic view of collected data.
    -   Categorized data presentation: Shortcuts, Videos, News, Games, Courses, Watchers, and Administrative functionalities.
    -   Features include interactive data tables, search, filtering, and potentially data export.
-   **Scheduling & Automation**:
    -   Cross-platform shell (`.sh`) and batch (`.bat`) scripts for automating the execution of ETL tasks, watchers, and the dashboard.
    -   Support for setting up tasks as background processes or services (e.g., using systemd on Linux or Task Scheduler on Windows).
    -   Centralized logging for all components, typically aggregated within the `logs/` directory.
-   **Data Management**:
    -   Utilizes Polars for high-performance data manipulation and analysis, with Pandas as a secondary option.
    -   Flexible data storage solutions, adaptable for various data types and sizes.

## Technologies Used

-   **Programming Language**: Python 3.10+
-   **Web Scraping**: Playwright, Beautiful Soup, Feedparser
-   **Data Processing**: Polars (primary), Pandas (secondary), NumPy
-   **Web Dashboard**: Streamlit
-   **Dependency Management**: Poetry (preferred, using `pyproject.toml`), pip with `requirements.txt` (for compatibility)
-   **Code Formatting & Linting**: Ruff
-   **Testing**: pytest
-   **Version Control**: Git
-   **Containerization**: Docker (see `Dockerfile`)
-   **Scheduling**: System-specific tools (e.g., cron, systemd on Linux; Task Scheduler on Windows via provided scripts)

## Project Structure

```
megalith/
├── .streamlit/            # Configuration for Streamlit (if any global settings)
├── .venv/                 # Python virtual environment (typically ignored by VCS)
├── api/                   # Potential future location for FastAPI or other APIs
│   └── games/
├── data/                  # Stores raw and processed data from ETL pipelines and watchers
│   ├── arxiv/
│   ├── bensbites/
│   ├── ... (other data sources)
├── docs/                  # Project documentation, use cases
│   └── use-cases/
├── logs/                  # Centralized directory for log files from various components
├── src/                   # Source code
│   ├── data/              # Data handling utilities, data models, and connectors
│   │   └── youtube/
│   ├── etl/               # ETL (Extract, Transform, Load) pipelines for various sources
│   │   ├── arxiv/
│   │   ├── games/
│   │   ├── goldigging/
│   │   └── news/
│   ├── miners/            # Specialized or intensive data extraction tools (e.g., for Steam, Udemy)
│   │   ├── asf-winonly/
│   │   └── udemy-universal/
│   ├── orchestrator/      # Scripts for managing, scheduling, and orchestrating processes
│   │   └── logs/          # Logs specific to the orchestrator
│   ├── utils/             # Common utility functions, classes, and modules shared across the project
│   ├── watchers/          # Modules for monitoring web content changes and triggering alerts/actions
│   └── web/               # Web application components
│       └── fullstreamlit/ # Streamlit dashboard application source code
│           ├── components/  # Reusable UI components for the Streamlit app
│           ├── data/        # Data specifically cached or used by the Streamlit app
│           ├── logs/        # Logs specific to the Streamlit app
│           ├── pages/       # Individual page modules for multi-page Streamlit apps (if used)
│           ├── styles/      # CSS and styling files for the Streamlit app
│           ├── utils/       # Utility functions specific to the Streamlit app
│           └── app.py       # Main Streamlit application entry point script
├── tests/                 # Unit, integration, and end-to-end tests (using pytest)
├── .dockerignore          # Specifies files to ignore when building Docker images
├── .gitignore             # Specifies intentionally untracked files that Git should ignore
├── Dockerfile             # Defines the Docker image for building and running the application
├── LICENSE                # Project's software license (e.g., MIT License)
├── README.md              # This file: project overview, setup, and usage documentation
├── requirements.txt       # Lists Python dependencies for pip (often generated from pyproject.toml)
├── pyproject.toml         # Project metadata, dependencies (for Poetry), and tool configurations (e.g., Ruff, pytest)
├── run_all_etl.bat / .sh  # Convenience scripts to run all defined ETL pipelines
├── run_watcher.bat / .sh  # Convenience scripts to execute registered watchers
├── run_streamlit.bat / .sh # Convenience scripts to launch the Streamlit dashboard
├── setup_etl_scheduler.ps1 / .sh       # Scripts for assisting with ETL task scheduling
└── setup_streamlit_service.ps1 / .sh   # Scripts for assisting with setting up Streamlit as a service
└── ... (other configuration files, utility scripts, and documentation)
```

## Installation

### Prerequisites

-   Python 3.10 or higher
-   Git
-   [UV](https://github.com/astral-sh/uv) (Recommended - extremely fast Python package manager)
-   [Playwright](https://playwright.dev/python/) browser binaries

### Clone the Repository

```bash
git clone https://github.com/yourusername/watchtower.git  # Replace with your actual repo URL
cd watchtower
```

### Set up Development Environment

#### Using UV (Recommended - 10-100x faster)

UV is the modern Python package manager that makes dependency management extremely fast and reliable.

1.  **Install UV** (if not already installed):
    ```bash
    # Windows
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    # macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Install dependencies and set up the project:**
    ```bash
    # Install all dependencies (automatically creates virtual environment)
    uv sync --all-extras
    
    # Install Playwright browsers
    uv run playwright install
    ```

3.  **Run the project:**
    ```bash
    # All commands use 'uv run' - no manual activation needed
    uv run python src/script.py
    uv run streamlit run src/web/fullstreamlit/app.py
    ```

#### Alternative: Development Setup Script

For automatic setup including UV installation:
```bash
# This script auto-installs UV if needed and sets up everything
python install_dev.py
```

#### Legacy: Using venv (Not Recommended)

If you must use traditional methods:
```bash
python -m venv .venv

# Activate environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt
playwright install
```

### Install Playwright Browsers

```bash
# With UV (recommended)
uv run playwright install

# Or with traditional methods
playwright install
```

## Configuration

Application configuration is crucial for tailoring MEGALITH to your needs and providing necessary credentials.

-   **Environment Variables (`.env` files)**:
    -   The primary method for providing sensitive information (API keys, database URLs, etc.) and environment-specific settings.
    -   Create a `.env` file in the project root, based on `.env.example` if provided.
    -   Variables in `.env` are typically loaded automatically by Python libraries like `python-dotenv` or handled by application entry points.
-   **Configuration Files (`config.py`, YAML, JSON)**:
    -   For less sensitive, more structural configuration (e.g., lists of URLs to scrape, default parameters), look for Python-based config files (e.g., `src/config.py`) or structured files (YAML, JSON) within module directories or a central `config/` directory.
-   **Script Arguments**:
    -   Many scripts accept command-line arguments for runtime adjustments. Use the `--help` flag for specific scripts to see available options (e.g., `python src/watchers/run_watcher.py --help`).

*Consult component-specific documentation or code for detailed configuration options.*

## Usage

Ensure your virtual environment is activated (e.g., `poetry shell` or `source .venv/bin/activate`) and you are in the project root directory before running any scripts.

### Running ETL Pipelines

Individual ETL scripts are typically located in `src/etl/`.

To run an individual ETL script (example for Hacker News):
```bash
# With UV (recommended)
uv run python src/etl/news/news_get_ycombinator.py

# Or traditional method
python src/etl/news/news_get_ycombinator.py
```

To run all major ETL pipelines:
-   Windows: `.\run_all_etl.bat`
-   macOS/Linux: `bash run_all_etl.sh`

### Running Watchers

The main script for managing watchers is `src/watchers/run_watcher.py`.

To run all registered watchers continuously:
```bash
# With UV (recommended)
uv run python src/watchers/run_watcher.py

# Or traditional method
python src/watchers/run_watcher.py
```

To run a specific watcher once (e.g., `ms_applied_skills`):
```bash
# With UV (recommended)
uv run python src/watchers/run_watcher.py ms_applied_skills --once

# Or traditional method
python src/watchers/run_watcher.py ms_applied_skills --once
```

To list available watchers:
```bash
# With UV (recommended)
uv run python src/watchers/run_watcher.py --list

# Or traditional method
python src/watchers/run_watcher.py --list
```

Convenience scripts are also provided for running all watchers (typically in continuous mode):
-   Windows: `.\run_watcher.bat [optional_watcher_name]`
-   macOS/Linux: `bash run_watcher.sh [optional_watcher_name]`

### Running Workflows with Prefect

With the transition to Prefect, the orchestration and execution of ETL pipelines and other tasks are managed by Prefect flows.

1.  **Install Prefect**:
    Prefect is included in the project's dependencies. Ensure it's installed by following the main [Installation](#installation) steps (e.g., `poetry install` or `pip install -r requirements.txt`).

2.  **Start the Prefect Server**:
    To visualize flow runs, manage deployments, and see logs, start the Prefect UI server:
    ```bash
    prefect server start
    ```
    This will typically make the UI available at `http://127.0.0.1:4200`.

3.  **Define and Build Deployments**:
    Deployments are how Prefect manages scheduled or triggerable flow runs. Flow definitions are in `prefect_flows/`.

    To create a deployment for a flow (e.g., `daily_news_flow` to run daily at 8 AM):
    ```bash
    prefect deployment build ./prefect_flows/news_flow.py:daily_news_flow -n daily_news_deployment -q default --cron "0 8 * * *" --apply
    ```
    -   `./prefect_flows/news_flow.py:daily_news_flow`: Path to the Python file and the flow function name.
    -   `-n daily_news_deployment`: Name for this deployment.
    -   `-q default`: Assigns the deployment to the "default" work queue.
    -   `--cron "0 8 * * *"`: Sets a CRON schedule (e.g., daily at 8:00 AM).
    -   `--apply`: Registers the deployment with the Prefect server immediately.

    You can create similar deployments for other flows like `periodic_data_collection_flow` from `prefect_flows/data_collection_flow.py`, adjusting the schedule and parameters as needed.

4.  **Start a Prefect Agent**:
    An agent polls a work queue for scheduled or ad-hoc flow runs and executes them.
    ```bash
    prefect agent start -q default
    ```
    Ensure the agent is running in an environment where it can access the project code and necessary configurations (e.g., activated virtual environment, correct `PYTHONPATH`).

5.  **Monitoring Flow Runs**:
    Use the Prefect UI (e.g., `http://127.0.0.1:4200`) to monitor the status of flow runs, view logs, and manage deployments.

### Decommissioning the Old Orchestration System

If you were using the previous `meta_orchestrator.py` with system-level schedulers (like `launchd` on macOS or Task Scheduler on Windows), you should disable or remove those configurations:

-   **macOS (`launchd`)**:
    ```bash
    # Unload the launch agent
    launchctl unload ~/Library/LaunchAgents/com.watchtower.etl.plist
    # Optionally, delete the plist file
    # rm ~/Library/LaunchAgents/com.watchtower.etl.plist
    ```
    Verify the path to your `.plist` file if it differs.

-   **Windows (Task Scheduler)**:
    1.  Open Task Scheduler.
    2.  Navigate to the Task Scheduler Library.
    3.  Find the task previously set up for `meta_orchestrator.py` or `run_all_etl.bat`.
    4.  Right-click the task and select "Disable" or "Delete".

-   **Old Scripts**:
    It's recommended to rename or remove the old `run_all_etl.bat`/`.sh` scripts and `src/orchestrator/meta_orchestrator.py` to avoid confusion, once you have fully migrated to Prefect.

### Launching the Web Dashboard

#### Main Watchtower Dashboard (Recommended)

To start the main Watchtower Dashboard (Dash-based):
-   Windows: `.\run_watchtower_dashboard.bat` or `uv run python run_watchtower_dashboard.py`
-   macOS/Linux: `bash run_watchtower_dashboard.sh` or `uv run python run_watchtower_dashboard.py`

This will start the main dashboard at `http://localhost:7777`. This is the **primary dashboard** with all the latest features.

#### Legacy Streamlit Dashboard (Optional)

For the legacy Streamlit dashboard (if needed):
-   Windows: `.\run_watchtower.bat` 
-   macOS/Linux: `bash run_streamlit.sh`

This will start the legacy dashboard at `http://localhost:8501`.

#### Complete System Launch

To run both ETL processes and the dashboard:
-   Windows: `.\run_all_etl_and_dashboard.bat`
-   macOS/Linux: `bash run_all_etl_and_dashboard.sh`

## Docker

This project includes a `Dockerfile` for building a container image, simplifying deployment and ensuring a consistent runtime environment.

**Build the Docker Image:**
```bash
docker build -t megalith-app .
```
*Ensure your `.dockerignore` file is comprehensive to optimize build times and image size.*

**Run the Docker Container:**
```bash
# Main Watchtower Dashboard
docker run -p 7777:7777 --env-file .env watchtower-app

# Legacy Streamlit Dashboard (if needed)
docker run -p 8501:8501 --env-file .env watchtower-app
```
-   Adjust port mapping (`-p HOST_PORT:CONTAINER_PORT`) as needed.
-   Use `--env-file .env` to pass environment variables from a local `.env` file. Alternatively, pass variables individually with `-e VAR_NAME=value`.
-   For persistent data, mount volumes: `-v /path/on/host:/app/data` (adjust paths accordingly).
-   Refer to the `Dockerfile` for build stages, exposed ports, and entry points.

## Scheduling and Automation (Legacy)

The information below pertains to the older, script-based scheduling methods. **With the introduction of Prefect, it is highly recommended to use Prefect Deployments for scheduling and automation as described in the "Running Workflows with Prefect" section.**

If you are still using or maintaining parts of the older system:
-   **ETL Scheduler & Watchers**:
    -   **Linux**: Use `cron` or `systemd` timers. The `setup_etl_scheduler.sh` might provide a basic cron setup.
    -   **Windows**: Use Task Scheduler. The `setup_etl_scheduler.ps1` script likely assists.
-   **Streamlit Service**:
    -   **Linux**: Use `systemd` to run Streamlit as a background service.
    -   **Windows**: The `setup_streamlit_service.ps1` script can help.

*Review and adapt any legacy scripts if you choose to continue using them, but migration to Prefect is preferred.*

## Automated Backups

This project includes a feature to automatically back up the `/data` and `/logs` directories to Google Drive after all ETL processes are complete. This ensures data persistence and allows for versioned recovery.

For detailed setup instructions, please see [Google Drive Backup Configuration](./docs/google_drive_backup.md).

## Important Notes & Known Issues (Prefect Implementation)

-   **PapersWithCode Client**: The `paperswithcode-client` dependency is currently commented out in `requirements.txt` due to historical Pydantic v1 conflicts. Consequently, its usage within `src/etl/arxiv/arxiv_etl.py` (for enriching ArXiv papers with PwC data) is also commented out. This part of the ArXiv ETL is therefore disabled.
-   **Python Path for Flows**: The Prefect flow scripts located in `prefect_flows/` (e.g., `news_flow.py`, `data_collection_flow.py`) have had `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))` added at the beginning. This is a workaround to ensure that modules from the `src/` directory can be imported correctly when these flows are executed. For long-term stability and best practices, consider setting up the project as an installable Python package or managing `PYTHONPATH` externally.
-   **NLTK Resource Downloads**: The `src/utils/nlp_classifier.py` (used by the ArXiv ETL) now automatically attempts to download missing NLTK resources (`punkt`, `stopwords`, `wordnet`, `averaged_perceptron_tagger`, `punkt_tab`, `averaged_perceptron_tagger_eng`) if they are not found. This was added to resolve errors during flow execution.
-   **Click Dependency**: The `requirements.txt` file includes `click>=8.0,<8.2`. This specific version range for the `click` library is required by Prefect 3.x and was adjusted to resolve dependency conflicts.

## Development Standards

This project adheres to a set of development standards to ensure code quality, maintainability, and scalability. Key principles include:

-   **Pythonic Practices**: PEP 8 (enforced by Ruff), readable code, Zen of Python.
-   **Architecture**: Single responsibility, composition over inheritance, logical structure.
-   **Quality Assurance**: Comprehensive type hints, Google-style docstrings, 90%+ test coverage (pytest), robust error handling, strategic logging.
-   **Performance**: Async/await for I/O, caching, resource monitoring, optimized data structures (Polars).
-   **API Development (if applicable)**: Pydantic, dependency injection, RESTful design, OpenAPI.

Contributors are expected to familiarize themselves with and follow these standards. (Refer to `CONTRIBUTING.md` or internal documentation for full details if available).

## Contributing

We welcome contributions! Please follow these guidelines to ensure a smooth process.

1.  **Fork the Repository**: Create your fork on GitHub.
2.  **Clone Your Fork**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/megalith.git # Use your fork's URL
    cd megalith
    ```
3.  **Set up Environment**: Follow the [Installation](#installation) section, preferably using Poetry.
4.  **Create a Feature Branch**:
    ```bash
    git checkout -b feature/your-exciting-feature # or fix/issue-number
    ```
5.  **Make Changes**:
    -   Implement your feature or bug fix.
    -   Write clean, well-documented code.

### Adherence to Development Standards
-   Ensure your code aligns with the project's [Development Standards](#development-standards).
-   Pay close attention to type hinting, docstrings, and overall code structure.

### Code Style
-   **Lint and Format**: Run Ruff to check and automatically format your code before committing.
    ```bash
    ruff format .
    ruff check . --fix
    ```
-   Follow Google-style docstrings for all public modules, classes, functions, and methods.
-   Use comprehensive type annotations.

### Testing
-   Write new tests for your features or bug fixes in the `tests/` directory using `pytest`.
-   Aim for high test coverage (ideally 90%+) for new code, covering common cases and edge cases.
-   Ensure all tests pass locally before pushing:
    ```bash
    pytest
    ```
7.  **Commit Your Changes**:
    Use clear, descriptive commit messages, preferably following the [Conventional Commits](https://www.conventionalcommits.org/) specification.
    ```bash
    git add .
    git commit -m "feat: Add new analytics module for user engagement"
    # Example: git commit -m "fix: Correct data parsing error in arXiv ETL"
    ```
8.  **Push to Your Fork**:
    ```bash
    git push origin feature/your-exciting-feature
    ```
9.  **Open a Pull Request (PR)**:
    -   Submit a PR from your feature branch to the `main` (or `develop`) branch of the upstream repository.
    -   Provide a concise title and a detailed description of your changes.
    -   Reference any related GitHub issues (e.g., "Closes #123", "Fixes #456").
    -   Ensure all automated CI checks (linting, tests, etc.) pass on your PR.

### Issue Reporting

-   Use GitHub Issues to report bugs or suggest features.
-   Provide detailed information: steps to reproduce, expected behavior, actual behavior, Python version, OS, Poetry/pip version, and relevant logs or screenshots.

### Pull Request Process

-   PRs will be reviewed by maintainers. Be prepared for feedback and requests for changes.
-   Maintain communication and address review comments promptly.
-   Once approved and all checks pass, your PR will be merged. Maintainers may squash or rebase commits.

Thank you for contributing to MEGALITH!

## Troubleshooting

-   **Playwright Issues**:
    -   Ensure browsers are installed *within your active virtual environment*: `playwright install`.
    -   If running headlessly (e.g., in Docker, CI), ensure all system dependencies for browsers are met (e.g., `ldd $(which playwright)` can help identify missing libraries for the browser executables).
-   **Dependency Conflicts (Poetry)**:
    -   Try `poetry lock --no-update` to resolve without updating dependencies.
    -   If necessary, `poetry update` to update specific packages or all.
    -   Check `pyproject.toml` for version constraints.
    -   Ensure you are using a compatible Python version as defined in `pyproject.toml`.
-   **Dependency Conflicts (`pip`/`venv`)**:
    -   Ensure your virtual environment is clean and activated.
    -   Try recreating the virtual environment and reinstalling dependencies.
-   **Dashboard Not Loading**:
    -   **Main Dashboard**: Check console output when running `run_watchtower_dashboard.py`. Default port is 7777.
    -   **Legacy Dashboard**: Check console output when running Streamlit. Default port is 8501.
    -   Ensure the correct port is not blocked by a firewall or used by another application.
    -   Try UV command: `uv run python run_watchtower_dashboard.py`
-   **Script Execution Failures**:
    -   Verify paths: Ensure scripts are run from the project root or that paths within scripts are correctly relative or absolute.
    -   Permissions: Check file and directory permissions, especially for `data/` and `logs/`.
    -   Check script-specific logs in the `logs/` directory (e.g., `logs/etl_arxiv.log`, `src/orchestrator/logs/`, `src/web/fullstreamlit/logs/`) for detailed error messages.
-   **Configuration Errors**:
    -   Ensure `.env` file is present in the root and correctly formatted if used.
    -   Verify API keys and other credentials are correct and have the necessary permissions.

*Add more common issues and solutions as they are identified.*

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
(If a `LICENSE` file is not present, please add one, typically containing the standard MIT License text.)

## Contact

For questions, issues, or collaboration, please refer to:
-   **GitHub Issues**: [Project's GitHub Issues Page](https://github.com/yourusername/megalith/issues) (Replace with actual link)
-   **Project Maintainer**: `<your.email@example.com>` or [GitHub Profile](https://github.com/yourusername) (Update with actual contact information)