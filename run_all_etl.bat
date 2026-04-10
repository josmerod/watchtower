@echo off
echo Starting ETL processes with Orchestrator at %date% %time%

REM Change to the project root directory
cd /d %~dp0

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
uv run python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Environment is not working properly!
    echo Please run setup_environment.bat to fix the environment.
    echo.
    pause
    exit /b 1
)

echo Using UV for Python Orchestrator
uv run python run_all_etl_orchestrator.py --workers 1

echo Script completed at %date% %time%
pause
