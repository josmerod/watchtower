import os
import json
import pandas as pd # Using pandas for easier data handling and date parsing
from datetime import datetime, timezone
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# --- Constants ---
GCP_BLOG_DATA_PATH = "../../../data/news/google_cloud_blog.json" # Relative to this file
KEYWORDS = ['skill', 'skills', 'training', 'certification', 'learn', 'boost', 'course', 'courses', 'badge', 'prepare', 'exam']
FILTERED_GCP_POSTS = pd.DataFrame() # Store filtered posts here

# --- Data Loading and Filtering ---
def parse_gcp_blog_date(date_str):
    """Parses GCP blog date strings into datetime objects."""
    if not date_str:
        return None
    try:
        # Example format from GCP blog: "2024-03-08T11:00:00.000-08:00" (has timezone)
        # or "Fri, 08 Mar 2024 19:00:00 GMT" (from RSS feed if that's the source)
        # datetime.fromisoformat handles the first. For RSS, specific strptime needed if not ISO.
        # Let's assume it's ISO-like for now, as often seen in JSON exports.
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except ValueError:
        try: # Fallback for RSS-like GMT dates
            dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
            return dt.astimezone(timezone.utc) # Ensure UTC
        except ValueError:
            print(f"Warning: Could not parse GCP blog date string: {date_str}")
            return None

def load_and_filter_gcp_blog_posts():
    global FILTERED_GCP_POSTS

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    actual_data_path = os.path.normpath(os.path.join(current_script_dir, GCP_BLOG_DATA_PATH))

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
        print(f"Warning: GCP Blog data file not found at {actual_data_path}")

    if not raw_posts or not isinstance(raw_posts, list):
        FILTERED_GCP_POSTS = pd.DataFrame()
        print("GCP Blog: No raw posts loaded or data is not in list format.")
        return

    relevant_posts_data = []
    for post in raw_posts:
        title = post.get('title', '').lower()
        # Categories might be a list of strings or a single string. Standardize to list of strings.
        categories_raw = post.get('categories', [])
        if isinstance(categories_raw, str):
            categories = [categories_raw.lower()]
        elif isinstance(categories_raw, list):
            categories = [str(cat).lower() for cat in categories_raw]
        else:
            categories = []

        content_to_check = [title] + categories

        is_relevant = any(
            any(keyword in text_item for keyword in KEYWORDS)
            for text_item in content_to_check
        )

        if is_relevant:
            published_date_str = post.get('published', post.get('pubDate')) # 'published' or 'pubDate'
            parsed_date = parse_gcp_blog_date(published_date_str)

            relevant_posts_data.append({
                'title': post.get('title', 'No Title'),
                'link': post.get('link', '#'),
                'published_date': parsed_date,
                'categories': ", ".join(post.get('categories', [])) if post.get('categories') else "N/A",
                'summary': post.get('summary', post.get('description', '')) # Summary or description
            })

    if not relevant_posts_data:
        FILTERED_GCP_POSTS = pd.DataFrame()
        print("GCP Blog: No relevant posts found after filtering.")
        return

    df = pd.DataFrame(relevant_posts_data)
    df = df[df['published_date'].notna()] # Remove rows where date parsing failed
    df = df.sort_values(by='published_date', ascending=False)
    FILTERED_GCP_POSTS = df
    print(f"GCP Blog: Loaded and filtered {len(FILTERED_GCP_POSTS)} relevant posts.")

# Load data on module import
load_and_filter_gcp_blog_posts()

# --- Layout Rendering ---
def render_gcp_blog_tab():
    if FILTERED_GCP_POSTS.empty:
        return html.Div([
            html.H3("Google Cloud Blog - Training & Certification Focus", className="mb-3"),
            dbc.Alert("No relevant Google Cloud Blog posts found matching the keywords or data is unavailable.", color="info")
        ])

    post_list_items = []
    for _, row in FILTERED_GCP_POSTS.iterrows():
        post_list_items.append(
            dbc.ListGroupItem([
                html.H5(dcc.Link(row['title'], href=row['link'], target="_blank")),
                html.P(
                    f"Published: {row['published_date'].strftime('%Y-%m-%d %H:%M UTC') if pd.notna(row['published_date']) else 'N/A'}",
                    className="small text-muted"
                ),
                html.P(f"Categories: {row['categories']}", className="small text-muted"),
                # html.P(row['summary'], className="small") # Optional: include summary
            ])
        )

    return html.Div([
        html.H3("Google Cloud Blog - Training & Certification Focus", className="mb-3"),
        html.P(f"Displaying {len(FILTERED_GCP_POSTS)} relevant posts (newest first).", className="text-muted mb-3"),
        dbc.ListGroup(post_list_items, flush=True) # flush=True for less padding if desired
    ])

if __name__ == '__main__':
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(render_gcp_blog_tab(), fluid=True, className="py-4")
    print(f"GCP Blog Test: {len(FILTERED_GCP_POSTS)} posts loaded for display.")
    if FILTERED_GCP_POSTS.empty:
        print(f"GCP Blog Test: Data file might be missing at {GCP_BLOG_DATA_PATH} or no relevant posts found.")
    app_test.run_server(debug=True, port=8054)
