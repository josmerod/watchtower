import json
import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from datetime import datetime, timezone, timedelta
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
import re

# Import shared utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_data_path, file_exists, parse_date_universal

# --- Enhanced Data Loading ---

def load_crypto_sentiment():
    """Load crypto sentiment data with multiple fallback paths."""
    file_paths = [
        get_data_path("crypto_sentiment", "crypto_sentiment_latest.json"),
        get_data_path("crypto_sentiment", "output", "latest.json"),
        get_data_path("miners", "crypto_sentiment", "output.json"),
        get_data_path("crypto", "sentiment_data.json")
    ]
    
    for file_path in file_paths:
        if file_exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        # Try multiple keys
                        for key in ['sentiment_data', 'data', 'items', 'results', 'entries']:
                            if key in data and isinstance(data[key], list):
                                return data[key]
                        # Single item
                        if any(k in data for k in ['sentiment', 'coin', 'text', 'content']):
                            return [data]
                    return []
            except Exception as e:
                print(f"Error loading crypto sentiment from {file_path}: {e}")
                continue
    
    return []

def process_crypto_data(data):
    """Process and enrich crypto sentiment data."""
    if not data:
        return []
    
    processed = []
    for item in data:
        # Standardize fields
        processed_item = {
            'timestamp': item.get('timestamp', item.get('date', item.get('created_at', datetime.now().isoformat()))),
            'sentiment': item.get('sentiment', 'neutral').lower(),
            'content': item.get('content', item.get('text', item.get('message', ''))),
            'source': item.get('source', item.get('platform', 'Unknown')),
            'coins_mentioned': item.get('coins_mentioned', item.get('coins', item.get('symbols', []))),
            'confidence': item.get('confidence', item.get('score', 0.5)),
            'url': item.get('url', item.get('link', '')),
            'author': item.get('author', item.get('username', 'Anonymous')),
            'engagement': item.get('engagement', item.get('likes', item.get('upvotes', 0))),
            'price_mentioned': item.get('price_mentioned', item.get('price', None)),
            'market_cap': item.get('market_cap', None),
            'volume': item.get('volume', None),
            'keywords': extract_crypto_keywords(item.get('content', item.get('text', ''))),
            'emotional_intensity': calculate_emotional_intensity(item.get('content', item.get('text', ''))),
            'urgency_level': calculate_urgency_level(item.get('content', item.get('text', '')))
        }
        
        # Ensure coins_mentioned is a list
        if isinstance(processed_item['coins_mentioned'], str):
            processed_item['coins_mentioned'] = [processed_item['coins_mentioned']]
        elif not isinstance(processed_item['coins_mentioned'], list):
            processed_item['coins_mentioned'] = []
        
        # Parse timestamp
        try:
            dt = parse_date_universal(processed_item['timestamp'])
            if dt:
                processed_item['datetime'] = dt
                processed_item['hour'] = dt.hour
                processed_item['day_of_week'] = dt.strftime('%A')
                processed_item['date_str'] = dt.strftime('%Y-%m-%d')
                processed_item['time_str'] = dt.strftime('%H:%M')
        except:
            processed_item['datetime'] = datetime.now()
            processed_item['date_str'] = 'Unknown'
        
        processed.append(processed_item)
    
    return processed

def extract_crypto_keywords(text):
    """Extract crypto-related keywords from text."""
    crypto_keywords = [
        'bull', 'bear', 'moon', 'hodl', 'diamond hands', 'paper hands',
        'pump', 'dump', 'whale', 'ape', 'fomo', 'fud', 'dyor', 'wagmi',
        'ngmi', 'gm', 'leverage', 'liquidation', 'margin', 'futures',
        'defi', 'nft', 'dao', 'yield', 'stake', 'mining', 'halving'
    ]
    
    if not text:
        return []
    
    text_lower = text.lower()
    found_keywords = [kw for kw in crypto_keywords if kw in text_lower]
    
    # Add price patterns
    price_patterns = re.findall(r'\$[\d,]+(?:\.\d+)?', text)
    if price_patterns:
        found_keywords.extend(['price_mention'])
    
    return found_keywords

def calculate_emotional_intensity(text):
    """Calculate emotional intensity of text."""
    if not text:
        return 0.5
    
    high_intensity = ['!', 'MOON', 'CRASH', 'PUMP', 'DUMP', 'ROCKET', '🚀', '📈', '📉']
    intensity_score = sum(1 for word in high_intensity if word in text.upper())
    return min(1.0, intensity_score / 10)

