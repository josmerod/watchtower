# Watchtower

**A comprehensive monitoring and ETL framework for scraping, aggregating, and visualizing data from diverse online sources.**

Watchtower is designed to automate the collection of information from news sites, game deal aggregators, online course platforms, and other web content. It features robust ETL (Extract, Transform, Load) pipelines, intelligent watchers for monitoring content changes, an orchestrator for managing and scheduling tasks, and a user-friendly Streamlit web dashboard for real-time data visualization and interaction.

## Table of Contents

- [Watchtower](#watchtower)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
  - [Technologies Used](#technologies-used)
  - [Project Structure](#project-structure)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Clone the Repository](#clone-the-repository)
    - [Set up Virtual Environment](#set-up-virtual-environment)
    - [Install Dependencies](#install-dependencies)
    - [Install Playwright Browsers](#install-playwright-browsers)
  - [Configuration](#configuration)
  - [Usage](#usage)
    - [Running ETL Pipelines](#running-etl-pipelines)
    - [Running Watchers](#running-watchers)
    - [Running the Orchestrator](#running-the-orchestrator)
    - [Launching the Web Dashboard](#launching-the-web-dashboard)
  - [Docker](#docker)
  - [Scheduling and Automation](#scheduling-and-automation)
  - [Contributing](#contributing)
    - [Issue Reporting](#issue-reporting)
    - [Pull Request Process](#pull-request-process)
  - [Troubleshooting](#troubleshooting)
  - [License](#license)
  - [Contact](#contact)

## Overview

Watchtower is an all-in-one solution for data acquisition and monitoring. Its key capabilities include:

-   **Automated Data Collection**: Regularly scrapes data from various websites, including news portals, e-learning platforms, and gaming sites.
-   **Change Detection**: Monitors specified web pages for any changes in content, providing alerts or updates.
-   **Process Management**: Orchestrates multiple data collection and monitoring tasks, ensuring they run reliably and efficiently.
-   **Data Visualization**: Presents the aggregated data through an interactive web interface, allowing for easy exploration and analysis.

This project is ideal for users who need to stay updated on specific topics, track changes on websites, or aggregate data for analysis and reporting.

## Features

-   **ETL Pipelines**:
    -   News Scraping: Hacker News, Future Tools, Bensbites, GoodDevs, Valencia Events, Medium GenAI, arXiv papers, etc.
    -   Game Deals: Aggregates deals, bundles, and giveaways.
    -   Online Courses: Tracks courses from platforms like Coursera and posts from DeepLearning.AI.
-   **Watchers**:
    -   Monitors web pages for content changes (e.g., Microsoft Applied Skills credentials, arXiv new submissions).
    -   Pluggable `BaseWatcher` class for creating custom watchers easily.
-   **Orchestrator**:
    -   `MetaOrchestrator` to run and oversee multiple specific orchestrators (e.g., ETL, GenAI, Golddigging) concurrently.
    -   Designed for fault tolerance with auto-restart capabilities for managed scripts.
-   **Web Dashboard**:
    -   Streamlit-based application providing a comprehensive view of collected data.
    -   Tabs for various categories: Shortcuts, Videos, News, Games, Courses, Watchers, and Admin functionalities.
    -   Interactive data tables, search, and filtering capabilities.
-   **Scheduling & Automation**:
    -   Shell (`.sh`) and batch (`.bat`) scripts for automating the execution of ETL tasks, watchers, and the dashboard.
    -   Support for setting up tasks as background processes or services.
    -   Centralized logging for all components, typically within the `logs/` directory.

## Technologies Used

-   **Programming Language**: Python 3.10+
-   **Web Scraping**: Playwright, Beautiful Soup, Feedparser
-   **Data Processing**: Pandas, NumPy
-   **Web Dashboard**: Streamlit
-   **Dependency Management**: pip with `requirements.txt`, `pyproject.toml` (compatible with Poetry/Rye)
-   **Code Formatting & Linting**: Ruff
-   **Version Control**: Git
-   **Containerization**: Docker (see `Dockerfile`)
-   **Scheduling**: System-specific tools (e.g., cron, Task Scheduler via provided scripts)

## Project Structure

```
watchtower/
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
│   ├── data/              # Data handling utilities, potentially specific to data modules
│   │   └── youtube/
│   ├── etl/               # ETL (Extract, Transform, Load) pipelines
│   │   ├── arxiv/
│   │   ├── games/
│   │   ├── goldigging/
│   │   └── news/
│   ├── miners/            # Specialized data extraction tools (e.g., for Steam)
│   │   ├── asf-winonly/
│   │   └── udemy-universal/
│   ├── orchestrator/      # Scripts for managing and orchestrating processes
│   │   └── logs/
│   ├── utils/             # Common utility functions and modules
│   ├── watchers/          # Modules for monitoring web content changes
│   └── web/               # Web application components
│       └── fullstreamlit/ # Streamlit dashboard application
│           ├── components/  # Reusable UI components for the Streamlit app
│           ├── data/        # Data specifically for the Streamlit app (e.g., cached)
│           ├── logs/        # Logs specific to the Streamlit app
│           ├── pages/       # (If using multi-page Streamlit app structure)
│           ├── styles/      # CSS styles for the Streamlit app
│           ├── utils/       # Utility functions for the Streamlit app
│           └── app.py       # Main Streamlit application script
├── tests/                 # Unit and integration tests (pytest recommended)
├── .dockerignore          # Specifies files to ignore when building Docker images
├── .gitignore             # Specifies intentionally untracked files that Git should ignore
├── Dockerfile             # Defines the Docker image for the application
├── README.md              # This file: project overview and documentation
├── requirements.txt       # Lists Python dependencies for pip
├── pyproject.toml         # Project metadata and build system configuration (e.g., for Poetry, Ruff)
├── run_all_etl.bat / .sh  # Scripts to run all ETL pipelines
├── run_watcher.bat / .sh  # Scripts to execute watchers
├── run_streamlit.bat / .sh # Scripts to launch the Streamlit dashboard
├── setup_etl_scheduler.ps1 / .sh       # Scripts for setting up ETL scheduling
└── setup_streamlit_service.ps1 / .sh   # Scripts for setting up Streamlit as a service
└── ... (other configuration and utility scripts)
```

## Installation

### Prerequisites

-   Python 3.10 or higher
-   Git
-   [Playwright](https://playwright.dev/python/) browser binaries

### Clone the Repository

```bash
git clone https://github.com/yourusername/watchtower.git  # Replace with your actual repo URL
cd watchtower
```

### Set up Virtual Environment

It's highly recommended to use a virtual environment:

```bash
python -m venv .venv
```

Activate the environment:
-   On Windows:
    ```powershell
    .\.venv\Scripts\Activate.ps1
    ```
    Or (cmd.exe):
    ```batch
    .venv\Scripts\activate.bat
    ```
-   On macOS and Linux:
    ```bash
    source .venv/bin/activate
    ```

### Install Dependencies

Ensure `pip` is up to date, then install the required packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Alternatively, if using Poetry:
```bash
poetry install
```

### Install Playwright Browsers

The application uses Playwright for browser automation. Install the necessary browser binaries:

-   Windows: Run `install_playwright.bat`
-   macOS/Linux: Run `bash install_playwright.sh`

This typically executes `playwright install`.

## Configuration

The application may require configuration for various services, API keys, or behaviors. Common places to look for configuration options include:

-   **Environment Variables**: Check if any scripts or modules expect environment variables to be set (e.g., `API_KEY_SERVICE_X`, `DATABASE_URL`). This is a common practice for sensitive data.
-   **Configuration Files**: Look for `.env` files, JSON, YAML, or Python configuration files (e.g., `config.py`) within specific modules or a central `config/` directory.
-   **Script Arguments**: Some scripts might accept configuration parameters via command-line arguments. Check their respective `--help` messages.

*Note: Specific configuration details should be documented per component or within a dedicated configuration guide if the project complexity warrants it.*

## Usage

Ensure your virtual environment is activated before running any scripts.

### Running ETL Pipelines

To run an individual ETL script (example):
```bash
python src/etl/news/news_get_ycombinator.py
```

To run all ETL pipelines (often in parallel, depending on the script's implementation):
-   Windows: `.\run_all_etl.bat`
-   macOS/Linux: `bash run_all_etl.sh`

### Running Watchers

To run all watchers:
```bash
python src/watchers/run_watcher.py
```

To run a specific watcher (e.g., `ms_applied_skills`):
```bash
python src/watchers/run_watcher.py ms_applied_skills --once
```
The `--once` flag typically means it runs one time and exits, otherwise it might run in a loop.

To list available watchers:
```bash
python src/watchers/run_watcher.py --list
```

Convenience scripts are also provided:
-   Windows: `.\run_watcher.bat [watcher_name]`
-   macOS/Linux: `bash run_watcher.sh [watcher_name]`

### Running the Orchestrator

The `meta_orchestrator.py` script is the main entry point for managing multiple processes:
```bash
python src/orchestrator/meta_orchestrator.py
```
This will typically start and monitor other orchestrator scripts or defined tasks.

### Launching the Web Dashboard

To start the Streamlit web dashboard:
-   Windows: `.\run_streamlit.bat` (or `.\start_streamlit.bat`)
-   macOS/Linux: `bash run_streamlit.sh` (or `bash start_streamlit.sh`)

This will usually run a command similar to `streamlit run src/web/fullstreamlit/app.py`.
Open your browser and navigate to `http://localhost:8501` (or the port indicated in the console).

## Docker

This project includes a `Dockerfile` to build a container image for the application. This can simplify deployment and ensure a consistent runtime environment.

**Build the Docker Image:**
```bash
docker build -t watchtower-app .
```

**Run the Docker Container:**
```bash
docker run -p 8501:8501 watchtower-app
```
*(Adjust port mapping and other Docker run options as needed, e.g., for volume mounts to persist data).*

Refer to the `Dockerfile` for details on the image setup. You might need to pass environment variables or mount configuration files into the container.

## Scheduling and Automation

The project provides scripts to help automate tasks:

-   **ETL Scheduler**:
    -   Unix: `bash setup_etl_scheduler.sh`
    -   Windows: `powershell -ExecutionPolicy Bypass -File setup_etl_scheduler.ps1`
    These scripts likely assist in setting up cron jobs (Unix) or Task Scheduler tasks (Windows) to run ETL pipelines regularly.

-   **Streamlit Service**:
    -   Unix: `bash setup_streamlit_service.sh`
    -   Windows: `powershell -ExecutionPolicy Bypass -File setup_streamlit_service.ps1`
    These scripts help in setting up the Streamlit dashboard to run as a background service.

Consult the content of these scripts for their specific actions and any prerequisites.

## Contributing

We welcome contributions of all kinds, whether it's reporting bugs, suggesting new features, improving documentation, or submitting code changes. Please adhere to the following guidelines:

1.  **Fork the Repository**: Create your own fork of the project on GitHub.
2.  **Clone Your Fork**:
    ```bash
    git clone https://github.com/yourusername/watchtower.git # Use your fork's URL
    cd watchtower
    ```
3.  **Create a Feature Branch**:
    ```bash
    git checkout -b feature/your-awesome-feature
    ```
4.  **Make Changes**:
    -   Ensure your code adheres to the project's style (PEP 8, Ruff for formatting).
    -   Include comprehensive type annotations for all functions, methods, and class members.
    -   Write detailed Google-style docstrings.
5.  **Lint and Format**:
    Run Ruff to check and format your code:
    ```bash
    ruff check . --fix
    ruff format .
    ```
6.  **Test Your Changes**:
    -   Add new tests for your features or bug fixes under a `tests/` directory.
    -   Aim for high test coverage, including common cases and edge cases. (pytest is the recommended framework).
    -   Ensure all tests pass.
7.  **Commit Your Changes**:
    Use clear, descriptive commit messages. Consider following the [Conventional Commits](https://www.conventionalcommits.org/) specification.
    ```bash
    git commit -m "feat: Add new feature for X"
    ```
8.  **Push to Your Fork**:
    ```bash
    git push origin feature/your-awesome-feature
    ```
9.  **Open a Pull Request (PR)**:
    Submit a PR from your feature branch to the `main` branch of the upstream (original) repository.
    -   Provide a concise title and a detailed description of your changes.
    -   Reference any related GitHub issues (e.g., "Closes #123").

### Issue Reporting

-   Use GitHub Issues to report bugs or suggest features.
-   Provide detailed information: steps to reproduce, expected behavior, actual behavior, Python version, OS, and relevant logs or screenshots.

### Pull Request Process

-   PRs will be reviewed by maintainers. Expect feedback and potential requests for changes.
-   Ensure all automated checks (CI/CD, linting, tests) pass.
-   Maintainers may squash or rebase commits for a cleaner merge history.

Thank you for contributing to Watchtower!

## Troubleshooting

-   **Playwright Issues**:
    -   Ensure browsers are installed: `playwright install`.
    -   If running headlessly in Docker or a CI environment, ensure all system dependencies for browsers are met.
-   **Dependency Conflicts**:
    -   Ensure your virtual environment is clean and activated.
    -   Try recreating the virtual environment and reinstalling dependencies.
-   **Streamlit App Not Loading**:
    -   Check the console output for errors when running `streamlit run ...`.
    -   Ensure the correct port (usually 8501) is not blocked by a firewall.
-   **Script Execution Failures**:
    -   Verify paths and permissions for files and directories the script might be accessing.
    -   Check script logs in the `logs/` directory for detailed error messages.

*Add more common issues and solutions as they are identified.*

## License

This project is licensed under the MIT License. See the `LICENSE` file for details (if one exists, otherwise state "MIT License").

## Contact

Project Maintainer <your.email@example.com>
*(Update with actual contact information or GitHub profile link)*