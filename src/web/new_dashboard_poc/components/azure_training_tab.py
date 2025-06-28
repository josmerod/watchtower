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
from utils import get_data_path, file_exists, dir_exists


# --- Constants ---
AZURE_TRAINING_DATA_PATH = get_data_path("courses", "azure_training_updates.json") # Relative to this file
AZURE_TRAINING_POSTS = pd.DataFrame() # Store posts here

# --- Data Loading ---
def parse_azure_training_date(date_str):
    """Parses Azure training date strings into datetime objects."""
    if not date_str:
        return None
    # Reusing the same parsing logic as AWS, assuming similar date formats might appear.
    # Primary format from Azure blogs is often ISO 8601.
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError:
        try: # Example: "Mar 8, 2024" or "March 8, 2024"
            dt = datetime.strptime(str(date_str), "%b %d, %Y")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                dt = datetime.strptime(str(date_str), "%B %d, %Y")
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                try: # Fallback for YYYY-MM-DD
                    dt = datetime.strptime(str(date_str), "%Y-%m-%d")
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    print(f"Warning: Could not parse Azure training date string: {date_str}")
                    return None

def load_azure_training_posts():
    global AZURE_TRAINING_POSTS

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    actual_data_path = os.path.normpath(os.path.join(current_script_dir, AZURE_TRAINING_DATA_PATH))

    raw_posts = []
    if file_exists(actual_data_path):
        try:
            with open(actual_data_path, 'r', encoding='utf-8') as f:
                raw_posts = json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {actual_data_path}")
            raw_posts = []
        except Exception as e:
            print(f"Error reading file {actual_data_path}: {e}")
            raw_posts = []
    else:
        print(f"Warning: Azure Training data file not found at {actual_data_path}")

    if not raw_posts or not isinstance(raw_posts, list):
        AZURE_TRAINING_POSTS = pd.DataFrame()
        print("Azure Training: No raw posts loaded or data is not in list format.")
        return

    processed_posts_data = []
    for post in raw_posts:
        title = post.get('title', 'No Title')
        link = post.get('link', post.get('url', '#'))
        published_date_str = post.get('published', post.get('date', post.get('pubDate')))
        parsed_date = parse_azure_training_date(published_date_str)

        categories_raw = post.get('categories', post.get('tags', []))
        if isinstance(categories_raw, str):
            categories_list = [cat.strip() for cat in categories_raw.split(',')]
        elif isinstance(categories_raw, list):
            categories_list = [str(cat) for cat in categories_raw]
        else:
            categories_list = []
        categories_str = ", ".join(categories_list) if categories_list else "N/A"

        summary = post.get('summary', post.get('description', ''))

        processed_posts_data.append({
            'title': title,
            'link': link,
            'published_date': parsed_date,
            'categories': categories_str,
            'summary': summary
        })

    if not processed_posts_data:
        AZURE_TRAINING_POSTS = pd.DataFrame()
        print("Azure Training: No posts were processed.")
        return

    df = pd.DataFrame(processed_posts_data)
    df = df[df['published_date'].notna()]
    df = df.sort_values(by='published_date', ascending=False)
    AZURE_TRAINING_POSTS = df
    print(f"Azure Training: Loaded and processed {len(AZURE_TRAINING_POSTS)} posts.")

load_azure_training_posts()

# --- Layout Rendering ---
def render_azure_training_tab():
    if AZURE_TRAINING_POSTS.empty:
        return html.Div([
            html.H3("Azure Training & Certification Updates (Microsoft Learn)", className="mb-3"),
            dbc.Alert("No Azure Training blog posts found or data is unavailable.", color="info")
        ])

    accordion_items = []
    for index, row in AZURE_TRAINING_POSTS.iterrows():
        accordion_items.append(
            dbc.AccordionItem(
                title=html.Div([
                    html.Strong(row['title']),
                    html.Div(
                        f"Published: {row['published_date'].strftime('%Y-%m-%d %H:%M UTC') if pd.notna(row['published_date']) else 'N/A'} | Categories: {row['categories']}",
                        className="small text-muted"
                    )
                ]),
                children=[
                    html.P(row['summary'] if row['summary'] else "No summary available.", className="mb-2"),
                    dcc.Link("Read More", href=row['link'], target="_blank", className="btn btn-sm btn-outline-primary")
                ],
                item_id=f"azure-item-{index}" # Unique ID for each item
            )
        )

    return html.Div([
        html.H3("Azure Training & Certification Updates (Microsoft Learn)", className="mb-3"),
        html.P(f"Displaying {len(AZURE_TRAINING_POSTS)} posts (newest first).", className="text-muted mb-3"),
        dbc.Accordion(accordion_items, flush=True, always_open=False, active_item=None)
    ])

if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_azure_training_tab(), fluid=True, className="py-4")
    print(f"Azure Training Test: {len(AZURE_TRAINING_POSTS)} posts loaded for display.")
    if AZURE_TRAINING_POSTS.empty:
        print(f"Azure Training Test: Data file might be missing at {AZURE_TRAINING_DATA_PATH} or no posts processed.")
    app_test.run_server(debug=True, port=8056)