def calculate_urgency_level(text):
    """Calculate urgency level of text."""
    if not text:
        return 'low'
    
    urgent_words = ['now', 'urgent', 'breaking', 'alert', 'immediate', 'quick', 'fast']
    text_lower = text.lower()
    urgency_count = sum(1 for word in urgent_words if word in text_lower)
    
    if urgency_count >= 2:
        return 'high'
    elif urgency_count == 1:
        return 'medium'
    else:
        return 'low'

# --- Advanced Analytics Functions ---

def create_sentiment_timeline(data):
    """Create advanced sentiment timeline with multiple metrics."""
    if not data:
        return go.Figure().add_annotation(
            text="No crypto sentiment data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    df = pd.DataFrame(data)
    
    # Group by hour for timeline
    df['hour_group'] = df['datetime'].dt.floor('H')
    hourly_data = df.groupby(['hour_group', 'sentiment']).size().unstack(fill_value=0)
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Sentiment Timeline', 'Confidence Distribution', 
                       'Engagement vs Sentiment', 'Emotional Intensity'),
        specs=[[{"secondary_y": True}, {"type": "histogram"}],
               [{"type": "scatter"}, {"type": "box"}]]
    )
    
    # Sentiment timeline
    if 'positive' in hourly_data.columns:
        fig.add_trace(go.Scatter(
            x=hourly_data.index, y=hourly_data['positive'],
            name='Positive', line=dict(color='green'), mode='lines+markers'
        ), row=1, col=1)
    
    if 'negative' in hourly_data.columns:
        fig.add_trace(go.Scatter(
            x=hourly_data.index, y=hourly_data['negative'],
            name='Negative', line=dict(color='red'), mode='lines+markers'
        ), row=1, col=1)
    
    if 'neutral' in hourly_data.columns:
        fig.add_trace(go.Scatter(
            x=hourly_data.index, y=hourly_data['neutral'],
            name='Neutral', line=dict(color='gray'), mode='lines+markers'
        ), row=1, col=1)
    
    # Confidence distribution
    fig.add_trace(go.Histogram(
        x=df['confidence'], name='Confidence', 
        marker_color='blue', opacity=0.7
    ), row=1, col=2)
    
    # Engagement vs Sentiment
    colors = {'positive': 'green', 'negative': 'red', 'neutral': 'gray'}
    for sentiment in df['sentiment'].unique():
        sentiment_data = df[df['sentiment'] == sentiment]
        fig.add_trace(go.Scatter(
            x=sentiment_data['engagement'], y=sentiment_data['confidence'],
            mode='markers', name=f'{sentiment.title()} Engagement',
            marker=dict(color=colors.get(sentiment, 'blue'), size=8, opacity=0.6)
        ), row=2, col=1)
    
    # Emotional intensity by sentiment
    fig.add_trace(go.Box(
        y=df[df['sentiment'] == 'positive']['emotional_intensity'],
        name='Positive Intensity', marker_color='green'
    ), row=2, col=2)
    
    fig.add_trace(go.Box(
        y=df[df['sentiment'] == 'negative']['emotional_intensity'],
        name='Negative Intensity', marker_color='red'
    ), row=2, col=2)
    
    fig.update_layout(height=800, showlegend=True, title_text="Crypto Sentiment Analytics Dashboard")
    return fig

