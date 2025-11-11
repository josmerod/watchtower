# Watchtower Advanced Deployment Guide

This guide covers the new unified deployment system that provides system-independent, auto-starting, and robust execution of the Watchtower intelligence platform.

## 🚀 Quick Start

### Option 1: Simple CLI (Recommended for Development)

```bash
# Development mode with hot reload
python watchtower.py dev

# Production mode
python watchtower.py prod

# ETL only mode
python watchtower.py etl

# Dashboard only mode
python watchtower.py dashboard
```

### Option 2: Podman Compose (Recommended for Production)

```bash
# Development deployment
python watchtower.py podman-dev --build

# Production deployment
python watchtower.py podman-prod --build

# Stop containers
python watchtower.py podman-stop
```

### Option 3: System Service (For Production Servers)

```bash
# Install as system service
python watchtower.py service install

# Start the service
python watchtower.py service start

# Check status
python watchtower.py service status
```

## 📋 Deployment Options Overview

| Method | Best For | Auto-start | Hot Reload | Resource Usage | Setup Complexity |
|--------|----------|------------|------------|----------------|------------------|
| **CLI** | Development | ❌ Manual | ✅ Yes | Low | Very Low |
| **Podman** | Production | ✅ Containers | ❌ No | Medium | Medium |
| **Service** | Servers | ✅ System | ❌ No | Low | High |

## 🔧 Detailed Setup Instructions

### Prerequisites

1. **Python 3.10+** with UV package manager
2. **Dependencies installed**: `uv sync --all-extras`
3. **Optional**: Podman and podman-compose for containerized deployment

### CLI Deployment (Development)

The CLI deployment is perfect for development with hot reload capabilities:

```bash
# Start in development mode
python watchtower.py dev

# Start in background (for servers)
python watchtower.py dev --background

# Check status
python watchtower.py status
```

**Features:**
- ✅ Hot reload on code changes (development mode only)
- ✅ Automatic ETL scheduling
- ✅ Health monitoring and recovery
- ✅ Parallel ETL execution
- ✅ Comprehensive logging

### Podman Compose Deployment (Production)

For production deployments, Podman Compose provides containerized, isolated execution:

#### Development Containers

```bash
# Build and start development containers
python watchtower.py podman-dev --build

# Access dashboard at http://localhost:7777
# View logs: podman-compose -f docker-compose.dev.yml logs -f
```

#### Production Containers

```bash
# Build and start production containers
python watchtower.py podman-prod --build

# Dashboard available at http://localhost:7777
# Check container status: podman-compose ps
# View logs: podman-compose logs -f
```

**Features:**
- ✅ Complete isolation from host system
- ✅ Consistent environment across machines
- ✅ Easy scaling and load balancing
- ✅ Health checks built-in
- ✅ Automatic restart policies

### System Service Deployment (Production Servers)

For production servers, install Watchtower as a system service:

#### Linux (systemd)

```bash
# Install service
sudo python watchtower.py service install

# Start service
sudo python watchtower.py service start

# Check status
sudo python watchtower.py service status

# View logs
sudo journalctl -u watchtower -f
```

#### macOS (launchd)

```bash
# Install service
python watchtower.py service install

# Start service
python watchtower.py service start

# Check status
python watchtower.py service status

# View logs
tail -f ~/Library/LaunchAgents/com.watchtower.platform.plist logs
```

#### Windows (Service)

```powershell
# Install service (requires NSSM or administrator privileges)
python watchtower.py service install

# Start service
python watchtower.py service start

# Check status
python watchtower.py service status

# View logs
Get-EventLog -LogName Application -Source WatchtowerPlatform
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCHTOWER_MODE` | development | Execution mode (development/production/etl_only/dashboard_only) |
| `WATCHTOWER_ETL_INTERVAL` | 3600 | ETL execution interval in seconds |
| `WATCHTOWER_DASHBOARD_PORT` | 7777 | Dashboard port |
| `WATCHTOWER_LOG_LEVEL` | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `WATCHTOWER_HOT_RELOAD` | false | Enable hot reload (development mode only) |

### Custom Configuration

You can override any configuration by setting environment variables:

```bash
# Custom ETL interval (30 minutes)
WATCHTOWER_ETL_INTERVAL=1800 python watchtower.py prod

# Debug logging
WATCHTOWER_LOG_LEVEL=DEBUG python watchtower.py dev

# Custom dashboard port
WATCHTOWER_DASHBOARD_PORT=8080 python watchtower.py dashboard
```

