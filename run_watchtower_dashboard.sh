#!/bin/bash
echo "========================================================"
echo "  🏯 Watchtower Dashboard - Main Launcher"
echo "  📡 Real-time Intelligence & Monitoring Platform"
echo "========================================================"
echo ""

# Change to the project root directory
cd "$(dirname "$0")"

# Check if UV is available
if ! command -v uv &> /dev/null; then
    echo "[ERROR] UV not found. Please install UV first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    exit 1
fi

echo "[INFO] UV is available. Starting Watchtower Dashboard..."
echo ""
echo "Running: uv run python run_watchtower_dashboard.py"
echo "Dashboard will be available at: http://localhost:7777"
echo "========================================================"
echo ""

# Run the Watchtower Dashboard using UV
uv run python run_watchtower_dashboard.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Watchtower Dashboard failed to start. Please check the output above."
else
    echo ""
    echo "[SUCCESS] Watchtower Dashboard closed successfully."
fi

echo ""
read -p "Press Enter to continue..." dummy 