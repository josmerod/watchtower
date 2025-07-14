#!/usr/bin/env python3
"""
Watchtower Dashboard Launcher
Main entry point for the Watchtower intelligence platform dashboard.
Works with UV environment management.
"""

import sys

def main():
    """Launch the Watchtower Dashboard with proper imports."""
    print("Starting Watchtower Dashboard...")
    print("Real-time Intelligence & Monitoring Platform")
    
    try:
        # Clean import using the src package structure
        from src.web.dashboard.app import app
        
        print("Successfully loaded Watchtower Dashboard")
        print("Starting server on http://0.0.0.0:7777")
        print("Dashboard available at: http://localhost:7777")
        print("Press Ctrl+C to stop the server")
        print("-" * 60)
        
        # Run the app (Dash >=3 uses app.run, older versions use app.run_server)
        # Production mode - disabled debug for stability
        if hasattr(app, "run"):
            app.run(debug=False, port=7777, host="0.0.0.0")
        else:
            app.run_server(debug=False, port=7777, host="0.0.0.0")
        
    except ModuleNotFoundError as e:
        print(f"Module not found: {e}")
        print("\nTroubleshooting:")
        print("1. Install dependencies: uv sync --all-extras")
        print("2. Check Watchtower installation")
        print("3. Try: uv run python run_watchtower_dashboard.py")
        sys.exit(1)
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("\nMissing dependencies detected.")
        print("Run: uv sync --all-extras")
        sys.exit(1)
        
    except Exception as e:
        print(f"Failed to start Watchtower Dashboard: {e}")
        print("Check logs for detailed error information")
        sys.exit(1)


if __name__ == '__main__':
    main() 