#!/usr/bin/env powershell
<#
.SYNOPSIS
    Launch Watchtower Dashboard with UV
.DESCRIPTION
    PowerShell script to launch the Watchtower Dashboard with proper environment setup
#>

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " 🏯 Watchtower Dashboard with UV" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if UV is available
try {
    $uvVersion = uv --version
    Write-Host "✅ UV found: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ UV not found. Please install UV first:" -ForegroundColor Red
    Write-Host "   iex (irm https://astral.sh/uv/install.ps1)" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if pyproject.toml exists
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "❌ Error: pyproject.toml not found. Please run from project root." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Clean up incompatible virtual environment if it exists
if (Test-Path ".venv") {
    Write-Host "🧹 Removing incompatible virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".venv"
}

# Set UV environment variables
$env:UV_LINK_MODE = "copy"

# Create Windows-compatible virtual environment
Write-Host "⚙️  Setting up Windows virtual environment..." -ForegroundColor Blue
try {
    uv sync --all-extras
    Write-Host "✅ Virtual environment created successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create virtual environment. Please check UV installation." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "🚀 Starting Watchtower Dashboard..." -ForegroundColor Blue
Write-Host "📡 Dashboard will be available at: http://localhost:7777" -ForegroundColor Cyan
Write-Host "⏹️  Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Run the dashboard
try {
    uv run python run_watchtower_dashboard.py
} catch {
    Write-Host ""
    Write-Host "❌ Dashboard failed to start. Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "Dashboard stopped" -ForegroundColor Yellow
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
