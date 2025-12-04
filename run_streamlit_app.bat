@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo  Watchtower Dashboard
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

REM Check if environment is set up
if not exist ".venv" (
    echo.
    echo ERROR: Virtual environment not found!
    echo Please run setup_environment.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

REM Verify UV and virtual environment are working
echo Checking environment...
uv run python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Environment is not working properly!
    echo Please run setup_environment.bat to fix the environment.
    echo.
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

echo.
echo Starting Watchtower Dashboard
echo.
echo Dashboard will be available at: http://localhost:7777
echo Press Ctrl+C to stop the server
echo.
echo ==========================================
echo.

REM Run the dashboard with proper error handling
uv run python run_watchtower_dashboard.py
set RUN_RESULT=%errorlevel%

echo.
echo ==========================================
if %RUN_RESULT% equ 0 (
    echo Dashboard stopped normally
) else (
    echo Dashboard stopped with error code: %RUN_RESULT%
    echo.
    echo If you see 'pyvenv.cfg' errors, try:
    echo 1. Run cleanup_env.bat first
    echo 2. Run this script again
    echo 3. Restart your computer
    echo 4. Run as administrator
)
echo ==========================================
echo.

pause
