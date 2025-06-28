@echo off
echo Starting Watchtower Dashboard with UV...
echo.

REM Check if UV is available
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo UV not found. Please install UV first:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

REM Start Streamlit app using UV
echo Starting Streamlit on http://localhost:8501
echo Running: uv run streamlit run src/web/fullstreamlit/app.py
uv run streamlit run src/web/fullstreamlit/app.py --server.port=8501
pause 