@echo off
setlocal EnableDelayedExpansion

echo ========================================================
echo Watchtower Streamlit Application Launcher
echo ========================================================

:: Change to the project directory
cd /d %~dp0
echo Working directory: %CD%


echo.
echo Step 1: Checking virtual environment...
if not exist .venv (
    echo Virtual environment not found. Creating new environment...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo Error creating virtual environment.
        goto error
    )
)

call .venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo Error activating virtual environment.
    goto error
)
echo Virtual environment activated successfully.

echo.
echo Step 2: Running Streamlit application...
echo.
echo You can access the application at http://localhost:5555
echo.
echo Press Ctrl+C to stop the application
echo ========================================================
echo.

python -m streamlit run src/web/fullstreamlit/app.py --server.port 5555
if !errorlevel! neq 0 (
    echo Error running Streamlit application.
    goto error
)

goto end

:error
echo.
echo ========================================================
echo An error occurred. Please check the following:
echo 1. Python 3.10+ is installed and accessible
echo 2. Virtual environment can be created/activated
echo 3. Required packages can be installed
echo 4. Streamlit app file exists at src/web/fullstreamlit/app.py
echo ========================================================
pause
exit /b 1

:end
echo Application closed successfully.
pause