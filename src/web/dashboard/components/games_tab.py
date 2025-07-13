import os
import json
import pandas as pd
from datetime import datetime, timezone
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, dir_exists, log_missing_file, handle_data_loading_error

import re # For parsing prices

# --- Constants ---
DATA_BASE_PATH = get_data_path("games", "") # Relative to this file
ALL_GAMES_DATA = {
    'deals': pd.DataFrame(),
    'bundles': pd.DataFrame(),
    'giveaways': pd.DataFrame(),
    'trending': pd.DataFrame(),
    'new_releases': pd.DataFrame(),
    'allkeyshop': pd.DataFrame()
}
DATA_LOADED_SUCCESSFULLY = {key: False for key in ALL_GAMES_DATA}

# --- Date Parsing Utility ---
def parse_game_date(date_str, source_format=None):
    if pd.isna(date_str) or not date_str:
        return None

    # Try ISO format first (common)
    try:
        # Handle 'Z' for UTC and potential timezone offsets
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass # Continue to other formats

    # Try specific format if provided
    if source_format:
        try:
            dt = datetime.strptime(str(date_str), source_format)
            return dt.replace(tzinfo=timezone.utc) # Assume UTC if naive
        except ValueError:
            pass

    # Fallback formats (add more as identified from data)
    common_formats = [
        "%Y-%m-%d",             # YYYY-MM-DD
        "%d/%m/%Y",             # DD/MM/YYYY
        "%m/%d/%Y",             # MM/DD/YYYY
        "%b %d, %Y",            # Jan 01, 2023
        "%B %d, %Y",            # January 01, 2023
        "%Y-%m-%dT%H:%M:%S",    # ISO without timezone part
    ]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return dt.replace(tzinfo=timezone.utc) # Assume UTC
        except ValueError:
            continue

    # Try epoch timestamp (seconds)
    try:
        timestamp = float(date_str)
        if timestamp > 10000000000: # Likely milliseconds, convert to seconds
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except ValueError:
        pass

    print(f"Warning: Could not parse game date: {date_str} with known formats.")
    return None

# --- Price Parsing Utility ---
def parse_price(price_str):
    if pd.isna(price_str) or price_str is None or str(price_str).strip() == '':
        return 0.0
    if isinstance(price_str, (int, float)): # Already a number
        return float(price_str)

    s_price = str(price_str).strip().lower()
    if s_price == 'free' or 'gratis' in s_price:
        return 0.0

    # Remove currency symbols and other non-numeric characters (except decimal point)
    # Handles formats like "$19.99", "€19,99", "19.99 USD"
    cleaned_price = re.sub(r"[^\d\.,]", "", s_price)

    # Standardize decimal separator to '.'
    if ',' in cleaned_price and '.' in cleaned_price: # e.g. 1.234,56
        cleaned_price = cleaned_price.replace('.', '') # Remove thousand separator
        cleaned_price = cleaned_price.replace(',', '.')
    elif ',' in cleaned_price: # e.g. 1234,56 or 1,23 (treat as decimal if only one)
        # Heuristic: if it's a single comma, assume it's decimal
        if cleaned_price.count(',') == 1 and len(cleaned_price.split(',')[-1]) == 2:
             cleaned_price = cleaned_price.replace(',', '.')
        else: # Multiple commas or not a typical decimal format, remove them
            cleaned_price = cleaned_price.replace(',', '')

    try:
        return float(cleaned_price)
    except ValueError:
        # Return 0.0 for invalid prices instead of None
        return 0.0


