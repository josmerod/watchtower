
import sys
import os
import requests
from urllib.parse import quote

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.watchers.arxiv_watcher import ArxivWatcher

def debug_arxiv():
    print("--- Starting ArXiv Watcher Debug (Simplified) ---")
    
    # Test 1: Simple Query directly with requests
    print("\nTest 1: Direct Requests with Simple Query")
    simple_url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=1"
    try:
        r = requests.get(simple_url)
        print(f"Simple Query Status: {r.status_code}")
        if r.status_code != 200:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"Simple Query Failed: {e}")

    # Test 2: Watcher with standard query
    print("\nTest 2: Watcher Query")
    try:
        watcher = ArxivWatcher(max_results=5, days_back=3)
        print(f"Constructed URL: {watcher.api_url}")
        
        # We manually call requests on watcher.api_url to see the error details directly
        print(f"Fetching manually to see error...")
        r = requests.get(watcher.api_url)
        print(f"Watcher URL Status: {r.status_code}")
        if r.status_code != 200:
            print(f"Response: {r.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_arxiv()
