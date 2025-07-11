# 🏯 Watchtower Dashboard - Deployment Guide

## Overview

This guide explains how to deploy the Watchtower Dashboard on different operating systems using the automated deployment scripts with built-in timeout handling.

## Quick Start

### One-Click Installation (Recommended)

Run the unified installer that automatically detects your OS:

```bash
python install_watchtower.py
```

This script will:
- ✅ Auto-detect your operating system
- ✅ Run the appropriate deployment script
- ✅ Handle timeouts to prevent hanging
- ✅ Provide clear error messages and troubleshooting

### Manual Installation by OS

If you prefer to run the OS-specific scripts directly:

#### Windows
```cmd
deploy_windows.bat
```

#### macOS
```bash
bash deploy_mac.sh
```

#### Linux
```bash
bash deploy_linux.sh
```

## What the Deployment Scripts Do

### 1. System Requirements Check
- ✅ Verify Python 3.10+ installation
- ✅ Check system compatibility
- ✅ Validate project structure

### 2. Package Manager Installation
- ✅ Install UV package manager (10-100x faster than pip)
- ✅ Fallback to pip if UV installation fails
- ✅ Add UV to system PATH

### 3. Dependency Installation
- ✅ Install all Python dependencies with `uv sync --all-extras`
- ✅ Timeout handling to prevent hanging
- ✅ Fallback to pip if needed

### 4. Browser Setup
- ✅ Install Playwright browser binaries
- ✅ Configure web scraping capabilities
- ✅ Handle installation failures gracefully

### 5. Project Structure
- ✅ Create required directories (`data/`, `logs/`, etc.)
- ✅ Set up proper file permissions
- ✅ Initialize project structure

### 6. Installation Verification
- ✅ Test configuration loading
- ✅ Verify all components work
- ✅ Provide success confirmation

## Timeout Handling

All deployment scripts include **30-second timeouts** for individual operations and **10-minute overall timeout** to prevent hanging issues:

- **Network Operations**: 30 seconds
- **Package Installation**: 30 seconds  
- **Browser Installation**: 30 seconds
- **Overall Process**: 10 minutes

If a timeout occurs, the script will:
1. Display clear error message
2. Suggest troubleshooting steps
3. Provide fallback options
4. Exit gracefully

## Post-Installation

After successful deployment, you can use these commands:

### Main Dashboard (Recommended)
```bash
# Windows
run_watchtower_dashboard.bat

# macOS/Linux
./run_watchtower_dashboard.sh
```
**URL**: http://localhost:7777

### Legacy Dashboard
```bash
# Windows
run_watchtower.bat

# macOS/Linux
./run_streamlit.sh
```
**URL**: http://localhost:8501

### ETL Processes
```bash
# Windows
run_all_etl.bat

# macOS/Linux
./run_all_etl.sh
```

### Complete System
```bash
# Windows
run_all_etl_and_dashboard.bat

# macOS/Linux
./run_all_etl_and_dashboard.sh
```

## Troubleshooting

### Common Issues

#### 1. Python Not Found
```bash
# Windows
# Download from: https://python.org/downloads/

# macOS
brew install python
# Or: xcode-select --install

# Linux (Ubuntu/Debian)
sudo apt update && sudo apt install python3 python3-pip

# Linux (CentOS/RHEL)
sudo yum install python3 python3-pip
```

#### 2. UV Installation Fails
```bash
# Manual UV installation
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew (macOS)
brew install uv
```

#### 3. Timeout Issues
- Check network connection
- Increase timeout in script if needed
- Use fallback pip installation
- Run components manually

#### 4. Permission Errors (macOS/Linux)
```bash
# Make scripts executable
chmod +x *.sh

# Install Xcode Command Line Tools (macOS)
sudo xcode-select --install
```

#### 5. Windows PowerShell Execution Policy
```powershell
# If needed, allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Advanced Troubleshooting

#### Manual Installation Steps
If automated deployment fails, you can install manually:

1. **Install UV**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Dependencies**:
   ```bash
   uv sync --all-extras
   ```

3. **Install Playwright**:
   ```bash
   uv run playwright install
   ```

4. **Test Installation**:
   ```bash
   uv run python -c "from src.config.settings import get_settings; print('Success!')"
   ```

#### Timeout Modifications
To modify timeouts, edit the deployment scripts:

- **Individual operations**: Change `TIMEOUT_SECONDS=30`
- **Overall timeout**: Modify `timeout_seconds=600` in `install_watchtower.py`

## Security Considerations

- Scripts download UV from official Astral repository
- Playwright installs browsers in isolated environment
- No elevated permissions required
- All dependencies verified through pyproject.toml

## Platform-Specific Notes

### Windows
- Works with Command Prompt and PowerShell
- Handles Windows path separators correctly
- Includes .bat file execution

### macOS
- Supports both Intel and Apple Silicon
- Integrates with Homebrew if available
- Handles Xcode Command Line Tools

### Linux
- Works with all major distributions
- Supports different package managers
- Handles various shell environments

## Next Steps

After successful deployment:

1. **Explore the Dashboard**: Visit http://localhost:7777
2. **Run ETL Processes**: Use `run_all_etl` scripts
3. **Read Documentation**: Check `docs/` folder
4. **Customize Settings**: Edit configuration files
5. **Add Data Sources**: Configure new ETL processes

## Support

If you encounter issues:
1. Check the console output for specific error messages
2. Review this troubleshooting guide
3. Check the project documentation
4. Look at the issue tracker on GitHub

---

**Happy Monitoring!** 🏯📡 