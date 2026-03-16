from bs4 import BeautifulSoup
import json

with open("classcentral_test.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

results = []
# ClassCentral typically uses a row or list item for courses
# Let's try to find course names
for a in soup.find_all("a", class_="course-name"):
    title = a.get_text(strip=True)
    url = "https://www.classcentral.com" + a.get('href', '')
    
    # Try to find provider, rating, duration, etc. near the element
    parent = a.find_parent("li")
    if parent:
        # e.g., duration might be under a span
        spans = parent.find_all("span")
        infos = [s.get_text(strip=True) for s in spans]
        results.append({
            "title": title,
            "url": url,
            "info": infos
        })
    else:
        results.append({
            "title": title,
            "url": url
        })

print(f"Found {len(results)} courses using 'course-name' class.")

if not results:
    # Let's try another common class for ClassCentral
    for h2 in soup.find_all("h2"):
        a = h2.find("a")
        if a and 'href' in a.attrs:
            title = h2.get_text(strip=True)
            url = "https://www.classcentral.com" + a['href']
            results.append({
                "title": title,
                "url": url
            })
    print(f"Found {len(results)} courses using h2->a.")

with open("cc_parsed.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("Saved to cc_parsed.json")
