@echo off
echo.
echo ==========================================
echo  Watchtower Streamlit Dashboard with UV
echo ==========================================
echo.
echo Starting Streamlit dashboard using UV...
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

echo Running: uv run streamlit run src/web/fullstreamlit/app.py
echo.
echo Dashboard will be available at: http://localhost:5555
echo Press Ctrl+C to stop the server
echo.
echo ==========================================
echo.

REM Run the Streamlit app using UV
uv run streamlit run src/web/fullstreamlit/app.py --server.port=5555 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false

echo.
echo ==========================================
echo Dashboard stopped
echo ==========================================
echo.
pause