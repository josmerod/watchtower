import requests
from bs4 import BeautifulSoup
import sys # For print to stderr

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def get_top_nonfiction_books():
    """
    Scrapes Goodreads' non-fiction genre page to find the "Most Read This Week"
    section and extracts book titles and their Goodreads URLs.
    Includes error handling for network issues and parsing errors.

    Returns:
        list: A list of dictionaries, where each dictionary contains:
              {'title': str, 'goodreads_url': str}
              Returns an empty list if scraping fails or section is not found.
    """
    url = 'https://www.goodreads.com/genres/non-fiction'
    headers = {'User-Agent': USER_AGENT}

    books_data_list = []
    book_links = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error: HTTP request to {url} failed: {e}", file=sys.stderr)
        return [] # Return empty list on request error

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        most_read_header = soup.find(['h2', 'h3', 'div'], string=lambda text: text and "most read this week" in text.lower())

        if not most_read_header:
            # This is an expected case if the section is missing, not necessarily an "error"
            # but for the purpose of this function, it means no data.
            print("Info: 'Most Read This Week' section header not found.", file=sys.stderr)
            # Try fallback (optional, or just return empty)
            # For now, let's be strict: if the primary target isn't there, return empty.
            return []

        # Consolidate link finding logic (from previous iterations)
        parent_container = most_read_header.find_parent()
        if parent_container:
            book_links.extend(parent_container.find_all('a', href=lambda href: href and '/book/show/' in href))

        sibling_container = most_read_header.find_next_sibling()
        if sibling_container and sibling_container.name in ['div', 'ul', 'ol', 'section']:
            book_links.extend(sibling_container.find_all('a', href=lambda href: href and '/book/show/' in href))

        if most_read_header.name == 'a' and '/book/show/' in most_read_header.get('href',''):
             book_links.append(most_read_header)
        else: # Check within the header element itself too
             book_links.extend(most_read_header.find_all('a', href=lambda href: href and '/book/show/' in href))

        if not book_links:
            print("Info: No book links found within the 'Most Read This Week' section.", file=sys.stderr)
            return []

        # Deduplicate links
        unique_tags = []
        seen_tags = set()
        for link_tag in book_links:
            if link_tag not in seen_tags:
                unique_tags.append(link_tag)
                seen_tags.add(link_tag)

        final_unique_links = []
        seen_hrefs = set()
        for link_tag in unique_tags: # Process unique tags
            href = link_tag.get('href')
            if href not in seen_hrefs:
                final_unique_links.append(link_tag)
                seen_hrefs.add(href)
        book_links = final_unique_links

        if not book_links: # Check again after deduplication
            print("Info: No unique book links found after deduplication.", file=sys.stderr)
            return []

        processed_urls = set()
        for link_tag in book_links:
            title_text = link_tag.get_text(strip=True)

            title_span = link_tag.find('span', attrs={'data-testid': 'bookTitle'})
            if title_span and title_span.get_text(strip=True):
                title_text = title_span.get_text(strip=True)
            else:
                span_in_link = link_tag.find('span')
                if span_in_link and span_in_link.get_text(strip=True):
                    title_text = span_in_link.get_text(strip=True)

            if not title_text or len(title_text) < 4:
                img_tag = link_tag.find('img', alt=True)
                if img_tag and img_tag['alt'] and len(img_tag['alt'].strip()) > 3:
                    title_text = img_tag['alt'].strip()

            book_url_path = link_tag.get('href')

            if not book_url_path or not title_text:
                continue

            full_book_url = book_url_path
            if not book_url_path.startswith('http'):
                full_book_url = 'https://www.goodreads.com' + book_url_path

            if full_book_url in processed_urls:
                continue

            if title_text and len(title_text) > 3 and "/book/show/" in full_book_url and "more" not in title_text.lower():
                processed_urls.add(full_book_url)
                books_data_list.append({
                    'title': title_text.strip(),
                    'goodreads_url': full_book_url
                })

        if not books_data_list:
            print("Info: No books matched the final criteria after parsing links.", file=sys.stderr)
            return []

        return books_data_list

    except Exception as e:
        # General exception during parsing (e.g., unexpected structure)
        print(f"Error: HTML parsing failed or unexpected structure: {e}", file=sys.stderr)
        return []


if __name__ == '__main__':
    print("Fetching top non-fiction books from Goodreads (with error handling)...")
    top_books = get_top_nonfiction_books()

    if top_books:
        print(f"\nFound {len(top_books)} books. Sample:")
        for i, book in enumerate(top_books[:3]):
            print(f"  {i+1}. Title: {book['title']}, URL: {book['goodreads_url']}")
    else:
        print("No books found or an error occurred during fetching/parsing.")
