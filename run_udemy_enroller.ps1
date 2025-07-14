# Enhanced Udemy Course Enroller - Windows Task Scheduler PowerShell Script
# This script runs the unified CLI for automated course enrollment
# Created: $(Get-Date)

param(
    [string]$ConfigFile = "default-duce-cli-settings.json",
    [switch]$Verbose,
    [switch]$DryRun
)

# Enable strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $ScriptDir "logs"
$ConfigDir = Join-Path $ScriptDir "src\miners\udemy-universal"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = Join-Path $LogDir "udemy_enroller_$Timestamp.log"

# Function to write timestamped log messages
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $LogEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry -ErrorAction SilentlyContinue
}

# Function to clean up old log files
function Cleanup-LogFiles {
    param([int]$DaysToKeep = 30)
    
    try {
        $CutoffDate = (Get-Date).AddDays(-$DaysToKeep)
        Get-ChildItem -Path $LogDir -Filter "udemy_enroller_*.log" | 
            Where-Object { $_.CreationTime -lt $CutoffDate } | 
            Remove-Item -Force
        Write-Log "Cleaned up log files older than $DaysToKeep days"
    } catch {
        Write-Log "Warning: Could not clean up old log files: $($_.Exception.Message)" "WARN"
    }
}

# Function to check UV availability
function Test-UVAvailability {
    try {
        $UVVersion = & uv --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "UV package manager found: $UVVersion"
            return $true
        } else {
            Write-Log "UV command failed with exit code: $LASTEXITCODE" "ERROR"
            return $false
        }
    } catch {
        Write-Log "UV package manager not found: $($_.Exception.Message)" "ERROR"
        Write-Log "Please install UV first: https://docs.astral.sh/uv/" "ERROR"
        Write-Log "Installation command: irm https://astral.sh/uv/install.ps1 | iex" "ERROR"
        return $false
    }
}

# Function to run the enrollment process
function Start-EnrollmentProcess {
    param(
        [string]$ConfigFilePath,
        [switch]$DryRun
    )
    
    $Arguments = @(
        "run",
        "src/miners/udemy-universal/unified_cli.py",
        "run",
        "--automated",
        "--config-file", $ConfigFilePath
    )
    
    if ($DryRun) {
        $Arguments += "--dry-run"
    }
    
    if ($Verbose) {
        $Arguments += "--verbose"
    }
    
    Write-Log "Starting course enrollment with command: uv $($Arguments -join ' ')"
    
    try {
        # Redirect both stdout and stderr to log file
        $Process = Start-Process -FilePath "uv" -ArgumentList $Arguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $LogFile -RedirectStandardError $LogFile
        
        return $Process.ExitCode
    } catch {
        Write-Log "Failed to start enrollment process: $($_.Exception.Message)" "ERROR"
        return 1
    }
}

# Main execution
try {
    Write-Log "========================================"
    Write-Log "Watchtower Udemy Course Enroller"
    Write-Log "Started: $(Get-Date)"
    Write-Log "========================================"
    
    # Set working directory
    Set-Location $ScriptDir
    Write-Log "Working directory: $(Get-Location)"
    
    # Set environment variables
    $env:PYTHONPATH = Join-Path $ScriptDir "src"
    $env:UDEMY_LOG_DIR = $LogDir
    $env:UDEMY_CONFIG_DIR = $ConfigDir
    
    # Create logs directory
    if (-not (Test-Path $LogDir)) {
        New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
        Write-Log "Created logs directory: $LogDir"
    }
    
    # Initialize log file
    Write-Log "Log file: $LogFile"
    
    # Check UV availability
    if (-not (Test-UVAvailability)) {
        throw "UV package manager is not available"
    }
    
    # Build config file path
    $ConfigPath = Join-Path $ConfigDir $ConfigFile
    if (-not (Test-Path $ConfigPath)) {
        throw "Configuration file not found: $ConfigPath"
    }
    
    Write-Log "Using configuration file: $ConfigPath"
    
    # Run enrollment process
    $ExitCode = Start-EnrollmentProcess -ConfigFilePath $ConfigPath -DryRun:$DryRun
    
    # Process results
    if ($ExitCode -eq 0) {
        Write-Log "========================================"
        Write-Log "SUCCESS: Course enrollment completed successfully!"
        Write-Log "Exit code: $ExitCode"
        Write-Log "Completed: $(Get-Date)"
        Write-Log "========================================"
        
        # Display log summary
        Write-Log ""
        Write-Log "Last 10 lines of enrollment log:"
        Write-Log "----------------------------------------"
        if (Test-Path $LogFile) {
            Get-Content $LogFile | Select-Object -Last 10 | ForEach-Object { Write-Log $_ }
        }
        Write-Log "----------------------------------------"
        
    } else {
        Write-Log "========================================"
        Write-Log "ERROR: Course enrollment failed!"
        Write-Log "Exit code: $ExitCode"
        Write-Log "Failed: $(Get-Date)"
        Write-Log "========================================"
        
        # Display error log
        Write-Log ""
        Write-Log "Last 20 lines of enrollment log for error diagnosis:"
        Write-Log "----------------------------------------"
        if (Test-Path $LogFile) {
            Get-Content $LogFile | Select-Object -Last 20 | ForEach-Object { Write-Log $_ }
        }
        Write-Log "----------------------------------------"
    }
    
    # Clean up old logs
    Cleanup-LogFiles -DaysToKeep 30
    
    Write-Log "Process completed with exit code: $ExitCode"
    Write-Log "End time: $(Get-Date)"
    
    exit $ExitCode
    
} catch {
    Write-Log "FATAL ERROR: $($_.Exception.Message)" "ERROR"
    Write-Log "Stack trace: $($_.Exception.StackTrace)" "ERROR"
    Write-Log "Script failed at: $(Get-Date)" "ERROR"
    
    # Clean up old logs even on error
    Cleanup-LogFiles -DaysToKeep 30
    
    exit 1
} 