# --- Data Loading Functions (to be implemented one by one) ---
def load_deals_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "deals.json"))

    if not file_exists(file_path):
        print(f"Warning (Deals): File not found at {file_path}")
        ALL_GAMES_DATA['deals'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['deals'] = False # Explicitly set to false
        return

    try:
        df = pd.read_json(file_path)
    except ValueError as e: # Handles JSON decoding errors in pandas
        print(f"Error (Deals): Could not decode JSON from {file_path}. Error: {e}")
        ALL_GAMES_DATA['deals'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['deals'] = False
        return
    except Exception as e:
        print(f"Error (Deals): Failed to read or process {file_path}. Error: {e}")
        ALL_GAMES_DATA['deals'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['deals'] = False
        return

    if df.empty:
        ALL_GAMES_DATA['deals'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['deals'] = True # File existed and was valid JSON, but empty
        print("Info (Deals): deals.json was empty or resulted in an empty DataFrame.")
        return

    # Standardize columns - adjust based on actual keys in deals.json
    # Common keys might be: 'title', 'url'/'link', 'store', 'newPrice', 'oldPrice', 'discount', 'addedDate'
    df.rename(columns={
        'url': 'link', # Assuming 'url' is the direct link to the deal
        'newPrice': 'price_new',
        'oldPrice': 'price_old',
        'addedDate': 'published_date_str', # Or a similar date field
        'name': 'title' # If 'name' is used for title
    }, inplace=True)

    # Ensure essential columns exist, fill with None if not
    expected_cols = ['title', 'link', 'store', 'price_new', 'price_old', 'discount', 'published_date_str']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df['published_date'] = df['published_date_str'].apply(lambda x: parse_game_date(x)) # Assuming a date field exists
    df['price_new_numeric'] = df['price_new'].apply(parse_price)
    df['price_old_numeric'] = df['price_old'].apply(parse_price)

    # Ensure discount is numeric if it's like "75%" -> 75.0 or 0.75
    if 'discount' in df.columns:
        df['discount_numeric'] = df['discount'].astype(str).str.extract(r'(\d+)').astype(float)
    else:
        df['discount_numeric'] = None

    df = df.sort_values(by='published_date', ascending=False, na_position='last')

    ALL_GAMES_DATA['deals'] = df
    DATA_LOADED_SUCCESSFULLY['deals'] = True
    print(f"Info (Deals): Loaded {len(df)} deals.")


def load_bundles_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_paths_with_store = [
        (os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "bundles.json")), "Various/Mixed"), # Default store if not specified in data
        (os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "humblebundles.json")), "Humble Bundle")
    ]

    all_bundles_dfs = []
    any_file_processed_successfully = False

    for file_path, store_name_default in file_paths_with_store:
        if not file_exists(file_path):
            print(f"Warning (Bundles): File not found at {file_path}")
            continue # Skip this file

        try:
            df = pd.read_json(file_path)
            if df.empty:
                print(f"Info (Bundles): File {file_path} was empty.")
                any_file_processed_successfully = True # File existed and was valid
                continue

            # Standardize columns - adjust based on actual keys
            # Common keys: 'title', 'url'/'link', 'price', 'game_count', 'store', 'endDate'/'expiryDate'
            df.rename(columns={
                'url': 'link',
                'endDate': 'expiry_date_str',
                'expiryDate': 'expiry_date_str', # another common name
                'name': 'title',
                'humbleLink': 'link', # Specific to humblebundles.json
                'humbleTitle': 'title' # Specific to humblebundles.json
            }, inplace=True)

            # Add store if not present
            if 'store' not in df.columns:
                df['store'] = store_name_default
            else: # Fill NaN stores with default if column exists but value is missing
                df['store'].fillna(store_name_default, inplace=True)

            # Ensure essential columns
            expected_cols = ['title', 'link', 'store', 'price', 'game_count', 'expiry_date_str']
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None # Add missing columns with None

            df['expiry_date'] = df['expiry_date_str'].apply(lambda x: parse_game_date(x))
            df['price_numeric'] = df['price'].apply(parse_price)

            # 'game_count' might need extraction if it's like "10 games"
            if 'game_count' in df.columns and df['game_count'].dtype == 'object':
                 df['game_count_numeric'] = df['game_count'].astype(str).str.extract(r'(\d+)').astype(float).fillna(0).astype(int)
            elif 'game_count' in df.columns: # Already numeric
                 df['game_count_numeric'] = pd.to_numeric(df['game_count'], errors='coerce').fillna(0).astype(int)
            else:
                 df['game_count_numeric'] = 0


            all_bundles_dfs.append(df)
            any_file_processed_successfully = True
            print(f"Info (Bundles): Loaded {len(df)} bundles from {os.path.basename(file_path)}.")

        except ValueError as e:
            print(f"Error (Bundles): Could not decode JSON from {file_path}. Error: {e}")
        except Exception as e:
            print(f"Error (Bundles): Failed to read or process {file_path}. Error: {e}")

    if not all_bundles_dfs:
        ALL_GAMES_DATA['bundles'] = pd.DataFrame()
        # If any file was processed (even if empty), consider it a "successful" load attempt for this category
        DATA_LOADED_SUCCESSFULLY['bundles'] = any_file_processed_successfully
        if not any_file_processed_successfully:
             print("Warning (Bundles): No bundle files found or processed.")
        return

    # Filter out empty DataFrames to avoid FutureWarning
    non_empty_dfs = [df for df in all_bundles_dfs if not df.empty]
    if non_empty_dfs:
        # Ensure all DataFrames have consistent columns to avoid FutureWarning
        if len(non_empty_dfs) > 1:
            # Get all unique columns
            all_columns = set()
            for df in non_empty_dfs:
                all_columns.update(df.columns)
            
            # Add missing columns with None values
            for i, df in enumerate(non_empty_dfs):
                for col in all_columns:
                    if col not in df.columns:
                        non_empty_dfs[i] = df.assign(**{col: None})
        
        combined_df = pd.concat(non_empty_dfs, ignore_index=True)
    else:
        combined_df = pd.DataFrame()  # Return empty DataFrame if no data

    # Use 'expiry_date' for sorting if available, otherwise it will sort Nones/NaTs
    # If bundles don't have a primary "published" date, expiry or a load date might be used.
    # For now, sorting by expiry date, making active bundles (future expiry) appear first if sorted ascending.
    # Or, if no reliable date, don't sort or sort by title. Let's sort by expiry_date descending for now.
    combined_df = combined_df.sort_values(by='expiry_date', ascending=False, na_position='last')

    ALL_GAMES_DATA['bundles'] = combined_df
    DATA_LOADED_SUCCESSFULLY['bundles'] = True
    print(f"Info (Bundles): Combined total of {len(combined_df)} bundles.")