def create_coin_analysis_chart(data):
    """Create comprehensive coin analysis visualization."""
    if not data:
        return go.Figure()
    
    # Count coin mentions
    coin_counts = Counter()
    coin_sentiments = defaultdict(list)
    
    for item in data:
        for coin in item['coins_mentioned']:
            if coin:
                coin_counts[coin] += 1
                coin_sentiments[coin].append(item['sentiment'])
    
    # Get top 15 coins
    top_coins = dict(coin_counts.most_common(15))
    
    if not top_coins:
        return go.Figure().add_annotation(
            text="No coin mention data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Calculate sentiment ratios for each coin
    coin_data = []
    for coin, count in top_coins.items():
        sentiments = coin_sentiments[coin]
        positive_ratio = sentiments.count('positive') / len(sentiments) if sentiments else 0
        negative_ratio = sentiments.count('negative') / len(sentiments) if sentiments else 0
        
        coin_data.append({
            'coin': coin,
            'mentions': count,
            'positive_ratio': positive_ratio,
            'negative_ratio': negative_ratio,
            'net_sentiment': positive_ratio - negative_ratio
        })
    
    df_coins = pd.DataFrame(coin_data)
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Top Mentioned Coins', 'Sentiment Distribution by Coin', 
                       'Net Sentiment Score', 'Mention Volume vs Sentiment'),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "scatter"}]]
    )
    
    # Top mentioned coins
    fig.add_trace(go.Bar(
        x=df_coins['coin'], y=df_coins['mentions'],
        name='Mentions', marker_color='blue'
    ), row=1, col=1)
    
    # Sentiment distribution
    fig.add_trace(go.Bar(
        x=df_coins['coin'], y=df_coins['positive_ratio'],
        name='Positive %', marker_color='green'
    ), row=1, col=2)
    
    fig.add_trace(go.Bar(
        x=df_coins['coin'], y=df_coins['negative_ratio'],
        name='Negative %', marker_color='red'
    ), row=1, col=2)
    
    # Net sentiment
    colors = ['green' if x > 0 else 'red' for x in df_coins['net_sentiment']]
    fig.add_trace(go.Bar(
        x=df_coins['coin'], y=df_coins['net_sentiment'],
        name='Net Sentiment', marker_color=colors
    ), row=2, col=1)
    
    # Volume vs sentiment scatter
    fig.add_trace(go.Scatter(
        x=df_coins['mentions'], y=df_coins['net_sentiment'],
        mode='markers+text', text=df_coins['coin'],
        textposition="top center", name='Coins',
        marker=dict(size=df_coins['mentions'], sizemode='diameter', sizeref=0.5)
    ), row=2, col=2)
    
    fig.update_layout(height=800, showlegend=True, title_text="Comprehensive Coin Analysis")
    return fig

def create_advanced_metrics_cards(data):
    """Create advanced metrics cards with trends."""
    if not data:
        return [
            dbc.Card(
                dbc.CardBody([
                    html.H4("No Data", className="card-title"),
                    html.P("No crypto sentiment data available", className="card-text")
                ]),
                color="warning", outline=True
            )
        ]
    
    df = pd.DataFrame(data)
    total_mentions = len(df)
    
    # Calculate time-based metrics
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    recent_hour = df[df['datetime'] >= hour_ago]
    recent_day = df[df['datetime'] >= day_ago]
    recent_week = df[df['datetime'] >= week_ago]
    
    # Sentiment distribution
    sentiment_counts = df['sentiment'].value_counts()
    dominant_sentiment = sentiment_counts.index[0] if len(sentiment_counts) > 0 else 'Unknown'
    
    # Top coin
    all_coins = [coin for coins in df['coins_mentioned'] for coin in coins if coin]
    top_coin = Counter(all_coins).most_common(1)[0] if all_coins else ('N/A', 0)
    
    # Average confidence
    avg_confidence = df['confidence'].mean() if not df['confidence'].isna().all() else 0
    
    # High urgency count
    high_urgency = len(df[df['urgency_level'] == 'high'])
    
    # Engagement metrics
    avg_engagement = df['engagement'].mean() if not df['engagement'].isna().all() else 0
    total_engagement = df['engagement'].sum() if not df['engagement'].isna().all() else 0
    
    # Emotional intensity
    avg_intensity = df['emotional_intensity'].mean() if not df['emotional_intensity'].isna().all() else 0
    
    cards = [
        # Total Volume Card
        dbc.Card(
            dbc.CardBody([
                html.H4(f"{total_mentions:,}", className="card-title text-primary"),
                html.P("Total Mentions", className="card-text"),
                html.Small([
                    html.I(className="fas fa-clock me-1"),
                    f"Last hour: {len(recent_hour)} | Last day: {len(recent_day)}"
                ], className="text-muted")
            ]),
            color="primary", outline=True, className="mb-3"
        ),
        
        # Dominant Sentiment Card
        dbc.Card(
            dbc.CardBody([
                html.H4(f"{dominant_sentiment.title()}", className="card-title text-success"),
                html.P("Dominant Sentiment", className="card-text"),
                html.Small([
                    html.I(className="fas fa-chart-pie me-1"),
                    f"{sentiment_counts.iloc[0] if len(sentiment_counts) > 0 else 0} occurrences"
                ], className="text-muted")
            ]),
            color="success", outline=True, className="mb-3"
        ),
        
        # Top Coin Card
        dbc.Card(
            dbc.CardBody([
                html.H4(f"{top_coin[0]}", className="card-title text-warning"),
                html.P("Most Mentioned Coin", className="card-text"),
                html.Small([
                    html.I(className="fas fa-coins me-1"),
                    f"{top_coin[1]} mentions"
                ], className="text-muted")
            ]),
            color="warning", outline=True, className="mb-3"
        ),
        
        # Confidence Score Card
        dbc.Card(
            dbc.CardBody([
                html.H4(f"{avg_confidence:.1%}", className="card-title text-info"),
                html.P("Avg Confidence", className="card-text"),
                html.Small([
                    html.I(className="fas fa-chart-line me-1"),
                    f"Based on {total_mentions} data points"
                ], className="text-muted")
            ]),
            color="info", outline=True, className="mb-3"
        ),
        
        # Urgency Alert Card
        dbc.Card(
            dbc.CardBody([
                html.H4(f"{high_urgency}", className="card-title text-danger"),
                html.P("High Urgency Alerts", className="card-text"),
                html.Small([
                    html.I(className="fas fa-exclamation-triangle me-1"),
                    f"{(high_urgency/total_mentions*100):.1f}% of total" if total_mentions > 0 else "0%"
                ], className="text-muted")
            ]),
            color="danger", outline=True, className="mb-3"
        ),
        
        # Engagement Card
        dbc.Card(
            dbc.CardBody([
                html.H4(f"{total_engagement:,.0f}", className="card-title text-secondary"),
                html.P("Total Engagement", className="card-text"),
                html.Small([
                    html.I(className="fas fa-heart me-1"),
                    f"Avg: {avg_engagement:.1f} per post"
                ], className="text-muted")
            ]),
            color="secondary", outline=True, className="mb-3"
        )
    ]
    
    return cards

