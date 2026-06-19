import json
import os
import re  # For parsing prices
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dcc, html

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path, log_missing_file

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# --- Constants ---
DATA_BASE_PATH = get_data_path("games", "")  # Relative to this file

# NEW: Repository-based loading (SOLID Pattern)
class GamesRepository(BaseRepository[dict[str, Any]]):
    """Repository for games data."""

    def __init__(self, data_path: str):
        """Initialize games repository.

        Args:
            data_path: Path to games data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> dict[str, Any]:
        """Transform JSON data into games data structure.

        Args:
            raw_data: Raw JSON data

        Returns:
            Games data dictionary
        """
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, list):
            return {"results": raw_data}
        else:
            return {}

# Create singleton instances for each games data source
deals_repo = GamesRepository(get_data_path("games", "deals.json"))
bundles_repo = GamesRepository(get_data_path("games", "bundles.json"))
trending_repo = GamesRepository(get_data_path("games", "itchio_trending.json"))
ALL_GAMES_DATA = {
    "deals": pd.DataFrame(),
    "bundles": pd.DataFrame(),
    "new_releases": pd.DataFrame(),
    "metacritic": pd.DataFrame(),
}
DATA_LOADED_SUCCESSFULLY = {key: False for key in ALL_GAMES_DATA}


# --- Date Parsing Utility ---
def parse_game_date(date_str, source_format=None):
    if pd.isna(date_str) or not date_str:
        return None

    # Try ISO format first (common)
    try:
        # Handle 'Z' for UTC and potential timezone offsets
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass  # Continue to other formats

    # Try specific format if provided
    if source_format:
        try:
            dt = datetime.strptime(str(date_str), source_format)
            return dt.replace(tzinfo=timezone.utc)  # Assume UTC if naive
        except ValueError:
            pass

    # Fallback formats (add more as identified from data)
    common_formats = [
        "%Y-%m-%d",  # YYYY-MM-DD
        "%d/%m/%Y",  # DD/MM/YYYY
        "%m/%d/%Y",  # MM/DD/YYYY
        "%b %d, %Y",  # Jan 01, 2023
        "%B %d, %Y",  # January 01, 2023
        "%Y-%m-%dT%H:%M:%S",  # ISO without timezone part
    ]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return dt.replace(tzinfo=timezone.utc)  # Assume UTC
        except ValueError:
            continue

    # Try epoch timestamp (seconds)
    try:
        timestamp = float(date_str)
        if timestamp > 10000000000:  # Likely milliseconds, convert to seconds
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except ValueError:
        pass

    print(f"Warning: Could not parse game date: {date_str} with known formats.")
    return None


# --- Price Parsing Utility ---
def parse_price(price_str):
    if pd.isna(price_str) or price_str is None or str(price_str).strip() == "":
        return 0.0
    if isinstance(price_str, (int, float)):  # Already a number
        return float(price_str)

    s_price = str(price_str).strip().lower()
    if s_price == "free" or "gratis" in s_price:
        return 0.0

    # Remove currency symbols and other non-numeric characters (except decimal point)
    # Handles formats like "$19.99", "€19,99", "19.99 USD"
    cleaned_price = re.sub(r"[^\d\.,]", "", s_price)

    # Standardize decimal separator to '.'
    if "," in cleaned_price and "." in cleaned_price:  # e.g. 1.234,56
        cleaned_price = cleaned_price.replace(".", "")  # Remove thousand separator
        cleaned_price = cleaned_price.replace(",", ".")
    elif "," in cleaned_price:  # e.g. 1234,56 or 1,23 (treat as decimal if only one)
        # Heuristic: if it's a single comma, assume it's decimal
        if cleaned_price.count(",") == 1 and len(cleaned_price.split(",")[-1]) == 2:
            cleaned_price = cleaned_price.replace(",", ".")
        else:  # Multiple commas or not a typical decimal format, remove them
            cleaned_price = cleaned_price.replace(",", "")

    try:
        return float(cleaned_price)
    except ValueError:
        # Return 0.0 for invalid prices instead of None
        return 0.0


# --- Data Loading Functions (using repositories) ---
# OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
# def load_deals_data():
#     global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
#     file_path = get_data_path("games", "deals.json")
#
#     if not file_exists(file_path):
#         print(f"Warning (Deals): File not found at {file_path}")
#         ALL_GAMES_DATA["deals"] = pd.DataFrame()
#         DATA_LOADED_SUCCESSFULLY["deals"] = False  # Explicitly set to false
#         return
#
#     try:
#         df = pd.read_json(file_path)
#     except ValueError as e:  # Handles JSON decoding errors in pandas
#         print(f"Error (Deals): Could not decode JSON from {file_path}. Error: {e}")
#         ALL_GAMES_DATA["deals"] = pd.DataFrame()
#         DATA_LOADED_SUCCESSFULLY["deals"] = False
#         return
#     except Exception as e:
#         print(f"Error (Deals): Failed to read or process {file_path}. Error: {e}")
#         ALL_GAMES_DATA["deals"] = pd.DataFrame()
#         DATA_LOADED_SUCCESSFULLY["deals"] = False
#         return
#
#     if df.empty:
#         ALL_GAMES_DATA["deals"] = pd.DataFrame()
#         DATA_LOADED_SUCCESSFULLY["deals"] = True  # File existed and was valid JSON, but empty
#         print("Info (Deals): deals.json was empty or resulted in an empty DataFrame.")
#         return
#
#     # Standardize columns - adjust based on actual keys in deals.json
#     # Common keys might be: 'title', 'url'/'link', 'store', 'newPrice', 'oldPrice', 'discount', 'addedDate'
#     df.rename(
#         columns={
#             "url": "link",  # Assuming 'url' is the direct link to the deal
#             "newPrice": "price_new",
#             "oldPrice": "price_old",
#             "addedDate": "published_date_str",  # Or a similar date field
#             "name": "title",  # If 'name' is used for title
#         },
#         inplace=True,
#     )
#
#     # Ensure essential columns exist, fill with None if not
#     expected_cols = [
#         "title",
#         "link",
#         "store",
#         "price_new",
#         "price_old",
#         "discount",
#         "published_date_str",
#     ]
#     for col in expected_cols:
#         if col not in df.columns:
#             df[col] = None
#
#     df["published_date"] = df["published_date_str"].apply(lambda x: parse_game_date(x))  # Assuming a date field exists
#     df["price_new_numeric"] = df["price_new"].apply(parse_price)
#     df["price_old_numeric"] = df["price_old"].apply(parse_price)
#
#     # Ensure discount is numeric if it's like "75%" -> 75.0 or 0.75
#     if "discount" in df.columns:
#         df["discount_numeric"] = df["discount"].astype(str).str.extract(r"(\d+)").astype(float)
#     else:
#         df["discount_numeric"] = None
#
#     df = df.sort_values(by="published_date", ascending=False, na_position="last")
#
#     ALL_GAMES_DATA["deals"] = df
#     DATA_LOADED_SUCCESSFULLY["deals"] = True
#     print(f"Info (Deals): Loaded {len(df)} deals.")


def load_deals_data():
    """Load deals data using repository pattern (NEW)."""
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY

    try:
        data = deals_repo.get()

        if not data:
            ALL_GAMES_DATA["deals"] = pd.DataFrame()
            DATA_LOADED_SUCCESSFULLY["deals"] = False
            return

        # Convert to DataFrame
        if isinstance(data, dict) and "results" in data:
            df = pd.json_normalize(data, "results")
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])

        if df.empty:
            ALL_GAMES_DATA["deals"] = pd.DataFrame()
            DATA_LOADED_SUCCESSFULLY["deals"] = True
            return

        # Standardize columns
        df.rename(
            columns={
                "url": "link",
                "newPrice": "price_new",
                "oldPrice": "price_old",
                "addedDate": "published_date_str",
                "name": "title",
            },
            inplace=True,
        )

        # Ensure essential columns exist
        expected_cols = [
            "title",
            "link",
            "store",
            "price_new",
            "price_old",
            "discount",
            "published_date_str",
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None

        df["published_date"] = df["published_date_str"].apply(lambda x: parse_game_date(x))
        df["price_new_numeric"] = df["price_new"].apply(parse_price)
        df["price_old_numeric"] = df["price_old"].apply(parse_price)

        if "discount" in df.columns:
            df["discount_numeric"] = df["discount"].astype(str).str.extract(r"(\d+)").astype(float)
        else:
            df["discount_numeric"] = None

        df = df.sort_values(by="published_date", ascending=False, na_position="last")

        ALL_GAMES_DATA["deals"] = df
        DATA_LOADED_SUCCESSFULLY["deals"] = True
        print(f"Info (Deals): Loaded {len(df)} deals.")

    except Exception as e:
        print(f"Error (Deals): {e}")
        ALL_GAMES_DATA["deals"] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY["deals"] = False


def load_bundles_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_paths_with_store = [
        (
            get_data_path("games", "bundles.json"),
            "Various/Mixed",
        ),  # Default store if not specified in data
        (get_data_path("games", "humblebundles.json"), "Humble Bundle"),
    ]

    all_bundles_dfs = []
    any_file_processed_successfully = False

    for file_path, store_name_default in file_paths_with_store:
        if not file_exists(file_path):
            print(f"Warning (Bundles): File not found at {file_path}")
            continue  # Skip this file

        try:
            df = pd.read_json(file_path)
            if df.empty:
                print(f"Info (Bundles): File {file_path} was empty.")
                any_file_processed_successfully = True  # File existed and was valid
                continue

            # Standardize columns - adjust based on actual keys
            # Common keys: 'title', 'url'/'link', 'price', 'game_count', 'store', 'endDate'/'expiryDate'
            df.rename(
                columns={
                    "url": "link",
                    "endDate": "expiry_date_str",
                    "expiryDate": "expiry_date_str",  # another common name
                    "name": "title",
                    "humbleLink": "link",  # Specific to humblebundles.json
                    "humbleTitle": "title",  # Specific to humblebundles.json
                },
                inplace=True,
            )

            # Add store if not present
            if "store" not in df.columns:
                df["store"] = store_name_default
            else:  # Fill NaN stores with default if column exists but value is missing
                df["store"].fillna(store_name_default, inplace=True)

            # Ensure essential columns
            expected_cols = [
                "title",
                "link",
                "store",
                "price",
                "game_count",
                "expiry_date_str",
            ]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None  # Add missing columns with None

            df["expiry_date"] = df["expiry_date_str"].apply(lambda x: parse_game_date(x))
            df["price_numeric"] = df["price"].apply(parse_price)

            # 'game_count' might need extraction if it's like "10 games"
            if "game_count" in df.columns and df["game_count"].dtype == "object":
                df["game_count_numeric"] = df["game_count"].astype(str).str.extract(r"(\d+)").astype(float).fillna(0).astype(int)
            elif "game_count" in df.columns:  # Already numeric
                df["game_count_numeric"] = pd.to_numeric(df["game_count"], errors="coerce").fillna(0).astype(int)
            else:
                df["game_count_numeric"] = 0

            all_bundles_dfs.append(df)
            any_file_processed_successfully = True
            print(f"Info (Bundles): Loaded {len(df)} bundles from {os.path.basename(file_path)}.")

        except ValueError as e:
            print(f"Error (Bundles): Could not decode JSON from {file_path}. Error: {e}")
        except Exception as e:
            print(f"Error (Bundles): Failed to read or process {file_path}. Error: {e}")

    if not all_bundles_dfs:
        ALL_GAMES_DATA["bundles"] = pd.DataFrame()
        # If any file was processed (even if empty), consider it a "successful" load attempt for this category
        DATA_LOADED_SUCCESSFULLY["bundles"] = any_file_processed_successfully
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
    combined_df = combined_df.sort_values(by="expiry_date", ascending=False, na_position="last")

    ALL_GAMES_DATA["bundles"] = combined_df
    DATA_LOADED_SUCCESSFULLY["bundles"] = True
    print(f"Info (Bundles): Combined total of {len(combined_df)} bundles.")





def load_trending_data():
    global ALL_GAMES_DATA, DATA_LOADED_SUCCESSFULLY
    file_path = get_data_path("games", "itchio_trending.json")

    if not file_exists(file_path):
        print(f"Warning (Trending): File not found at {file_path}")
        ALL_GAMES_DATA["trending"] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY["trending"] = False
        return

    try:
        df = pd.read_json(file_path)
    except ValueError as e:
        print(f"Error (Trending): Could not decode JSON from {file_path}. Error: {e}")
        ALL_GAMES_DATA["trending"] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY["trending"] = False
        return
    except Exception as e:
        print(f"Error (Trending): Failed to read or process {file_path}. Error: {e}")
        ALL_GAMES_DATA["trending"] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY["trending"] = False
        return

    if df.empty:
        ALL_GAMES_DATA["trending"] = pd.DataFrame()
        DATA_LOADED_SUCCESSFULLY["trending"] = True  # File existed, valid, but empty
        print("Info (Trending): itchio_trending.json was empty.")
        return

    # Standardize columns: 'title', 'link', 'author', 'price', 'published_date' (if available)
    # Itch.io data might have 'name' for title, 'user.name' for author, 'price_value', 'url'
    df.rename(
        columns={
            "name": "title",
            "url": "link",
            "user.name": "author",  # If author is nested
            "price_value": "price",  # If price is 'price_value'
            # 'published_at' or similar for date, if available
        },
        inplace=True,
    )

    # If author is in a nested 'user' dict and not flattened by pd.read_json's normalize
    if "user" in df.columns and isinstance(df["user"].iloc[0], dict) and "author" not in df.columns:
        df["author"] = df["user"].apply(lambda x: x.get("name") if isinstance(x, dict) else None)

    expected_cols = [
        "title",
        "link",
        "author",
        "price",
    ]  # 'published_date' might not exist for trending
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df["price_numeric"] = df["price"].apply(parse_price)

    # Itch.io trending might not have a reliable "published_date" for the game itself,
    # it's more about current popularity. If there's a 'crawled_date' or similar,
    # it could be used, but it's not the game's release/publish date.
    # For now, we won't sort by date unless a suitable field is identified.
    # If sorting is desired, one might sort by rank if available, or just display as is.

    ALL_GAMES_DATA["trending"] = df
    DATA_LOADED_SUCCESSFULLY["trending"] = True
    print(f"Info (Trending): Loaded {len(df)} trending Itch.io games.")





def load_all_games_data():
    # This will call the individual loaders
    load_deals_data()
    load_bundles_data()
    load_trending_data()
    # load_giveaways_data() # Removed
    # load_new_releases_data() # Removed
    # Optional: Metacritic reviews from RSS
    try:
        file_path = get_data_path("games", "metacritic_latest.json")
        if file_exists(file_path):
            df = pd.read_json(file_path)
            # Standardize minimal columns
            df.rename(
                columns={
                    "link": "url",
                    "published": "published_date_str",
                },
                inplace=True,
            )
            if "published_date_str" not in df.columns:
                df["published_date_str"] = None
            df["published_date"] = df["published_date_str"].apply(lambda x: parse_game_date(x))
            ALL_GAMES_DATA["metacritic"] = df
            DATA_LOADED_SUCCESSFULLY["metacritic"] = True
        else:
            DATA_LOADED_SUCCESSFULLY["metacritic"] = False
    except Exception as e:
        print(f"Error (Metacritic): {e}")
        DATA_LOADED_SUCCESSFULLY["metacritic"] = False
    # GiantBomb games/reviews removed
    print("Attempted to load all games data.")

    print("Attempted to load all games data.")


# Load data dynamically instead of at import time
# load_all_games_data()


# --- Layout Rendering Functions ---
def format_display_date(dt_obj):
    if pd.isna(dt_obj) or dt_obj is None:
        return "N/A"
    return dt_obj.strftime("%Y-%m-%d")  # Simpler date format for tables





def render_bundles_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get("bundles", False) or df.empty:
        return dbc.Alert(
            "No game bundles data currently available or failed to load.",
            color="info",
            className="mt-3 alert-info",
        )

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Store"),
                    html.Th("Price"),
                    html.Th("Games Count"),
                    html.Th("Expiry Date"),
                ]
            )
        )
    ]
    table_body_rows = []
    for _, row in df.head(50).iterrows():
        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.A(
                            row.get("title", "N/A"),
                            href=row.get("link"),
                            target="_blank",
                        )
                    ),
                    html.Td(row.get("store", "N/A")),
                    html.Td(f"${row.get('price_numeric', 0.0):.2f}" if pd.notna(row.get("price_numeric")) else "N/A"),
                    html.Td(row.get("game_count_numeric", "N/A")),
                    html.Td(format_display_date(row.get("expiry_date"))),
                ]
            )
        )
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mt-3",
    )


def render_deals_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get("deals", False) or df.empty:
        return dbc.Alert(
            "No game deals data currently available or failed to load.",
            color="info",
            className="mt-3 alert-info",
        )

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Store"),
                    html.Th("New Price"),
                    html.Th("Old Price"),
                    html.Th("Discount"),
                    html.Th("Published"),
                ]
            )
        )
    ]
    table_body_rows = []
    for _, row in df.head(50).iterrows():
        discount_display = f"{int(row.get('discount_numeric', 0))}%" if pd.notna(row.get("discount_numeric")) else "N/A"
        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.A(
                            row.get("title", "N/A"),
                            href=row.get("link"),
                            target="_blank",
                        )
                    ),
                    html.Td(row.get("store", "N/A")),
                    html.Td(f"${row.get('price_new_numeric', 0.0):.2f}" if pd.notna(row.get("price_new_numeric")) else "N/A"),
                    html.Td(f"${row.get('price_old_numeric', 0.0):.2f}" if pd.notna(row.get("price_old_numeric")) else "N/A"),
                    html.Td(discount_display),
                    html.Td(format_display_date(row.get("published_date"))),
                ]
            )
        )
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mt-3",
    )


def render_trending_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get("trending", False) or df.empty:
        return dbc.Alert(
            "No trending Itch.io data currently available or failed to load.",
            color="info",
            className="mt-3 alert-info",
        )

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Author"),
                    html.Th("Price"),
                    # No reliable date for trending games, so not included
                ]
            )
        )
    ]
    table_body_rows = []
    for _, row in df.head(50).iterrows():
        price_display = "Free" if row.get("price_numeric", -1) == 0.0 else (f"${row.get('price_numeric', 0.0):.2f}" if pd.notna(row.get("price_numeric")) else "N/A")
        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.A(
                            row.get("title", "N/A"),
                            href=row.get("link"),
                            target="_blank",
                        )
                    ),
                    html.Td(row.get("author", "N/A")),
                    html.Td(price_display),
                ]
            )
        )
    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mt-3",
    )


def render_metacritic_sub_tab(df):
    if not DATA_LOADED_SUCCESSFULLY.get("metacritic", False) or df.empty:
        return dbc.Alert(
            "No Metacritic reviews available or failed to load.",
            color="info",
            className="mt-3 alert-info",
        )

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Score"),
                    html.Th("Published"),
                ]
            )
        )
    ]
    rows = []
    for _, row in df.head(50).iterrows():
        title = row.get("title", "N/A")
        url = row.get("url") or row.get("link")
        score = row.get("metacritic_score", "N/A")
        published = row.get("published_date") or row.get("published")
        rows.append(
            html.Tr(
                [
                    html.Td(html.A(title, href=url, target="_blank") if url else title),
                    html.Td(str(int(score)) if pd.notna(score) else "N/A"),
                    html.Td(format_display_date(published)),
                ]
            )
        )
    return dbc.Table(
        [table_header[0], html.Tbody(rows)],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mt-3",
    )





def render_games_tab():
    # Load fresh data each time
    load_all_games_data()

    # Check if any data was loaded at all to provide a general message
    if not any(DATA_LOADED_SUCCESSFULLY.values()):
        # Check if it's because files are missing vs other errors
        all_files_missing = True
        for key in ALL_GAMES_DATA:
            file_path = get_data_path("games", f"{key}.json")  # Adjust filename if needed
            # Special handling for bundles, etc.
            if key == "bundles":
                file_path = get_data_path("games", "bundles.json")
            if key == "trending":
                file_path = get_data_path("games", "itchio_trending.json")
            if key == "new_releases":
                file_path = get_data_path("games", "new_releases.json")
            if key == "metacritic":
                file_path = get_data_path("games", "metacritic_latest.json")

            if file_exists(file_path):  # A bit simplified, assumes direct mapping for check
                all_files_missing = False
                break
        if all_files_missing:
            return html.Div(
                [
                    html.H3("Games", className="mb-3"),
                    dbc.Alert(
                        "All game data files are missing. Please run the corresponding ETLs.",
                        color="danger",
                        className="alert-danger",
                    ),
                ]
            )
        else:
            return html.Div(
                [
                    html.H3("Games", className="mb-3"),
                    dbc.Alert(
                        "Could not load game data or no data is available. Check the console for more details.",
                        color="warning",
                        className="alert-warning",
                    ),
                ]
            )

    return html.Div(
        [
            html.H3("Games", className="mb-3"),
            dbc.Tabs(
                id="games-sub-tabs",
                children=[
                    dbc.Tab(
                        label="Reviews (Metacritic)",
                        tab_id="subtab-metacritic",
                        children=render_metacritic_sub_tab(ALL_GAMES_DATA["metacritic"]),
                    ),

                ],
            ),
        ]
    )


if __name__ == "__main__":
    # For testing, call load_all_games_data directly.
    # This ensures data is loaded before app runs for standalone test.
    # In actual app, this will be called at import or by main app.
    if not DATA_LOADED_SUCCESSFULLY["deals"]:
        load_deals_data()
    if not DATA_LOADED_SUCCESSFULLY["bundles"]:
        load_bundles_data()
    if not DATA_LOADED_SUCCESSFULLY["giveaways"]:
        load_giveaways_data()
    if not DATA_LOADED_SUCCESSFULLY["trending"]:
        load_trending_data()
    if not DATA_LOADED_SUCCESSFULLY["new_releases"]:
        load_new_releases_data()

    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_games_tab(), fluid=True, className="py-4")

    # Summary of loaded data for testing
    for key, df in ALL_GAMES_DATA.items():
        status = "loaded" if DATA_LOADED_SUCCESSFULLY[key] else "not loaded or empty"
        print(f"Games Test: Data for '{key}' {status} - {len(df)} records.")
        if not DATA_LOADED_SUCCESSFULLY[key] and df.empty:
            # More specific path based on how individual loaders will be implemented
            filename_map = {
                "deals": "deals.json",
                "bundles": "bundles.json/humblebundles.json",
                "giveaways": "giveaways.json",
                "trending": "itchio_trending.json",
                "new_releases": "new_releases.json",
            }
            print(f"  Check if {DATA_BASE_PATH}{filename_map.get(key, key + '.json')} exists and is valid.")

    app_test.run_server(debug=True, port=8057)