def load_giveaways_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "giveaways.json"))

    if not file_exists(file_path):
        print(f"Warning (Giveaways): File not found at {file_path}")
        ALL_GAMES_DATA['giveaways'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['giveaways'] = False
        return

    try:
        df = pd.read_json(file_path)
    except ValueError as e:
        print(f"Error (Giveaways): Could not decode JSON from {file_path}. Error: {e}")
        ALL_GAMES_DATA['giveaways'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['giveaways'] = False
        return
    except Exception as e:
        print(f"Error (Giveaways): Failed to read or process {file_path}. Error: {e}")
        ALL_GAMES_DATA['giveaways'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['giveaways'] = False
        return

    if df.empty:
        ALL_GAMES_DATA['giveaways'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['giveaways'] = True # File existed, valid, but empty
        print("Info (Giveaways): giveaways.json was empty.")
        return

    # Standardize columns - e.g., 'title', 'url'/'link', 'store', 'publishedDate', 'expiryDate'
    df.rename(columns={
        'url': 'link',
        'publishedDate': 'published_date_str', # Or similar field for when it was posted
        'expiryDate': 'expiry_date_str', # Or similar field for when it expires
        'name': 'title'
    }, inplace=True)

    expected_cols = ['title', 'link', 'store', 'published_date_str', 'expiry_date_str']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df['published_date'] = df['published_date_str'].apply(lambda x: parse_game_date(x))
    df['expiry_date'] = df['expiry_date_str'].apply(lambda x: parse_game_date(x))

    # Giveaways are typically free
    df['price_numeric'] = 0.0

    df = df.sort_values(by='published_date', ascending=False, na_position='last')

    ALL_GAMES_DATA['giveaways'] = df
    DATA_LOADED_SUCCESSFULLY['giveaways'] = True
    print(f"Info (Giveaways): Loaded {len(df)} giveaways.")


def load_trending_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "itchio_trending.json"))

    if not file_exists(file_path):
        print(f"Warning (Trending): File not found at {file_path}")
        ALL_GAMES_DATA['trending'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['trending'] = False
        return

    try:
        df = pd.read_json(file_path)
    except ValueError as e:
        print(f"Error (Trending): Could not decode JSON from {file_path}. Error: {e}")
        ALL_GAMES_DATA['trending'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['trending'] = False
        return
    except Exception as e:
        print(f"Error (Trending): Failed to read or process {file_path}. Error: {e}")
        ALL_GAMES_DATA['trending'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['trending'] = False
        return

    if df.empty:
        ALL_GAMES_DATA['trending'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['trending'] = True # File existed, valid, but empty
        print("Info (Trending): itchio_trending.json was empty.")
        return

    # Standardize columns: 'title', 'link', 'author', 'price', 'published_date' (if available)
    # Itch.io data might have 'name' for title, 'user.name' for author, 'price_value', 'url'
    df.rename(columns={
        'name': 'title',
        'url': 'link',
        'user.name': 'author', # If author is nested
        'price_value': 'price' # If price is 'price_value'
        # 'published_at' or similar for date, if available
    }, inplace=True)

    # If author is in a nested 'user' dict and not flattened by pd.read_json's normalize
    if 'user' in df.columns and isinstance(df['user'].iloc[0], dict) and 'author' not in df.columns :
        df['author'] = df['user'].apply(lambda x: x.get('name') if isinstance(x, dict) else None)

    expected_cols = ['title', 'link', 'author', 'price'] # 'published_date' might not exist for trending
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df['price_numeric'] = df['price'].apply(parse_price)

    # Itch.io trending might not have a reliable "published_date" for the game itself,
    # it's more about current popularity. If there's a 'crawled_date' or similar,
    # it could be used, but it's not the game's release/publish date.
    # For now, we won't sort by date unless a suitable field is identified.
    # If sorting is desired, one might sort by rank if available, or just display as is.

    ALL_GAMES_DATA['trending'] = df
    DATA_LOADED_SUCCESSFULLY['trending'] = True
    print(f"Info (Trending): Loaded {len(df)} trending Itch.io games.")


def load_new_releases_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "new_releases.json"))

    if not file_exists(file_path):
        log_missing_file(file_path, "New Releases", is_optional=True)
        ALL_GAMES_DATA['new_releases'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['new_releases'] = False
        return

    try:
        # It's possible new_releases.json is a list of dicts, or a dict with a key like 'results' or 'items'
        # For now, assume direct list of dicts or pandas handles it.
        # If it's nested, may need to adjust: data = json.load(f); df = pd.json_normalize(data, 'results')
        raw_data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        if isinstance(raw_data, dict) and 'results' in raw_data: # Common for APIs like RAWG
            df = pd.json_normalize(raw_data, 'results')
        elif isinstance(raw_data, list):
            df = pd.DataFrame(raw_data)
        else:
            raise ValueError("JSON structure not a list of records or recognized dict like {'results': [...]}")

    except ValueError as e:
        print(f"Error (New Releases): Could not decode or normalize JSON from {file_path}. Error: {e}")
        ALL_GAMES_DATA['new_releases'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['new_releases'] = False
        return
    except Exception as e:
        print(f"Error (New Releases): Failed to read or process {file_path}. Error: {e}")
        ALL_GAMES_DATA['new_releases'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['new_releases'] = False
        return

    if df.empty:
        ALL_GAMES_DATA['new_releases'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['new_releases'] = True # File existed, valid, but empty
        print("Info (New Releases): new_releases.json was empty or contained no results.")
        return

    # Standardize columns - Example for RAWG API like structure
    df.rename(columns={
        'name': 'title',
        'released': 'release_date_str', # RAWG uses 'released'
        'metacritic': 'metacritic_score',
        'description_raw': 'description', # If 'description_raw' is plain text description
        'slug': 'slug_for_rawg_link' # To construct link to RAWG page
        # 'platforms' is often a list of dicts, 'stores' similar
    }, inplace=True)

    # Ensure essential columns
    # 'link' will be constructed if 'slug_for_rawg_link' is available
    expected_cols = ['title', 'release_date_str', 'metacritic_score', 'description', 'slug_for_rawg_link', 'platforms', 'stores']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df['release_date'] = df['release_date_str'].apply(lambda x: parse_game_date(x, source_format="%Y-%m-%d"))

    # Extract platform names
    def get_platform_names(platforms_list):
        if isinstance(platforms_list, list):
            return ", ".join([p['platform']['name'] for p in platforms_list if 'platform' in p and 'name' in p['platform']])
        return "N/A"
    df['platform_names'] = df['platforms'].apply(get_platform_names)

    # Construct RAWG link
    df['link'] = df['slug_for_rawg_link'].apply(lambda x: f"https://rawg.io/games/{x}" if x else None)

    # Convert metacritic_score to numeric, coercing errors
    df['metacritic_score'] = pd.to_numeric(df['metacritic_score'], errors='coerce')


    df = df.sort_values(by='release_date', ascending=False, na_position='last')

    ALL_GAMES_DATA['new_releases'] = df
    DATA_LOADED_SUCCESSFULLY['new_releases'] = True
    print(f"Info (New Releases): Loaded {len(df)} new releases.")


def load_allkeyshop_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "allkeyshop.json"))

    if not file_exists(file_path):
        print(f"Warning (AllKeyShop): File not found at {file_path}")
        ALL_GAMES_DATA['allkeyshop'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['allkeyshop'] = False
        return

    try:
        df = pd.read_json(file_path)
    except ValueError as e:
        print(f"Error (AllKeyShop): Could not decode JSON from {file_path}. Error: {e}")
        ALL_GAMES_DATA['allkeyshop'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['allkeyshop'] = False
        return
    except Exception as e:
        print(f"Error (AllKeyShop): Failed to read or process {file_path}. Error: {e}")
        ALL_GAMES_DATA['allkeyshop'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['allkeyshop'] = False
        return

    if df.empty:
        ALL_GAMES_DATA['allkeyshop'] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY['allkeyshop'] = True
        print("Info (AllKeyShop): allkeyshop.json was empty.")
        return

    # Standardize columns for AllKeyShop data
    df.rename(columns={
        'url': 'link',
        'fetched_at': 'fetched_date_str'
    }, inplace=True)

    # Ensure essential columns exist
    expected_cols = ['title', 'link', 'current_price', 'original_price', 'discount_percentage', 
                     'store_name', 'deal_score', 'game_type', 'is_dlc', 'fetched_date_str', 'source']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # Parse dates
    df['fetched_date'] = df['fetched_date_str'].apply(lambda x: parse_game_date(x))
    
    # Ensure price columns are numeric
    df['current_price_numeric'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0.0)
    df['original_price_numeric'] = pd.to_numeric(df['original_price'], errors='coerce').fillna(0.0)
    df['discount_percentage_numeric'] = pd.to_numeric(df['discount_percentage'], errors='coerce').fillna(0.0)
    df['deal_score_numeric'] = pd.to_numeric(df['deal_score'], errors='coerce').fillna(0.0)

    # Calculate savings
    df['savings'] = df['original_price_numeric'] - df['current_price_numeric']
    df['savings'] = df['savings'].apply(lambda x: max(0, x))  # Ensure non-negative

    # Sort by fetched date (most recent first) and then by discount percentage
    df = df.sort_values(by=['fetched_date', 'discount_percentage_numeric'], 
                       ascending=[False, False], na_position='last')

    ALL_GAMES_DATA['allkeyshop'] = df
    DATA_LOADED_SUCCESSFULLY['allkeyshop'] = True
    print(f"Info (AllKeyShop): Loaded {len(df)} AllKeyShop games.")


def load_all_games_data():
    # This will call the individual loaders
    load_deals_data()
    load_bundles_data()
    load_giveaways_data()
    load_trending_data()
    load_new_releases_data()
    load_allkeyshop_data()
    print("Attempted to load all games data.")

# Load data on module import
load_all_games_data()

# --- Layout Rendering Functions ---
def format_display_date(dt_obj):
    if pd.isna(dt_obj) or dt_obj is None:
        return "N/A"
    return dt_obj.strftime('%Y-%m-%d') # Simpler date format for tables

def render_giveaways_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get('giveaways', False) or df.empty : # Check load status too
        return dbc.Alert("No giveaways data currently available or failed to load.", color="info", className="mt-3 alert-info")

    table_header = [
        html.Thead(html.Tr([
            html.Th("Title"),
            html.Th("Store"),
            html.Th("Published Date"),
            html.Th("Expires Date")
        ]))
    ]
    table_body_rows = []
    for _, row in df.head(50).iterrows(): # Limit rows for display performance initially
        table_body_rows.append(html.Tr([
            html.Td(html.A(row.get('title', 'N/A'), href=row.get('link'), target="_blank")),
            html.Td(row.get('store', 'N/A')),
            html.Td(format_display_date(row.get('published_date'))),
            html.Td(format_display_date(row.get('expiry_date')))
        ]))
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True, size="sm", color="dark", className="table-responsive mt-3")

def render_bundles_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get('bundles', False) or df.empty:
        return dbc.Alert("No game bundles data currently available or failed to load.", color="info", className="mt-3 alert-info")

    table_header = [
        html.Thead(html.Tr([
            html.Th("Title"),
            html.Th("Store"),
            html.Th("Price"),
            html.Th("Games Count"),
            html.Th("Expiry Date")
        ]))
    ]
    table_body_rows = []
    for _, row in df.head(50).iterrows():
        table_body_rows.append(html.Tr([
            html.Td(html.A(row.get('title', 'N/A'), href=row.get('link'), target="_blank")),
            html.Td(row.get('store', 'N/A')),
            html.Td(f"${row.get('price_numeric', 0.0):.2f}" if pd.notna(row.get('price_numeric')) else "N/A"),
            html.Td(row.get('game_count_numeric', 'N/A')),
            html.Td(format_display_date(row.get('expiry_date')))
        ]))
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True, size="sm", color="dark", className="table-responsive mt-3")

def render_deals_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get('deals', False) or df.empty:
        return dbc.Alert("No game deals data currently available or failed to load.", color="info", className="mt-3 alert-info")

    table_header = [
        html.Thead(html.Tr([
            html.Th("Title"),
            html.Th("Store"),
            html.Th("New Price"),
            html.Th("Old Price"),
            html.Th("Discount"),
            html.Th("Published")
        ]))
    ]
    table_body_rows = []
    for _, row in df.head(50).iterrows():
        discount_display = f"{int(row.get('discount_numeric', 0))}%" if pd.notna(row.get('discount_numeric')) else "N/A"
        table_body_rows.append(html.Tr([
            html.Td(html.A(row.get('title', 'N/A'), href=row.get('link'), target="_blank")),
            html.Td(row.get('store', 'N/A')),
            html.Td(f"${row.get('price_new_numeric', 0.0):.2f}" if pd.notna(row.get('price_new_numeric')) else "N/A"),
            html.Td(f"${row.get('price_old_numeric', 0.0):.2f}" if pd.notna(row.get('price_old_numeric')) else "N/A"),
            html.Td(discount_display),
            html.Td(format_display_date(row.get('published_date')))
        ]))
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True, size="sm", color="dark", className="table-responsive mt-3")

def render_trending_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get('trending', False) or df.empty:
        return dbc.Alert("No trending Itch.io data currently available or failed to load.", color="info", className="mt-3 alert-info")

    table_header = [
        html.Thead(html.Tr([
            html.Th("Title"),
            html.Th("Author"),
            html.Th("Price")
            # No reliable date for trending games, so not included
        ]))
    ]
    table_body_rows = []
    for _, row in df.head(50).iterrows():
        price_display = "Free" if row.get('price_numeric', -1) == 0.0 else (f"${row.get('price_numeric', 0.0):.2f}" if pd.notna(row.get('price_numeric')) else "N/A")
        table_body_rows.append(html.Tr([
            html.Td(html.A(row.get('title', 'N/A'), href=row.get('link'), target="_blank")),
            html.Td(row.get('author', 'N/A')),
            html.Td(price_display)
        ]))
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True, size="sm", color="dark", className="table-responsive mt-3")

def render_new_releases_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get('new_releases', False) or df.empty:
        return dbc.Alert("No new releases data currently available or failed to load.", color="info", className="mt-3 alert-info")

    accordion_items = []
    for index, row in df.head(30).iterrows(): # Limit for accordion display
        title_display = row.get('title', 'N/A')
        metacritic_score = row.get('metacritic_score', 'N/A')
        if pd.notna(metacritic_score):
            metacritic_display = str(int(metacritic_score))
            color = "success" if metacritic_score >= 75 else ("warning" if metacritic_score >= 50 else "danger")
            badge = dbc.Badge(metacritic_display, color=color, className="ms-2")
            title_display = html.Div([title_display, badge])

        accordion_items.append(
            dbc.AccordionItem(
                title=title_display,
                children=[
                    html.P(f"Release Date: {format_display_date(row.get('release_date'))}"),
                    html.P(f"Platforms: {row.get('platform_names', 'N/A')}"),
                    html.P(html.A("View on RAWG.io", href=row.get('link', '#'), target="_blank") if row.get('link') else "No RAWG link"),
                    html.Div([
                        html.H6("Description:", className="mt-2"),
                        dcc.Markdown(row.get('description', 'No description available.'), className="small", dangerously_allow_html=False, link_target="_blank")
                    ])
                ],
                item_id=f"nr-item-{index}"
            )
        )
    return dbc.Accordion(accordion_items, flush=True, always_open=False, active_item=None, className="mt-3")


def render_allkeyshop_new_releases_sub_tab(df):
    """Render AllKeyShop new releases sub-tab."""
    new_releases_df = df[df['game_type'] == 'new_release'] if not df.empty else pd.DataFrame()
    
    if not DATA_LOADED_SUCCESSFULLY.get('allkeyshop', False) or new_releases_df.empty:
        return dbc.Alert("No AllKeyShop new releases data currently available or failed to load.", color="info", className="mt-3 alert-info")

    # Summary cards
    summary_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{len(new_releases_df)}", className="card-title text-primary"),
                    html.P("New Releases", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"€{new_releases_df['current_price_numeric'].mean():.2f}", className="card-title text-success"),
                    html.P("Average Price", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{len(new_releases_df[new_releases_df['current_price_numeric'] == 0])}", className="card-title text-info"),
                    html.P("Free Games", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{len(new_releases_df[new_releases_df['is_dlc'] == True])}", className="card-title text-warning"),
                    html.P("DLC/Expansions", className="card-text")
                ])
            ])
        ], width=3)
    ], className="mb-4")

    # Games table
    table_header = [
        html.Thead(html.Tr([
            html.Th("Title"),
            html.Th("Store"),
            html.Th("Price"),
            html.Th("Type"),
            html.Th("Fetched")
        ]))
    ]
    
    table_body_rows = []
    for _, row in new_releases_df.head(50).iterrows():
        price_display = "FREE" if row.get('current_price_numeric', 0) == 0 else f"€{row.get('current_price_numeric', 0):.2f}"
        price_color = "success" if row.get('current_price_numeric', 0) == 0 else "primary"
        
        game_type = "DLC" if row.get('is_dlc') else "Game"
        type_color = "warning" if row.get('is_dlc') else "info"
        
        table_body_rows.append(html.Tr([
            html.Td(html.A(row.get('title', 'N/A'), href=row.get('link'), target="_blank")),
            html.Td(row.get('store_name', 'N/A')),
            html.Td(dbc.Badge(price_display, color=price_color)),
            html.Td(dbc.Badge(game_type, color=type_color)),
            html.Td(format_display_date(row.get('fetched_date')))
        ]))
    
    table_body = [html.Tbody(table_body_rows)]
    games_table = dbc.Table(table_header + table_body, bordered=True, hover=True, 
                           responsive=True, striped=True, size="sm", color="dark", 
                           className="table-responsive mt-3")
    
    return html.Div([summary_cards, games_table])


