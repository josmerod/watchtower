@echo off
echo ========================================================
echo  Watchtower New Dashboard POC Launcher (with UV)
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

echo [INFO] UV is available. Starting the New Dashboard POC...
echo.
echo Running: uv run python run_new_dashboard_poc.py
echo ========================================================
echo.

REM Run the new dashboard POC script using UV
uv run python run_new_dashboard_poc.py

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] The script failed to run. Please check the output above.
) else (
    echo.
    echo [SUCCESS] Application closed successfully.
)

echo.
pause