@echo off
echo ========================================================
echo  Watchtower Service Installation (Administrator Required)
echo ========================================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Administrator privileges detected.
) else (
    echo ERROR: Administrator privileges required for service installation.
    echo Please run this script as Administrator or right-click and "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Installing Watchtower service...
echo.

REM Create service wrapper script
set "WRAPPER_SCRIPT=%~dp0watchtower_service.bat"
echo @echo off > "%WRAPPER_SCRIPT%"
echo setlocal enabledelayedexpansion >> "%WRAPPER_SCRIPT%"
echo. >> "%WRAPPER_SCRIPT%"
echo cd /d "%%~dp0" >> "%WRAPPER_SCRIPT%"
echo uv run python "%%~dp0..\src\launcher\main.py" --mode production >> "%WRAPPER_SCRIPT%"
echo. >> "%WRAPPER_SCRIPT%"
echo endlocal >> "%WRAPPER_SCRIPT%"

REM Create the service
sc create WatchtowerPlatform binPath= "\"%WRAPPER_SCRIPT%\"" start= auto DisplayName= "Watchtower Intelligence Platform"

if %errorLevel% == 0 (
    echo.
    echo SUCCESS: Watchtower service installed successfully!
    echo.
    echo Service name: WatchtowerPlatform
    echo.
    echo You can now start the service with:
    echo   net start WatchtowerPlatform
    echo.
    echo Or manage it with:
    echo   sc query WatchtowerPlatform
    echo   sc stop WatchtowerPlatform
    echo.
    echo To uninstall:
    echo   sc delete WatchtowerPlatform
    echo.
) else (
    echo.
    echo ERROR: Failed to install service. Error code: %errorLevel%
    echo.
)

echo Setting service restart policy...
sc failure WatchtowerPlatform reset= 3600 actions= restart/60000/restart/60000/restart/60000

echo.
echo Installation completed.
pause