def render_allkeyshop_deals_sub_tab(df):
    """Render AllKeyShop deals/offers sub-tab."""
    deals_df = df[df['game_type'] == 'offer'] if not df.empty else pd.DataFrame()
    
    if not DATA_LOADED_SUCCESSFULLY.get('allkeyshop', False) or deals_df.empty:
        return dbc.Alert("No AllKeyShop deals data currently available or failed to load.", color="info", className="mt-3 alert-info")

    # Filter for deals with discounts
    discounted_deals = deals_df[deals_df['discount_percentage_numeric'] > 0]
    
    # Summary cards
    summary_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{len(deals_df)}", className="card-title text-primary"),
                    html.P("Total Deals", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{len(discounted_deals)}", className="card-title text-success"),
                    html.P("With Discounts", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{discounted_deals['discount_percentage_numeric'].mean():.0f}%", className="card-title text-warning"),
                    html.P("Avg Discount", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"€{discounted_deals['savings'].sum():.2f}", className="card-title text-info"),
                    html.P("Total Savings", className="card-text")
                ])
            ])
        ], width=3)
    ], className="mb-4")

    # Deals table
    table_header = [
        html.Thead(html.Tr([
            html.Th("Title"),
            html.Th("Store"),
            html.Th("Current Price"),
            html.Th("Original Price"),
            html.Th("Discount"),
            html.Th("Deal Score"),
            html.Th("Fetched")
        ]))
    ]
    
    table_body_rows = []
    for _, row in deals_df.head(50).iterrows():
        current_price = row.get('current_price_numeric', 0)
        original_price = row.get('original_price_numeric', 0)
        discount_pct = row.get('discount_percentage_numeric', 0)
        deal_score = row.get('deal_score_numeric', 0)
        
        # Price display
        current_price_display = "FREE" if current_price == 0 else f"€{current_price:.2f}"
        current_price_color = "success" if current_price == 0 else "primary"
        
        # Original price display
        original_price_display = f"€{original_price:.2f}" if original_price > 0 else "N/A"
        
        # Discount display
        discount_display = f"{discount_pct:.0f}%" if discount_pct > 0 else "N/A"
        discount_color = "success" if discount_pct >= 50 else ("warning" if discount_pct >= 25 else "secondary")
        
        # Deal score display
        deal_score_display = f"{deal_score:.0f}/100" if deal_score > 0 else "N/A"
        score_color = "success" if deal_score >= 80 else ("warning" if deal_score >= 60 else "secondary")
        
        table_body_rows.append(html.Tr([
            html.Td(html.A(row.get('title', 'N/A'), href=row.get('link'), target="_blank")),
            html.Td(row.get('store_name', 'N/A')),
            html.Td(dbc.Badge(current_price_display, color=current_price_color)),
            html.Td(original_price_display),
            html.Td(dbc.Badge(discount_display, color=discount_color) if discount_pct > 0 else "N/A"),
            html.Td(dbc.Badge(deal_score_display, color=score_color) if deal_score > 0 else "N/A"),
            html.Td(format_display_date(row.get('fetched_date')))
        ]))
    
    table_body = [html.Tbody(table_body_rows)]
    deals_table = dbc.Table(table_header + table_body, bordered=True, hover=True, 
                           responsive=True, striped=True, size="sm", color="dark", 
                           className="table-responsive mt-3")
    
    return html.Div([summary_cards, deals_table])

