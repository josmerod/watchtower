# Check for administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "You need to run this script as an Administrator."
    Write-Host "Press Enter to continue anyway, or Ctrl+C to cancel..."
    Read-Host
}

# Check if NSSM is installed, if not download and extract it
$nssmPath = "C:\nssm\nssm.exe"
$nssmDir = "C:\nssm"

if (-not (Test-Path $nssmPath)) {
    Write-Host "NSSM not found. Downloading and installing..."
    
    # Create directory for NSSM
    New-Item -ItemType Directory -Path $nssmDir -Force | Out-Null
    
    # Download NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $zipPath = "$env:TEMP\nssm.zip"
    
    Invoke-WebRequest -Uri $nssmUrl -OutFile $zipPath
    
    # Extract NSSM
    Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
    
    # Copy the appropriate executable to the NSSM directory
    if ([Environment]::Is64BitOperatingSystem) {
        Copy-Item "$env:TEMP\nssm-2.24\win64\nssm.exe" -Destination $nssmPath
    } else {
        Copy-Item "$env:TEMP\nssm-2.24\win32\nssm.exe" -Destination $nssmPath
    }
    
    # Clean up
    Remove-Item $zipPath
    Remove-Item "$env:TEMP\nssm-2.24" -Recurse
    
    Write-Host "NSSM installed successfully."
}

# Get the current directory of the script
$scriptDir = $PSScriptRoot
$fullstreamlitDir = Join-Path $scriptDir "src\web\fullstreamlit"

# Create a direct batch file for the service that uses absolute paths
$serviceBatchPath = Join-Path $scriptDir "streamlit_service_runner.bat"
$batchContent = @"
@echo off
cd /d "$scriptDir"

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Change to the Streamlit app directory
cd /d "$fullstreamlitDir"

REM Set environment variables
set PYTHONPATH=$scriptDir
set DATA_DIR=$scriptDir\data
echo Starting Streamlit app at %date% %time% from %CD%
echo Using Python: %VIRTUAL_ENV%

python -m streamlit run app.py --server.port=8501 --browser.serverAddress=localhost
"@
Set-Content -Path $serviceBatchPath -Value $batchContent

# Install Streamlit as a service using NSSM
$serviceName = "WatchtowerStreamlit"

# Check if service already exists
$serviceExists = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if ($serviceExists) {
    Write-Host "Service '$serviceName' already exists. Removing it first..."
    Start-Process -FilePath $nssmPath -ArgumentList "remove $serviceName confirm" -NoNewWindow -Wait
}

# Install the service
Write-Host "Installing Streamlit as a Windows service..."
Start-Process -FilePath $nssmPath -ArgumentList "install $serviceName `"$serviceBatchPath`"" -NoNewWindow -Wait

# Configure service properties
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName DisplayName `"Watchtower Streamlit App`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName Description `"Runs the Watchtower Streamlit dashboard continuously`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName Start SERVICE_AUTO_START" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppStdout `"$scriptDir\streamlit_service.log`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppStderr `"$scriptDir\streamlit_service_error.log`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppDirectory `"$scriptDir`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppNoConsole 1" -NoNewWindow -Wait

# Set dependencies - make sure network is available
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName DependOnService Tcpip" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName DependOnService Dnscache" -NoNewWindow -Wait

# Set environment variables directly in NSSM
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppEnvironmentExtra PATH=$env:PATH" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppEnvironmentExtra PYTHONPATH=$scriptDir" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppEnvironmentExtra DATA_DIR=$scriptDir\data" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppEnvironmentExtra VIRTUAL_ENV=$scriptDir\.venv" -NoNewWindow -Wait

# Set a delayed start to ensure all systems are ready
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName Start SERVICE_DELAYED_AUTO_START" -NoNewWindow -Wait

# Start the service
Start-Process -FilePath $nssmPath -ArgumentList "start $serviceName" -NoNewWindow -Wait

Write-Host "Streamlit service '$serviceName' installed and started successfully."
Write-Host "Your Streamlit app is now running as a Windows service and will start automatically when Windows boots."
Write-Host "You can access it at: http://localhost:8501" 