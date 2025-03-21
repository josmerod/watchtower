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
$batchFilePath = Join-Path $scriptDir "run_streamlit.bat"

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
Start-Process -FilePath $nssmPath -ArgumentList "install $serviceName `"$batchFilePath`"" -NoNewWindow -Wait

# Configure service properties
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName DisplayName `"Watchtower Streamlit App`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName Description `"Runs the Watchtower Streamlit dashboard continuously`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName Start SERVICE_AUTO_START" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppStdout `"$scriptDir\streamlit_service.log`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppStderr `"$scriptDir\streamlit_service_error.log`"" -NoNewWindow -Wait
Start-Process -FilePath $nssmPath -ArgumentList "set $serviceName AppDirectory `"$scriptDir`"" -NoNewWindow -Wait

# Start the service
Start-Process -FilePath $nssmPath -ArgumentList "start $serviceName" -NoNewWindow -Wait

Write-Host "Streamlit service '$serviceName' installed and started successfully."
Write-Host "Your Streamlit app is now running as a Windows service and will start automatically when Windows boots."
Write-Host "You can access it at: http://localhost:8501" 