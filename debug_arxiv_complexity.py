
import sys
import os
import requests
from urllib.parse import quote
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.watchers.arxiv_watcher import ArxivWatcher

def debug_arxiv():
    print("--- Testing Query Complexity ---")
    
    base_url = "http://export.arxiv.org/api/query"
    
    # Full list from the class (24 items)
    full_cats = [
        "cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.NE", "stat.ML",
        "cs.PL", "cs.SE", "cs.LO", "cs.FL", "cs.DS",
        "cs.DC", "cs.NI", "cs.OS", "cs.AR", "cs.SY", "cs.PF",
        "cs.DB", "cs.CY", "cs.ET", "cs.CR", "cs.SI", "cs.CE"
    ]
    
    # Reduced list (Core AI + SE)
    reduced_cats = [
        "cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.NE", "stat.ML",
        "cs.SE", "cs.PL"
    ]
    
    date_since = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")
    
    def test_query(cats, name):
        cat_str = " OR ".join(cats)
        raw_query = f"cat:({cat_str}) AND submittedDate:[{date_since}000000 TO 999999999999]"
        encoded_query = quote(raw_query)
        url = f"{base_url}?search_query={encoded_query}&sortBy=submittedDate&sortOrder=descending&max_results=1"
        
        print(f"\nTesting {name} ({len(cats)} categories)...")
        try:
            r = requests.get(url)
            print(f"Status: {r.status_code}")
            if r.status_code != 200:
                print(f"Response: {r.text[:200]}...")
            else:
                print("Success!")
        except Exception as e:
            print(f"Failed: {e}")

    test_query(full_cats, "Full List")
    test_query(reduced_cats, "Reduced List")

if __name__ == "__main__":
    debug_arxiv()
