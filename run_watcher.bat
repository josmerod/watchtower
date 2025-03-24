@echo off
REM Watcher runner batch file for Windows
REM This makes it easy to run watchers without having to type out the full command

SETLOCAL ENABLEDELAYEDEXPANSION

REM Set up paths
SET "SCRIPT_DIR=%~dp0"
SET "PYTHON_PATH=python"
SET "WATCHER_SCRIPT=src\watchers\run_watcher.py"

REM Check if Python is available
%PYTHON_PATH% --version 2>NUL
IF %ERRORLEVEL% NEQ 0 (
    ECHO Python is not available. Please install Python or update your PATH.
    EXIT /B 1
)

REM Check if a watcher name was provided
IF "%~1"=="" (
    ECHO Running all watchers
    %PYTHON_PATH% "%SCRIPT_DIR%%WATCHER_SCRIPT%" all %*
) ELSE (
    ECHO Running watcher: %~1
    %PYTHON_PATH% "%SCRIPT_DIR%%WATCHER_SCRIPT%" %*
)

IF %ERRORLEVEL% NEQ 0 (
    ECHO Error running watcher. Check logs for details.
    EXIT /B 1
)

ECHO Watcher execution completed.
EXIT /B 0 