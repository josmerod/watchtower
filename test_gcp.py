import urllib.request
import json
import traceback

url = "https://partner.skills.google/catalog/list?page=1&per_page=50"
req = urllib.request.Request(
    url, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/html, */*'
    }
)

try:
    with urllib.request.urlopen(req) as response:
        content_type = response.headers.get('Content-Type', '')
        data = response.read()
        print(f"Content-Type: {content_type}")
        print(f"Data length: {len(data)}")
        
        try:
            # Try to parse as JSON
            jdata = json.loads(data)
            with open("gcp_test.json", "w", encoding="utf-8") as f:
                json.dump(jdata, f, indent=2)
            print("Saved as JSON to gcp_test.json")
        except json.JSONDecodeError:
            with open("gcp_test.html", "w", encoding="utf-8") as f:
                f.write(data.decode('utf-8'))
            print("Saved as HTML to gcp_test.html")
except Exception as e:
    print(f"Error fetching URL: {e}")
    traceback.print_exc()
