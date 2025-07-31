# Environment Setup Guide

This guide explains the unified environment management for Watchtower automation scripts.

## Quick Start

1. **First Time Setup (Required)**:
   ```bash
   # Windows
   .\setup_environment.bat
   
   # Linux/Mac
   ./setup_environment.sh
   ```

2. **Run Automation Scripts** (after setup):
   ```bash
   # Windows
   .\run_all_etl.bat         # ETL processes
   .\run_streamlit_app.bat   # Dashboard
   
   # Linux/Mac
   ./run_all_etl.sh          # ETL processes
   ./run_streamlit_app.sh    # Dashboard
   ```

## What Changed

### Before (The Problem)
- Both `run_all_etl.bat` and `run_streamlit_app.bat` were **destroying and rebuilding** the virtual environment **every single time**
- This caused daily failures, environment corruption, and extremely slow startup times
- Aggressive cleanup processes with multiple fallback methods that often failed
- Dependencies weren't properly installed, leading to `ModuleNotFoundError`s

### After (The Solution)
- **One-time setup**: `setup_environment.bat/sh` creates the environment **once** with proper dependency installation
- **Fast automation**: ETL and dashboard scripts simply check that the environment exists and run
- **Reliable operation**: No more daily environment corruption issues
- **Proper dependency management**: All required modules (requests, feedparser, pandas, playwright, etc.) are installed correctly
- **Missing file handling**: ETL script only runs files that actually exist

## Environment Setup Script

The `setup_environment` script:
- Installs UV package manager if needed
- Creates a fresh virtual environment using UV
- Installs all project dependencies
- Verifies everything works
- **Only needs to be run once** or when dependencies change

## Automation Scripts

The simplified automation scripts:
- Check if the virtual environment exists
- Verify it's working properly
- Run the actual processes
- **No environment management** - just execution

## When to Re-run Setup

You only need to run the setup script again if:
- Dependencies in `pyproject.toml` have changed
- The virtual environment becomes corrupted
- You want to upgrade to a newer Python version
- You're setting up on a new machine

## Troubleshooting

If automation scripts fail:
1. Run the setup script: `.\setup_environment.bat` (Windows) or `./setup_environment.sh` (Linux/Mac)
2. Try the automation script again
3. If still failing, delete the `.venv` folder and run setup again

## Benefits

- **No more daily debugging**: Environment is stable once set up
- **Faster execution**: Scripts start in seconds instead of minutes
- **Reliable automation**: No more environment-related failures
- **Simple maintenance**: Clear separation between setup and execution