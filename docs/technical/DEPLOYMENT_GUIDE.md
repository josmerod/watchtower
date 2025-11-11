# Deployment Guide

This guide covers deployment strategies, configuration, and operational procedures for the Watchtower platform.

## Quick Start Deployment

### Prerequisites

- **Python 3.10+** (required for modern type hints and performance)
- **UV Package Manager** (recommended) or pip + venv
- **Git** for version control
- **4GB+ RAM** recommended for processing large datasets
- **20GB+ storage** for data files and logs

### Basic Setup

```bash
# Clone the repository
git clone <repository-url>
cd watchtower

# Install dependencies with UV (recommended)
uv sync --all-extras

# Alternative: Traditional pip installation
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Install Playwright browsers for web scraping
uv run playwright install
# or
playwright install

# Create necessary directories
mkdir -p data logs

# Verify installation
uv run python -c "import src.config.settings; print('Setup successful')"
```

### Environment Configuration

Create `.env` file in the project root:

```bash
# Environment configuration
ENVIRONMENT=production
DEBUG=false

# Database configuration (if using database storage)
DATABASE__URL=sqlite:///data/watchtower.db
DATABASE__ECHO=false

# Logging configuration
LOGGING__LEVEL=INFO
LOGGING__FILE_ENABLED=true
LOGGING__CONSOLE_ENABLED=true

# ETL configuration
ETL__BATCH_SIZE=100
ETL__MAX_RETRIES=3
ETL__CLEANUP_OLD_DATA_DAYS=30

# API Keys (add as needed)
# API__OPENAI_KEY=your_openai_key_here
# API__GITHUB_TOKEN=your_github_token_here
# API__REDDIT_CLIENT_ID=your_reddit_client_id

# Dashboard configuration
STREAMLIT__PORT=8501
STREAMLIT__HOST=0.0.0.0

# Scraping configuration
SCRAPING__USER_AGENT=Watchtower/1.0 (+https://github.com/josmerod/watchtower)
SCRAPING__TIMEOUT=30
SCRAPING__MAX_RETRIES=3
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

# Copy requirements and install dependencies
COPY requirements.txt uv.lock* pyproject.toml ./
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
    CMD curl -f http://localhost:7777/health || exit 1

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
      - "7777:7777"  # Dash dashboard
      - "8501:8501"  # Streamlit dashboard (if needed)
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7777/health"]
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
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env
    command: ["uv", "run", "python", "src/schedulers/etl_scheduler.py"]
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

### ETL Scheduling Service

Create `/etc/systemd/system/watchtower-etl.service`:

```ini
[Unit]
Description=Watchtower ETL Scheduler
After=network.target

[Service]
Type=simple
User=watchtower
Group=watchtower
WorkingDirectory=/opt/watchtower
Environment=PATH=/opt/watchtower/.venv/bin
ExecStart=/opt/watchtower/.venv/bin/python -c "
import schedule
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_etl():
    logger.info('Starting ETL run')
    subprocess.run(['/opt/watchtower/.venv/bin/python', '-m', 'src.etl.run_all_etl'])
    logger.info('ETL run completed')

# Schedule ETL runs
schedule.every(6).hours.do(run_etl)
schedule.every().day.at('02:00').do(run_etl)

while True:
    schedule.run_pending()
    time.sleep(60)
"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

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
uv sync --all-extras
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
    server 127.0.0.1:7777;
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
sudo ufw allow 7777/tcp

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
   netstat -tlnp | grep 7777
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