# Dashboard Development Guide

This guide covers development of interactive dashboard components for the Watchtower platform using Dash and Bootstrap.

## Dashboard Architecture Overview

The Watchtower dashboard uses a modern tab-based architecture built on Dash with Bootstrap styling. Each tab is a self-contained component with its own data loading, filtering, and callback logic.

### Key Components

- **Main App** (`src/web/dashboard/app.py`): Tab container and global configuration
- **Tab Components** (`src/web/dashboard/components/`): Individual tab implementations
- **Utilities** (`src/web/dashboard/utils.py`): Shared functionality and data paths
- **Assets** (`src/web/dashboard/assets/`): CSS, JavaScript, and static files

## Creating a New Dashboard Tab

### Step 1: Basic Tab Structure

Create a new component file:

```python
# src/web/dashboard/components/my_new_tab.py
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dcc, html, callback_context

from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)

class MyDataManager:
    """Manages data loading and filtering for My New Tab."""

    def __init__(self):
        self.data = []
        self.loaded = False
        self.last_loaded = None

    def load_data(self) -> List[Dict[str, Any]]:
        """Load data from JSON files with caching."""
        current_time = datetime.now()

        # Cache data for 5 minutes to improve performance
        if (self.loaded and self.last_loaded and
            (current_time - self.last_loaded).seconds < 300):
            return self.data

        logger.info("Loading data for My New Tab...")
        self.data = []

        # Load data from the appropriate JSON file
        data_path = Path(get_data_path("my_data_source"))
        json_file = data_path / "my_data_latest.json"

        if not json_file.exists():
            logger.warning(f"Data file not found: {json_file}")
            self.loaded = True
            self.last_loaded = current_time
            return []

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Ensure data is a list
            if isinstance(data, dict):
                data = data.get('items', [])
            elif not isinstance(data, list):
                logger.error(f"Unexpected data format in {json_file}")
                data = []

            # Process and validate data
            processed_data = []
            for item in data:
                if self._validate_item(item):
                    processed_item = self._process_item(item)
                    processed_data.append(processed_item)

            self.data = processed_data
            logger.info(f"Loaded {len(self.data)} items for My New Tab")

        except Exception as e:
            logger.error(f"Error loading data from {json_file}: {e}")
            self.data = []

        self.loaded = True
        self.last_loaded = current_time
        return self.data

    def _validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate individual data item."""
        required_fields = ['title', 'id']
        return all(field in item and item[field] for field in required_fields)

    def _process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize individual item."""
        return {
            'id': item.get('id', ''),
            'title': item.get('title', 'No Title'),
            'description': item.get('description', '')[:200] + '...' if len(item.get('description', '')) > 200 else item.get('description', ''),
            'url': item.get('url', ''),
            'created_at': item.get('created_at', ''),
            'category': item.get('category', 'general'),
            'metadata': item.get('metadata', {})
        }

    def filter_data(
        self,
        search_term: Optional[str] = None,
        category_filter: Optional[str] = None,
        date_range: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Filter data based on criteria."""
        data = self.load_data()

        if not data:
            return []

        # Apply search filter
        if search_term:
            search_lower = search_term.lower()
            data = [
                item for item in data
                if (search_lower in item.get('title', '').lower() or
                    search_lower in item.get('description', '').lower())
            ]

        # Apply category filter
        if category_filter and category_filter != 'all':
            data = [item for item in data if item.get('category') == category_filter]

        # Apply date filter (days back)
        if date_range and date_range > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=date_range)
            data = [
                item for item in data
                if self._parse_date(item.get('created_at', '')) >= cutoff_date
            ]

        return data

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def get_categories(self) -> List[str]:
        """Get unique categories from data."""
        data = self.load_data()
        categories = list(set(item.get('category', 'general') for item in data))
        return sorted(categories)

# Global data manager instance
data_manager = MyDataManager()

def render_my_new_tab() -> dbc.Container:
    """Render the My New Tab component."""

    # Load initial data to get categories
    categories = data_manager.get_categories()
    category_options = [{'label': 'All Categories', 'value': 'all'}]
    category_options.extend([
        {'label': cat.title(), 'value': cat} for cat in categories
    ])

    return dbc.Container([
        # Header section
        dbc.Row([
            dbc.Col([
                html.H3("My New Data Dashboard", className="mb-3"),
                html.P("Real-time monitoring of my data source", className="text-muted")
            ])
        ], className="mb-4"),

        # Filter controls
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("🔍"),
                    dbc.Input(
                        id="my-tab-search-input",
                        placeholder="Search items...",
                        type="text",
                        debounce=True
                    )
                ])
            ], width=4),
            dbc.Col([
                dcc.Dropdown(
                    id="my-tab-category-filter",
                    options=category_options,
                    value="all",
                    placeholder="Select category...",
                    clearable=False
                )
            ], width=3),
            dbc.Col([
                dcc.Dropdown(
                    id="my-tab-date-filter",
                    options=[
                        {'label': 'All Time', 'value': 0},
                        {'label': 'Last 7 Days', 'value': 7},
                        {'label': 'Last 30 Days', 'value': 30},
                        {'label': 'Last 90 Days', 'value': 90},
                    ],
                    value=30,
                    clearable=False
                )
            ], width=3),
            dbc.Col([
                dbc.Button(
                    "Refresh Data",
                    id="my-tab-refresh-btn",
                    color="primary",
                    size="sm",
                    className="w-100"
                )
            ], width=2)
        ], className="mb-4"),

        # Statistics summary
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(id="my-tab-total-count", className="text-primary mb-0"),
                        html.P("Total Items", className="text-muted mb-0")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(id="my-tab-today-count", className="text-success mb-0"),
                        html.P("Today", className="text-muted mb-0")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(id="my-tab-week-count", className="text-info mb-0"),
                        html.P("This Week", className="text-muted mb-0")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(id="my-tab-categories-count", className="text-warning mb-0"),
                        html.P("Categories", className="text-muted mb-0")
                    ])
                ], className="text-center")
            ], width=3)
        ], className="mb-4"),

        # Main content area
        dbc.Row([
            dbc.Col([
                dbc.Spinner([
                    html.Div(id="my-tab-content")
                ], size="lg", color="primary")
            ])
        ])
    ], fluid=True)

def render_items_grid(items: List[Dict[str, Any]]) -> List[dbc.Card]:
    """Render items as a grid of cards."""
    if not items:
        return [
            dbc.Alert(
                "No items found matching your criteria.",
                color="info",
                className="text-center"
            )
        ]

    cards = []
    for item in items:
        # Create card for each item
        card = dbc.Card([
            dbc.CardBody([
                html.H5(
                    item.get('title', 'No Title'),
                    className="card-title mb-2"
                ),
                html.P(
                    item.get('description', 'No description available'),
                    className="card-text text-muted mb-3"
                ),
                dbc.Badge(
                    item.get('category', 'general').title(),
                    color="secondary",
                    className="mb-2"
                ),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        html.Small(
                            f"Created: {item.get('created_at', 'Unknown')[:10]}",
                            className="text-muted"
                        )
                    ], width=8),
                    dbc.Col([
                        dbc.Button(
                            "View",
                            size="sm",
                            color="outline-primary",
                            href=item.get('url', '#'),
                            target="_blank" if item.get('url') else None,
                            disabled=not item.get('url')
                        )
                    ], width=4, className="text-end")
                ])
            ])
        ], className="h-100 mb-3")
        cards.append(card)

    # Arrange cards in responsive grid
    grid_items = []
    for i in range(0, len(cards), 3):
        row_cards = cards[i:i+3]
        cols = [dbc.Col(card, width=4) for card in row_cards]
        grid_items.append(dbc.Row(cols, className="mb-3"))

    return grid_items

def register_my_tab_callbacks(app):
    """Register callbacks for My New Tab."""

    @app.callback(
        [
            Output("my-tab-content", "children"),
            Output("my-tab-total-count", "children"),
            Output("my-tab-today-count", "children"),
            Output("my-tab-week-count", "children"),
            Output("my-tab-categories-count", "children")
        ],
        [
            Input("my-tab-search-input", "value"),
            Input("my-tab-category-filter", "value"),
            Input("my-tab-date-filter", "value"),
            Input("my-tab-refresh-btn", "n_clicks")
        ],
        prevent_initial_call=False
    )
    def update_content(search_term, category_filter, date_filter, refresh_clicks):
        """Update tab content based on filters."""
        try:
            # Force data refresh if refresh button was clicked
            if callback_context.triggered and "refresh-btn" in callback_context.triggered[0]['prop_id']:
                data_manager.loaded = False

            # Get filtered data
            filtered_items = data_manager.filter_data(
                search_term=search_term,
                category_filter=category_filter,
                date_range=date_filter
            )

            # Calculate statistics
            all_items = data_manager.load_data()
            total_count = len(all_items)

            # Today's items
            today = datetime.now(timezone.utc).date()
            today_count = len([
                item for item in all_items
                if data_manager._parse_date(item.get('created_at', '')).date() == today
            ])

            # This week's items
            week_start = datetime.now(timezone.utc) - timedelta(days=7)
            week_count = len([
                item for item in all_items
                if data_manager._parse_date(item.get('created_at', '')) >= week_start
            ])

            # Categories count
            categories_count = len(data_manager.get_categories())

            # Render content
            content = render_items_grid(filtered_items)

            return (
                content,
                str(total_count),
                str(today_count),
                str(week_count),
                str(categories_count)
            )

        except Exception as e:
            logger.error(f"Error updating My Tab content: {e}")
            error_content = dbc.Alert(
                f"Error loading data: {str(e)}",
                color="danger",
                className="text-center"
            )
            return error_content, "Error", "Error", "Error", "Error"

# Testing and debugging
if __name__ == "__main__":
    # Test data loading
    print("Testing My New Tab data loading...")

    manager = MyDataManager()
    data = manager.load_data()
    print(f"Loaded {len(data)} items")

    if data:
        print("Sample item:", data[0])

    categories = manager.get_categories()
    print(f"Categories: {categories}")

    # Test filtering
    filtered = manager.filter_data(search_term="test")
    print(f"Filtered items: {len(filtered)}")
```

