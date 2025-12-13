
import sys
import os
import requests
from urllib.parse import quote
from datetime import datetime, timedelta

def test_structure():
    print("--- Testing Query Structure ---")
    base_url = "http://export.arxiv.org/api/query"
    
    date_since = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")
    
    # 1. Date Format Check
    # date_query = f"submittedDate:[{date_since}000000 TO 999999999999]"
    # Let's try 6 months ago to be sure we find something
    date_since_old = "20250601" 
    date_query = f"submittedDate:[{date_since_old}000000 TO 999999999999]"

    tests = [
        ("Simple Cat", "cat:cs.AI"),
        ("Grouped Cat", "cat:(cs.AI OR cs.LG)"),
        ("Explicit invalid", "cat:cs.AI OR cat:cs.LG"), # Might need parens around whole thing
        ("Cat + Date", f"cat:cs.AI AND {date_query}"),
        ("Grouped Cat + Date", f"cat:(cs.AI OR cs.LG) AND {date_query}"),
    ]
    
    for name, query in tests:
        encoded = quote(query)
        url = f"{base_url}?search_query={encoded}&start=0&max_results=1"
        try:
            print(f"\nTesting: {name}")
            # print(f"Query: {query}")
            r = requests.get(url)
            if r.status_code == 200 and '<entry>' in r.text:
                 print("✅ Success (Found entries)")
            elif r.status_code == 200 and 'totalResults="0"' in r.text:
                 print("✅ Success (0 results)")
            elif r.status_code == 200 and '<title>Error</title>' in r.text:
                 print(f"❌ API Error: {r.text.split('<summary>')[1].split('</summary>')[0] if '<summary>' in r.text else 'Unknown'}")
            else:
                 print(f"❌ HTTP {r.status_code}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_structure()
