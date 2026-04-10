import requests
from bs4 import BeautifulSoup
import json

url = "https://humble.dadand.dev/bundles/108"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

print(f"Title: {soup.find('h1').text.strip() if soup.find('h1') else 'No H1'}")

for div in soup.find_all(["h2", "h3", "h4", "p", "a"]):
    text = div.text.strip()
    if text and len(text) > 5 and 'Humble' not in text:
        print(f"[{div.name}] {text}")
