# Deployment Guide

This guide covers deployment strategies, configuration, and operational procedures for the Watchtower platform.

## Quick Start Deployment

### Prerequisites

- **Python 3.10+** (required for modern type hints and performance)
- **uv**, the package manager the project is locked with
- **Git** for version control
- **4GB+ RAM** recommended for processing large datasets
- **20GB+ storage** for data files and logs

### Basic Setup

```bash
# Clone the repository
git clone <repository-url>
cd watchtower

# Install the locked dependencies (creates .venv itself)
uv sync

# Install the browser for the Playwright-backed ETLs
uv run playwright install chromium

# Create necessary directories
mkdir -p data logs

# Verify installation
uv run python -c "import src.config.settings; print('Setup successful')"
```

### Environment Configuration

A base deployment needs no credentials: copy `.env.example` to `.env` in the
project root and add keys only for the sources you opt into. Settings are read
from the environment as `WATCHTOWER_<COMPONENT>__<SETTING>` (`src/config/settings.py`); the defaults shown here are the ones the code already uses:

```bash
# Core
WATCHTOWER_ENVIRONMENT=production
WATCHTOWER_DEBUG=false

# Logging
WATCHTOWER_LOGGING__LEVEL=INFO
WATCHTOWER_LOGGING__FILE_ENABLED=true
WATCHTOWER_LOGGING__CONSOLE_ENABLED=true

# ETL
WATCHTOWER_ETL__MAX_WORKERS=4
WATCHTOWER_ETL__CLEANUP_OLD_DATA_DAYS=90

# Dashboard port
WATCHTOWER_DASHBOARD_PORT=7780

# Scraping
WATCHTOWER_SCRAPING__TIMEOUT=30
WATCHTOWER_SCRAPING__MAX_RETRIES=3
```

## Production Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy the dependency files and install them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Install Playwright browsers
RUN uv run playwright install --with-deps chromium

# Copy application code
COPY . .

# Create data and logs directories
RUN mkdir -p data logs

# Set up non-root user for security
RUN useradd -m -u 1000 watchtower && \
    chown -R watchtower:watchtower /app
USER watchtower

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7780/health || exit 1