### Step 2: Add Tab to Main App

Update the main dashboard app:

```python
# src/web/dashboard/app.py (add these imports and tab)
from src.web.dashboard.components.my_new_tab import (
    render_my_new_tab,
    register_my_tab_callbacks
)

# Add to the tabs list in app.layout
dbc.Tab(
    label="My New Tab",
    tab_id="tab-my-new",
    children=[render_my_new_tab()],
),

# Register callbacks at the bottom
register_my_tab_callbacks(app)
```

## Advanced Dashboard Patterns

### Data Manager Pattern

For complex data handling, implement a dedicated manager class:

```python
class AdvancedDataManager:
    """Advanced data manager with caching and aggregation."""

    def __init__(self):
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes

    def get_data_with_cache(self, data_source: str, force_refresh: bool = False):
        """Get data with intelligent caching."""
        cache_key = f"data_{data_source}"
        current_time = time.time()

        # Check cache validity
        if (not force_refresh and
            cache_key in self._cache and
            current_time - self._cache[cache_key]['timestamp'] < self._cache_timeout):
            return self._cache[cache_key]['data']

        # Load fresh data
        data = self._load_data(data_source)

        # Update cache
        self._cache[cache_key] = {
            'data': data,
            'timestamp': current_time
        }

        return data

    def aggregate_metrics(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregated metrics from data."""
        if not data:
            return {'total': 0, 'categories': [], 'recent': 0}

        # Convert to DataFrame for easier aggregation
        df = pd.DataFrame(data)

        # Calculate metrics
        metrics = {
            'total': len(df),
            'categories': df['category'].unique().tolist() if 'category' in df.columns else [],
            'recent': len(df[df['created_at'] >= (datetime.now() - timedelta(days=7)).isoformat()]) if 'created_at' in df.columns else 0,
            'top_categories': df['category'].value_counts().head(5).to_dict() if 'category' in df.columns else {}
        }

        return metrics
```

