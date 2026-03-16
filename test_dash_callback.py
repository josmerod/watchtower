import sys
import os

# Add the project root to sys.path so we can import src
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.web.dashboard.components.courses_tab import update_ms_skills_table, load_all_courses_data

print("Loading data...")
load_all_courses_data()

print("Testing MS Skills callback...")
try:
    result = update_ms_skills_table("")
    print("Success! Table was built successfully.")
    import json
    import plotly
    # Try to serialize the result to JSON as Dash would do, to trigger any NaN serialization errors
    json.dumps(result, cls=plotly.utils.PlotlyJSONEncoder)
    print("Serialization success!")
except Exception as e:
    print(f"FAILED: {e}")