def create_advanced_data_table(data):
    """Create advanced, interactive data table."""
    if not data:
        return html.Div("No crypto sentiment data to display.")
    
    # Prepare data for table
    table_data = []
    for item in data[:100]:  # Show top 100 items
        coins_str = ', '.join(item['coins_mentioned'][:3])
        if len(item['coins_mentioned']) > 3:
            coins_str += f" +{len(item['coins_mentioned'])-3} more"
        
        keywords_str = ', '.join(item['keywords'][:3])
        if len(item['keywords']) > 3:
            keywords_str += '...'
        
        table_data.append({
            'timestamp': item['date_str'] + ' ' + item['time_str'],
            'sentiment': item['sentiment'].title(),
            'confidence': f"{item['confidence']:.1%}",
            'coins': coins_str,
            'source': item['source'],
            'engagement': f"{item['engagement']:,}",
            'urgency': item['urgency_level'].title(),
            'intensity': f"{item['emotional_intensity']:.1f}",
            'keywords': keywords_str,
            'content': item['content'][:150] + ('...' if len(item['content']) > 150 else ''),
            'url': item['url']
        })
    
    columns = [
        {"name": "Time", "id": "timestamp", "type": "text"},
        {"name": "Sentiment", "id": "sentiment", "type": "text"},
        {"name": "Confidence", "id": "confidence", "type": "text"},
        {"name": "Coins", "id": "coins", "type": "text"},
        {"name": "Source", "id": "source", "type": "text"},
        {"name": "Engagement", "id": "engagement", "type": "numeric"},
        {"name": "Urgency", "id": "urgency", "type": "text"},
        {"name": "Intensity", "id": "intensity", "type": "numeric"},
        {"name": "Keywords", "id": "keywords", "type": "text"},
        {"name": "Content", "id": "content", "type": "text"}
    ]
    
    return dash_table.DataTable(
        data=table_data,
        columns=columns,
        filter_action="native",
        sort_action="native",
        page_size=20,
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'minWidth': '100px',
            'maxWidth': '300px',
            'whiteSpace': 'normal'
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{sentiment} = Positive'},
                'backgroundColor': '#d4edda',
                'color': 'black',
            },
            {
                'if': {'filter_query': '{sentiment} = Negative'},
                'backgroundColor': '#f8d7da',
                'color': 'black',
            },
            {
                'if': {'filter_query': '{urgency} = High'},
                'fontWeight': 'bold'
            }
        ],
        tooltip_data=[
            {
                column: {'value': str(row[column]), 'type': 'markdown'}
                for column in ['content', 'url']
            } for row in table_data
        ],
        tooltip_duration=None
    )

# --- Enhanced Main Tab Function ---

