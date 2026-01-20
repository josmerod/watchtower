import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.web.dashboard.utils import get_data_path

def test_load():
    path = get_data_path("udemy", "udemy_courses.json")
    print(f"Path: {path}")
    if os.path.exists(path):
        print("File exists")
        try:
            df = pd.read_json(path)
            print(f"Loaded {len(df)} rows")
            print(df.head())
            print(df.columns)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("File does not exist")

if __name__ == "__main__":
    test_load()