def render_games_tab():
    # Call load_all_games_data() here if not loading on import,
    # or ensure it's loaded before app starts. For now, assume it's loaded on import.

    # Check if any data was loaded at all to provide a general message
    if not any(DATA_LOADED_SUCCESSFULLY.values()):
         # Check if it's because files are missing vs other errors
        all_files_missing = True
        for key in ALL_GAMES_DATA:
            file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, f"{key}.json")) # Adjust filename if needed
            # Special handling for bundles, etc.
            if key == 'bundles': file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "bundles.json"))
            if key == 'trending': file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "itchio_trending.json"))
            if key == 'new_releases': file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_BASE_PATH, "new_releases.json"))

            if file_exists(file_path): # A bit simplified, assumes direct mapping for check
                all_files_missing = False
                break
        if all_files_missing:
            return html.Div([
                html.H3("Juegos", className="mb-3"),
                dbc.Alert("Todos los archivos de datos de juegos están ausentes. Por favor, ejecute los ETLs correspondientes.", color="danger", className="alert-danger")
            ])
        else:
            return html.Div([
                html.H3("Juegos", className="mb-3"),
                dbc.Alert("No se pudieron cargar los datos de los juegos o no hay datos disponibles. Verifique la consola para más detalles.", color="warning", className="alert-warning")
            ])


    return html.Div([
        html.H3("Juegos", className="mb-3"),
        dbc.Tabs(id="games-sub-tabs", children=[
            dbc.Tab(label="Juegos Gratuitos", tab_id="subtab-giveaways", children=render_giveaways_sub_tab(ALL_GAMES_DATA['giveaways'])),
            dbc.Tab(label="Paquetes de Juegos", tab_id="subtab-bundles", children=render_bundles_sub_tab(ALL_GAMES_DATA['bundles'])),
            dbc.Tab(label="Ofertas de Juegos", tab_id="subtab-deals", children=render_deals_sub_tab(ALL_GAMES_DATA['deals'])),
            dbc.Tab(label="Tendencias Itch.io", tab_id="subtab-trending", children=render_trending_sub_tab(ALL_GAMES_DATA['trending'])),
            dbc.Tab(label="Nuevos Lanzamientos", tab_id="subtab-new-releases", children=render_new_releases_sub_tab(ALL_GAMES_DATA['new_releases'])),
            dbc.Tab(label="AllKeyShop - Nuevos", tab_id="subtab-allkeyshop-new", children=render_allkeyshop_new_releases_sub_tab(ALL_GAMES_DATA['allkeyshop'])),
            dbc.Tab(label="AllKeyShop - Ofertas", tab_id="subtab-allkeyshop-deals", children=render_allkeyshop_deals_sub_tab(ALL_GAMES_DATA['allkeyshop'])),
        ])
    ])

