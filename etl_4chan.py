import requests
import json
import time
from bs4 import BeautifulSoup

API_BASE_URL = "https://a.4cdn.org"
BOARD_URL_BASE = "https://boards.4chan.org"

# -------------------- EXTRACT --------------------

def get_boards():
    """
    Returns a hardcoded list of example board objects.
    """
    # In a real scenario, this could fetch from https://a.4cdn.org/boards.json
    # For now, hardcoded as per requirements.
    return [
        {"board": "adv", "title": "Advice"},
        {"board": "b", "title": "Random"},
        {"board": "biz", "title": "Business & Finance"},
        {"board": "cgl", "title": "Cosplay & EGL"},
        {"board": "ck", "title": "Food & Cooking"},
        {"board": "diy", "title": "Do-It-Yourself"},
        {"board": "fit", "title": "Fitness"},
        {"board": "lit", "title": "Literature"},
        {"board": "news", "title": "Current News"},
        {"board": "sci", "title": "Science & Math"},
        {"board": "tech", "title": "Technology"},
        {"board": "travel", "title": "Travel"},
        {"board": "v", "title": "Video Games"},
        {"board": " χρόνος", "title": "Time"}, # Example with non-ascii
    ]

def get_catalog(board_code):
    """
    Fetches the catalog for a given board using a real HTTP request.
    """
    catalog_url = f"{API_BASE_URL}/{board_code}/catalog.json"
    print(f"Fetching catalog for /{board_code}/ from {catalog_url}...")
    try:
        response = requests.get(catalog_url)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        time.sleep(1)  # Adhere to API rate limit
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error fetching catalog for /{board_code}/: {e}")
        if response.status_code == 404:
            print(f"Board /{board_code}/ not found (404). It might be an invalid board code.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching catalog for /{board_code}/: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from catalog for /{board_code}/. Response: {response.text[:200]}...") # Log part of response
        return None

def get_thread(board_code, thread_no):
    """
    Fetches a specific thread from a board using a real HTTP request.
    Returns the full thread data which is a dictionary with a "posts" list.
    """
    thread_url = f"{API_BASE_URL}/{board_code}/thread/{thread_no}.json"
    print(f"Fetching thread /{board_code}/{thread_no} from {thread_url}...")
    try:
        response = requests.get(thread_url)
        response.raise_for_status() # Raise an exception for HTTP errors
        time.sleep(1) # Adhere to API rate limit
        return response.json() # This should be a dictionary like {"posts": [...]}
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error fetching thread /{board_code}/{thread_no}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching thread /{board_code}/{thread_no}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON for thread /{board_code}/{thread_no}. Response: {response.text[:200]}...")
        return None

# -------------------- TRANSFORM --------------------

def summarize_post(op_post_data, board_code, thread_no_from_op): # thread_no_from_op is op_post_data.get('no')
    """
    Summarizes an original post (OP) using BeautifulSoup for HTML parsing.
    """
    if not op_post_data:
        return None

    html_comment = op_post_data.get('com', '')
    soup = BeautifulSoup(html_comment, 'html.parser')
    clean_text = soup.get_text(separator=' ', strip=True) # Use space as separator, strip whitespace

    summary_text = clean_text[:250]
    full_comment_preview = clean_text[:500]

    return {
        "board": board_code,
        "thread_no": thread_no_from_op, # op_post_data.get('no')
        "subject": op_post_data.get('sub', 'No Subject'),
        "summary_text": summary_text,
        "full_comment_preview": full_comment_preview,
        "replies": op_post_data.get('replies', 0),
        "images": op_post_data.get('images', 0), # Number of image+spoiler files
        "unique_ips": op_post_data.get('unique_ips', 0), # If available from OP in thread data
        "semantic_url": op_post_data.get('semantic_url', ''), # If available
        "timestamp": op_post_data.get('time', 0), # UNIX timestamp
        "datetime": op_post_data.get('now', ''), # String representation of time like "MM/DD/YY(Day)HH:MM:SS"
        "thread_url": f"{BOARD_URL_BASE}/{board_code}/thread/{thread_no_from_op}"
    }

# -------------------- LOAD --------------------

def save_data(data, filename="summarized_posts.json"):
    """
    Saves the processed data to a JSON file.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data saved to {filename}")
    except IOError as e:
        print(f"Error saving data to {filename}: {e}")

# -------------------- MAIN --------------------

if __name__ == "__main__":
    print("Starting 4chan ETL process...")

    # For now, let's use a predefined board, e.g., 'adv' (Advice)
    selected_board_code = "adv"

    print(f"Processing board: /{selected_board_code}/")

    # get_catalog returns a list of page objects.
    # Each page object is a dictionary like: {"page": 1, "threads": [...]}
    catalog_pages = get_catalog(selected_board_code)

    if catalog_pages: # catalog_pages is a list of pages
        all_summaries = []
        threads_processed_count = 0
        max_threads_to_process = 5 # Limiting for this example

        for page_data in catalog_pages: # Iterate through pages
            if threads_processed_count >= max_threads_to_process:
                break

            page_threads = page_data.get("threads", []) # Get list of threads for the current page
            if not page_threads:
                print(f"No threads found on page {page_data.get('page')} for board /{selected_board_code}/.")
                continue

            for thread_catalog_summary in page_threads: # Iterate through threads on this page
                if threads_processed_count >= max_threads_to_process:
                    break

                thread_no_from_catalog = thread_catalog_summary.get("no")
                if not thread_no_from_catalog:
                    print("Skipping thread summary from catalog due to missing 'no'.")
                    continue

                print(f"Fetching details for thread /{selected_board_code}/{thread_no_from_catalog}...")

                # Fetch the full thread data.
                # get_thread returns a dictionary: {"posts": [...]}
                full_thread_data = get_thread(selected_board_code, thread_no_from_catalog)

                if full_thread_data and "posts" in full_thread_data and full_thread_data["posts"]:
                    # The OP is the first post in the "posts" list
                    op_post_data = full_thread_data["posts"][0]

                    # The 'no' field in the OP post data is its own post number, which is also the thread_no for OPs.
                    # Use the 'no' from the OP data itself as the definitive thread number.
                    actual_thread_no = op_post_data.get("no", thread_no_from_catalog)
                    if actual_thread_no != thread_no_from_catalog:
                        print(f"  Info: Thread ID from OP data ({actual_thread_no}) differs from catalog ({thread_no_from_catalog}). Using OP data's ID.")

                    summary = summarize_post(op_post_data, selected_board_code, actual_thread_no)
                    if summary:
                        subject_preview = summary['subject'][:30] if summary['subject'] else "No Subject"
                        print(f"  Successfully summarized OP for thread /{selected_board_code}/{actual_thread_no}: '{subject_preview}...'")
                        all_summaries.append(summary)
                    else:
                        print(f"  Could not summarize OP for thread /{selected_board_code}/{actual_thread_no}.")
                else:
                    print(f"  Could not fetch or parse details for thread /{selected_board_code}/{thread_no_from_catalog}. Response: {full_thread_data}")

                threads_processed_count += 1
                if threads_processed_count >= max_threads_to_process:
                    print(f"Reached processing limit of {max_threads_to_process} threads for board /{selected_board_code}/.")
                    break

        if all_summaries:
            save_data(all_summaries, f"summarized_{selected_board_code}_posts.json")
        else:
            print(f"No summaries were generated for board /{selected_board_code}/.")
    else:
        print(f"Could not fetch or process catalog for board /{selected_board_code}/. No data to save.")

    print("4chan ETL process finished.")
