"""Data loading utilities for the Watchtower Streamlit application.

This module provides functions to load course data from various platforms
like Coursera, typically from JSON files, and returns them as Pandas DataFrames.
"""
import json
import pandas as pd
import os
from typing import Dict, Optional, Any

def load_coursera_courses() -> pd.DataFrame:
    """
    Load Coursera courses data from JSON file
    
    Returns
    -------
    pd.DataFrame
        DataFrame containing Coursera courses data or empty DataFrame if file not found
    """
    try:
        # Use the direct path that worked in our test
        coursera_file = "data/classcentral/coursera_courses.json"
        
        if not os.path.exists(coursera_file):
            print(f"Coursera data file not found at: {coursera_file}")
            return pd.DataFrame()
            
        with open(coursera_file, 'r', encoding='utf-8') as f:
            coursera_data = json.load(f)
            
        df = pd.DataFrame(coursera_data)
        print(f"Loaded {len(df)} Coursera courses")
        return df
    except Exception as e:
        print(f"Error loading Coursera data: {e}")
        return pd.DataFrame()
        
def load_courses_data() -> Dict[str, pd.DataFrame]:
    """
    Load courses data from all available platforms
    
    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionary with platform name as key and DataFrame as value
    """
    courses_data = {}
    
    # Load Coursera data
    coursera_df = load_coursera_courses()
    if not coursera_df.empty:
        courses_data["coursera"] = coursera_df
    
    # Add other platforms as they are added
    # edx_df = load_edx_courses()
    # if not edx_df.empty:
    #     courses_data["edx"] = edx_df
    
    return courses_data 