if __name__ == '__main__':
    # For testing, call load_all_games_data directly.
    # This ensures data is loaded before app runs for standalone test.
    # In actual app, this will be called at import or by main app.
    if not DATA_LOADED_SUCCESSFULLY['deals']: load_deals_data()
    if not DATA_LOADED_SUCCESSFULLY['bundles']: load_bundles_data()
    if not DATA_LOADED_SUCCESSFULLY['giveaways']: load_giveaways_data()
    if not DATA_LOADED_SUCCESSFULLY['trending']: load_trending_data()
    if not DATA_LOADED_SUCCESSFULLY['new_releases']: load_new_releases_data()
    if not DATA_LOADED_SUCCESSFULLY['allkeyshop']: load_allkeyshop_data()

    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_games_tab(), fluid=True, className="py-4")

    # Summary of loaded data for testing
    for key, df in ALL_GAMES_DATA.items():
        status = "cargado" if DATA_LOADED_SUCCESSFULLY[key] else "no cargado o vacío"
        print(f"Juegos Test: Datos para '{key}' {status} - {len(df)} registros.")
        if not DATA_LOADED_SUCCESSFULLY[key] and df.empty:
             # More specific path based on how individual loaders will be implemented
            filename_map = {
                'deals': 'deals.json', 'bundles': 'bundles.json/humblebundles.json',
                'giveaways': 'giveaways.json', 'trending': 'itchio_trending.json',
                'new_releases': 'new_releases.json', 'allkeyshop': 'allkeyshop.json'
            }
            print(f"  Verifique si {DATA_BASE_PATH}{filename_map.get(key, key+'.json')} existe y es válido.")

    app_test.run_server(debug=True, port=8057)
