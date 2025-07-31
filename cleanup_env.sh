#!/bin/bash

echo ""
echo "=========================================="
echo " Watchtower Environment Cleanup"
echo "=========================================="
echo ""
echo "This script will completely reset your UV environment"
echo "and cache to fix persistent issues."
echo ""

read -p "Press Enter to continue..."

# Change to the project root directory
cd "$(dirname "$0")"

echo "Cleaning up UV environment..."
echo ""

# 1. Remove virtual environment
if [ -d ".venv" ]; then
    echo "Removing .venv directory..."
    rm -rf .venv 2>/dev/null || {
        echo "Using sudo to force remove .venv..."
        sudo rm -rf .venv 2>/dev/null || true
    }
    
    # Double check
    if [ -d ".venv" ]; then
        echo "Warning: .venv still exists. You may need to remove it manually."
    else
        echo ".venv removed successfully."
    fi
fi

# 2. Clear UV cache
echo ""
echo "Clearing UV cache..."
if uv cache clean >/dev/null 2>&1; then
    echo "UV cache cleared successfully."
else
    echo "UV cache clear failed or UV not installed."
fi

# 3. Clear temporary directories
echo ""
echo "Clearing temporary directories..."
if [ -d "${TMPDIR:-/tmp}/uv-cache" ]; then
    rm -rf "${TMPDIR:-/tmp}/uv-cache" 2>/dev/null
    echo "Temp UV cache cleared."
fi

# 4. Remove Python cache files
echo ""
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "Python cache files removed."

# 5. Reset UV configuration
echo ""
echo "Resetting UV configuration..."
export UV_LINK_MODE=copy
export UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache"
export UV_PYTHON_PREFERENCE=only-managed

echo ""
echo "=========================================="
echo "Cleanup completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run ./run_streamlit_app.sh to start fresh"
echo "2. Or run: uv sync --all-extras"
echo "3. Then run: uv run python run_watchtower_dashboard.py"
echo "" 