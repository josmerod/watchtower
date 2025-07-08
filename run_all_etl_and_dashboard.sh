#!/bin/bash
echo "========================================================"
echo "  🏯 Watchtower Complete System Launcher"
echo "  📡 ETL Processes + Dashboard"
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

echo "[INFO] Starting ETL processes first..."
echo ""

# Create required directories
mkdir -p data
mkdir -p logs

echo "[INFO] Running ETL processes..."
bash run_all_etl.sh

echo ""
echo "[INFO] Waiting 5 seconds for ETL processes to initialize..."
sleep 5

echo ""
echo "[INFO] Starting Watchtower Dashboard..."
echo "Dashboard will be available at: http://localhost:7777"
echo "========================================================"
echo ""

# Run the Watchtower Dashboard
uv run python run_watchtower_dashboard.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Watchtower Dashboard failed to start. Please check the output above."
else
    echo ""
    echo "[SUCCESS] Watchtower system closed successfully."
fi

echo ""
read -p "Press Enter to continue..." dummy 