## 🔍 Monitoring and Health Checks

### Health Monitoring Features

The new deployment system includes comprehensive health monitoring:

- **Process Health**: Monitors dashboard and ETL processes
- **System Resources**: CPU, memory, and disk usage tracking
- **Data Integrity**: Validates data directory structure and recent files
- **Network Connectivity**: Tests external service availability
- **External Dependencies**: Verifies required modules are available

### Automatic Recovery

When health issues are detected, the system automatically:

1. **Restarts failed processes** with exponential backoff
2. **Cleans up disk space** when usage is high (>85%)
3. **Restarts categories** of ETL processes when individual ones fail
4. **Provides detailed logging** for troubleshooting

### Status Checking

```bash
# Check overall status
python watchtower.py status

# View health metrics (JSON format)
curl http://localhost:7777/health

# Check Docker container health
docker-compose ps
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs for errors
python watchtower.py service status

# View detailed logs
tail -f logs/launcher.log

# Check system resources
python watchtower.py status
```

#### 2. Podman Issues

```bash
# Check container status
podman-compose ps

# View container logs
podman-compose logs

# Rebuild containers
python watchtower.py podman-prod --build
```

#### 3. High Resource Usage

```bash
# Check system resources
python watchtower.py status

# The system will automatically clean up old files
# Manual cleanup if needed
find data -type f -mtime +30 -delete
```

#### 4. ETL Processes Failing

```bash
# Check which processes are running
python watchtower.py status

# View ETL logs
tail -f logs/etl_*.log

# Restart ETL processes
python watchtower.py etl
```

### Log Files

- **Main logs**: `logs/launcher.log`
- **Health metrics**: `logs/health_metrics.jsonl`
- **ETL process logs**: `logs/etl_*.log`
- **System logs**: `/var/log/watchtower.log` (system service)

## 🔄 Migration from Old System

### From Batch Files/Windows Task Scheduler

1. **Stop existing processes**: Close any running batch files or scheduled tasks
2. **Install new system**: Choose Docker or Service deployment method
3. **Verify functionality**: Check status with `python watchtower.py status`
4. **Remove old files**: Delete old `.bat` files and scheduled tasks

### Environment Migration

The new system uses the same data directories and configuration, so your existing data will be preserved.

## 📈 Performance Improvements

The new deployment system provides significant improvements over the old batch file approach:

| Aspect | Old System | New System | Improvement |
|--------|------------|------------|-------------|
| **Startup Time** | Manual execution | Auto-start on boot | ✅ System service |
| **Error Handling** | Basic | Comprehensive recovery | ✅ Health monitoring |
| **Resource Management** | Uncontrolled | Intelligent scheduling | ✅ Parallel execution |
| **Monitoring** | Manual | Automatic | ✅ Real-time health checks |
| **Hot Reload** | None | Development mode | ✅ Code change detection |
| **Cross-platform** | Windows only | All platforms | ✅ Podman + Services |

## 🔒 Security Considerations

### Production Deployment

1. **Use Podman containers** for production to isolate the application
2. **Run as non-root user** in containers
3. **Limit resource usage** with container limits
4. **Use secrets management** for API keys and credentials
5. **Enable health checks** for load balancer integration

### Service Security

1. **System services run as dedicated user** (not root)
2. **Resource limits** prevent system overload
3. **Private temporary directories** for security
4. **No new privileges** escalation

## 📚 Advanced Usage

### Custom ETL Scheduling

```bash
# Run ETL every 30 minutes
WATCHTOWER_ETL_INTERVAL=1800 python watchtower.py prod

# Run only specific ETL categories
# (Configure in src/launcher/main.py ETLScheduler.etl_categories)
```

### Multiple Instances

```bash
# Run dashboard on different port
WATCHTOWER_DASHBOARD_PORT=7778 python watchtower.py dashboard

# Run ETL with different intervals
WATCHTOWER_ETL_INTERVAL=7200 python watchtower.py etl
```

### Development Workflow

```bash
# Start development environment
python watchtower.py dev

# Make code changes - automatic hot reload
# Check status
python watchtower.py status

# View logs
tail -f logs/launcher.log
```

This advanced deployment system provides a robust, scalable, and maintainable foundation for the Watchtower intelligence platform, addressing all the limitations of the previous batch file approach while adding powerful new capabilities for monitoring and automatic recovery.
