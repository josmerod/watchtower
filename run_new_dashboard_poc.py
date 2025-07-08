#!/usr/bin/env python3
"""
Runner for the New Dashboard POC.
Works with UV environment management.
"""

import sys

def main():
    """Run the new dashboard POC using proper imports."""
    print("Starting New Dashboard POC with UV-compatible imports...")
    
    try:
        # Clean import using the src package structure
        from src.web.new_dashboard_poc.app import app
        
        print("✅ Successfully imported dashboard app")
        print("🚀 Starting server on http://0.0.0.0:7777")
        print("📊 Dashboard will be available at: http://localhost:7777")
        print("⏹️  Press Ctrl+C to stop the server")
        print("-" * 60)
        
        # Run the app (Dash >=3 uses app.run, older versions use app.run_server)
        # Disabled debug mode to prevent auto-reload cycles
        if hasattr(app, "run"):
            app.run(debug=False, port=7777, host="0.0.0.0")
        else:
            app.run_server(debug=False, port=7777, host="0.0.0.0")
        
    except ModuleNotFoundError as e:
        print(f"❌ Module not found: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure dependencies are installed: uv sync")
        print("2. Check if src/web/new_dashboard_poc/app.py exists")
        print("3. Try running: uv run python run_new_dashboard_poc.py")
        sys.exit(1)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n🔧 This might be due to missing dependencies.")
        print("Try: uv sync --all-extras")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Failed to start dashboard server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
