#!/bin/bash

echo ""
echo "=========================================="
echo "  Watchtower Environment Setup"
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

# Check if UV is available
echo "Checking UV installation..."
if ! command -v uv &> /dev/null; then
    echo ""
    echo "ERROR: UV not found. Installing UV..."
    echo ""
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the shell profile to get UV in PATH
    if [ -f "$HOME/.bashrc" ]; then
        source "$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        source "$HOME/.zshrc"
    fi
    
    # Check if UV is now available
    if ! command -v uv &> /dev/null; then
        echo ""
        echo "UV installation failed. Please install UV manually:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        exit 1
    fi
fi

echo "UV version:"
uv --version

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo "Setting up Python environment..."
echo ""

# Check if virtual environment already exists and is working
if [ -d ".venv" ]; then
    echo "Checking existing virtual environment..."
    if uv run python --version &> /dev/null; then
        echo "Virtual environment exists and is working!"
        echo ""
        echo "Checking if dependencies are up to date..."
        if uv sync --check &> /dev/null; then
            echo "Dependencies are up to date. Environment ready!"
            echo ""
            echo "Environment setup completed successfully!"
            echo "You can now run:"
            echo "  ./run_all_etl.sh"
            echo "  ./run_streamlit_app.sh"
            echo ""
            exit 0
        else
            echo "Dependencies need updating..."
        fi
    else
        echo "Virtual environment is corrupted, recreating..."
    fi
fi

# Kill any processes that might be using the venv
echo "Terminating any Python processes..."
pkill -f python &> /dev/null || true

# Wait for processes to terminate
sleep 2

# Remove existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf .venv
    echo ".venv removed successfully!"
fi

# Clear UV cache
echo "Clearing UV cache..."
uv cache clean &> /dev/null || true

# Set UV environment variables for compatibility
export UV_LINK_MODE=copy
export UV_PYTHON_PREFERENCE=only-managed

echo ""
echo "Creating fresh virtual environment..."
echo ""

# Install Python 3.11 if needed
echo "Installing Python 3.11..."
uv python install 3.11 &> /dev/null

# Create new virtual environment
echo "Creating new virtual environment..."
if ! uv venv --seed &> /dev/null; then
    echo "Trying alternative venv creation..."
    if ! uv venv --python 3.11 --seed &> /dev/null; then
        echo "ERROR: Failed to create virtual environment."
        echo ""
        echo "Manual steps:"
        echo "1. Check if you have sufficient permissions"
        echo "2. Try: uv venv --python 3.11"
        echo ""
        exit 1
    fi
fi

# Install dependencies with retry logic
echo "Installing dependencies..."
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Attempt $RETRY_COUNT of $MAX_RETRIES"
    
    if uv sync --all-extras --reinstall; then
        break
    else
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Sync failed, retrying in 3 seconds..."
            sleep 3
            uv cache clean &> /dev/null || true
        else
            echo ""
            echo "ERROR: Failed to sync dependencies after $MAX_RETRIES attempts."
            echo ""
            echo "Troubleshooting steps:"
            echo "1. Check internet connection"
            echo "2. Run: uv cache clean"
            echo "3. Check pyproject.toml for syntax errors"
            echo ""
            exit 1
        fi
    fi
done

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
if ! uv run playwright install &> /dev/null; then
    echo "Warning: Playwright browser installation failed. Web scraping may not work properly."
fi

# Verify the virtual environment is working
echo ""
echo "Verifying Python environment..."
if ! uv run python --version; then
    echo ""
    echo "ERROR: Python environment verification failed."
    echo "Please run this script again."
    exit 1
fi

# Test core dependencies
echo "Testing core dependencies..."
if ! uv run python -c "import requests; import feedparser; import pandas; import playwright; print('All core dependencies available!')"; then
    echo ""
    echo "ERROR: Core dependencies are not working properly."
    echo "Please run this script again."
    exit 1
fi

echo ""
echo "=========================================="
echo "Environment setup completed successfully!"
echo "=========================================="
echo ""
echo "You can now run your automation scripts:"
echo "  ./run_all_etl.sh         - Run ETL processes"
echo "  ./run_streamlit_app.sh   - Run dashboard"
echo ""
echo "This setup script only needs to be run once or when"
echo "dependencies change. The automation scripts will now"
echo "be much faster and more reliable."
echo ""