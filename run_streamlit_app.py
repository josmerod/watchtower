#!/usr/bin/env python3
"""Run Streamlit app using UV for consistent environment management."""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run the Streamlit application using UV."""
    print("🚀 Starting Watchtower Streamlit Dashboard with UV...")
    
    # Change to the project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if UV is available
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ UV not found. Please install UV first:")
        print("   Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        print("   Unix/Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    
    # Build the command
    cmd = [
        "uv", "run",
        "streamlit", "run", 
        "src/web/fullstreamlit/app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    
    try:
        print("🔧 Running with UV: uv run streamlit run src/web/fullstreamlit/app.py")
        print("📊 Dashboard will be available at: http://localhost:8501")
        print("⏹️  Press Ctrl+C to stop the server")
        print("-" * 60)
        
        # Run the Streamlit app
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run Streamlit app: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure dependencies are installed: uv sync")
        print("2. Check if src/web/fullstreamlit/app.py exists")
        print("3. Try running: uv run streamlit run src/web/fullstreamlit/app.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Streamlit app stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main() 