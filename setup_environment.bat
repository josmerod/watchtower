@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo  Watchtower Environment Setup
echo ==========================================
echo.

REM Change to the project root directory
cd /d "%~dp0"

REM Verify we're in the right directory
if not exist "pyproject.toml" (
    echo Error: pyproject.toml not found. Please run from project root.
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if UV is available
echo Checking UV installation...
uv --version >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: UV not found. Installing UV...
    echo.
    powershell -Command "& {try { Invoke-RestMethod -Uri 'https://astral.sh/uv/install.ps1' | Invoke-Expression } catch { Write-Host 'Failed to install UV automatically. Please install manually.' -ForegroundColor Red; exit 1 }}"
    
    REM Check if UV is now available
    uv --version >nul 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo UV installation failed. Please install UV manually:
        echo   powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex"
        echo.
        pause
        exit /b 1
    )
)

echo UV version: 
uv --version

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

echo.
echo Setting up Python environment...
echo.

REM Check if virtual environment already exists and is working
if exist ".venv" (
    echo Checking existing virtual environment...
    uv run python --version >nul 2>nul
    if %errorlevel% equ 0 (
        echo Virtual environment exists and is working!
        echo.
        echo Checking if dependencies are up to date...
        uv sync --check >nul 2>nul
        if %errorlevel% equ 0 (
            echo Dependencies are up to date. Environment ready!
            echo.
            echo Environment setup completed successfully!
            echo You can now run:
            echo   .\run_all_etl.bat
            echo   .\run_streamlit_app.bat
            echo.
            pause
            exit /b 0
        ) else (
            echo Dependencies need updating...
        )
    ) else (
        echo Virtual environment is corrupted, recreating...
    )
)

REM Kill any processes that might be using the venv
echo Terminating any Python processes...
taskkill /f /im python.exe >nul 2>nul
taskkill /f /im python3.exe >nul 2>nul
taskkill /f /im pythonw.exe >nul 2>nul

REM Wait for processes to terminate
timeout /t 2 /nobreak >nul

REM Remove existing virtual environment if it exists
if exist ".venv" (
    echo Removing existing virtual environment...
    
    REM Try basic removal first
    rmdir /s /q ".venv" >nul 2>nul
    
    REM If that fails, try PowerShell force removal
    if exist ".venv" (
        echo Using PowerShell force removal...
        powershell -Command "& {Get-ChildItem -Path '.venv' -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item '.venv' -Recurse -Force -ErrorAction SilentlyContinue}"
    )
    
    REM Final check
    if exist ".venv" (
        echo WARNING: Cannot remove .venv directory completely.
        echo This may cause issues. Consider restarting your computer.
        echo Continuing anyway...
    ) else (
        echo .venv removed successfully!
    )
)

REM Clear UV cache
echo Clearing UV cache...
uv cache clean >nul 2>nul

REM Set UV environment variables for Windows compatibility
set UV_LINK_MODE=copy
set UV_CACHE_DIR=%TEMP%\uv-cache-%RANDOM%
set UV_PYTHON_PREFERENCE=only-managed

echo.
echo Creating fresh virtual environment...
echo.

REM Install Python 3.11 if needed
echo Installing Python 3.11...
uv python install 3.11 >nul 2>nul

REM Create new virtual environment
echo Creating new virtual environment...
uv venv --seed >nul 2>nul
if %errorlevel% neq 0 (
    echo Trying alternative venv creation...
    uv venv --python 3.11 --seed >nul 2>nul
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        echo.
        echo Manual steps:
        echo 1. Restart your computer
        echo 2. Run as administrator
        echo 3. Or try: uv venv --python 3.11
        echo.
        pause
        exit /b 1
    )
)

REM Install dependencies with retry logic
echo Installing dependencies...
set MAX_RETRIES=3
set RETRY_COUNT=0

:retry_sync
set /a RETRY_COUNT+=1
echo Attempt %RETRY_COUNT% of %MAX_RETRIES%

uv sync --all-extras --reinstall
set SYNC_RESULT=%errorlevel%

if %SYNC_RESULT% neq 0 (
    if %RETRY_COUNT% lss %MAX_RETRIES% (
        echo Sync failed, retrying in 3 seconds...
        timeout /t 3 /nobreak >nul
        uv cache clean >nul 2>nul
        goto retry_sync
    ) else (
        echo.
        echo ERROR: Failed to sync dependencies after %MAX_RETRIES% attempts.
        echo.
        echo Troubleshooting steps:
        echo 1. Check internet connection
        echo 2. Run: uv cache clean
        echo 3. Restart computer and try again
        echo 4. Run as administrator
        echo.
        pause
        exit /b 1
    )
)

REM Install Playwright browsers
echo.
echo Installing Playwright browsers...
uv run playwright install >nul 2>nul
if %errorlevel% neq 0 (
    echo Warning: Playwright browser installation failed. Web scraping may not work properly.
)

REM Verify the virtual environment is working
echo.
echo Verifying Python environment...
uv run python --version
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python environment verification failed.
    echo Please run this script again or restart your computer.
    pause
    exit /b 1
)

REM Test core dependencies
echo Testing core dependencies...
uv run python -c "import requests; import feedparser; import pandas; import playwright; print('All core dependencies available!')"
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Core dependencies are not working properly.
    echo Please run this script again.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Environment setup completed successfully!
echo ==========================================
echo.
echo You can now run your automation scripts:
echo   .\run_all_etl.bat         - Run ETL processes
echo   .\run_streamlit_app.bat   - Run dashboard
echo.
echo This setup script only needs to be run once or when
echo dependencies change. The automation scripts will now
echo be much faster and more reliable.
echo.
pause