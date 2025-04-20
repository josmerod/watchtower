# Watchtower

A comprehensive monitoring and ETL framework for scraping and aggregating data from various sources, including news sites, game deals, online courses, and web content. It features ETL pipelines, watchers, an orchestrator for process management, and a Streamlit web dashboard for real-time visualization.

## Table of Contents

- [Watchtower](#watchtower)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Clone the Repository](#clone-the-repository)
    - [Install Dependencies](#install-dependencies)
    - [Install Playwright Browsers](#install-playwright-browsers)
  - [Setup](#setup)
  - [Usage](#usage)
    - [Run ETL Pipelines](#run-etl-pipelines)
    - [Run Watchers](#run-watchers)
    - [Orchestrator](#orchestrator)
    - [Web Dashboard](#web-dashboard)
  - [Project Structure](#project-structure)
  - [Dependencies](#dependencies)
  - [Contribution](#contribution)
  - [License](#license)
  - [Contact](#contact)

## Features

- **ETL Pipelines**  
  - News scraping: Hacker News, Future Tools, Bensbites, GoodDevs, Valencia Events, Medium GenAI, etc.  
  - Game deals: Aggregated deals, bundles, and giveaways.  
  - Gold digging courses: Coursera, DeepLearning.AI posts.  
- **Watchers**  
  - Monitor web pages for content changes (e.g., Microsoft Applied Skills credentials).  
  - Pluggable base class for custom watchers.  
- **Orchestrator**  
  - Meta orchestrator to run and monitor multiple orchestrators concurrently.  
  - Fault-tolerant auto-restart of orchestrator scripts.  
- **Web Dashboard**  
  - Streamlit application with tabs for shortcuts, videos, news, games, courses, watchers, and admin.  
  - Interactive data tables and visualizations.  
- **Scheduling & Automation**  
  - Shell and batch scripts for running ETL, watchers, and the dashboard as background processes or services.  
  - Centralized logging for all components.

## Installation

### Prerequisites

- Python 3.10+  
- [Playwright](https://playwright.dev/python/) browser binaries  

### Clone the Repository

```bash
git clone https://github.com/yourusername/watchtower.git
cd watchtower
```

### Install Dependencies

Using pip and a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Using Poetry:

```bash
poetry install
```

### Install Playwright Browsers

```bash
# Windows
install_playwright.bat

# Unix
bash install_playwright.sh
```

## Setup

- **ETL Scheduler**  
  - Unix: `bash setup_etl_scheduler.sh`  
  - Windows: `powershell setup_etl_scheduler.ps1`  
- **Streamlit Service**  
  - Unix: `bash setup_streamlit_service.sh`  
  - Windows: `powershell setup_streamlit_service.ps1`

## Usage

### Run ETL Pipelines

```bash
# Individual ETL script
python src/etl/news/news_get_ycombinator.py

# Run all ETL pipelines in parallel
bash run_all_etl.sh
# Windows
.\run_all_etl.bat
```

### Run Watchers

```bash
# Run all watchers
python src/watchers/run_watcher.py

# Run a specific watcher
python src/watchers/run_watcher.py ms_applied_skills --once
# List watchers
python src/watchers/run_watcher.py --list

# Or use provided scripts
bash run_watcher.sh [watcher_name]
.\run_watcher.bat [watcher_name]
```

### Orchestrator

```bash
python src/orchestrator/meta_orchestrator.py
```

### Web Dashboard

```bash
bash run_streamlit.sh
# Windows
.\run_streamlit.bat
```

Open your browser at http://localhost:8501.

## Project Structure

```
watchtower/
├── src/
│   ├── etl/               # ETL pipelines for games, news, and courses
│   │   ├── games/
│   │   ├── news/
│   │   └── goldigging/
│   ├── watchers/          # Watcher modules for web content monitoring
│   ├── orchestrator/      # Orchestrator scripts for process management
│   └── web/fullstreamlit/ # Streamlit dashboard application
├── data/                  # Raw and processed data files
├── logs/                  # Log files for ETL and watchers
├── .venv/                 # Python virtual environment (ignored in VCS)
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata
├── run_all_etl.sh         # Run all ETL pipelines
├── run_watcher.sh         # Run watchers script (Unix)
├── run_streamlit.sh       # Run Streamlit dashboard (Unix)
├── setup_etl_scheduler.sh # Setup ETL scheduler
└── setup_streamlit_service.sh # Setup Streamlit service
```

## Dependencies

For full list, see `requirements.txt` and `pyproject.toml`.

## Contribution

Contributions are welcome! Please fork the repository and submit pull requests, following the existing style and lint rules.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

Your Name <your.email@example.com>