import requests
from bs4 import BeautifulSoup
import sys

# Ensure stdout encodes correctly on Windows
sys.stdout.reconfigure(encoding='utf-8')

url = "https://humble.dadand.dev/"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

active_section = soup.find(lambda tag: tag.name == "h2" and "Active Bundles" in tag.text)
if not active_section:
    print("Could not find Active Bundles section.")
    sys.exit(1)

# Find all sibling elements after "Active Bundles" h2 until "Past Bundles" h2
bundles = []
for sibling in active_section.find_next_siblings():
    if sibling.name == "h2" and "Past Bundles" in sibling.text:
        break
    
    # Bundle links are usually in an 'a' tag inside 'h3' or directly as 'a'
    if sibling.name == "h3":
        link = sibling.find("a")
        if link and "/bundles/" in link.get("href"):
            href = link.get("href")
            title = link.text.strip()
            # The href might be relative
            if href.startswith("/"):
                href = "https://humble.dadand.dev" + href
            bundles.append({"title": title, "url": href})

if not bundles:
    # Maybe the links are not inside h3? Let's try finding all links between the two h2s
    print("No bundles found in h3. Searching all links in section...")
    for sibling in active_section.find_next_siblings():
        if sibling.name == "h2" and "Past Bundles" in sibling.text:
            break
        for link in sibling.find_all("a"):
            href = link.get("href")
            if href and "/bundles/" in href:
                title = link.text.strip()
                if href.startswith("/"):
                    href = "https://humble.dadand.dev" + href
                bundles.append({"title": title, "url": href})
                
# Remove duplicates (sometimes 'shared books' links point to the same bundle)
unique_bundles = {}
for b in bundles:
    unique_bundles[b["url"]] = b
bundles = list(unique_bundles.values())

print(f"Found {len(bundles)} active bundles.")

for b in bundles[:2]:
    print(f"\nFetching books for: {b['title']} ({b['url']})")
    b_resp = requests.get(b['url'])
    b_soup = BeautifulSoup(b_resp.text, "html.parser")
    
    books = []
    for h4 in b_soup.find_all("h4"):
        if h4.text.strip():
            books.append(h4.text.strip())
            
    print(f"Found {len(books)} books.")
    for book in books[:3]:
        print("  -", book)

