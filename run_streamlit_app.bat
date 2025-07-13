@echo off
echo.
echo ==========================================
echo  Watchtower Dashboard with UV
echo ==========================================
echo.
echo Starting dashboard using UV...
echo.

REM Change to the project root directory
cd /d %~dp0

REM Check if UV is available
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo UV not found. Please install UV first:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
echo.
    pause
    exit /b 1
)

REM Check if pyproject.toml exists
if not exist pyproject.toml (
    echo Error: pyproject.toml not found. Please run from project root.
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Clean up incompatible virtual environment if it exists
if exist .venv (
    echo Removing incompatible virtual environment...
    rmdir /s /q .venv
)

REM Create Windows-compatible virtual environment
echo Setting up Windows virtual environment...
uv sync --all-extras
if %errorlevel% neq 0 (
    echo Failed to create virtual environment. Please check UV installation.
    pause
    exit /b 1
)

echo Running: uv run python run_watchtower_dashboard.py
echo.
echo Dashboard will be available at: http://localhost:7777
echo Press Ctrl+C to stop the server
echo.
echo ==========================================
echo.

REM Set UV environment for Windows/WSL compatibility  
set UV_LINK_MODE=copy

REM Run the dashboard using UV
uv run python run_watchtower_dashboard.py

echo.
echo ==========================================
echo Dashboard stopped
echo ==========================================
echo.
pause