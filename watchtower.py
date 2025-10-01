#!/usr/bin/env python3
"""
Watchtower Platform - Unified Entry Point

This script provides easy access to all Watchtower functionality:
- Development and production modes
- Docker deployment
- Service management
- ETL and dashboard control

Usage:
    python watchtower.py dev          # Development mode
    python watchtower.py prod         # Production mode
    python watchtower.py etl          # ETL only
    python watchtower.py dashboard    # Dashboard only
    python watchtower.py docker-dev   # Docker development
    python watchtower.py docker-prod  # Docker production
    python watchtower.py service install  # Install system service
    python watchtower.py status       # Show status
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

try:
    from launcher.cli import main
    main()
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure dependencies are installed: uv sync --all-extras")
    sys.exit(1)
