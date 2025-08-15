"""Giveaways Tab Component

This module creates the giveaways dashboard tab showing free games, courses, books,
software, and other giveaways from multiple sources.
"""

import json
import os
from typing import Any, Dict, List

import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from src.web.dashboard.utils import get_data_path


def create_giveaways_tab():
    """Create the giveaways tab layout."""
    return html.Div(
        [
            html.H2("🎁 Giveaways & Free Content", className="text-center mb-4"),
            # Summary cards
            html.Div(id="giveaways-summary-cards", className="row mb-4"),
            # Filter controls
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Category:", className="form-label"),
                            dcc.Dropdown(
                                id="giveaways-category-filter",
                                options=[
                                    {"label": "All Categories", "value": "all"},
                                    {"label": "🎮 Games", "value": "games"},
                                    {
                                        "label": "📚 Books & Courses",
                                        "value": "education",
                                    },
                                    {"label": "💻 Software", "value": "software"},
                                    {"label": "🎯 General", "value": "general"},
                                ],
                                value="all",
                                className="form-select",
                            ),
                        ],
                        className="col-md-3",
                    ),
                    html.Div(
                        [
                            html.Label("Platform:", className="form-label"),
                            dcc.Dropdown(
                                id="giveaways-platform-filter",
                                options=[{"label": "All Platforms", "value": "all"}],
                                value="all",
                                className="form-select",
                            ),
                        ],
                        className="col-md-3",
                    ),
                    html.Div(
                        [
                            html.Label("Availability:", className="form-label"),
                            dcc.Dropdown(
                                id="giveaways-availability-filter",
                                options=[
                                    {"label": "All", "value": "all"},
                                    {"label": "⭐ Active Now", "value": "active"},
                                    {"label": "⏰ Ending Soon", "value": "ending_soon"},
                                    {"label": "🔜 Upcoming", "value": "upcoming"},
                                ],
                                value="all",
                                className="form-select",
                            ),
                        ],
                        className="col-md-3",
                    ),
                    html.Div(
                        [
                            html.Label("Sort by:", className="form-label"),
                            dcc.Dropdown(
                                id="giveaways-sort-filter",
                                options=[
                                    {"label": "Relevance", "value": "relevance"},
                                    {"label": "Latest", "value": "latest"},
                                    {"label": "Value", "value": "value"},
                                    {"label": "Popularity", "value": "popularity"},
                                ],
                                value="relevance",
                                className="form-select",
                            ),
                        ],
                        className="col-md-3",
                    ),
                ],
                className="row mb-4",
            ),
            # Charts section
            html.Div(
                [
                    html.Div(
                        [dcc.Graph(id="giveaways-category-chart")], className="col-md-6"
                    ),
                    html.Div(
                        [dcc.Graph(id="giveaways-platform-chart")], className="col-md-6"
                    ),
                ],
                className="row mb-4",
            ),
            # Giveaways list
            html.Div(id="giveaways-list", className="row"),
            # Auto-refresh
            dcc.Interval(
                id="giveaways-interval",
                interval=5 * 60 * 1000,  # Refresh every 5 minutes
                n_intervals=0,
            ),
        ]
    )


@callback(
    [
        Output("giveaways-summary-cards", "children"),
        Output("giveaways-platform-filter", "options"),
        Output("giveaways-category-chart", "figure"),
        Output("giveaways-platform-chart", "figure"),
        Output("giveaways-list", "children"),
    ],
    [
        Input("giveaways-category-filter", "value"),
        Input("giveaways-platform-filter", "value"),
        Input("giveaways-availability-filter", "value"),
        Input("giveaways-sort-filter", "value"),
        Input("giveaways-interval", "n_intervals"),
    ],
)
def update_giveaways_content(
    category_filter, platform_filter, availability_filter, sort_filter, n_intervals
):
    """Update giveaways content based on filters."""

    # Load all giveaway data
    giveaways_data = load_all_giveaways_data()

    if not giveaways_data:
        return (
            create_empty_summary_cards(),
            [{"label": "All Platforms", "value": "all"}],
            create_empty_chart("No Data", "Categories"),
            create_empty_chart("No Data", "Platforms"),
            [
                html.Div(
                    "No giveaways data available.", className="text-center text-muted"
                )
            ],
        )

    # Filter data
    filtered_data = filter_giveaways_data(
        giveaways_data, category_filter, platform_filter, availability_filter
    )

    # Sort data
    sorted_data = sort_giveaways_data(filtered_data, sort_filter)

    # Create summary cards
    summary_cards = create_summary_cards(giveaways_data, filtered_data)

    # Update platform filter options
    platform_options = get_platform_options(giveaways_data)

    # Create charts
    category_chart = create_category_chart(filtered_data)
    platform_chart = create_platform_chart(filtered_data)

    # Create giveaways list
    giveaways_list = create_giveaways_list(sorted_data)

    return (
        summary_cards,
        platform_options,
        category_chart,
        platform_chart,
        giveaways_list,
    )


