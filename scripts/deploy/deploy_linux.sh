#!/bin/bash
set -e  # Exit on any error

echo "========================================================"
echo "  🏯 Watchtower Dashboard - Linux Deployment Script"
echo "  📡 Real-time Intelligence & Monitoring Platform"
echo "========================================================"
echo ""

# Set timeout for commands to avoid hanging (30 seconds)
TIMEOUT_SECONDS=30

echo "[INFO] Starting Watchtower deployment on Linux..."
echo "[INFO] Timeout set to $TIMEOUT_SECONDS seconds for each operation"
echo ""

# Change to the project root directory
cd "$(dirname "$0")" || exit

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "[ERROR] pyproject.toml not found. Please run this script from the project root."
    echo "[ERROR] Current directory: $(pwd)"
    exit 1
fi

echo "[STEP 1/6] Checking Python version..."
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ERROR] Python not found. Please install Python 3.10+ first."
    echo "[INFO] Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo "[INFO] CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "[INFO] Fedora: sudo dnf install python3 python3-pip"
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "[PASS] Python version: $PYTHON_VERSION"
echo ""

echo "[STEP 2/6] Installing UV package manager..."
# Check if UV is already installed
if command -v uv &> /dev/null; then
    echo "[PASS] UV already installed"
else
    echo "[INFO] Installing UV..."
    if timeout $TIMEOUT_SECONDS bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"; then
        # Add UV to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"
        echo "[PASS] UV installed successfully"
    else
        echo "[ERROR] Failed to install UV. Please install manually:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
fi
echo ""

echo "[STEP 3/6] Installing dependencies with UV..."
echo "[INFO] This may take a few minutes..."
sleep 2

# Install dependencies with timeout
if timeout $TIMEOUT_SECONDS uv sync --all-extras; then
    echo "[PASS] Dependencies installed successfully"
elif command -v pip3 &> /dev/null; then
    echo "[ERROR] UV installation failed, trying fallback..."
    if pip3 install -r requirements.txt; then
        echo "[PASS] Fallback installation successful"
    else
        echo "[ERROR] Both UV and pip installation failed"
        exit 1
    fi
else
    echo "[ERROR] No package manager available"
    exit 1
fi
echo ""

echo "[STEP 4/6] Installing Playwright browsers..."
echo "[INFO] Installing browser binaries for web scraping..."
sleep 2

# Install Playwright with timeout
if timeout $TIMEOUT_SECONDS uv run playwright install; then
    echo "[PASS] Playwright browsers installed"
elif command -v playwright &> /dev/null; then
    echo "[WARNING] UV Playwright failed, trying fallback..."
    if playwright install; then
        echo "[PASS] Playwright browsers installed (fallback)"
    else
        echo "[WARNING] Playwright installation failed. Some features may not work."
        echo "[INFO] You can install manually later with: uv run playwright install"
    fi
else
    echo "[WARNING] Playwright not available. Some features may not work."
fi
echo ""

echo "[STEP 5/6] Creating required directories..."
mkdir -p data/{arxiv,games,news,courses,ai_platforms,deals,entertainment,anime,adhd,fourchan,spanish_public_aid,intelligence,github,giveaways,ecommerce}
mkdir -p data/watchers data/shortcuts
mkdir -p logs
echo "[PASS] Complete directory structure created"
echo ""

echo "[STEP 6/6] Testing installation..."
echo "[INFO] Running quick test..."
sleep 2

# Test import with timeout
if timeout $TIMEOUT_SECONDS uv run python -c "from src.config.settings import get_settings; print('[TEST] Configuration loaded successfully')" 2>/dev/null; then
    echo "[PASS] Installation test successful"
else
    echo "[WARNING] Installation test failed. Some components may need manual setup."
fi
echo ""

echo "========================================================"
echo "  ✅ Watchtower Deployment Complete!"
echo "========================================================"
echo ""
echo "[SUCCESS] Watchtower is now installed and ready to use!"
echo ""
echo "🚀 Quick Start Commands:"
echo "  Main Dashboard:    ./run_watchtower_dashboard.sh"
echo "  Legacy Dashboard:  ./run_streamlit_app.sh"
echo "  Run ETL Processes: ./run_all_etl.sh"
echo "  Complete System:   ./run_all_etl_and_dashboard.sh"
echo ""
echo "🌐 Dashboard URLs:"
echo "  Main Dashboard:    http://localhost:7777"
echo "  Legacy Dashboard:  http://localhost:8501"
echo "  Health Check:      http://localhost:7777/health"
echo "  Metrics:           http://localhost:7777/metrics"
echo ""
echo "📖 Documentation:"
echo "  Deployment Guide:  docs/DEPLOYMENT_GUIDE.md"
echo "  Dashboard Guide:   docs/DASHBOARD_DEVELOPMENT_GUIDE.md"
echo "  Development Setup: CLAUDE.md"
echo "  Architecture:      docs/ARCHITECTURE_OVERVIEW.md"
echo ""
echo "[INFO] For help, see: https://github.com/yourusername/watchtower"
echo "========================================================"
echo ""

# Make scripts executable
# shellcheck disable=SC2035
chmod +x *.sh 2>/dev/null || true

echo "[INFO] Deployment script completed. Scripts are now executable."
echo "[INFO] You can now run: ./run_watchtower_dashboard.sh"
