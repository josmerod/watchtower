# game_fetchers/itchio_fetcher.py
import urllib.request
import xml.etree.ElementTree as ET # Basic XML parsing
from datetime import datetime
import re # Added for regex operations

# URLs for the RSS feeds
RSS_FEEDS = {
    "top_rated": "https://itch.io/games/top-rated.xml",
    "featured": "https://itch.io/feed/featured.xml",
    "free": "https://itch.io/games/price-free.xml"
}

def parse_itchio_rss_feed(feed_url: str, fetch_source: str) -> list:
    """
    Fetches and parses an itch.io RSS feed into a list of game dictionaries.
    Uses basic XML parsing. A more robust solution would use a library like feedparser.
    """
    games = []
    try:
        with urllib.request.urlopen(feed_url) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            # RSS feeds typically have items under channel -> item
            for item in root.findall('./channel/item'):
                game = {}
                try:
                    game['title'] = item.find('title').text if item.find('title') is not None else "N/A"
                    game['url'] = item.find('link').text if item.find('link') is not None else "#"

                    description_node = item.find('description')
                    if description_node is not None:
                        game['description_short'] = description_node.text # This will be HTML, needs stripping
                    else:
                        game['description_short'] = "N/A"

                    price_value = 0.0
                    price_currency = "USD" # Default
                    is_free = True # Assume free unless price found

                    desc_text_lower = (game['description_short'] or "").lower()
                    title_text_lower = (game['title'] or "").lower()

                    if "$" in desc_text_lower or "€" in desc_text_lower or "£" in desc_text_lower or \
                       "$" in title_text_lower or "€" in title_text_lower or "£" in title_text_lower:
                        if "$0.00" in desc_text_lower or "$0.00" in title_text_lower or "free" in title_text_lower:
                            is_free = True
                            price_value = 0.0
                        else:
                            is_free = False
                            match = re.search(r'[\$€£](\d+\.?\d*)', desc_text_lower + title_text_lower)
                            if match:
                                try:
                                    price_value = float(match.group(1))
                                except ValueError:
                                    price_value = 0.0
                                    is_free = True
                            else:
                                price_value = 0.0
                                is_free = True

                    game['price_value'] = price_value
                    game['price_currency'] = price_currency
                    game['is_free'] = is_free

                    img_match = re.search(r'<img src="([^"]+)"', game['description_short'])
                    if img_match:
                        game['cover_image_url'] = img_match.group(1)
                    else:
                        game['cover_image_url'] = None

                    pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else None
                    if pub_date_str:
                        try:
                            game['published_date'] = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
                        except ValueError:
                            game['published_date'] = None
                    else:
                        game['published_date'] = None

                    game['developer_name'] = None
                    game['developer_url'] = None
                    game['last_updated_date'] = None
                    game['platforms'] = []
                    game['genres'] = []
                    game['tags'] = []
                    game['rating_average'] = None
                    game['rating_count'] = None
                    game['fetch_source'] = fetch_source

                    games.append(game)
                except Exception as e_item:
                    print(f"Error parsing item: {ET.tostring(item, encoding='unicode')}. Error: {e_item}")

    except urllib.error.URLError as e:
        print(f"Error fetching RSS feed {feed_url}: {e}")
    except ET.ParseError as e:
        print(f"Error parsing XML from {feed_url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred with {feed_url}: {e}")

    return games

def fetch_top_rated_games():
    """Fetches top-rated games from itch.io RSS feed."""
    return parse_itchio_rss_feed(RSS_FEEDS['top_rated'], "top_rated_rss")

def fetch_featured_games():
    """Fetches featured (trending) games from itch.io RSS feed."""
    return parse_itchio_rss_feed(RSS_FEEDS['featured'], "featured_rss")

def fetch_free_games():
    """Fetches free games from itch.io RSS feed."""
    return parse_itchio_rss_feed(RSS_FEEDS['free'], "free_rss")

if __name__ == '__main__':
    print("Fetching Top Rated Games...")
    top_rated = fetch_top_rated_games()
    if top_rated:
        print(f"Found {len(top_rated)} top-rated games. First game: {top_rated[0]['title']}")
    else:
        print("No top-rated games found or error fetching.")

    print("\nFetching Featured Games...")
    featured = fetch_featured_games()
    if featured:
        print(f"Found {len(featured)} featured games. First game: {featured[0]['title']}")
    else:
        print("No featured games found or error fetching.")

    print("\nFetching Free Games...")
    free = fetch_free_games()
    if free:
        print(f"Found {len(free)} free games. First game: {free[0]['title']}")
    else:
        print("No free games found or error fetching.")
