import feedparser
import requests

urls = [
    "https://www.microsiervos.com/index.xml",
    "https://www.microsiervos.com/feed",
    "https://microsiervos.com/index.xml",
    "http://www.microsiervos.com/index.xml"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

for url in urls:
    print(f"--- Testing {url} ---")
    try:
        # Try retrieving with requests first to check status
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {r.status_code}")
        print(f"Content Type: {r.headers.get('Content-Type')}")
        
        if r.status_code == 200:
            # Parse the content directly
            feed = feedparser.parse(r.content)
            print(f"Feed Title: {feed.feed.get('title', 'Unknown')}")
            print(f"Entries found: {len(feed.entries)}")
            if len(feed.entries) > 0:
                print(f"First Entry: {feed.entries[0].title}")
                break # Found a working one
        else:
            print("Request failed")
    except Exception as e:
        print(f"Error: {e}")
    print("\n")
