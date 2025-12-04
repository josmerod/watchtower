#!/bin/bash
clear # Clear the console for a clean start
echo "========================================================"
echo "  🏯 Watchtower Dashboard - Main Launcher"
echo "  📡 Real-time Intelligence & Monitoring Platform"
echo "========================================================"
echo ""

# Change to the project root directory
cd "$(dirname "$0")" || exit

# Check if UV is available
if ! command -v uv &> /dev/null; then
    echo "[ERROR] UV not found. Please install UV first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    read -r -p "Press Enter to exit..." # Pause before exit, similar to .bat
    exit 1
fi

echo "[INFO] UV is available. Starting Watchtower Dashboard..."
echo ""
echo "Running: uv run python run_watchtower_dashboard.py"
echo "Dashboard will be available at: http://localhost:7777"
echo "========================================================"
echo ""

# Run the Watchtower Dashboard using UV (fallback to python3 if UV fails)
# Capture output to allow for inspection if UV fails.
if ! uv run python run_watchtower_dashboard.py; then
    echo "[WARN] UV command failed. Attempting fallback to direct python3 execution..."
    # Ensure python3 is available for fallback
    if ! command -v python3 &> /dev/null; then
        echo "[ERROR] python3 not found. Cannot run dashboard without UV or python3."
        EXIT_STATUS=1
    else
        echo "Running: python3 run_watchtower_dashboard.py"
        python3 run_watchtower_dashboard.py
        EXIT_STATUS=$?
    fi
else
    EXIT_STATUS=0
fi

echo "" # Add a newline for better readability before the final status message

if [ $EXIT_STATUS -ne 0 ]; then
    echo "[ERROR] Watchtower Dashboard failed to start or exited with an error. Please check the output above."
else
    echo "[SUCCESS] Watchtower Dashboard closed successfully."
fi

echo ""
read -r -p "Press Enter to continue..."
