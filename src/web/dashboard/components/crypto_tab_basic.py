import json

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# --- Data Loading ---


def load_crypto_sentiment():
    """Load crypto sentiment data."""
    file_path = get_data_path("crypto_sentiment", "crypto_sentiment_latest.json")
    if not file_exists(file_path):
        return []

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "sentiment_data" in data:
                return data["sentiment_data"]
            else:
                return [data] if data else []
    except Exception as e:
        print(f"Error loading crypto sentiment data: {e}")
        return []


def create_sentiment_chart(data):
    """Create sentiment analysis chart."""
    if not data:
        return go.Figure().add_annotation(
            text="No crypto sentiment data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    df = pd.DataFrame(data)

    # Create sentiment distribution chart
    if "sentiment" in df.columns:
        sentiment_counts = df["sentiment"].value_counts()
        fig = px.pie(
            values=sentiment_counts.values,
            names=sentiment_counts.index,
            title="Crypto Market Sentiment Distribution",
        )
        fig.update_layout(height=400)
        return fig

    return go.Figure().add_annotation(
        text="No sentiment data to display",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
    )


def create_crypto_cards(data):
    """Create crypto sentiment summary cards."""
    if not data:
        return [
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("No Data", className="card-title"),
                        html.P("No crypto sentiment data available", className="card-text"),
                    ]
                ),
                color="warning",
                outline=True,
            )
        ]

    # Calculate summary metrics
    total_mentions = len(data)

    sentiment_counts = {}
    coin_mentions = {}

    for item in data:
        sentiment = item.get("sentiment", "unknown")
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

        coins = item.get("coins_mentioned", [])
        if isinstance(coins, str):
            coins = [coins]
        for coin in coins:
            coin_mentions[coin] = coin_mentions.get(coin, 0) + 1

    # Most mentioned coin
    top_coin = max(coin_mentions.items(), key=lambda x: x[1]) if coin_mentions else ("N/A", 0)

    # Dominant sentiment
    dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1]) if sentiment_counts else ("N/A", 0)

    cards = [
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4(f"{total_mentions:,}", className="card-title text-primary"),
                    html.P("Total Mentions", className="card-text"),
                ]
            ),
            color="primary",
            outline=True,
            className="mb-3",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4(f"{top_coin[0]}", className="card-title text-success"),
                    html.P(f"{top_coin[1]} mentions", className="card-text"),
                ]
            ),
            color="success",
            outline=True,
            className="mb-3",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4(
                        f"{dominant_sentiment[0].title()}",
                        className="card-title text-info",
                    ),
                    html.P(f"{dominant_sentiment[1]} occurrences", className="card-text"),
                ]
            ),
            color="info",
            outline=True,
            className="mb-3",
        ),
    ]

    return cards


def create_crypto_sentiment_table(data):
    """Create crypto sentiment data table."""
    if not data:
        return html.Div("No crypto sentiment data to display.")

    # Limit to recent 50 items
    recent_data = data[:50]

    table_rows = []
    for item in recent_data:
        timestamp = item.get("timestamp", "Unknown")
        if timestamp != "Unknown":
            try:
                dt = parse_date_universal(timestamp)
                timestamp = dt.strftime("%Y-%m-%d %H:%M") if dt else timestamp
            except:
                pass

        sentiment = item.get("sentiment", "Unknown")
        sentiment_color = {
            "positive": "success",
            "negative": "danger",
            "neutral": "secondary",
            "bullish": "success",
            "bearish": "danger",
        }.get(sentiment.lower(), "secondary")

        coins = item.get("coins_mentioned", [])
        if isinstance(coins, str):
            coins = [coins]
        coins_text = ", ".join(coins[:3]) + ("..." if len(coins) > 3 else "")

        source = item.get("source", "Unknown")
        content = item.get("content", item.get("text", ""))[:200] + ("..." if len(item.get("content", item.get("text", ""))) > 200 else "")

        row = html.Tr(
            [
                html.Td(timestamp, className="text-muted small"),
                html.Td(dbc.Badge(sentiment.title(), color=sentiment_color)),
                html.Td(coins_text, className="text-primary"),
                html.Td(source, className="text-info"),
                html.Td(content, className="small"),
            ]
        )
        table_rows.append(row)

    table = dbc.Table(
        [
            html.Thead(
                [
                    html.Tr(
                        [
                            html.Th("Time", style={"width": "15%"}),
                            html.Th("Sentiment", style={"width": "10%"}),
                            html.Th("Coins", style={"width": "15%"}),
                            html.Th("Source", style={"width": "10%"}),
                            html.Th("Content", style={"width": "50%"}),
                        ]
                    )
                ]
            ),
            html.Tbody(table_rows),
        ],
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        size="sm",
    )

    return table


# --- Main Tab Function ---


def crypto_tab():
    """Main crypto/financial tab function."""
    crypto_data = load_crypto_sentiment()

    return dbc.Container(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("🪙 Crypto & Financial Intelligence", className="mb-3"),
                            html.P(
                                "Real-time cryptocurrency sentiment analysis and market intelligence",
                                className="text-muted mb-4",
                            ),
                        ]
                    )
                ]
            ),
            # Summary Cards
            dbc.Row(
                [dbc.Col(card, md=4) for card in create_crypto_cards(crypto_data)],
                className="mb-4",
            ),
            # Charts Section
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Sentiment Analysis Overview"),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="crypto-sentiment-chart",
                                                figure=create_sentiment_chart(crypto_data),
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        md=12,
                    )
                ],
                className="mb-4",
            ),
            # Data Table
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H5(
                                                "Recent Crypto Sentiment Data",
                                                className="mb-0",
                                            ),
                                            html.Small(
                                                f"Showing latest {min(50, len(crypto_data))} entries",
                                                className="text-muted",
                                            ),
                                        ]
                                    ),
                                    dbc.CardBody([create_crypto_sentiment_table(crypto_data)]),
                                ]
                            )
                        ]
                    )
                ]
            ),
        ],
        fluid=True,
    )