# Default command
CMD ["uv", "run", "python", "run_watchtower_dashboard.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  watchtower:
    build: .
    ports:
      - "7780:7780"  # Dash dashboard
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - WATCHTOWER_ENVIRONMENT=production
      - WATCHTOWER_DEBUG=false
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7780/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Optional: ETL scheduler service
  etl-scheduler:
    build: .
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - WATCHTOWER_ENVIRONMENT=production
      - WATCHTOWER_DEBUG=false
    env_file:
      - .env
    command: ["uv", "run", "python", "deployment/etl_scheduler.py"]
    restart: unless-stopped
    depends_on:
      - watchtower

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - watchtower
    restart: unless-stopped
```

The repository ships its own image definition and deploy script under `deployment/`; the files above are a generic example, not what the server runs. To deploy:

```bash
# Connection settings come from .env: UNRAID_HOST, UNRAID_USER and UNRAID_PASSWORD, or the SSH key ~/.ssh/id_ed25519
uv run --with paramiko python deployment/deploy.py
```

`deployment/deploy.py` does the following, in this order:

1. **Archive**: packs the working tree, limited to the paths in its `INCLUDE_PATHS` list (`src`, `deployment`, `config`, `Tests`, `pyproject.toml`, `uv.lock`, `run_all_etl.sh`, `run_watchtower_dashboard.py`, `run_all_etl_orchestrator.py`, `README.md`, `GEMINI.md` and `changelog.json`) and without bytecode or tool caches. The archive comes from the working tree, so uncommitted changes are deployed too; `.env` is not part of it.
2. **Build**: uploads the archive over SSH, extracts it on the server, tags the running image as `watchtower:previous` and builds `deployment/Dockerfile` there as the new `watchtower` image. If the build fails, the running container is not touched.
3. **Swap**: removes the running container and starts the new image with `docker run`, publishing the dashboard as 7777 → 7780 and the API as 45714 → 45714 and mounting only the `data` and `logs` volumes.
4. **Health check**: polls the container's health status every 5 seconds for up to 240 seconds. The `HEALTHCHECK` in `deployment/Dockerfile` calls `http://localhost:45714/health`, so the API is the gate.
5. **Rollback**: if the new container does not become healthy and a previous image exists, that image is put back behind the container. When the new container is not healthy the script exits with code 1, whether or not a rollback happened; it exits with 0 only when the container is healthy.

`deployment/deploy.ps1` is deprecated; its header says not to deploy with it and points to the command above.

Inside the container, `deployment/supervisord.conf` is the main process (the `CMD` of `deployment/Dockerfile`, which starts from a Python 3.11 image with `uv`) and starts three programs, all from `/app` and with `autorestart`:

| Program | Command | Serves |
| :-- | :-- | :-- |
| `dashboard` | `uv run python run_watchtower_dashboard.py` | Dash dashboard on port 7780 |
| `api` | `uv run uvicorn src.api.main:app --port 45714`, listening on all interfaces | API on port 45714 |
| `etl_scheduler` | `uv run python deployment/etl_scheduler.py` | ETL cycle |

`deployment/etl_scheduler.py` runs `./run_all_etl.sh` when it starts and then every 2 hours, and after each cycle it restarts the API (`supervisorctl restart api`) so that it serves the fresh data; the dashboard is not restarted. Program output goes to `/app/logs/` (`dashboard`, `api` and `scheduler` `.out.log` and `.err.log` files).

### Systemd Service (Linux)

Create `/etc/systemd/system/watchtower.service`:

```ini
[Unit]
Description=Watchtower Data Intelligence Platform
After=network.target

[Service]
Type=simple
User=watchtower
Group=watchtower
WorkingDirectory=/opt/watchtower
Environment=PATH=/opt/watchtower/.venv/bin
ExecStart=/opt/watchtower/.venv/bin/python run_watchtower_dashboard.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
TimeoutStopSec=20

# Resource limits
LimitNOFILE=65536
MemoryMax=4G
CPUQuota=200%

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/watchtower/data /opt/watchtower/logs

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable watchtower
sudo systemctl start watchtower
sudo systemctl status watchtower
```

### ETL Scheduling

The ETLs are scheduled by `deployment/etl_scheduler.py`: it runs `./run_all_etl.sh` when it starts and then every 2 hours, and after each cycle it restarts the `api` program through `supervisorctl`. That makes it a fit for the container, where supervisord runs both. On a plain host, start `uv run python run_all_etl_orchestrator.py` from a timer (`systemd` timer or `cron`) and restart the API service after each run; the unit that used to be listed here called a module that no longer exists.

## Cloud Deployment

### AWS EC2 Deployment

1. **Launch EC2 Instance**:
   - Instance type: t3.medium or larger
   - Ubuntu 22.04 LTS
   - Security group: Allow HTTP (80), HTTPS (443), SSH (22)
   - Storage: 20GB+ EBS volume

2. **Setup Script**:

```bash
#!/bin/bash
# AWS EC2 setup script

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv git nginx certbot python3-certbot-nginx

# Create application user
sudo useradd -m -s /bin/bash watchtower
sudo mkdir -p /opt/watchtower
sudo chown watchtower:watchtower /opt/watchtower

# Switch to app user
sudo -u watchtower bash << 'EOF'
cd /opt/watchtower

# Clone repository
git clone <your-repo-url> .

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.cargo/env

# Install dependencies
uv sync
uv run playwright install

# Create directories
mkdir -p data logs config

# Copy configuration
cp .env.example .env
# Edit .env with your settings
EOF

# Install systemd service
sudo cp /opt/watchtower/deploy/watchtower.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable watchtower
sudo systemctl start watchtower

# Configure Nginx
sudo cp /opt/watchtower/deploy/nginx.conf /etc/nginx/sites-available/watchtower
sudo ln -s /etc/nginx/sites-available/watchtower /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# Setup SSL (replace your-domain.com)
sudo certbot --nginx -d your-domain.com
```

### Nginx Configuration

Create `/etc/nginx/sites-available/watchtower`:

```nginx
upstream watchtower {
    server <host>:7780;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Main application
    location / {
        proxy_pass http://watchtower;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for Dash)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (if any)
    location /assets/ {
        alias /opt/watchtower/src/web/dashboard/assets/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Health check
    location /health {
        access_log off;
        proxy_pass http://watchtower/health;
    }
}
```

## Monitoring and Maintenance

### Health Monitoring

The application provides health endpoints:

- `GET /health` - Basic health check
- `GET /metrics` - Detailed system metrics

### Log Management

Configure log rotation with `logrotate`:

```bash
# /etc/logrotate.d/watchtower
/opt/watchtower/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 watchtower watchtower
    postrotate
        systemctl reload watchtower
    endscript
}
```

### Backup Strategy

Create backup script:

```bash
#!/bin/bash
# /opt/watchtower/scripts/backup.sh

BACKUP_DIR="/opt/backups/watchtower"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup data files
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" -C /opt/watchtower data/

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C /opt/watchtower config/ .env

# Backup logs (last 7 days)
find /opt/watchtower/logs -name "*.log" -mtime -7 -exec tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" {} +

# Keep only last 30 backups
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Performance Monitoring

Create monitoring script:

```bash
#!/bin/bash
# /opt/watchtower/scripts/monitor.sh

# Check service status
systemctl is-active --quiet watchtower || echo "ERROR: Watchtower service is down"

# Check disk usage
DISK_USAGE=$(df -h /opt/watchtower | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "WARNING: Disk usage is at ${DISK_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEM_USAGE" -gt 80 ]; then
    echo "WARNING: Memory usage is at ${MEM_USAGE}%"
fi

# Check ETL data freshness
LATEST_ETL=$(find /opt/watchtower/data -name "*_latest.json" -mmin -360 | wc -l)
if [ "$LATEST_ETL" -lt 5 ]; then
    echo "WARNING: ETL data appears stale (less than 5 recent files)"
fi
```

## Security Configuration

### Firewall Setup (UFW)

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow dashboard port (if direct access needed)
sudo ufw allow 7780/tcp

# Check status
sudo ufw status
```

### SSL/TLS Configuration

For production deployments, always use HTTPS:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Test renewal
sudo certbot renew --dry-run

# Setup auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Environment Security

1. **Use strong secrets**: Generate secure API keys and passwords
2. **Limit file permissions**: Ensure `.env` files are readable only by the application user
3. **Regular updates**: Keep system packages and Python dependencies updated
4. **Network security**: Use VPC/security groups to limit network access
5. **User isolation**: Run services as dedicated non-root users

## Troubleshooting

### Common Issues

1. **Dashboard not loading**:
   ```bash
   # Check service status
   sudo systemctl status watchtower

   # Check logs
   tail -f /opt/watchtower/logs/dashboard.log

   # Check port availability
   netstat -tlnp | grep 7780
   ```

2. **ETL failures**:
   ```bash
   # Check ETL logs
   ls -la /opt/watchtower/logs/
   tail -f /opt/watchtower/logs/etl_*.log

   # Test individual ETL
   cd /opt/watchtower
   uv run python src/etl/news/news_get_ycombinator.py
   ```

3. **High memory usage**:
   ```bash
   # Check process memory
   ps aux | grep python | sort -k4 -nr

   # Restart services if needed
   sudo systemctl restart watchtower
   ```

4. **Disk space issues**:
   ```bash
   # Check largest files
   du -h /opt/watchtower/data | sort -hr | head -20

   # Clean old data (if configured)
   find /opt/watchtower/data -name "*.json" -mtime +30 -not -name "*_latest.json"
   ```

### Performance Tuning

1. **Increase ETL batch sizes** for better throughput
2. **Adjust cache timeouts** based on data freshness requirements
3. **Use SSD storage** for better I/O performance
4. **Configure appropriate resource limits** in systemd service files
5. **Monitor and optimize** database queries if using database storage

This deployment guide provides a solid foundation for running Watchtower in production environments with proper security, monitoring, and maintenance procedures.
