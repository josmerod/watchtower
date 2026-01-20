import sys
import os
import logging

# Configure logging to capture any utils errors
logging.basicConfig(level=logging.INFO)

# Add project root to path
sys.path.append(os.getcwd())

from src.web.dashboard.components.news_tab import get_all_news_data

print("--- Verifying News Data Loading ---")
try:
    data = get_all_news_data()
    tc_data = data.get('techcrunch', [])
    print(f"TechCrunch Articles Found: {len(tc_data)}")
    
    if tc_data:
        first = tc_data[0]
        print(f"Latest Article Title: {first.get('title')}")
        print(f"Published Date: {first.get('published')}")
        print(f"Fetched At: {first.get('fetched_at')}")
        print(f"Source File: {first.get('source')}")
    else:
        print("ERROR: No TechCrunch data found in loaded dict.")
        
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