### Interactive Filtering

Implement advanced filtering with multiple criteria:

```python
def create_advanced_filters() -> dbc.Row:
    """Create advanced filter controls."""
    return dbc.Row([
        # Search input
        dbc.Col([
            dbc.InputGroup([
                dbc.InputGroupText("🔍"),
                dbc.Input(
                    id="advanced-search",
                    placeholder="Search across all fields...",
                    type="text",
                    debounce=True
                )
            ])
        ], width=3),

        # Multi-select categories
        dbc.Col([
            dcc.Dropdown(
                id="multi-category-filter",
                placeholder="Select categories...",
                multi=True
            )
        ], width=3),

        # Date range picker
        dbc.Col([
            dcc.DatePickerRange(
                id="date-range-picker",
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                display_format='YYYY-MM-DD'
            )
        ], width=3),

        # Sort options
        dbc.Col([
            dcc.Dropdown(
                id="sort-options",
                options=[
                    {'label': 'Newest First', 'value': 'date_desc'},
                    {'label': 'Oldest First', 'value': 'date_asc'},
                    {'label': 'Title A-Z', 'value': 'title_asc'},
                    {'label': 'Title Z-A', 'value': 'title_desc'}
                ],
                value='date_desc'
            )
        ], width=3)
    ])
```

### Error Boundaries

Implement comprehensive error handling:

```python
def safe_render_component(render_func, fallback_message="Unable to load component"):
    """Safely render component with error boundary."""
    try:
        return render_func()
    except Exception as e:
        logger.error(f"Error rendering component: {e}")
        return dbc.Alert(
            [
                html.H5("Component Error", className="alert-heading"),
                html.P(fallback_message),
                html.Hr(),
                html.P(f"Technical details: {str(e)}", className="text-muted small")
            ],
            color="warning"
        )

@app.callback(
    Output("safe-content", "children"),
    Input("trigger", "n_clicks")
)
def safe_callback(n_clicks):
    """Callback with error boundary."""
    try:
        # Main callback logic
        return process_data()
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return dbc.Alert(
            "Sorry, there was an error processing your request. Please try again.",
            color="danger"
        )
```

