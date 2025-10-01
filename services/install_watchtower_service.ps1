#Requires -Version 5.1
#Requires -RunAsAdministrator

param(
    [switch]$Uninstall
)

$ServiceName = "WatchtowerPlatform"
$ServiceDisplayName = "Watchtower Intelligence Platform"
$ScriptPath = $PSScriptRoot + "\..\src\launcher\main.py"
$PythonPath = (Get-Command python).Source
$UvPath = (Get-Command uv).Source

if ($Uninstall) {
    Write-Host "Uninstalling Watchtower service..." -ForegroundColor Yellow

    # Stop and remove service if it exists
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Stop-Service -Name $ServiceName -Force
        sc.exe delete $ServiceName
        Write-Host "Service uninstalled successfully." -ForegroundColor Green
    } else {
        Write-Host "Service not found." -ForegroundColor Yellow
    }
    exit
}

Write-Host "Installing Watchtower service..." -ForegroundColor Yellow

# Check if UV is available
if (-not $UvPath) {
    Write-Error "UV not found. Please install UV first."
    exit 1
}

# Create service using NSSM if available, otherwise use sc.exe
$nssmPath = "${env:ProgramFiles}\nssm\win64\nssm.exe"
if (Test-Path $nssmPath) {
    Write-Host "Using NSSM for service management..." -ForegroundColor Cyan

    & $nssmPath install $ServiceName $UvPath
    & $nssmPath set $ServiceName AppDirectory (Split-Path $ScriptPath -Parent)
    & $nssmPath set $ServiceName AppParameters "run python `"$ScriptPath`" --mode production"
    & $nssmPath set $ServiceName DisplayName $ServiceDisplayName
    & $nssmPath set $ServiceName Description "Watchtower Intelligence Platform - Real-time data collection and monitoring"
    & $nssmPath set $ServiceName Start SERVICE_AUTO_START
    & $nssmPath set $ServiceName AppEnvironmentExtra "WATCHTOWER_MODE=production,WATCHTOWER_ETL_INTERVAL=3600,WATCHTOWER_DASHBOARD_PORT=7777,WATCHTOWER_LOG_LEVEL=INFO"

    # Set failure actions
    & $nssmPath set $ServiceName AppRestartDelay 10000
    & $nssmPath set $ServiceName AppStopMethodSkip 0

    Write-Host "Service installed with NSSM." -ForegroundColor Green
} else {
    Write-Host "NSSM not found. Using sc.exe..." -ForegroundColor Cyan
    Write-Warning "For better service management, consider installing NSSM from https://nssm.cc/"

    # Create a wrapper script for sc.exe
    $wrapperScript = @"
@echo off
setlocal enabledelayedexpansion

set "UV_CMD=$UvPath"
set "SCRIPT_PATH=$ScriptPath"
set "PYTHON_CMD=$PythonPath"

cd /d "%~dp0"
%UV_CMD% run python "%SCRIPT_PATH%" --mode production

endlocal
"@

    $wrapperPath = "$PSScriptRoot\watchtower_service.bat"
    $wrapperScript | Out-File -FilePath $wrapperPath -Encoding ASCII

    # Create service with sc.exe
    sc.exe create $ServiceName binPath= "\"$wrapperPath\"" start= auto DisplayName= "$ServiceDisplayName"
    sc.exe description $ServiceName "Watchtower Intelligence Platform - Real-time data collection and monitoring"

    Write-Host "Service created with sc.exe." -ForegroundColor Green
    Write-Host "Wrapper script created at: $wrapperPath" -ForegroundColor Cyan
}

# Set service to restart on failure
sc.exe failure $ServiceName reset= 3600 actions= restart/60000/restart/60000/restart/60000

Write-Host "Service installation completed!" -ForegroundColor Green
Write-Host "You can start the service with: Start-Service -Name $ServiceName" -ForegroundColor Cyan
Write-Host "Or manage it with: Get-Service -Name $ServiceName" -ForegroundColor Cyan
