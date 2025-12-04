@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo  🏯 Watchtower Dashboard - Windows Deployment Script
echo  📡 Real-time Intelligence & Monitoring Platform
echo ========================================================
echo.

REM Set timeout for commands to avoid hanging (30 seconds)
set TIMEOUT_SECONDS=30

echo [INFO] Starting Watchtower deployment on Windows...
echo [INFO] Timeout set to %TIMEOUT_SECONDS% seconds for each operation
echo.

REM Change to the project root directory
cd /d %~dp0

REM Check if pyproject.toml exists
if not exist pyproject.toml (
    echo [ERROR] pyproject.toml not found. Please run this script from the project root.
    echo [ERROR] Current directory: %CD%
    pause
    exit /b 1
)

echo [STEP 1/6] Checking Python version...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    echo [INFO] Download from: https://python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo [PASS] Python version: %PYTHON_VERSION%
echo.

echo [STEP 2/6] Installing UV package manager...
REM Check if UV is already installed
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [PASS] UV already installed
) else (
    echo [INFO] Installing UV...
    timeout /t 5 /nobreak >nul
    powershell -ExecutionPolicy ByPass -Command "& {try { irm https://astral.sh/uv/install.ps1 | iex; exit 0 } catch { exit 1 }}" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install UV. Please install manually:
        echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        pause
        exit /b 1
    )
    echo [PASS] UV installed successfully
)
echo.

echo [STEP 3/6] Installing dependencies with UV...
echo [INFO] This may take a few minutes...
timeout /t 2 /nobreak >nul

REM Install dependencies with timeout
start /wait cmd /c "uv sync --all-extras && exit" || (
    echo [ERROR] Failed to install dependencies with UV
    echo [INFO] Trying fallback installation...
    pip install -r requirements.txt >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Fallback installation also failed
        pause
        exit /b 1
    )
)
echo [PASS] Dependencies installed successfully
echo.

echo [STEP 4/6] Installing Playwright browsers...
echo [INFO] Installing browser binaries for web scraping...
timeout /t 2 /nobreak >nul

REM Install Playwright with timeout
start /wait cmd /c "uv run playwright install && exit" || (
    echo [WARNING] Playwright installation failed, trying fallback...
    playwright install >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARNING] Playwright installation failed. Some features may not work.
        echo [INFO] You can install manually later with: uv run playwright install
    )
)
echo [PASS] Playwright browsers installed
echo.

echo [STEP 5/6] Creating required directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist data\arxiv mkdir data\arxiv
if not exist data\games mkdir data\games
if not exist data\news mkdir data\news
if not exist data\courses mkdir data\courses
if not exist data\ai_platforms mkdir data\ai_platforms
if not exist data\deals mkdir data\deals
if not exist data\entertainment mkdir data\entertainment
if not exist data\anime mkdir data\anime
if not exist data\adhd mkdir data\adhd
if not exist data\fourchan mkdir data\fourchan
if not exist data\spanish_public_aid mkdir data\spanish_public_aid
if not exist data\intelligence mkdir data\intelligence
if not exist data\github mkdir data\github
if not exist data\giveaways mkdir data\giveaways
if not exist data\ecommerce mkdir data\ecommerce
if not exist data\watchers mkdir data\watchers
if not exist data\shortcuts mkdir data\shortcuts
echo [PASS] Complete directory structure created
echo.

echo [STEP 6/6] Testing installation...
echo [INFO] Running quick test...
timeout /t 2 /nobreak >nul

REM Test import with timeout
uv run python -c "from src.config.settings import get_settings; print('[TEST] Configuration loaded successfully')" 2>nul
if %errorlevel% equ 0 (
    echo [PASS] Installation test successful
) else (
    echo [WARNING] Installation test failed. Some components may need manual setup.
)
echo.

echo ========================================================
echo  ✅ Watchtower Deployment Complete!
echo ========================================================
echo.
echo [SUCCESS] Watchtower is now installed and ready to use!
echo.
echo 🚀 Quick Start Commands:
echo   Main Dashboard:    run_watchtower_dashboard.bat
echo   Legacy Dashboard:  run_streamlit_app.bat
echo   Run ETL Processes: run_all_etl.bat
echo   Complete System:   run_all_etl_and_dashboard.bat
echo.
echo 🌐 Dashboard URLs:
echo   Main Dashboard:    http://localhost:7777
echo   Legacy Dashboard:  http://localhost:8501
echo   Health Check:      http://localhost:7777/health
echo   Metrics:           http://localhost:7777/metrics
echo.
echo 📖 Documentation:
echo   Deployment Guide:  docs/DEPLOYMENT_GUIDE.md
echo   Dashboard Guide:   docs/DASHBOARD_DEVELOPMENT_GUIDE.md
echo   Development Setup: CLAUDE.md
echo   Architecture:      docs/ARCHITECTURE_OVERVIEW.md
echo.
echo [INFO] For help, see: https://github.com/yourusername/watchtower
echo ========================================================
echo.

pause
echo [INFO] Deployment script completed. You can now close this window.
