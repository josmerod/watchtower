import os
import json
import pandas as pd # Using pandas for easier data handling
from datetime import datetime, timezone
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# --- Constants ---
AWS_TRAINING_DATA_PATH = "../../../data/courses/aws_training_updates.json" # Relative to this file
AWS_TRAINING_POSTS = pd.DataFrame() # Store posts here

# --- Data Loading ---
def parse_aws_training_date(date_str):
    """Parses AWS training date strings into datetime objects."""
    if not date_str:
        return None
    try:
        # Common formats: "YYYY-MM-DD", "Month DD, YYYY", or ISO with time
        # Try ISO format first, as it's more specific
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError:
        try:
            # Example: "Mar 8, 2024" or "March 8, 2024"
            dt = datetime.strptime(str(date_str), "%b %d, %Y")
            return dt.replace(tzinfo=timezone.utc) # Assume UTC if no timezone info
        except ValueError:
            try:
                dt = datetime.strptime(str(date_str), "%B %d, %Y")
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                try: # Fallback for YYYY-MM-DD
                    dt = datetime.strptime(str(date_str), "%Y-%m-%d")
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    print(f"Warning: Could not parse AWS training date string: {date_str}")
                    return None

def load_aws_training_posts():
    global AWS_TRAINING_POSTS

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    actual_data_path = os.path.normpath(os.path.join(current_script_dir, AWS_TRAINING_DATA_PATH))

    raw_posts = []
    if os.path.exists(actual_data_path):
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
        print(f"Warning: AWS Training data file not found at {actual_data_path}")

    if not raw_posts or not isinstance(raw_posts, list):
        AWS_TRAINING_POSTS = pd.DataFrame()
        print("AWS Training: No raw posts loaded or data is not in list format.")
        return

    processed_posts_data = []
    for post in raw_posts:
        # Assuming keys from a typical blog/news structure: title, link, published, categories, summary
        title = post.get('title', 'No Title')
        link = post.get('link', post.get('url', '#')) # Common variations for URL
        published_date_str = post.get('published', post.get('date', post.get('pubDate'))) # Common date fields
        parsed_date = parse_aws_training_date(published_date_str)

        # Categories might be a list or a string. Standardize.
        categories_raw = post.get('categories', post.get('tags', [])) # 'categories' or 'tags'
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
        AWS_TRAINING_POSTS = pd.DataFrame()
        print("AWS Training: No posts were processed (list remained empty).")
        return

    df = pd.DataFrame(processed_posts_data)
    df = df[df['published_date'].notna()] # Remove rows where date parsing failed
    df = df.sort_values(by='published_date', ascending=False)
    AWS_TRAINING_POSTS = df
    print(f"AWS Training: Loaded and processed {len(AWS_TRAINING_POSTS)} posts.")

# Load data on module import
load_aws_training_posts()

# --- Layout Rendering ---
def render_aws_training_tab():
    if AWS_TRAINING_POSTS.empty:
        return html.Div([
            html.H3("AWS Training & Certification Blog Updates", className="mb-3"),
            dbc.Alert("No AWS Training blog posts found or data is unavailable.", color="info")
        ])

    accordion_items = []
    for index, row in AWS_TRAINING_POSTS.iterrows():
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
                item_id=f"aws-item-{index}" # Unique ID for each item
            )
        )

    return html.Div([
        html.H3("AWS Training & Certification Blog Updates", className="mb-3"),
        html.P(f"Displaying {len(AWS_TRAINING_POSTS)} posts (newest first).", className="text-muted mb-3"),
        dbc.Accordion(accordion_items, flush=True, always_open=False, active_item=None) # Start with all items collapsed
    ])

if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_aws_training_tab(), fluid=True, className="py-4")
    print(f"AWS Training Test: {len(AWS_TRAINING_POSTS)} posts loaded for display.")
    if AWS_TRAINING_POSTS.empty:
        print(f"AWS Training Test: Data file might be missing at {AWS_TRAINING_DATA_PATH} or no posts processed.")
    app_test.run_server(debug=True, port=8055)
