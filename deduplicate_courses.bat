@echo off
setlocal enabledelayedexpansion

REM Deduplicate Courses Utility
REM This script runs the course deduplication tool on JSON files

REM Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in the PATH.
    echo Please install Python and try again.
    exit /b 1
)

REM Determine the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Activate virtual environment if exists
if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
)

REM Process command line arguments
set "INPUT_PATH="
set "OUTPUT_PATH="
set "KEY_FIELD=url"
set "PREFER_OLDER="
set "RECURSIVE="
set "BACKUP=--backup"
set "VERBOSE="

:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="--help" (
    echo Usage: deduplicate_courses.bat [input_path] [options]
    echo.
    echo Options:
    echo   --output-file PATH   Output file path (for single file)
    echo   --key-field FIELD    Field to use for deduplication (url or title)
    echo   --prefer-older       Keep older entries (default: keep newer)
    echo   --recursive          Process directories recursively
    echo   --no-backup          Don't create backup files
    echo   --verbose            Enable verbose output
    echo.
    exit /b 0
)
if "!INPUT_PATH!"=="" (
    set "INPUT_PATH=%~1"
) else if /i "%~1"=="--output-file" (
    set "OUTPUT_PATH=--output-file %~2"
    shift
) else if /i "%~1"=="--key-field" (
    set "KEY_FIELD=%~2"
    shift
) else if /i "%~1"=="--prefer-older" (
    set "PREFER_OLDER=--prefer-older"
) else if /i "%~1"=="--recursive" (
    set "RECURSIVE=--recursive"
) else if /i "%~1"=="--no-backup" (
    set "BACKUP="
) else if /i "%~1"=="--verbose" (
    set "VERBOSE=--verbose"
)
shift
goto :parse_args
:end_parse_args

REM Check for required arguments
if "!INPUT_PATH!"=="" (
    echo Error: No input path specified.
    echo Try 'deduplicate_courses.bat --help' for usage information.
    exit /b 1
)

REM Execute the deduplication script
echo Running course deduplication...
python "%SCRIPT_DIR%src\utils\deduplicate_courses_cli.py" "!INPUT_PATH!" !OUTPUT_PATH! --key-field !KEY_FIELD! !PREFER_OLDER! !RECURSIVE! !BACKUP! !VERBOSE!

if %errorlevel% neq 0 (
    echo Deduplication failed with error code %errorlevel%
    exit /b %errorlevel%
)

echo Deduplication completed successfully.
exit /b 0 