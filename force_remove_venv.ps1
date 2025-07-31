# Force Remove .venv Directory - PowerShell Script
# This script aggressively removes the .venv directory using multiple methods

param(
    [string]$VenvPath = ".venv"
)

Write-Host "=========================================="
Write-Host " Force Remove .venv Directory"
Write-Host "=========================================="
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if .venv exists
if (-not (Test-Path $VenvPath)) {
    Write-Host ".venv directory not found. Nothing to remove."
    exit 0
}

Write-Host "Found .venv directory. Starting aggressive removal..."
Write-Host ""

# Method 1: Terminate Python processes
Write-Host "Step 1: Terminating Python processes..."
try {
    Get-Process | Where-Object { $_.ProcessName -match "python" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "Python processes terminated."
} catch {
    Write-Host "No Python processes found or failed to terminate."
}

# Method 2: Remove read-only attributes
Write-Host "Step 2: Removing read-only attributes..."
try {
    Get-ChildItem -Path $VenvPath -Recurse -Force | ForEach-Object {
        $_.IsReadOnly = $false
        $_.Attributes = $_.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
    }
    Write-Host "Read-only attributes removed."
} catch {
    Write-Host "Warning: Could not remove all read-only attributes."
}

# Method 3: Force unlock files using Handle.exe (if available)
Write-Host "Step 3: Attempting to unlock files..."
try {
    if (Get-Command handle.exe -ErrorAction SilentlyContinue) {
        $handles = & handle.exe -p python.exe -nobanner 2>$null
        if ($handles) {
            Write-Host "Found locked handles, attempting to close..."
            # This is informational - handle.exe would need additional parameters to close
        }
    }
} catch {
    Write-Host "Handle.exe not available or failed."
}

# Method 4: Take ownership of files
Write-Host "Step 4: Taking ownership of files..."
try {
    & takeown.exe /f $VenvPath /r /d Y 2>$null | Out-Null
    & icacls.exe $VenvPath /grant Administrators:F /t 2>$null | Out-Null
    Write-Host "Ownership taken and permissions granted."
} catch {
    Write-Host "Warning: Could not take ownership of all files."
}

# Method 5: Force remove using PowerShell
Write-Host "Step 5: Force removing with PowerShell..."
try {
    Remove-Item -Path $VenvPath -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $VenvPath) {
        Write-Host "PowerShell removal incomplete, trying alternative method..."
        
        # Alternative method: Remove files individually
        Get-ChildItem -Path $VenvPath -Recurse -Force | ForEach-Object {
            try {
                Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Host "Could not remove: $($_.FullName)"
            }
        }
        
        # Try to remove directories
        Get-ChildItem -Path $VenvPath -Recurse -Directory -Force | Sort-Object FullName -Descending | ForEach-Object {
            try {
                Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Host "Could not remove directory: $($_.FullName)"
            }
        }
        
        # Finally try to remove the root directory
        Remove-Item -Path $VenvPath -Force -ErrorAction SilentlyContinue
    }
} catch {
    Write-Host "PowerShell removal failed."
}

# Method 6: Use robocopy to delete (Windows-specific trick)
Write-Host "Step 6: Using robocopy deletion method..."
try {
    $emptyDir = "$env:TEMP\empty_dir_$([System.Guid]::NewGuid().ToString())"
    New-Item -ItemType Directory -Path $emptyDir -Force | Out-Null
    
    & robocopy.exe $emptyDir $VenvPath /mir /nfl /ndl /njh /njs /np /ns /nc 2>$null | Out-Null
    Remove-Item -Path $emptyDir -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $VenvPath -Force -ErrorAction SilentlyContinue
    
    Write-Host "Robocopy deletion method applied."
} catch {
    Write-Host "Robocopy method failed."
}

# Method 7: Rename and remove (if still exists)
if (Test-Path $VenvPath) {
    Write-Host "Step 7: Rename and remove method..."
    try {
        $newName = ".venv_old_$(Get-Random)"
        Rename-Item -Path $VenvPath -NewName $newName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        Remove-Item -Path $newName -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Rename and remove method applied."
    } catch {
        Write-Host "Rename and remove method failed."
    }
}

# Final check
Write-Host ""
Write-Host "=========================================="
if (Test-Path $VenvPath) {
    Write-Host "ERROR: .venv directory still exists!"
    Write-Host "Manual intervention required:"
    Write-Host "1. Restart your computer"
    Write-Host "2. Run as Administrator"
    Write-Host "3. Use Process Monitor to find what's locking the files"
    Write-Host "4. Try running: Remove-Item .venv -Recurse -Force"
    Write-Host "=========================================="
    exit 1
} else {
    Write-Host "SUCCESS: .venv directory removed successfully!"
    Write-Host "You can now run the dashboard script again."
    Write-Host "=========================================="
    exit 0
} 