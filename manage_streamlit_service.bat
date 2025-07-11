@echo off
setlocal enabledelayedexpansion

echo Watchtower Streamlit Service Manager
echo ==================================
echo.

REM Check admin privileges
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo WARNING: Administrator privileges required for service operations
    echo.
)

:menu
echo Choose an option:
echo 1) Start service (admin)
echo 2) Stop service (admin)
echo 3) Restart service (admin)
echo 4) Check status
echo 5) Reinstall service (admin)
echo 6) Run directly
echo 7) Test runner
echo 8) View logs
echo 9) Exit
echo.

set /p choice=Enter choice (1-9): 

if "%choice%"=="1" (
    echo Starting service...
    powershell -Command "Start-Process cmd -ArgumentList '/c sc start WatchtowerStreamlit' -Verb RunAs"
    timeout /t 2 >nul
    goto :status
)
if "%choice%"=="2" (
    echo Stopping service...
    powershell -Command "Start-Process cmd -ArgumentList '/c sc stop WatchtowerStreamlit' -Verb RunAs"
    timeout /t 2 >nul
    goto :status
)
if "%choice%"=="3" (
    echo Restarting service...
    powershell -Command "Start-Process cmd -ArgumentList '/c sc stop WatchtowerStreamlit && timeout /t 2 && sc start WatchtowerStreamlit' -Verb RunAs"
    timeout /t 3 >nul
    goto :status
)
if "%choice%"=="4" goto :status
if "%choice%"=="5" (
    echo Reinstalling service...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %~dp0 && PowerShell -ExecutionPolicy Bypass -File setup_streamlit_service.ps1' -Verb RunAs"
    timeout /t 5 >nul
    goto :status
)
if "%choice%"=="6" (
    echo Running Streamlit directly...
    start cmd /k "%~dp0streamlit_service_runner.bat"
    echo App will be available at: http://localhost:8501
    echo.
    goto :menu
)
if "%choice%"=="7" (
    echo Testing runner...
    call "%~dp0streamlit_service_runner.bat"
    goto :menu
)
if "%choice%"=="8" (
    echo Checking logs...
    echo.
    echo === Service Log ===
    powershell -Command "if (Test-Path '%~dp0streamlit_service.log') { Get-Content '%~dp0streamlit_service.log' -Tail 10 } else { Write-Host 'Log not found' }"
    echo.
    echo === Error Log ===
    powershell -Command "if (Test-Path '%~dp0streamlit_service_error.log') { Get-Content '%~dp0streamlit_service_error.log' -Tail 10 } else { Write-Host 'Error log not found' }"
    echo.
    pause
    goto :menu
)
if "%choice%"=="9" exit /b 0

echo Invalid choice
echo.
goto :menu

:status
echo.
echo Service status:
sc query WatchtowerStreamlit
echo.
echo Logs: %~dp0streamlit_service.log
echo Errors: %~dp0streamlit_service_error.log
echo.
echo App: http://localhost:8501
echo.
goto :menu