### Performance Optimization

Optimize for large datasets:

```python
def paginated_display(items: List[Dict], page_size: int = 50, current_page: int = 1):
    """Display items with pagination."""
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size

    # Calculate slice indices
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)

    # Get items for current page
    page_items = items[start_idx:end_idx]

    # Render pagination controls
    pagination = dbc.Pagination(
        id="pagination",
        max_value=total_pages,
        fully_expanded=False,
        first_last=True,
        previous_next=True,
        active_page=current_page
    )

    return html.Div([
        render_items_grid(page_items),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                html.P(f"Showing {start_idx + 1}-{end_idx} of {total_items} items")
            ], width=6),
            dbc.Col([pagination], width=6, className="text-end")
        ])
    ])

def lazy_load_content(container_id: str, data_loader_func):
    """Implement lazy loading for heavy content."""
    return html.Div([
        dbc.Spinner(
            html.Div(id=container_id),
            size="lg"
        ),
        dcc.Interval(
            id=f"{container_id}-interval",
            interval=1000,  # 1 second
            n_intervals=0,
            max_intervals=1  # Load only once
        )
    ])
```

## Testing Dashboard Components

### Unit Testing

```python
# Tests/web/test_my_new_tab.py
import pytest
from unittest.mock import patch, mock_open
import json

from src.web.dashboard.components.my_new_tab import MyDataManager, render_my_new_tab

class TestMyDataManager:
    """Test suite for MyDataManager."""

    @pytest.fixture
    def sample_data(self):
        return [
            {
                'id': '1',
                'title': 'Test Item 1',
                'description': 'Test description',
                'category': 'test',
                'created_at': '2023-01-01T00:00:00Z'
            },
            {
                'id': '2',
                'title': 'Another Test',
                'description': 'Another description',
                'category': 'other',
                'created_at': '2023-01-02T00:00:00Z'
            }
        ]

    @patch('src.web.dashboard.components.my_new_tab.get_data_path')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_data_success(self, mock_file, mock_path, sample_data):
        """Test successful data loading."""
        mock_path.return_value = "/fake/path"
        mock_file.return_value.read.return_value = json.dumps(sample_data)

        manager = MyDataManager()
        data = manager.load_data()

        assert len(data) == 2
        assert data[0]['title'] == 'Test Item 1'

    def test_filter_data(self, sample_data):
        """Test data filtering functionality."""
        manager = MyDataManager()
        manager.data = sample_data
        manager.loaded = True

        # Test search filter
        filtered = manager.filter_data(search_term="Another")
        assert len(filtered) == 1
        assert filtered[0]['title'] == 'Another Test'

        # Test category filter
        filtered = manager.filter_data(category_filter="test")
        assert len(filtered) == 1
        assert filtered[0]['category'] == 'test'
```

### Integration Testing

```python
# Tests/web/test_dashboard_integration.py
import pytest
from dash.testing.application_runners import import_app

def test_dashboard_loads():
    """Test that dashboard loads without errors."""
    app = import_app("src.web.dashboard.app")
    assert app is not None

def test_tab_rendering():
    """Test that tabs render correctly."""
    from src.web.dashboard.components.my_new_tab import render_my_new_tab

    component = render_my_new_tab()
    assert component is not None
    assert hasattr(component, 'children')
```

## Best Practices

### 1. Component Structure
- Use consistent naming conventions (`{tab_name}_tab.py`)
- Implement data manager classes for complex data handling
- Separate rendering logic from data processing logic
- Use type hints for better code maintainability

### 2. Performance
- Implement caching for expensive operations
- Use pagination for large datasets
- Lazy load heavy content when possible
- Minimize callback frequency with debouncing

### 3. Error Handling
- Wrap components in error boundaries
- Provide user-friendly error messages
- Log errors with sufficient context for debugging
- Implement graceful degradation when data is unavailable

### 4. User Experience
- Use loading spinners for async operations
- Provide clear feedback for user actions
- Implement responsive design with Bootstrap grid
- Use consistent styling and color schemes

### 5. Testing
- Write unit tests for data managers and utility functions
- Test error conditions and edge cases
- Use integration tests for complete workflows
- Mock external dependencies appropriately

### 6. Accessibility
- Use semantic HTML elements
- Provide alt text for images
- Ensure keyboard navigation works
- Use sufficient color contrast

This guide provides the foundation for creating interactive, performant dashboard components that integrate seamlessly with the Watchtower platform.