def load_all_giveaways_data() -> List[Dict[str, Any]]:
    """Load data from all giveaway sources."""
    all_data = []

    # Load Reddit giveaways
    try:
        reddit_path = get_data_path("giveaways", "reddit_giveaways.json")
        if os.path.exists(reddit_path):
            with open(reddit_path, "r", encoding="utf-8") as f:
                reddit_data = json.load(f)
                for item in reddit_data:
                    item["data_source"] = "reddit"
                all_data.extend(reddit_data)
    except Exception as e:
        print(f"Error loading Reddit giveaways: {e}")

    # Load free games (prefer canonical latest file)
    try:
        latest_games_path = get_data_path("giveaways", "free_games_latest.json")
        games_path = (
            latest_games_path
            if os.path.exists(latest_games_path)
            else get_data_path("giveaways", "free_games.json")
        )
        if os.path.exists(games_path):
            with open(games_path, "r", encoding="utf-8") as f:
                games_data = json.load(f)
                for item in games_data:
                    item["data_source"] = "free_games"
                    # Normalize fields for consistency
                    if "title" not in item and "name" in item:
                        item["title"] = item["name"]
                all_data.extend(games_data)
    except Exception as e:
        print(f"Error loading free games: {e}")

    # Load free courses (prefer canonical latest file if we standardize later)
    try:
        latest_courses_path = get_data_path("giveaways", "free_courses_latest.json")
        courses_path = (
            latest_courses_path
            if os.path.exists(latest_courses_path)
            else get_data_path("giveaways", "free_courses.json")
        )
        if os.path.exists(courses_path):
            with open(courses_path, "r", encoding="utf-8") as f:
                courses_data = json.load(f)
                for item in courses_data:
                    item["data_source"] = "free_courses"
                all_data.extend(courses_data)
    except Exception as e:
        print(f"Error loading free courses: {e}")

    return all_data


def filter_giveaways_data(
    data: List[Dict],
    category_filter: str,
    platform_filter: str,
    availability_filter: str,
) -> List[Dict]:
    """Filter giveaways data based on user selections."""
    filtered = data

    # Category filter
    if category_filter != "all":
        if category_filter == "games":
            filtered = [
                item
                for item in filtered
                if item.get("category") == "games"
                or item.get("giveaway_type") == "free_game"
            ]
        elif category_filter == "education":
            filtered = [
                item
                for item in filtered
                if item.get("category")
                in ["courses", "machine_learning", "programming", "academic"]
            ]
        elif category_filter == "software":
            filtered = [item for item in filtered if item.get("category") == "software"]
        else:
            filtered = [
                item for item in filtered if item.get("category") == category_filter
            ]

    # Platform filter
    if platform_filter != "all":
        filtered = [
            item
            for item in filtered
            if item.get("platform", "").lower() == platform_filter.lower()
        ]

    # Availability filter
    if availability_filter != "all":
        if availability_filter == "active":
            filtered = [item for item in filtered if item.get("is_active", True)]
        elif availability_filter == "ending_soon":
            filtered = [
                item
                for item in filtered
                if item.get("availability")
                in ["limited_time", "ends_soon", "ends_today"]
            ]
        elif availability_filter == "upcoming":
            filtered = [
                item for item in filtered if item.get("availability") == "upcoming"
            ]

    return filtered


def sort_giveaways_data(data: List[Dict], sort_by: str) -> List[Dict]:
    """Sort giveaways data."""
    if sort_by == "relevance":
        return sorted(
            data,
            key=lambda x: (
                x.get("relevance_score", 0),
                x.get("score", 0),
                x.get("upvote_ratio", 0),
            ),
            reverse=True,
        )
    elif sort_by == "latest":
        return sorted(data, key=lambda x: x.get("created_date", ""), reverse=True)
    elif sort_by == "value":
        return sorted(
            data,
            key=lambda x: (x.get("original_price", 0), x.get("savings", 0)),
            reverse=True,
        )
    elif sort_by == "popularity":
        return sorted(
            data,
            key=lambda x: (x.get("score", 0), x.get("num_comments", 0)),
            reverse=True,
        )

    return data


