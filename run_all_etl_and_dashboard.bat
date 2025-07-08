@echo off
echo ========================================================
echo  🏯 Watchtower Complete System Launcher
echo  📡 ETL Processes + Dashboard
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

echo [INFO] Starting ETL processes first...
echo.

REM Create required directories
if not exist data mkdir data
if not exist logs mkdir logs

echo [INFO] Running ETL processes...
call run_all_etl.bat

echo.
echo [INFO] Waiting 5 seconds for ETL processes to initialize...
timeout /t 5 /nobreak >nul

echo.
echo [INFO] Starting Watchtower Dashboard...
echo Dashboard will be available at: http://localhost:7777
echo ========================================================
echo.

REM Run the Watchtower Dashboard
uv run python run_watchtower_dashboard.py

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Watchtower Dashboard failed to start. Please check the output above.
) else (
    echo.
    echo [SUCCESS] Watchtower system closed successfully.
)

echo.
pause 