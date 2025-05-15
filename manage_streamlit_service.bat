@echo off
setlocal enabledelayedexpansion

echo Watchtower Streamlit Service Manager
echo ==================================
echo.

REM Check if running as administrator
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if %errorlevel% NEQ 0 (
    echo WARNING: You are NOT running as Administrator.
    echo Service management operations require administrator privileges.
    echo.
)

:menu
echo Choose an option:
echo 1) Start Streamlit service (requires admin)
echo 2) Stop Streamlit service (requires admin)
echo 3) Restart Streamlit service (requires admin)
echo 4) Check service status
echo 5) Reinstall service (requires admin)
echo 6) Run Streamlit directly (without service)
echo 7) Test service batch file
echo 8) Check service logs
echo 9) Exit
echo.

set /p choice=Enter your choice (1-9): 

if "%choice%"=="1" (
    echo Starting Streamlit service...
    powershell -Command "Start-Process cmd -ArgumentList '/c sc start WatchtowerStreamlit' -Verb RunAs"
    timeout /t 2 /nobreak >nul
    goto :status
)
if "%choice%"=="2" (
    echo Stopping Streamlit service...
    powershell -Command "Start-Process cmd -ArgumentList '/c sc stop WatchtowerStreamlit' -Verb RunAs"
    timeout /t 2 /nobreak >nul
    goto :status
)
if "%choice%"=="3" (
    echo Restarting Streamlit service...
    powershell -Command "Start-Process cmd -ArgumentList '/c sc stop WatchtowerStreamlit' -Verb RunAs"
    timeout /t 3 /nobreak >nul
    powershell -Command "Start-Process cmd -ArgumentList '/c sc start WatchtowerStreamlit' -Verb RunAs"
    timeout /t 2 /nobreak >nul
    goto :status
)
if "%choice%"=="4" (
    goto :status
)
if "%choice%"=="5" (
    echo Reinstalling service with proper configuration...
    echo This requires administrator privileges.
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %~dp0 && PowerShell -ExecutionPolicy Bypass -File setup_streamlit_service.ps1' -Verb RunAs"
    echo Service reinstallation initiated. Please wait...
    timeout /t 5 /nobreak >nul
    goto :status
)
if "%choice%"=="6" (
    echo Running Streamlit directly (not as service)...
    start cmd /k "%~dp0streamlit_service_runner.bat"
    echo Streamlit is starting in a new window.
    echo The app will be accessible at: http://localhost:8501
    echo.
    goto :menu
)
if "%choice%"=="7" (
    echo Testing service batch file...
    call "%~dp0streamlit_service_runner.bat"
    goto :menu
)
if "%choice%"=="8" (
    echo Checking service logs...
    echo.
    echo === Last 10 lines of service log ===
    powershell -Command "if (Test-Path '%~dp0streamlit_service.log') { Get-Content '%~dp0streamlit_service.log' -Tail 10 } else { Write-Host 'Log file not found.' }"
    echo.
    echo === Last 10 lines of error log ===
    powershell -Command "if (Test-Path '%~dp0streamlit_service_error.log') { Get-Content '%~dp0streamlit_service_error.log' -Tail 10 } else { Write-Host 'Error log file not found.' }"
    echo.
    pause
    goto :menu
)
if "%choice%"=="9" (
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
echo Service logs can be found at: %~dp0streamlit_service.log
echo Error logs can be found at: %~dp0streamlit_service_error.log
echo.
echo The Streamlit app is accessible at: http://localhost:8501
echo.
goto :menu 