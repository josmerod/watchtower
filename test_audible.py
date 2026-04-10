from bs4 import BeautifulSoup
import requests
import json

url = "https://www.audible.es/newreleases?audible_programs=21870165031&feature_six_browse-bin=18385686031&feature_six_browse-bin=18385668031&feature_twelve_browse-bin=18385638031&feature_twelve_browse-bin=18385639031&publication_date=20260215-20260315&sort=pubdate-desc-rank"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

products = soup.find_all('li', class_='productListItem')
print(f"Found {len(products)} products on the first page.")

results = []
for p in products:
    title_span = p.find('h3', class_='bc-heading')
    if not title_span:
        continue
    a_tag = title_span.find('a')
    title = a_tag.text.strip() if a_tag else title_span.text.strip()
    link = "https://www.audible.es" + a_tag['href'] if a_tag and 'href' in a_tag.attrs else ""
    
    author_span = p.find('li', class_='authorLabel')
    author = author_span.text.replace('De:', '').strip() if author_span else ""
    
    narrator_span = p.find('li', class_='narratorLabel')
    narrator = narrator_span.text.replace('Narrado por:', '').strip() if narrator_span else ""

    runtime_span = p.find('li', class_='runtimeLabel')
    runtime = runtime_span.text.replace('Duración:', '').strip() if runtime_span else ""
    
    date_span = p.find('li', class_='releaseDateLabel')
    date = date_span.text.replace('Fecha de publicación:', '').strip() if date_span else ""
    
    lang_span = p.find('li', class_='languageLabel')
    lang = lang_span.text.replace('Idioma:', '').strip() if lang_span else ""

    results.append({
        "title": title,
        "link": link,
        "author": author,
        "narrator": narrator,
        "runtime": runtime,
        "published": date,
        "language": lang
    })

print(json.dumps(results[:3], indent=2, ensure_ascii=False))
