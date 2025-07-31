@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo  Watchtower Environment Cleanup
echo ==========================================
echo.
echo This script will completely reset your UV environment
echo and cache to fix persistent issues.
echo.

pause

REM Change to the project root directory
cd /d "%~dp0"

echo Cleaning up UV environment...
echo.

REM 1. Use PowerShell script for aggressive .venv removal
if exist ".venv" (
    echo Running PowerShell script for aggressive .venv removal...
    powershell -ExecutionPolicy Bypass -File "force_remove_venv.ps1"
    
    if exist ".venv" (
        echo PowerShell script could not remove .venv completely.
        echo Trying manual methods...
        
        REM Fallback methods
        echo Terminating Python processes...
        taskkill /f /im python.exe >nul 2>nul
        taskkill /f /im python3.exe >nul 2>nul
        taskkill /f /im pythonw.exe >nul 2>nul
        
        timeout /t 3 /nobreak >nul
        
        echo Taking ownership and removing...
        takeown /f ".venv" /r /d y >nul 2>nul
        icacls ".venv" /grant administrators:F /t >nul 2>nul
        rmdir /s /q ".venv" >nul 2>nul
        
        if exist ".venv" (
            echo Renaming and removing...
            ren ".venv" ".venv_old_%RANDOM%" >nul 2>nul
            for /d %%i in (.venv_old_*) do (
                rmdir /s /q "%%i" >nul 2>nul
            )
        )
        
        if exist ".venv" (
            echo.
            echo ERROR: .venv directory still exists!
            echo Please restart your computer and run this script again.
            echo Or try running as administrator.
            echo.
        ) else (
            echo .venv removed successfully!
        )
    ) else (
        echo .venv removed successfully!
    )
) else (
    echo .venv directory not found.
)

REM 2. Clear UV cache
echo.
echo Clearing UV cache...
uv cache clean >nul 2>nul
if %errorlevel% equ 0 (
    echo UV cache cleared successfully.
) else (
    echo UV cache clear failed or UV not installed.
)

REM 3. Clear temporary directories
echo.
echo Clearing temporary directories...
if exist "%TEMP%\uv-cache*" (
    for /d %%i in ("%TEMP%\uv-cache*") do (
        rmdir /s /q "%%i" >nul 2>nul
    )
    echo Temp UV cache cleared.
)

if exist "%LOCALAPPDATA%\uv" (
    rmdir /s /q "%LOCALAPPDATA%\uv\cache" >nul 2>nul
    echo Local UV cache cleared.
)

REM 4. Remove Python cache files
echo.
echo Removing Python cache files...
for /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d" >nul 2>nul
    )
)

for /r . %%f in (*.pyc) do (
    if exist "%%f" (
        del "%%f" >nul 2>nul
    )
)

echo Python cache files removed.

REM 5. Reset UV configuration
echo.
echo Resetting UV configuration...
set UV_LINK_MODE=copy
set UV_CACHE_DIR=%TEMP%\uv-cache-%RANDOM%
set UV_PYTHON_PREFERENCE=only-managed
set UV_TOOL_DIR=%TEMP%\uv-tools-%RANDOM%

REM 6. Clear any old renamed directories
echo.
echo Cleaning up old renamed directories...
for /d %%i in (.venv_old_*) do (
    echo Removing old directory: %%i
    rmdir /s /q "%%i" >nul 2>nul
)

echo.
echo ==========================================
echo Cleanup completed!
echo ==========================================
echo.
echo Next steps:
echo 1. Run run_streamlit_app.bat to start fresh
echo 2. If still having issues, restart your computer
echo 3. Try running as administrator
echo 4. Or manually run: uv sync --all-extras
echo.

pause 