def create_summary_cards(all_data: List[Dict], filtered_data: List[Dict]) -> html.Div:
    """Create summary statistics cards."""
    total_items = len(all_data)
    filtered_items = len(filtered_data)

    # Count by category
    categories = {}
    active_count = 0

    for item in all_data:
        category = item.get("category", "other")
        categories[category] = categories.get(category, 0) + 1
        if item.get("is_active", True):
            active_count += 1

    # Calculate total savings
    total_savings = sum(
        item.get("savings", 0) for item in all_data if item.get("savings", 0) > 0
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                str(total_items), className="card-title text-primary"
                            ),
                            html.P("Total Giveaways", className="card-text"),
                        ],
                        className="card-body text-center",
                    )
                ],
                className="card col-md-3",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                str(active_count), className="card-title text-success"
                            ),
                            html.P("Active Now", className="card-text"),
                        ],
                        className="card-body text-center",
                    )
                ],
                className="card col-md-3",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                str(len(categories)), className="card-title text-info"
                            ),
                            html.P("Categories", className="card-text"),
                        ],
                        className="card-body text-center",
                    )
                ],
                className="card col-md-3",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                f"${total_savings:,.0f}",
                                className="card-title text-warning",
                            ),
                            html.P("Total Savings", className="card-text"),
                        ],
                        className="card-body text-center",
                    )
                ],
                className="card col-md-3",
            ),
        ],
        className="row",
    )


def create_empty_summary_cards() -> html.Div:
    """Create empty summary cards."""
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H4("0", className="card-title text-muted"),
                            html.P("Total Giveaways", className="card-text"),
                        ],
                        className="card-body text-center",
                    )
                ],
                className="card col-md-3",
            )
        ],
        className="row",
    )


def get_platform_options(data: List[Dict]) -> List[Dict]:
    """Get platform filter options."""
    platforms = set()
    for item in data:
        platform = item.get("platform", "")
        if platform:
            platforms.add(platform)

    options = [{"label": "All Platforms", "value": "all"}]
    for platform in sorted(platforms):
        options.append({"label": platform, "value": platform})

    return options


def create_category_chart(data: List[Dict]) -> go.Figure:
    """Create category distribution chart."""
    if not data:
        return create_empty_chart("No Data", "Giveaways by Category")

    category_counts = {}
    for item in data:
        category = item.get("category", "other")
        category_counts[category] = category_counts.get(category, 0) + 1

    if not category_counts:
        return create_empty_chart("No Categories", "Giveaways by Category")

    fig = px.pie(
        values=list(category_counts.values()),
        names=list(category_counts.keys()),
        title="Giveaways by Category",
    )

    fig.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))

    return fig


def create_platform_chart(data: List[Dict]) -> go.Figure:
    """Create platform distribution chart."""
    if not data:
        return create_empty_chart("No Data", "Giveaways by Platform")

    platform_counts = {}
    for item in data:
        platform = item.get("platform", "Unknown")
        platform_counts[platform] = platform_counts.get(platform, 0) + 1

    if not platform_counts:
        return create_empty_chart("No Platforms", "Giveaways by Platform")

    # Show top 10 platforms
    sorted_platforms = sorted(
        platform_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]

    fig = px.bar(
        x=[count for _, count in sorted_platforms],
        y=[platform for platform, _ in sorted_platforms],
        orientation="h",
        title="Giveaways by Platform (Top 10)",
    )

    fig.update_layout(
        height=300,
        margin=dict(t=40, b=0, l=0, r=0),
        yaxis={"categoryorder": "total ascending"},
    )

    return fig


