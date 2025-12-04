@echo off
echo ========================================================
echo  🏯 Watchtower Legacy Streamlit Dashboard
echo  📡 Old Streamlit Implementation (Port 8501)
echo ========================================================
echo.
echo [DEPRECATED] This launches the old Streamlit dashboard.
echo [RECOMMENDED] Use run_watchtower_dashboard.bat for the new Dash dashboard.
echo.

REM Check if UV is available
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo UV not found. Please install UV first:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

echo [INFO] Starting Legacy Streamlit Dashboard...
echo Dashboard will be available at: http://localhost:8501
echo ========================================================
echo.

REM Start Streamlit app using UV
uv run streamlit run src/web/fullstreamlit/app.py --server.port=8501
pause
