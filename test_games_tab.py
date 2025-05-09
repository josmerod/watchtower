import pandas as pd
import json
import os
import sys

# Add project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import Streamlit and project modules
import streamlit as st
from src.web.fullstreamlit.components import games_tab
from src.utils.logging import get_logger

logger = get_logger("GameTabTest")

def load_test_data():
    """Load game data from JSON files"""
    data = {
        "deals": pd.DataFrame(),
        "bundles": pd.DataFrame(),
        "giveaways": pd.DataFrame()
    }
    
    # Load Humble Bundle data
    try:
        if os.path.exists("data/games/humblebundles.json"):
            with open("data/games/humblebundles.json", "r", encoding="utf-8") as f:
                bundles = json.load(f)
                if bundles:
                    # Filter to only include game bundles
                    game_bundles = [b for b in bundles if b.get("type") == "games"]
                    if game_bundles:
                        data["bundles"] = pd.DataFrame(game_bundles)
                        print(f"Loaded {len(game_bundles)} game bundles from humblebundles.json")
    except Exception as e:
        print(f"Error loading Humble Bundle data: {e}")
    
    # Load other game data if available
    for file_name, data_key in [
        ("deals.json", "deals"),
        ("bundles.json", "bundles"),  # Regular bundles (non-Humble)
        ("giveaways.json", "giveaways")
    ]:
        try:
            file_path = f"data/games/{file_name}"
            if os.path.exists(file_path) and data[data_key].empty:
                with open(file_path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    if items:
                        df = pd.DataFrame(items)
                        if not df.empty:
                            data[data_key] = df
                            print(f"Loaded {len(df)} items from {file_name}")
        except Exception as e:
            print(f"Error loading {file_name}: {e}")
    
    return data

def main():
    """Test the games tab with our data"""
    st.set_page_config(page_title="Watchtower Game Tab Test", layout="wide")
    st.title("Watchtower Game Tab Test")
    
    # Load data
    data = load_test_data()
    
    # Display data stats
    st.write("## Data Statistics")
    for key, df in data.items():
        if not df.empty:
            st.write(f"**{key.capitalize()}:** {len(df)} items")
            st.write(f"Columns: {', '.join(df.columns.tolist())}")
        else:
            st.write(f"**{key.capitalize()}:** No data available")
    
    # Rename end_date to published_date for compatibility
    if not data["bundles"].empty and "end_date" in data["bundles"].columns:
        data["bundles"] = data["bundles"].rename(columns={"end_date": "published_date"})
    
    # Add game_count based on games list
    if not data["bundles"].empty and "games" in data["bundles"].columns:
        data["bundles"]["game_count"] = data["bundles"]["games"].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )
    
    # Render the games tab
    games_tab.render(data["deals"], data["bundles"], data["giveaways"], logger)

if __name__ == "__main__":
    main() 