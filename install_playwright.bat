@echo off
REM Install Playwright and its browser dependencies

SETLOCAL ENABLEDELAYEDEXPANSION

REM Set up paths
SET "SCRIPT_DIR=%~dp0"
SET "PYTHON_PATH=python"

REM Check if Python is available
%PYTHON_PATH% --version 2>NUL
IF %ERRORLEVEL% NEQ 0 (
    ECHO Python is not available. Please install Python or update your PATH.
    EXIT /B 1
)

ECHO Installing Playwright...
%PYTHON_PATH% -m pip install playwright

ECHO Installing Playwright browsers...
%PYTHON_PATH% -m playwright install

ECHO Playwright installation completed.
EXIT /B 0 