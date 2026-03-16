import sys
import os

try:
    import urllib.request
    url = "https://www.classcentral.com/provider/aws-skill-builder?sort=created-up"
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        
    print(f"Fetched {len(html)} bytes.")
    if "Cloudflare" in html or "Just a moment" in html:
        print("Warning: Cloudflare protection detected.")
    
    with open("classcentral_test.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Saved HTML to classcentral_test.html")
except Exception as e:
    print(f"Error fetching URL: {e}")
