@echo off
setlocal enabledelayedexpansion

echo Watchtower Streamlit Service Manager
echo ==================================
echo.

:menu
echo Choose an option:
echo 1) Start Streamlit service
echo 2) Stop Streamlit service
echo 3) Restart Streamlit service
echo 4) Check service status
echo 5) Exit
echo.

set /p choice=Enter your choice (1-5): 

if "%choice%"=="1" (
    echo Starting Streamlit service...
    sc start WatchtowerStreamlit
    goto :status
)
if "%choice%"=="2" (
    echo Stopping Streamlit service...
    sc stop WatchtowerStreamlit
    goto :status
)
if "%choice%"=="3" (
    echo Restarting Streamlit service...
    sc stop WatchtowerStreamlit
    timeout /t 3 /nobreak >nul
    sc start WatchtowerStreamlit
    goto :status
)
if "%choice%"=="4" (
    goto :status
)
if "%choice%"=="5" (
    exit /b 0
)

echo Invalid choice. Please try again.
echo.
goto :menu

:status
echo.
echo Current service status:
sc query WatchtowerStreamlit
echo.
echo The Streamlit app is accessible at: http://localhost:8501
echo.
goto :menu 