def crypto_tab():
    """Enhanced crypto/financial tab with advanced analytics."""
    # Load fresh data each time
    crypto_data = load_crypto_sentiment()
    processed_data = process_crypto_data(crypto_data)
    
    return dbc.Container([
        # Enhanced Header
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-coins me-2"),
                    "🪙 Crypto Intelligence Center"
                ], className="mb-3"),
                html.P([
                    "Advanced cryptocurrency sentiment analysis, market intelligence, and trend monitoring. ",
                    html.Strong(f"Analyzing {len(processed_data):,} data points "),
                    "from multiple sources with real-time insights."
                ], className="text-muted mb-4"),
                
                # Quick Stats Bar
                dbc.Row([
                    dbc.Col([
                        dbc.Badge(f"📊 {len(processed_data)} Total Records", color="primary", className="me-2"),
                        dbc.Badge(f"🔄 Last Updated: {datetime.now().strftime('%H:%M')}", color="secondary", className="me-2"),
                        dbc.Badge("📈 Live Analysis", color="success", className="me-2"),
                    ])
                ], className="mb-4")
            ])
        ]),
        
        # Advanced Summary Cards
        dbc.Row([
            dbc.Col(card, md=4, lg=2) for card in create_advanced_metrics_cards(processed_data)
        ], className="mb-4"),
        
        # Advanced Charts Section
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="fas fa-chart-line me-2"),
                            "Sentiment Analytics Dashboard"
                        ], className="mb-0"),
                        html.Small("Real-time sentiment timeline, confidence metrics, and engagement analysis", 
                                 className="text-muted")
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="crypto-sentiment-timeline",
                            figure=create_sentiment_timeline(processed_data),
                            config={'displayModeBar': True, 'toImageButtonOptions': {'format': 'png'}}
                        )
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Coin Analysis Section
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="fas fa-coins me-2"),
                            "Comprehensive Coin Analysis"
                        ], className="mb-0"),
                        html.Small("Mention volume, sentiment distribution, and market perception analysis", 
                                 className="text-muted")
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="crypto-coin-analysis",
                            figure=create_coin_analysis_chart(processed_data),
                            config={'displayModeBar': True}
                        )
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Interactive Filters Section
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🔍 Advanced Filters & Search"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Sentiment Filter:"),
                                dcc.Dropdown(
                                    id="sentiment-filter",
                                    options=[
                                        {'label': 'All Sentiments', 'value': 'all'},
                                        {'label': 'Positive', 'value': 'positive'},
                                        {'label': 'Negative', 'value': 'negative'},
                                        {'label': 'Neutral', 'value': 'neutral'}
                                    ],
                                    value='all',
                                    clearable=False
                                )
                            ], md=3),
                            dbc.Col([
                                html.Label("Urgency Level:"),
                                dcc.Dropdown(
                                    id="urgency-filter",
                                    options=[
                                        {'label': 'All Levels', 'value': 'all'},
                                        {'label': 'High', 'value': 'high'},
                                        {'label': 'Medium', 'value': 'medium'},
                                        {'label': 'Low', 'value': 'low'}
                                    ],
                                    value='all',
                                    clearable=False
                                )
                            ], md=3),
                            dbc.Col([
                                html.Label("Source Filter:"),
                                dcc.Dropdown(
                                    id="source-filter",
                                    options=[{'label': 'All Sources', 'value': 'all'}] + 
                                            [{'label': source, 'value': source} 
                                             for source in set(item['source'] for item in processed_data)],
                                    value='all',
                                    clearable=False
                                )
                            ], md=3),
                            dbc.Col([
                                html.Label("Search Keywords:"),
                                dcc.Input(
                                    id="keyword-search",
                                    type="text",
                                    placeholder="Search in content...",
                                    className="form-control"
                                )
                            ], md=3)
                        ])
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Advanced Data Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="fas fa-table me-2"),
                            "Interactive Data Explorer"
                        ], className="mb-0"),
                        html.Small(f"Detailed view of {min(100, len(processed_data))} most recent entries with advanced filtering", 
                                 className="text-muted")
                    ]),
                    dbc.CardBody([
                        create_advanced_data_table(processed_data),
                        
                        # Export Options
                        dbc.Row([
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button("📊 Export CSV", color="primary", size="sm", className="me-2"),
                                    dbc.Button("📈 Export Analytics", color="secondary", size="sm", className="me-2"),
                                    dbc.Button("🔔 Set Alerts", color="warning", size="sm")
                                ], className="mt-3")
                            ])
                        ])
                    ])
                ])
            ])
        ])
    ], fluid=True)