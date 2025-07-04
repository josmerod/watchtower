import os
import sys

# Add src to Python path to allow direct import of src.web.new_dashboard_poc.app
# This is often necessary when running scripts from the project root.
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Now import the app
try:
    from web.new_dashboard_poc.app import app
except ModuleNotFoundError as e:
    print(f"Error: Could not import the Dash app. Original error: {e}")
    print("Make sure you are running this script from the project root directory,")
    print("and that the 'src' directory is correctly structured with 'web/new_dashboard_poc/app.py'.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)
except ImportError as e:
    print(f"Error: An import error occurred. Original error: {e}")
    print("This might be due to missing dependencies or issues within the app itself.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)


if __name__ == '__main__':
    print("Attempting to start the New Dashboard POC server...")
    print("Serving on http://127.0.0.1:8051 (Press CTRL+C to quit)")
    try:
        # Check if the app object was imported successfully
        if 'app' in locals() and app is not None:
             # The ALL_SHORTCUTS_DATA and ALL_NEWS_DATA in the components are loaded
             # when components are imported by app.py.
             # The relative paths like '../../../data/...' in those components
             # are resolved based on the CWD when app.py is imported.
             # Since this run script is at the project root, and app.py is imported,
             # the CWD during the import of app.py and its components should be the project root.
            app.run(debug=True, port=8051, host='0.0.0.0')
        else:
            print("Error: The Dash 'app' object was not loaded correctly. Cannot start server.")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to start the Dash server: {e}")
        sys.exit(1)
