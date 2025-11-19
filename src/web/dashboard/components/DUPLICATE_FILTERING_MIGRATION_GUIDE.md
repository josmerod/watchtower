# Duplicate Filtering Migration Guide

This guide explains how to add duplicate filtering functionality to existing dashboard tabs.

## Quick Start (3 Steps)

### Step 1: Import Required Components

```python
from src.web.dashboard.components.duplicate_filter import (
    create_duplicate_filter_component,
    register_duplicate_filter_callback,
    register_filtered_data_callback,
    get_filtered_data_callback_id,
)
```

### Step 2: Add Duplicate Filter to Layout

Add this to your tab's layout function:

```python
def create_layout():
    return html.Div([
        # Add data store for your data
        dcc.Store(id="your-tab-data-store"),

        # Add duplicate filter component (ADD THIS)
        *create_duplicate_filter_component(
            "your-tab",  # component_id
            "your-tab-data-store",  # data_store_id
            "items"  # data_name (e.g., "papers", "articles", "courses")
        ),

        # Your existing layout content...
    ])
```

### Step 3: Register Callbacks

Add this to your tab's callback registration:

```python
def register_callbacks(app):
    # Load your data (existing pattern)
    @app.callback(
        Output("your-tab-data-store", "data"),
        Input("your-tab-data-store", "data"),
        prevent_initial_call=False
    )
    def load_data(_):
        # Your existing data loading logic
        return your_data_list

    # Register duplicate filtering callbacks (ADD THIS)
    register_duplicate_filter_callback("your-tab", "your-tab-data-store", "items")
    register_filtered_data_callback(
        "your-tab",
        "your-tab-data-store",
        (get_filtered_data_callback_id("your-tab"), "data")
    )

    # Update your existing display callbacks to use filtered data
    @app.callback(
        Output("your-tab-content", "children"),
        Input(get_filtered_data_callback_id("your-tab"), "data"),  # Use filtered data
        # ... other inputs
    )
    def update_content(filtered_data, ...):
        # Use filtered_data instead of raw data
        return create_display_elements(filtered_data)
```

## Detailed Example

### Before (Simple Tab)
```python
def create_layout():
    return html.Div([
        dcc.Store(id="news-data-store"),
        html.Div(id="news-content")
    ])

def register_callbacks(app):
    @app.callback(
        Output("news-data-store", "data"),
        Input("news-data-store", "data")
    )
    def load_news_data(_):
        return load_news_from_files()  # Returns list of news items

    @app.callback(
        Output("news-content", "children"),
        Input("news-data-store", "data")
    )
    def display_news(news_data):
        return create_news_cards(news_data)
```

### After (With Duplicate Filtering)
```python
from src.web.dashboard.components.duplicate_filter import (
    create_duplicate_filter_component,
    register_duplicate_filter_callback,
    register_filtered_data_callback,
    get_filtered_data_callback_id,
)

def create_layout():
    return html.Div([
        dcc.Store(id="news-data-store"),
        # Add duplicate filter component
        *create_duplicate_filter_component("news", "news-data-store", "articles"),
        html.Div(id="news-content")
    ])

def register_callbacks(app):
    @app.callback(
        Output("news-data-store", "data"),
        Input("news-data-store", "data")
    )
    def load_news_data(_):
        return load_news_from_files()  # Returns list of news items

    # Register duplicate filtering callbacks
    register_duplicate_filter_callback("news", "news-data-store", "articles")
    register_filtered_data_callback(
        "news",
        "news-data-store",
        (get_filtered_data_callback_id("news"), "data")
    )

    # Update display callback to use filtered data
    @app.callback(
        Output("news-content", "children"),
        Input(get_filtered_data_callback_id("news"), "data")  # Use filtered data
    )
    def display_news(filtered_news_data):
        return create_news_cards(filtered_news_data)
```

## What Gets Added

### Visual Components
- **Show/Hide Duplicates Button**: Toggles between showing unique items only and all items
- **Duplicate Summary**: Shows count of unique items and hidden duplicates
- **Duplicate Badges**: Visual indicators for duplicate/original status
- **Quality Score Badges**: Shows quality scores for items

### Data Processing
- **Automatic Filtering**: `is_duplicate=False` items shown by default
- **Group Information**: Maintains duplicate group relationships
- **Quality-Based Prioritization**: Highest quality items shown as "originals"

### Data Requirements
Your data should include these fields (automatically added by deduplication engine):
- `is_duplicate`: Boolean indicating if item is a duplicate
- `duplicate_group_id`: String ID for duplicate groups
- `quality_score`: Float from 0.0 to 100.0

## Component ID Patterns

- Data Store: `{component_id}-data-store`
- Filtered Data: `{component_id}-filtered-data`
- Show Duplicates Toggle: `{component_id}-show-duplicates`
- Toggle Button: `{component_id}-toggle-duplicates`
- Controls: `{component_id}-duplicate-controls`
- Summary: `{component_id}-duplicate-summary`

## Customization

### Custom Button Text
```python
from ..deduplication_utils import create_show_duplicates_button

# Instead of using the component, create custom button
button = create_show_duplicates_button(
    button_id="custom-toggle",
    data=your_data,
    current_show_duplicates=False,
    button_text="Custom Toggle Text"
)
```

### Custom Filtering Logic
```python
from ..deduplication_utils import filter_duplicates, get_duplicate_groups

# Filter duplicates manually
filtered_data = filter_duplicates(raw_data, show_duplicates=False)
duplicate_groups = get_duplicate_groups(raw_data)
```

## Testing

To test duplicate filtering:
1. Create test data with duplicate entries
2. Verify the button toggles correctly
3. Check that duplicate counts are accurate
4. Ensure filtered data excludes duplicates when show_duplicates=False

## Migration Checklist

- [ ] Import duplicate filter components
- [ ] Add data store to layout
- [ ] Add duplicate filter component to layout
- [ ] Register data loading callback
- [ ] Register duplicate filter callbacks
- [ ] Update display callbacks to use filtered data
- [ ] Test with sample duplicate data
- [ ] Verify button functionality
- [ ] Check duplicate counts and badges

## Support

If you encounter issues during migration:
1. Check that your data follows the expected format
2. Verify component IDs are consistent
3. Ensure callback chains are properly connected
4. Test with small datasets first