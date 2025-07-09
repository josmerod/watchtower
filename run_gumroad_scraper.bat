@echo off
echo Starting Gumroad Free Products Scraper at %date% %time%

REM Change to the project root directory
cd /d %~dp0

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Check if this is a first run or regular run
if "%1"=="--first-run" (
    echo Running first-time scraping (10000 items)
    uv run python run_gumroad_scraper.py --first-run > logs/gumroad_scraper.log 2>&1
) else if "%1"=="--debug" (
    echo Running with debug logging
    uv run python run_gumroad_scraper.py --debug > logs/gumroad_scraper.log 2>&1
) else if "%1"=="--dry-run" (
    echo Running dry run (no data saved)
    uv run python run_gumroad_scraper.py --dry-run > logs/gumroad_scraper.log 2>&1
) else if "%1"=="--help" (
    echo Usage: run_gumroad_scraper.bat [--first-run^|--debug^|--dry-run^|--help]
    echo.
    echo Options:
    echo   --first-run  Run first-time scraping (10000 items instead of 500)
    echo   --debug      Enable debug logging
    echo   --dry-run    Run without saving data (for testing)
    echo   --help       Show this help message
    goto :end
) else (
    echo Running regular scraping (500 items)
    uv run python run_gumroad_scraper.py > logs/gumroad_scraper.log 2>&1
)

if %errorlevel% equ 0 (
    echo Gumroad scraper completed successfully
    echo Check logs/gumroad_scraper.log for details
) else (
    echo Gumroad scraper failed with error code %errorlevel%
    echo Check logs/gumroad_scraper.log for error details
)

:end
echo Finished at %date% %time%

REM Show data directories if successful
if %errorlevel% equ 0 (
    echo.
    echo Data directories:
    echo - data/gumroad_scraper/output/
    echo - data/scavenging/
)

pause 