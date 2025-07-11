# Watchtower Setup Guide

A comprehensive guide for setting up Watchtower on different platforms and environments.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Platform-Specific Setup](#platform-specific-setup)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

For impatient users who want to get started immediately:

```bash
# Clone and setup
git clone <repository-url>
cd watchtower

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt

# Install browser binaries for web scraping
playwright install

# Run first ETL to test setup
python Tests/etl/test_hackernews_etl.py

# Launch dashboard
streamlit run src/web/fullstreamlit/app.py
```

🎉 **That's it!** Visit http://localhost:8501 to see your dashboard.

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.10+ (3.11+ recommended) |
| **RAM** | 4GB (8GB+ recommended) |
| **Storage** | 2GB free space |
| **Network** | Internet connection for data sources |

### Supported Platforms

- ✅ **Windows** 10/11 (tested)
- ✅ **Linux** Ubuntu 20.04+, Debian 11+, CentOS 8+
- ✅ **macOS** 10.15+ (Catalina)
- ✅ **Docker** Any platform with Docker support

### Required System Dependencies

#### Windows
```powershell
# Python 3.10+ from python.org or Microsoft Store
# Git for Windows
# Visual C++ Build Tools (for some packages)
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip git build-essential
```

#### CentOS/RHEL
```bash
sudo dnf install python3.10 python3-pip git gcc gcc-c++ make
```

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and Git
brew install python@3.10 git
```

---

## Installation Methods

### Method 1: UV Installation (Recommended - 10-100x faster)

**Step 1: Clone Repository**
```bash
git clone <repository-url>
cd watchtower
```

**Step 2: Install UV**
```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Step 3: Install Dependencies**
```bash
# Install all dependencies (creates virtual environment automatically)
uv sync --all-extras

# Install browser binaries
uv run playwright install
```

**Step 4: Run the project**
```bash
# All commands use 'uv run' - no manual activation needed
uv run python run_watchtower_dashboard.py
```

### Method 2: Development Setup Script (Easiest)

**Automatic Setup with UV:**
```bash
# This script auto-installs UV and sets up everything
python install_dev.py
```

### Method 3: Legacy Installation (Not Recommended)

**Traditional Virtual Environment:**
```bash
git clone <repository-url>
cd watchtower

# Create virtual environment
python -m venv .venv

# Activate environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate.bat  # Windows CMD
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
playwright install
```

### Method 3: Docker Installation

For containerized deployment:

```bash
# Clone repository
git clone <repository-url>
cd watchtower

# Build Docker image
docker build -t watchtower .

# Run container
docker run -p 8501:8501 -v $(pwd)/data:/app/data watchtower
```

---

## Configuration

### Environment Configuration

Watchtower automatically detects the environment. You can override with:

```bash
export ENVIRONMENT=production  # Linux/Mac
set ENVIRONMENT=production     # Windows CMD
$env:ENVIRONMENT="production"  # Windows PowerShell
```

### Configuration File

Create `.env` file in project root for custom settings:

```bash
# Application settings
APP_NAME=Watchtower
ENVIRONMENT=development
DEBUG=true

# Database configuration
DATABASE__URL=sqlite:///watchtower.db
DATABASE__ECHO=false

# Logging configuration
LOGGING__LEVEL=INFO
LOGGING__FILE_ENABLED=true

# ETL configuration
ETL__BATCH_SIZE=1000
ETL__MAX_WORKERS=4

# Scraping configuration
SCRAPING__TIMEOUT=30
SCRAPING__MAX_RETRIES=3
SCRAPING__CONCURRENT_LIMIT=10

# Dashboard configuration
DASHBOARD__HOST=localhost
DASHBOARD__PORT=7777

# Legacy Streamlit configuration
STREAMLIT__HOST=localhost
STREAMLIT__PORT=8501
```

### Directory Structure Setup

Watchtower will automatically create required directories, but you can pre-create them:

```bash
mkdir -p data/{arxiv,hackernews,games,news}
mkdir -p logs
mkdir -p config
```

---

## Platform-Specific Setup

### Windows Setup

**Using Windows Batch Scripts:**
```batch
# Setup environment
setup_venv.bat

# Run all ETL processes
run_all_etl.bat

# Start main dashboard
run_watchtower_dashboard.bat

# Start legacy Streamlit dashboard
run_watchtower.bat

# Setup as Windows service
setup_streamlit_service.ps1
```

**PowerShell Execution Policy:**
If you encounter execution policy issues:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Linux Setup

**Using Shell Scripts:**
```bash
# Make scripts executable
chmod +x *.sh

# Setup environment
./setup_venv.sh

# Run all ETL processes
./run_all_etl.sh

# Start main dashboard
./run_watchtower_dashboard.sh

# Start legacy Streamlit dashboard
./run_streamlit.sh

# Setup as systemd service
sudo ./setup_streamlit_service.sh
```

**Systemd Service Setup:**
```bash
# Create service file
sudo tee /etc/systemd/system/watchtower.service > /dev/null <<EOF
[Unit]
Description=Watchtower Dashboard
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/watchtower
Environment=PATH=/path/to/watchtower/.venv/bin
ExecStart=/path/to/watchtower/.venv/bin/streamlit run src/web/fullstreamlit/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable watchtower
sudo systemctl start watchtower
```

### macOS Setup

Similar to Linux, but using macOS-specific tools:

```bash
# Install dependencies
brew install python@3.10 git

# Follow standard installation
# For service management, use launchd instead of systemd
```

---

## Production Deployment

### Security Considerations

**1. Environment Variables:**
```bash
# Use strong secret keys
SECRET_KEY=your-very-secure-secret-key-at-least-32-characters

# Database security
DATABASE__URL=postgresql://user:password@localhost/watchtower_prod

# Disable debug mode
DEBUG=false
ENVIRONMENT=production
```

**2. Network Security:**
```bash
# Restrict Streamlit access
STREAMLIT__HOST=127.0.0.1  # Localhost only
# Use reverse proxy (nginx) for external access
```

**3. File Permissions:**
```bash
# Secure configuration files
chmod 600 .env
chmod 700 logs/
chmod 700 data/
```

### Performance Optimization

**1. Database Configuration:**
```bash
# Use PostgreSQL for production
DATABASE__URL=postgresql://user:pass@localhost/watchtower
DATABASE__POOL_SIZE=20
DATABASE__MAX_OVERFLOW=30
```

**2. ETL Configuration:**
```bash
# Optimize batch processing
ETL__BATCH_SIZE=5000
ETL__MAX_WORKERS=8

# Scraping optimization
SCRAPING__CONCURRENT_LIMIT=20
SCRAPING__RATE_LIMIT=2.0
```

**3. Resource Monitoring:**
```bash
# Enable performance monitoring
MONITORING__METRICS_ENABLED=true
MONITORING__PERFORMANCE_MONITORING=true
```

### Load Balancing

For high-traffic deployments:

```yaml
# docker-compose.yml
version: '3.8'
services:
  watchtower:
    image: watchtower:latest
    deploy:
      replicas: 3
    environment:
      - STREAMLIT__HOST=0.0.0.0
      - DATABASE__URL=postgresql://user:pass@db/watchtower
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Backup Strategy

**1. Data Backup:**
```bash
# Backup data directory
tar -czf watchtower-data-$(date +%Y%m%d).tar.gz data/

# Database backup (if using PostgreSQL)
pg_dump watchtower > backup-$(date +%Y%m%d).sql
```

**2. Configuration Backup:**
```bash
# Backup configuration
cp .env .env.backup
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/
```

---

## Troubleshooting

### Common Issues

#### 1. Python Version Issues
```bash
# Check Python version
python --version

# If wrong version, use specific version
python3.10 -m venv .venv
```

#### 2. Playwright Installation Issues
```bash
# Install browsers with dependencies
playwright install --with-deps

# For permission issues
sudo playwright install-deps
```

#### 3. Port Already in Use
```bash
# Check what's using port 8501
netstat -an | grep 8501  # Linux/Mac
netstat -an | findstr 8501  # Windows

# Use different port
streamlit run src/web/fullstreamlit/app.py --server.port 8502
```

#### 4. Permission Denied Errors
```bash
# Fix file permissions
chmod +x *.sh
chmod 755 src/

# Fix directory permissions
chmod 755 data/ logs/
```

#### 5. Import Errors
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

### Performance Issues

#### 1. Slow ETL Processing
```bash
# Increase batch size
export ETL__BATCH_SIZE=2000

# Increase workers
export ETL__MAX_WORKERS=8

# Check resource usage
top  # Linux/Mac
taskmgr  # Windows
```

#### 2. Dashboard Loading Slowly
```bash
# Clear Streamlit cache
streamlit cache clear

# Optimize data loading
# Use data pagination in dashboard
```

#### 3. Memory Issues
```bash
# Monitor memory usage
free -h  # Linux
vm_stat  # Mac
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory  # Windows

# Reduce batch size if needed
export ETL__BATCH_SIZE=500
```

### Debugging

**Enable Debug Mode:**
```bash
export DEBUG=true
export LOGGING__LEVEL=DEBUG
```

**Check Logs:**
```bash
# View latest logs
tail -f logs/watchtower.log

# Search for errors
grep -i error logs/watchtower.log
```

**Test Components:**
```bash
# Test ETL
python Tests/etl/test_hackernews_etl.py

# Test configuration
python -c "from src.config.settings import get_settings; print(get_settings())"

# Test imports
python -c "import src.etl.base; print('ETL import OK')"
```

---

## Next Steps

After successful setup:

1. **Explore Main Dashboard**: Visit http://localhost:7777 (recommended)
2. **Explore Legacy Dashboard**: Visit http://localhost:8501 (if needed)
3. **Run ETL Processes**: Use `run_all_etl` scripts or `uv run python src/etl/...`
4. **Configure Watchers**: Set up monitoring for your desired websites
5. **Read Documentation**: Check out the [API Reference](development/api-reference.md)
6. **Review Use Cases**: Explore [Use Cases](use-cases/) for practical examples

For additional help, see:
- [Dashboard Guide](dashboard_guide.md)
- [Development Documentation](development/)
- [Project Status](project-status/) 