@echo off
echo ========================================================
echo  🏯 Watchtower Dashboard - Main Launcher
echo  📡 Real-time Intelligence & Monitoring Platform
echo ========================================================
echo.

REM Change to the project root directory
cd /d %~dp0

REM Check if UV is available
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] UV not found. Please install UV first:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    pause
    exit /b 1
)

echo [INFO] UV is available. Starting Watchtower Dashboard...
echo.
echo Running: uv run python run_watchtower_dashboard.py
echo Dashboard will be available at: http://localhost:7777
echo ========================================================
echo.

REM Run the Watchtower Dashboard using UV
uv run python run_watchtower_dashboard.py

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Watchtower Dashboard failed to start. Please check the output above.
) else (
    echo.
    echo [SUCCESS] Watchtower Dashboard closed successfully.
)

echo.
pause 