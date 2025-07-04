# Watchtower Deployment

## One-Command Setup

Setting up Watchtower is now as simple as running a single command:

```bash
git clone https://github.com/josmerod/watchtower.git
cd watchtower
./deploy.sh
```

That's it! The deployment script will automatically:

✅ **Environment Setup**
- Detect and validate Ubuntu 24.04+ system
- Install required system packages (Python, build tools, etc.)
- Create and configure Python virtual environment
- Install all Python dependencies including Playwright browsers

✅ **Configuration**
- Generate environment configuration files
- Create necessary data and log directories
- Set up proper permissions and paths

✅ **ETL Pipeline Deployment**
- Deploy all ETL pipelines for data collection
- Configure logging and error handling
- Validate pipeline functionality

✅ **Dashboard Deployment**
- Deploy Streamlit web dashboard
- Configure as systemd service for auto-start
- Set up proper networking and accessibility

✅ **Post-Deployment Validation**
- Verify all components are working
- Test service connectivity
- Validate configuration integrity

## What You Get

After running `./deploy.sh`, you'll have:

- **Streamlit Dashboard**: Available at http://localhost:8501
- **ETL Pipelines**: Ready to collect data from 20+ sources
- **System Service**: Auto-starts on boot, manages restarts
- **Comprehensive Logging**: All activities logged for monitoring
- **Error Handling**: Robust error recovery and rollback capabilities

## Service Management

Control your Watchtower installation:

```bash
# Start/stop the dashboard
sudo systemctl start watchtower-streamlit
sudo systemctl stop watchtower-streamlit
sudo systemctl restart watchtower-streamlit

# Check status
sudo systemctl status watchtower-streamlit

# Run ETL pipelines manually
./run_all_etl.sh
```

## Requirements

- **Operating System**: Ubuntu 20.04+ (tested on 24.04)
- **Privileges**: sudo access for package installation
- **Network**: Internet connection for downloading dependencies
- **Disk Space**: ~2GB free space for dependencies and data
- **Memory**: 2GB+ RAM recommended for optimal performance

## Features

- **Zero Configuration**: No manual setup steps required
- **Idempotent**: Safe to run multiple times
- **Rollback Support**: Automatic cleanup on failure
- **Cross-Platform Ready**: Prepared for future Windows/macOS support
- **Production Ready**: Systemd service integration included

## Troubleshooting

If deployment fails:

1. **Check the logs**: `tail -f logs/deployment.log`
2. **Verify system requirements**: Ensure Ubuntu 20.04+ with sudo access
3. **Check internet connectivity**: Required for package downloads
4. **Re-run deployment**: The script is designed to be re-runnable

For issues, check the troubleshooting section in the full README or create an issue on GitHub.