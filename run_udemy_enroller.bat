@echo off
setlocal enabledelayedexpansion

REM Enhanced Udemy Course Enroller - Windows Task Scheduler Script
REM This script runs the unified CLI for automated course enrollment
REM Created: %DATE%

echo ========================================
echo Watchtower Udemy Course Enroller
echo Started: %DATE% %TIME%
echo ========================================

REM Change to the script directory
cd /d "%~dp0"

REM Set environment variables
set PYTHONPATH=%CD%\src
set UDEMY_LOG_DIR=%CD%\logs
set UDEMY_CONFIG_DIR=%CD%\src\miners\udemy-universal

REM Create logs directory if it doesn't exist
if not exist "%UDEMY_LOG_DIR%" mkdir "%UDEMY_LOG_DIR%"

REM Generate timestamp for log file
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "datestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

set LOG_FILE=%UDEMY_LOG_DIR%\udemy_enroller_%datestamp%.log

echo Starting Udemy course enrollment process...
echo Log file: %LOG_FILE%
echo Working directory: %CD%
echo.

REM Check if UV is available
uv --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: UV package manager not found!
    echo Please install UV first: https://docs.astral.sh/uv/
    echo.
    echo Installation command: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    exit /b 1
)

echo UV package manager found:
uv --version

REM Run the unified CLI with automated enrollment
echo.
echo Starting course enrollment with unified CLI...
echo Command: uv run src/miners/udemy-universal/unified_cli.py run --automated --config-file "%UDEMY_CONFIG_DIR%\default-duce-cli-settings.json"
echo.

REM Execute the enrollment process and capture output
uv run src/miners/udemy-universal/unified_cli.py run --automated --config-file "%UDEMY_CONFIG_DIR%\default-duce-cli-settings.json" > "%LOG_FILE%" 2>&1

set ENROLLMENT_RESULT=%errorlevel%

REM Check the result
if %ENROLLMENT_RESULT% equ 0 (
    echo.
    echo ========================================
    echo SUCCESS: Course enrollment completed successfully!
    echo Exit code: %ENROLLMENT_RESULT%
    echo Completed: %DATE% %TIME%
    echo Log file: %LOG_FILE%
    echo ========================================

    REM Display last few lines of log for quick summary
    echo.
    echo Last 10 lines of log:
    echo ----------------------------------------
    powershell "Get-Content '%LOG_FILE%' | Select-Object -Last 10"
    echo ----------------------------------------

) else (
    echo.
    echo ========================================
    echo ERROR: Course enrollment failed!
    echo Exit code: %ENROLLMENT_RESULT%
    echo Failed: %DATE% %TIME%
    echo Log file: %LOG_FILE%
    echo ========================================

    REM Display last few lines of log for error diagnosis
    echo.
    echo Last 20 lines of log for error diagnosis:
    echo ----------------------------------------
    powershell "Get-Content '%LOG_FILE%' | Select-Object -Last 20"
    echo ----------------------------------------
)

REM Clean up old log files (keep last 30 days)
echo.
echo Cleaning up old log files...
forfiles /p "%UDEMY_LOG_DIR%" /s /m udemy_enroller_*.log /d -30 /c "cmd /c del @path" >nul 2>&1

echo.
echo Process completed with exit code: %ENROLLMENT_RESULT%
echo End time: %DATE% %TIME%

REM Exit with the same code as the enrollment process
exit /b %ENROLLMENT_RESULT%
