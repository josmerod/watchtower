#!/bin/bash

echo ""
echo "=========================================="
echo "  Watchtower Dashboard"
echo "=========================================="
echo ""

# Change to the project root directory
cd "$(dirname "$0")"

# Verify we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Please run from project root."
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check if environment is set up
if [ ! -d ".venv" ]; then
    echo ""
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./setup_environment.sh first to set up the environment."
    echo ""
    exit 1
fi

# Verify UV and virtual environment are working
echo "Checking environment..."
if ! uv run python --version &> /dev/null; then
    echo ""
    echo "ERROR: Environment is not working properly!"
    echo "Please run ./setup_environment.sh to fix the environment."
    echo ""
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo "Starting Watchtower Dashboard..."
echo ""
echo "Dashboard will be available at: http://localhost:7777"
echo "Press Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

# Run the dashboard with proper error handling
if uv run python run_watchtower_dashboard.py; then
    RUN_RESULT=0
else
    RUN_RESULT=$?
fi

echo ""
echo "=========================================="
if [ $RUN_RESULT -eq 0 ]; then
    echo "Dashboard stopped normally"
else
    echo "Dashboard stopped with error code: $RUN_RESULT"
    echo ""
    echo "If you see 'pyvenv.cfg' errors, try:"
    echo "1. Delete .venv folder manually: rm -rf .venv"
    echo "2. Run this script again"
    echo "3. Or run: uv cache clean"
fi
echo "=========================================="
echo "" 