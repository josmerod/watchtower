import json
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, timezone

# --- Data Loading ---
NEWS_SOURCES_CONFIG = {
    "futuretools": {"path": "../../../data/futuretools/futuretoolsnews.json", "name": "FutureTools"},
    "bensbites": {"path": "../../../data/bensbites/bensbites_news.json", "name": "Ben's Bites"},
    "hackernews": {"path": "../../../data/hackernews/hackernews.json", "name": "Hacker News"},
    "medium_genai": {"path": "../../../data/medium_genai/medium_genai.json", "name": "Medium GenAI"},
    "kdnuggets": {"path": "../../../data/kdnuggets/kdnuggets.json", "name": "KDnuggets"},
    "gooddevs": {"path": "../../../data/gooddevs/gooddevs_latest.json", "name": "Good Devs"},
    "meneame_general": {"path": "../../../data/meneame/meneame_general_latest.json", "name": "Meneame General"},
    "meneame_tecnologia": {"path": "../../../data/meneame/meneame_tecnologia_latest.json", "name": "Meneame Tech"},
    "podcasts": {"path": "../../../data/podcasts/podcasts_latest.json", "name": "Podcasts"},
}

def load_news_from_file(file_path):
    """Loads news items from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure data is a list of records
            if isinstance(data, dict): # Handle cases where JSON might be a dict with a key containing the list
                if 'articles' in data and isinstance(data['articles'], list):
                    return data['articles']
                elif 'items' in data and isinstance(data['items'], list):
                    return data['items']
                # Add more checks if other common patterns are found
                else: # If it's a dictionary but not a recognized pattern, wrap it in a list if it looks like a single item
                    if all(k in data for k in ['title', 'url']): # Heuristic for a single item
                         return [data]
                    print(f"Warning: Data in {file_path} is a dict but not a recognized list structure. Returning empty.")
                    return []
            elif isinstance(data, list):
                return data
            else:
                print(f"Warning: Data in {file_path} is not a list or recognized dict structure. Type: {type(data)}. Returning empty.")
                return []
    except FileNotFoundError:
        print(f"Warning: News file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {file_path}")
        return []
    except Exception as e:
        print(f"Error loading news from {file_path}: {e}")
        return []

ALL_NEWS_DATA = {
    source_key: load_news_from_file(config["path"])
    for source_key, config in NEWS_SOURCES_CONFIG.items()
}

# --- Helper function to parse dates ---
def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Handle various possible ISO 8601 formats, including those with 'Z' or timezone offsets
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        # Convert to UTC if timezone aware, otherwise assume UTC
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        try:
            # Fallback for simpler date formats if fromisoformat fails
            return datetime.strptime(str(date_str), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            try: #epoch time
                return datetime.fromtimestamp(float(date_str), tz=timezone.utc)
            except (ValueError, TypeError):
                 print(f"Warning: Could not parse date string: {date_str}")
                 return None

# --- Layout Generation ---

MAX_ARTICLES_PER_SOURCE = 50 # Limit number of articles displayed per source initially

def format_article_date(article):
    """Extracts and parses date from an article, returns formatted string or 'Date N/A'."""
    # Common date fields in order of preference
    date_fields = ['published_at', 'published_date', 'created_at', 'time', 'pubDate', 'updated']
    date_str = None
    for field in date_fields:
        date_str = article.get(field)
        if date_str:
            break

    parsed_dt = parse_date(date_str)
    return parsed_dt.strftime('%Y-%m-%d %H:%M UTC') if parsed_dt else "Date N/A"

def create_article_card(article, source_name="N/A"):
    """Creates a dbc.Card for a single news article."""
    title = article.get('title', 'No Title')
    url = article.get('url', article.get('link')) # 'link' is common in RSS-like structures
    # Description/summary can also be added if available and desired
    # description = article.get('description', article.get('summary', ''))

    date_display = format_article_date(article)

    card_content = [
        dbc.CardHeader(html.H5(title, className="card-title")),
        dbc.CardBody([
            html.P(f"Source: {article.get('source', source_name)}", className="card-text text-muted small"),
            html.P(f"Published: {date_display}", className="card-text text-muted small"),
            # Can add description here: html.P(description, className="card-text")
        ]),
        dbc.CardFooter(
            dbc.Button("Read More", href=url, target="_blank", color="primary", size="sm") if url else "No link available"
        )
    ]
    return dbc.Card(card_content, className="mb-3")

def create_news_source_tab_content(source_keys, combined_name=None):
    """
    Creates the content for a news tab, potentially combining multiple sources.
    Sorts articles by date before limiting.
    """
    all_articles_for_tab = []
    if isinstance(source_keys, str): # Single source key
        source_keys = [source_keys]
        source_display_name = NEWS_SOURCES_CONFIG[source_keys[0]]['name']
    else: # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined News"

    for key in source_keys:
        articles = ALL_NEWS_DATA.get(key, [])
        # Add source name to each article if not already present (for combined views)
        for article in articles:
            if 'source' not in article: # Some datasets like hackernews might not have it
                 article['source_display'] = NEWS_SOURCES_CONFIG[key]['name'] # Use specific source name
            else: # Use existing source if available
                 article['source_display'] = article['source']
        all_articles_for_tab.extend(articles)

    # Sort all articles by date (descending)
    # We need a reliable date for sorting. parse_date can return None.
    def get_sortable_date(article):
        date_str = article.get('published_at') or article.get('published_date') or article.get('created_at') or article.get('time') or article.get('pubDate')
        parsed = parse_date(date_str)
        return parsed if parsed else datetime.min.replace(tzinfo=timezone.utc) # Use min datetime for items without a valid date

    all_articles_for_tab.sort(key=get_sortable_date, reverse=True)

    # Limit after sorting
    articles_to_display = all_articles_for_tab[:MAX_ARTICLES_PER_SOURCE]

    if not articles_to_display:
        return dbc.Alert(f"No news items available for {source_display_name}.", color="info")

    return html.Div([
        create_article_card(article, source_name=article.get('source_display', source_display_name)) for article in articles_to_display
    ], style={"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"})


# Main function to render the news tab
def render_news_tab():
    tab_definitions = [
        {"label": "FutureTools & Ben's Bites", "keys": ["futuretools", "bensbites"], "id": "ft-bb"},
        {"label": "Hacker News", "keys": "hackernews", "id": "hn"},
        {"label": "Medium GenAI", "keys": "medium_genai", "id": "med_genai"},
        {"label": "KDnuggets", "keys": "kdnuggets", "id": "kdn"},
        {"label": "Good Devs", "keys": "gooddevs", "id": "gd"},
        {"label": "Meneame General", "keys": "meneame_general", "id": "men_gen"},
        {"label": "Meneame Tech", "keys": "meneame_tecnologia", "id": "men_tec"},
        {"label": "Podcasts", "keys": "podcasts", "id": "pod"},
    ]

    tabs_children = []
    for i, tab_def in enumerate(tab_definitions):
        tab_id = f"news-tab-{tab_def['id']}"
        content = create_news_source_tab_content(tab_def["keys"], combined_name=tab_def["label"])
        tabs_children.append(
            dbc.Tab(label=tab_def["label"], tab_id=tab_id, children=content, id=tab_id+"-container") # Added id to tab for potential future targeting
        )

    return html.Div([
        html.H3("News Feed", className="mb-3"),
        dbc.Tabs(id="news-source-tabs-main", children=tabs_children, active_tab="news-tab-ft-bb") # Default active tab
    ])

if __name__ == '__main__':
    # For testing this component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # The render_news_tab now produces the full tabbed layout
    app_test.layout = dbc.Container([
        html.H1("News Tab Test (Standalone)"),
        render_news_tab() # This will include the tabs and initial content
    ], fluid=True, className="py-4")

    print("Running standalone test for news_tab.py...")
    print(f"Displaying max {MAX_ARTICLES_PER_SOURCE} articles per tab, sorted by date.")
    print("Expected news JSON files relative to project root, e.g., data/futuretools/futuretoolsnews.json")
    print("Check console for warnings about missing files or parsing errors, especially date parsing.")
    app_test.run_server(debug=True, port=8052)
