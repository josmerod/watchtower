# Watchtower FAQ

Frequently Asked Questions about the Watchtower platform.

## General Questions

### What is Watchtower?

Watchtower is a comprehensive data intelligence and monitoring platform that aggregates, processes, and monitors information from 50+ data sources including research papers, news feeds, courses, games, and more. It provides automated ETL pipelines, real-time monitoring watchers, and an interactive dashboard for data visualization.

### What can I use Watchtower for?

- Monitor research papers from ArXiv
- Track technology news from multiple sources
- Find free games and deals
- Discover online courses and learning resources
- Monitor GitHub trending repositories
- Track AI platform updates (OpenAI, Anthropic, HuggingFace)
- Get local event information
- Collect ADHD research papers
- Monitor 4chan boards
- Track Spanish public aid programs
- And much more!

### Is Watchtower free?

Yes, Watchtower is open-source software licensed under the MIT License. It's completely free to use, modify, and distribute.

### What are the system requirements?

- **Python**: 3.10 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 5-10GB for data storage
- **OS**: Windows, macOS, or Linux
- **Network**: Internet connection for data collection

## Installation & Setup

### How do I install Watchtower?

See the [Quickstart Guide](QUICKSTART.md) for step-by-step installation instructions. The fastest method uses UV package manager:

```bash
git clone https://github.com/yourusername/watchtower.git
cd watchtower
uv sync --all-extras
uv run playwright install
```

### Do I need API keys?

Most data sources don't require API keys. However, some advanced features need credentials:
- **Optional**: GitHub API token (for trending repositories)
- **Optional**: Reddit API credentials (for specific subreddits)
- **Optional**: Cloud platform API keys (for cloud skills monitoring)

Basic functionality works without any API keys.

### Why UV instead of pip?

UV is 10-100x faster than pip for dependency management and provides better reliability. It's optional but highly recommended. You can still use traditional pip/venv if preferred.

### How do I upgrade to the latest version?

```bash
cd watchtower
git pull origin main
uv sync --all-extras  # Update dependencies
```

## Usage Questions

### How do I run ETL pipelines?

```bash
# Run single ETL
uv run python src/etl/news/news_get_ycombinator.py

# Run all ETLs
.\run_all_etl.bat  # Windows
bash run_all_etl.sh  # Linux/macOS
```

### How do I start the dashboard?

```bash
uv run python run_watchtower_dashboard.py
# Open browser to http://localhost:7777
```

### How often should I run ETL pipelines?

Recommended frequencies:
- **News**: 2-4 times daily
- **ArXiv**: Daily
- **Games**: Daily for deals, weekly for releases
- **Courses**: Weekly
- **GitHub Trending**: Daily

### Where is collected data stored?

All data is stored in the `data/` directory as JSON files:
- `data/news/` - News articles
- `data/arxiv/` - Research papers
- `data/games/` - Game deals and releases
- `data/youtube/` - YouTube videos
- `data/watchers/` - Watcher states and events

### Can I customize which data sources to use?

Yes! You can:
- Comment out sources in `run_all_etl.bat` or `run_all_etl.sh`
- Edit individual ETL scripts in `src/etl/`
- Create custom ETL pipelines (see [ETL Development Guide](technical/ETL_DEVELOPMENT_GUIDE.md))

## Watchers

### What are watchers?

Watchers are monitoring components that continuously check data sources for changes and log events when changes occur. They're useful for tracking updates to specific websites or APIs.

### How do I run watchers?

```bash
# Run specific watcher once
uv run python src/watchers/run_watcher.py arxiv_watcher --once

# Run all watchers continuously
uv run python src/watchers/run_watcher.py

# List available watchers
uv run python src/watchers/run_watcher.py --list
```

### Can I create custom watchers?

Yes! See the [Watchers Guide](technical/WATCHERS_GUIDE.md) for comprehensive documentation on creating custom watchers.

## Dashboard

### Why isn't the dashboard showing any data?

You need to run ETL pipelines first to collect data:

```bash
.\run_all_etl.bat  # Windows
bash run_all_etl.sh  # Linux/macOS
```

Then start the dashboard:

```bash
uv run python run_watchtower_dashboard.py
```

### Can I customize the dashboard?

Yes! The dashboard is built with Dash and Bootstrap. See the [Dashboard Development Guide](technical/DASHBOARD_DEVELOPMENT_GUIDE.md) for customization instructions.

### What port does the dashboard use?

Default port is **7777**. You can change it:

```bash
uv run python run_watchtower_dashboard.py --port 8888
```

### Can I access the dashboard remotely?

Yes, but be careful with security. To allow remote access:

```bash
uv run python run_watchtower_dashboard.py --host 0.0.0.0
```

**Security Warning**: Only do this on trusted networks or behind a firewall.

## Automation & Scheduling

### How do I schedule automatic data collection?

