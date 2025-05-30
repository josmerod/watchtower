import requests
import logging
from bs4 import BeautifulSoup
import time # Keep for consistency, though sleep won't be used in this version

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

PARK_URL = "https://parquesnaturales.gva.es/web/pn-l-albufera"
FETCH_RETRIES = 0
FETCH_TIMEOUT = 15 # Keep it reasonably short for this test

def fetch_page_content(url, retries=FETCH_RETRIES, timeout=FETCH_TIMEOUT):
    """Fetches the HTML content of a given URL with retries."""
    logging.debug(f"Attempting to fetch {url} (timeout: {timeout}s)")
    print(f"Attempting to fetch: {url}")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        response.encoding = 'utf-8'
        logging.debug(f"Successfully fetched {url}")
        print(f"Successfully fetched: {url}")
        return response.text
    except requests.exceptions.Timeout:
        logging.error(f"Timeout fetching {url} after {retries + 1} attempt(s).")
        print(f"Timeout fetching: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        print(f"Error fetching {url}: {e}")
        return None

def main():
    logging.info("Starting minimal test script...")
    print("Starting minimal test script...")

    html_content = fetch_page_content(PARK_URL)

    if html_content:
        logging.info(f"Successfully fetched content from {PARK_URL}")
        print(f"Successfully fetched content from {PARK_URL}")
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.text.strip() if title_tag else "No title found"
            logging.info(f"Page title: {title}")
            print(f"Page title: {title}")
        except Exception as e:
            logging.error(f"Error parsing HTML: {e}")
            print(f"Error parsing HTML: {e}")
    else:
        logging.warning(f"Failed to fetch content from {PARK_URL}")
        print(f"Failed to fetch content from {PARK_URL}")

    logging.info("Minimal test script finished.")
    print("Minimal test script finished.")

if __name__ == "__main__":
    main()
