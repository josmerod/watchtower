import requests
from bs4 import BeautifulSoup

url = "https://www.audible.es/newreleases?audible_programs=21870165031&feature_six_browse-bin=18385686031&feature_six_browse-bin=18385668031&feature_twelve_browse-bin=18385638031&feature_twelve_browse-bin=18385639031&publication_date=20260215-20260315&sort=pubdate-desc-rank&page=2"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

products = soup.find_all('li', class_='productListItem')
print(f"Page 2 products: {len(products)}")

pagination = soup.find('ul', class_='pagingElements')
if pagination:
    pages = pagination.find_all('li', class_='bc-list-item')
    print(f"Max page listed: {pages[-2].text.strip() if len(pages) > 1 else 'Unknown'}")