def create_empty_chart(message: str, title: str) -> go.Figure:
    """Create empty chart with message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray"),
    )
    fig.update_layout(
        title=title,
        height=300,
        margin=dict(t=40, b=0, l=0, r=0),
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def create_giveaways_list(data: List[Dict]) -> List[html.Div]:
    """Create list of giveaway cards."""
    if not data:
        return [
            html.Div(
                "No giveaways match your filters.", className="text-center text-muted"
            )
        ]

    cards = []
    for item in data[:50]:  # Limit to 50 items for performance
        card = create_giveaway_card(item)
        cards.append(card)

    return cards


def create_giveaway_card(item: Dict[str, Any]) -> html.Div:
    """Create individual giveaway card."""
    title = item.get("title", "Unknown Title")
    description = item.get("description", "No description available")
    url = item.get("url", "#")
    platform = item.get("platform", "Unknown")
    category = item.get("category", "other")
    image_url = item.get("image_url", "")

    # Determine card styling based on category
    category_colors = {
        "games": "border-primary",
        "courses": "border-success",
        "machine_learning": "border-info",
        "software": "border-warning",
        "general": "border-secondary",
    }

    card_class = category_colors.get(category, "border-secondary")

    # Availability indicator
    availability = item.get("availability", "active")
    availability_badge = get_availability_badge(availability)

    # Price information
    price_info = get_price_info(item)

    # Expiration info
    expiration_info = ""
    if item.get("promotion_end"):
        try:
            from datetime import datetime

            end_date = datetime.fromisoformat(
                item["promotion_end"].replace("Z", "+00:00")
            )
            expiration_info = f"⏰ Ends {end_date.strftime('%b %d, %Y')}"
        except:
            pass

    # Image element
    card_image = None
    if image_url:
        card_image = html.Img(
            src=image_url,
            className="card-img-top",
            style={"height": "150px", "objectFit": "cover"},
            alt=title,
        )

    return html.Div(
        [
            html.Div(
                [
                    card_image,
                    html.Div(
                        [
                            html.H6(
                                title[:80] + "..." if len(title) > 80 else title,
                                className="card-title",
                            ),
                            html.P(
                                (
                                    description[:150] + "..."
                                    if len(description) > 150
                                    else description
                                ),
                                className="card-text text-muted small",
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        f"📍 {platform}",
                                        className="badge bg-light text-dark me-1 mb-1",
                                    ),
                                    html.Span(
                                        f"🏷️ {category}",
                                        className="badge bg-light text-dark me-1 mb-1",
                                    ),
                                    availability_badge,
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    price_info,
                                    (
                                        html.Span(
                                            expiration_info,
                                            className="badge bg-warning text-dark ms-1",
                                        )
                                        if expiration_info
                                        else None
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.A(
                                "View Giveaway",
                                href=url,
                                target="_blank",
                                className="btn btn-outline-primary btn-sm",
                            ),
                        ],
                        className="card-body",
                    ),
                ],
                className=f"card h-100 {card_class}",
            )
        ],
        className="col-md-6 col-lg-4 mb-3",
    )


def get_availability_badge(availability: str) -> html.Span:
    """Get availability status badge."""
    badges = {
        "active": html.Span("🟢 Active", className="badge bg-success"),
        "limited_time": html.Span("⏰ Limited Time", className="badge bg-warning"),
        "ends_today": html.Span("🔴 Ends Today", className="badge bg-danger"),
        "ends_soon": html.Span("🟡 Ends Soon", className="badge bg-warning"),
        "upcoming": html.Span("🔵 Upcoming", className="badge bg-info"),
        "expired": html.Span("⚫ Expired", className="badge bg-secondary"),
        "permanent": html.Span("💎 Permanent", className="badge bg-primary"),
    }

    return badges.get(
        availability, html.Span("🟢 Available", className="badge bg-success")
    )


def get_price_info(item: Dict[str, Any]) -> html.Span:
    """Get price information display."""
    original_price = item.get("original_price", 0)
    current_price = item.get("current_price", 0)
    discount_percentage = item.get("discount_percentage", 0)

    if original_price > 0 and current_price == 0:
        return html.Span(
            f"💰 Free (was ${original_price:.2f})", className="badge bg-success"
        )
    elif discount_percentage > 0 and original_price > 0:
        savings = original_price - current_price
        return html.Span(
            f"💰 Save ${savings:.2f} ({discount_percentage}% off)",
            className="badge bg-success",
        )
    elif current_price == 0:
        return html.Span("🆓 Free", className="badge bg-success")
    elif original_price > 0:
        return html.Span(
            f"💵 ${original_price:.2f}", className="badge bg-light text-dark"
        )
    else:
        return html.Span("")


# Register the tab
def register_giveaways_tab():
    """Register the giveaways tab."""
    return {
        "label": "🎁 Giveaways",
        "value": "giveaways",
        "content": create_giveaways_tab(),
    }