**Linux/macOS** (using cron):
```bash
# Edit crontab
crontab -e

# Add line for daily execution at 8 AM
0 8 * * * cd /path/to/watchtower && bash run_all_etl.sh
```

**Windows** (using Task Scheduler):
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., Daily at 8:00 AM)
4. Set action to run `run_all_etl.bat`

See [User Guide](USER_GUIDE.md) for detailed scheduling instructions.

### Can watchers run continuously?

Yes! Watchers are designed for continuous operation. Run them as a background service using systemd (Linux) or Task Scheduler (Windows).

## Performance & Optimization

### Watchtower is using too much disk space

Data accumulates over time. To manage:
- Delete old timestamped files in `data/` directories
- Implement data retention policies
- Use the built-in cleanup utilities

### ETL pipelines are slow

Optimization tips:
- Run pipelines in parallel when possible
- Use `--batch-size` flag for large datasets
- Enable caching where appropriate
- Check network connection speed

### Dashboard is slow to load

Performance improvements:
- Reduce data/` files
- Implement pagination for large datasets
- Clear browser cache
- Use data filtering

## Troubleshooting

### "UV command not found"

UV not in PATH. Restart terminal or add UV to PATH manually:

```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Windows
# Add %USERPROFILE%\.local\bin to System PATH
```

### "Playwright browsers not found"

Install Playwright browsers:

```bash
uv run playwright install

# Or install system dependencies (Linux)
sudo apt-get install -y libgbm1 libnss3 libnspr4 libatk1.0-0
```

### "Permission denied" errors

Fix permissions:

```bash
# Linux/macOS
chmod -R 755 data/ logs/

# Windows (run as Administrator)
icacls data /grant Everyone:F /T
```

### ETL script fails with import errors

Ensure virtual environment is activated or use `uv run`:

```bash
# With UV (recommended)
uv run python src/etl/script.py

# Or activate venv first
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
python src/etl/script.py
```

### Dashboard shows "No data available"

1. Check data directory has files: `ls data/`
2. Run ETL pipelines: `bash run_all_etl.sh`
3. Check logs for errors: `cat logs/*.log`
4. Restart dashboard

### "Port already in use" error

Another process is using port 7777. Either:
- Stop the other process
- Use a different port: `--port 8888`

```bash
# Find process using port (Linux/macOS)
lsof -i :7777

# Find process using port (Windows)
netstat -ano | findstr :7777
```

## Development

### How do I contribute?

See the [Contributing Guide](CONTRIBUTING.md) for comprehensive contribution instructions.

### How do I create custom ETL pipelines?

See the [ETL Development Guide](technical/ETL_DEVELOPMENT_GUIDE.md) for step-by-step instructions on creating custom pipelines.

### What's the best way to test my changes?

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test
uv run pytest tests/etl/test_my_feature.py
```

### How do I report bugs?

Open an issue on [GitHub Issues](https://github.com/yourusername/watchtower/issues) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Python version)
- Relevant log files

## Data Privacy & Security

### What data does Watchtower collect?

Watchtower only collects publicly available data from the sources you configure. It doesn't collect personal data or telemetry.

### Is my data secure?

- All data is stored locally on your machine
- No data is sent to external servers (except to fetch public data)
- API keys are stored in `.env` files (never committed to version control)

### Can I use Watchtower commercially?

Yes! The MIT License permits commercial use. See the LICENSE file for details.

## Advanced Questions

### Can I deploy Watchtower to a server?

Yes! See the [Deployment Guide](technical/DEPLOYMENT_GUIDE.md) and [Advanced Deployment Guide](technical/ADVANCED_DEPLOYMENT_GUIDE.md) for:
- Docker deployment
- Systemd services
- Cloud deployment
- Unraid server setup

### Does Watchtower support databases?

Currently, Watchtower uses file-based JSON storage. Database support is planned for future releases. See [ROADMAP.md](ROADMAP.md) for future plans.

### Can I integrate Watchtower with other tools?

Yes! Integration options:
- Export data as JSON/CSV
- Use as a data source for analytics tools
- Create custom APIs (see API development guide)
- Integrate via webhooks (planned feature)

### How do I backup my data?

Automated backup options:
1. Copy `data/` directory regularly
2. Use git for version control
3. Sync to cloud storage (Google Drive, Dropbox)
4. Use the built-in backup utilities

### Can I run multiple instances?

Yes, but ensure they don't conflict:
- Use different data directories
- Use different ports for dashboards
- Consider using Docker containers for isolation

## Still Have Questions?

- **Documentation**: Check [full documentation](INDEX.md)
- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/watchtower/issues)
- **Discussions**: [Community discussions](https://github.com/yourusername/watchtower/discussions)
- **Contributing**: [Help improve Watchtower](CONTRIBUTING.md)

---

**FAQ Last Updated**: January 10, 2025
