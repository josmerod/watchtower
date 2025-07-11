"""
Crypto Sentiment tab component for the Watchtower Streamlit application.
Displays cryptocurrency sentiment analysis and trends.
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Get the project root directory
def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    return project_root

# Define crypto data path using absolute path
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CRYPTO_DATA_DIR = os.path.join(DATA_DIR, "crypto_sentiment")
CRYPTO_DATA_FILE = os.path.join(CRYPTO_DATA_DIR, "crypto_sentiment_latest.json")

def clean_dataframe_for_caching(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame to avoid unhashable type errors."""
    if df.empty:
        return df
    
    # Convert any dictionary or list columns to strings
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check if column contains dictionaries or lists
            sample_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(sample_value, (dict, list)):
                df[col] = df[col].astype(str)
    
    return df

def load_crypto_sentiment_data() -> pd.DataFrame:
    """Load cryptocurrency sentiment analysis data."""
    data_file = CRYPTO_DATA_FILE
    
    try:
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data:
                    df = pd.DataFrame(data)
                    # Clean DataFrame to avoid caching issues
                    df = clean_dataframe_for_caching(df)
                    st.sidebar.success(f"✅ Crypto Sentiment: {len(df)} items")
                    return df
                else:
                    st.sidebar.warning("⚠️ Crypto Sentiment: No data")
                    return pd.DataFrame()
        else:
            st.sidebar.error("❌ Crypto Sentiment: File not found")
            return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"❌ Crypto Sentiment: Error loading data - {str(e)}")
        return pd.DataFrame()

def display_crypto_metrics(df: pd.DataFrame):
    """Display overview metrics for crypto sentiment data."""
    if df.empty:
        st.warning("No cryptocurrency sentiment data available")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_mentions = len(df)
        st.metric("Total Mentions", f"{total_mentions:,}")
    
    with col2:
        if 'sentiment_score' in df.columns:
            avg_sentiment = df['sentiment_score'].mean()
            sentiment_emoji = "🟢" if avg_sentiment > 0.1 else "🔴" if avg_sentiment < -0.1 else "🟡"
            st.metric("Avg Sentiment", f"{avg_sentiment:.2f} {sentiment_emoji}")
        else:
            st.metric("Avg Sentiment", "N/A")
    
    with col3:
        if 'sentiment_category' in df.columns:
            bullish_count = len(df[df['sentiment_category'].isin(['bullish', 'very_bullish'])])
            bullish_pct = (bullish_count / total_mentions * 100) if total_mentions > 0 else 0
            st.metric("Bullish Sentiment", f"{bullish_pct:.1f}%")
        else:
            st.metric("Bullish Sentiment", "N/A")
    
    with col4:
        if 'platform' in df.columns:
            platform_count = df['platform'].nunique()
            st.metric("Data Sources", f"{platform_count}")
        else:
            st.metric("Data Sources", "N/A")

def display_sentiment_distribution(df: pd.DataFrame):
    """Display sentiment distribution charts."""
    if df.empty or 'sentiment_category' not in df.columns:
        return
    
    st.subheader("📊 Sentiment Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sentiment category pie chart
        sentiment_counts = df['sentiment_category'].value_counts()
        colors = {
            'very_bullish': '#00C851',
            'bullish': '#4CAF50', 
            'neutral': '#FFC107',
            'bearish': '#FF9800',
            'very_bearish': '#F44336'
        }
        
        fig = px.pie(
            values=sentiment_counts.values,
            names=sentiment_counts.index,
            title="Overall Sentiment Distribution",
            color=sentiment_counts.index,
            color_discrete_map=colors
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Sentiment score histogram
        if 'sentiment_score' in df.columns:
            fig = px.histogram(
                df,
                x='sentiment_score',
                title="Sentiment Score Distribution",
                nbins=30,
                color_discrete_sequence=['#2E86AB']
            )
            fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Neutral")
            st.plotly_chart(fig, use_container_width=True)

def display_crypto_leaderboard(df: pd.DataFrame):
    """Display cryptocurrency leaderboard by mentions and sentiment."""
    if df.empty or 'cryptocurrency' not in df.columns:
        return
    
    st.subheader("🏆 Cryptocurrency Leaderboard")
    
    # Group by cryptocurrency
    crypto_stats = df.groupby('cryptocurrency').agg({
        'sentiment_score': ['mean', 'count'],
        'platform': 'nunique'
    }).round(3)
    
    crypto_stats.columns = ['avg_sentiment', 'mentions', 'platforms']
    crypto_stats = crypto_stats.reset_index()
    crypto_stats = crypto_stats.sort_values('mentions', ascending=False)
    
    # Display top cryptocurrencies
    for i, (_, crypto) in enumerate(crypto_stats.head(10).iterrows()):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            crypto_name = crypto['cryptocurrency']
            rank = i + 1
            
            # Add emoji based on sentiment
            sentiment = crypto['avg_sentiment']
            if sentiment > 0.2:
                emoji = "🚀"
            elif sentiment > 0:
                emoji = "📈"
            elif sentiment < -0.2:
                emoji = "📉"
            else:
                emoji = "➡️"
            
            st.markdown(f"**#{rank} {emoji} {crypto_name}**")
        
        with col2:
            st.metric("Mentions", f"{int(crypto['mentions'])}")
        
        with col3:
            sentiment_color = "normal"
            if sentiment > 0.1:
                sentiment_color = "green"
            elif sentiment < -0.1:
                sentiment_color = "red"
            
            st.metric("Avg Sentiment", f"{sentiment:.2f}", delta_color=sentiment_color)
        
        with col4:
            st.metric("Platforms", f"{int(crypto['platforms'])}")
        
        st.divider()

def display_platform_analysis(df: pd.DataFrame):
    """Display platform-wise sentiment analysis."""
    if df.empty or 'platform' not in df.columns:
        return
    
    st.subheader("📱 Platform Analysis")
    
    # Platform sentiment comparison
    platform_stats = df.groupby('platform').agg({
        'sentiment_score': 'mean',
        'cryptocurrency': 'count'
    }).round(3)
    
    platform_stats.columns = ['avg_sentiment', 'total_mentions']
    platform_stats = platform_stats.reset_index()
    platform_stats = platform_stats.sort_values('total_mentions', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Platform mentions bar chart
        fig = px.bar(
            platform_stats,
            x='platform',
            y='total_mentions',
            title="Mentions by Platform",
            color='total_mentions',
            color_continuous_scale='Blues'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Platform sentiment comparison
        fig = px.bar(
            platform_stats,
            x='platform',
            y='avg_sentiment',
            title="Average Sentiment by Platform",
            color='avg_sentiment',
            color_continuous_scale='RdYlGn',
            color_continuous_midpoint=0
        )
        fig.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="Neutral")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

def display_trending_mentions(df: pd.DataFrame):
    """Display trending cryptocurrency mentions."""
    if df.empty:
        return
    
    st.subheader("🔥 Trending Mentions")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'platform' in df.columns:
            platforms = ['All'] + sorted(df['platform'].unique().tolist())
            selected_platform = st.selectbox("Platform", platforms, key="crypto_platform")
        else:
            selected_platform = 'All'
    
    with col2:
        if 'sentiment_category' in df.columns:
            sentiments = ['All'] + sorted(df['sentiment_category'].unique().tolist())
            selected_sentiment = st.selectbox("Sentiment", sentiments, key="crypto_sentiment")
        else:
            selected_sentiment = 'All'
    
    with col3:
        if 'cryptocurrency' in df.columns:
            cryptos = ['All'] + sorted(df['cryptocurrency'].unique().tolist())
            selected_crypto = st.selectbox("Cryptocurrency", cryptos, key="crypto_coin")
        else:
            selected_crypto = 'All'
    
    # Apply filters
    filtered_df = df.copy()
    if selected_platform != 'All' and 'platform' in df.columns:
        filtered_df = filtered_df[filtered_df['platform'] == selected_platform]
    if selected_sentiment != 'All' and 'sentiment_category' in df.columns:
        filtered_df = filtered_df[filtered_df['sentiment_category'] == selected_sentiment]
    if selected_crypto != 'All' and 'cryptocurrency' in df.columns:
        filtered_df = filtered_df[filtered_df['cryptocurrency'] == selected_crypto]
    
    # Sort by sentiment score and recency
    if 'sentiment_score' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(['sentiment_score', 'fetched_at'], ascending=[False, False])
    
    # Display mentions
    for _, mention in filtered_df.head(10).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                title = mention.get('title', mention.get('content', 'No title'))[:100] + "..."
                url = mention.get('url', '#')
                platform = mention.get('platform', 'Unknown')
                crypto = mention.get('cryptocurrency', 'Unknown')
                
                st.markdown(f"**[{title}]({url})**")
                st.write(f"🪙 {crypto} | 📱 {platform}")
                
                # Content preview
                content = mention.get('content', '')
                if content:
                    st.write(f"💬 {content[:200]}...")
            
            with col2:
                sentiment_score = mention.get('sentiment_score', 0)
                sentiment_category = mention.get('sentiment_category', 'neutral')
                
                # Color code sentiment
                if sentiment_score > 0.2:
                    st.success(f"🚀 {sentiment_score:.2f}")
                elif sentiment_score > 0:
                    st.info(f"📈 {sentiment_score:.2f}")
                elif sentiment_score < -0.2:
                    st.error(f"📉 {sentiment_score:.2f}")
                else:
                    st.warning(f"➡️ {sentiment_score:.2f}")
                
                st.caption(sentiment_category.replace('_', ' ').title())
        
        st.divider()

def create_sentiment_timeline(df: pd.DataFrame):
    """Create sentiment timeline chart."""
    if df.empty or 'fetched_at' not in df.columns:
        return
    
    st.subheader("📈 Sentiment Timeline")
    
    try:
        # Convert fetched_at to datetime
        df['timestamp'] = pd.to_datetime(df['fetched_at'])
        
        # Group by hour and calculate average sentiment
        df['hour'] = df['timestamp'].dt.floor('H')
        hourly_sentiment = df.groupby(['hour', 'cryptocurrency'])['sentiment_score'].mean().reset_index()
        
        # Create line chart
        fig = px.line(
            hourly_sentiment,
            x='hour',
            y='sentiment_score',
            color='cryptocurrency',
            title="Sentiment Over Time by Cryptocurrency",
            labels={'sentiment_score': 'Sentiment Score', 'hour': 'Time'}
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Neutral")
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error creating timeline: {str(e)}")

def render(logger):
    """Render the Cryptocurrency Sentiment tab."""
    
    st.header("₿ Cryptocurrency Sentiment")
    st.markdown("Real-time sentiment analysis across social media and news platforms")
    
    # Load data
    with st.spinner("Loading cryptocurrency sentiment data..."):
        df = load_crypto_sentiment_data()
    
    if df.empty:
        st.warning("No cryptocurrency sentiment data available. Please run the crypto sentiment miner first.")
        st.info("Run: `python src/miners/crypto_sentiment_miner.py` to collect sentiment data.")
        return
    
    # Display overview metrics
    display_crypto_metrics(df)
    
    st.divider()
    
    # Create tabs for different views
    tabs = st.tabs(["🏆 Leaderboard", "📊 Analytics", "🔥 Trending", "📈 Timeline"])
    
    with tabs[0]:
        display_crypto_leaderboard(df)
    
    with tabs[1]:
        display_sentiment_distribution(df)
        st.divider()
        display_platform_analysis(df)
    
    with tabs[2]:
        display_trending_mentions(df)
    
    with tabs[3]:
        create_sentiment_timeline(df)
    
    # Market sentiment summary
    if not df.empty and 'sentiment_score' in df.columns:
        st.divider()
        
        avg_sentiment = df['sentiment_score'].mean()
        total_mentions = len(df)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if avg_sentiment > 0.1:
                st.success("📈 **Market Sentiment: BULLISH**")
                st.write("The overall sentiment is positive across platforms.")
            elif avg_sentiment < -0.1:
                st.error("📉 **Market Sentiment: BEARISH**")
                st.write("The overall sentiment is negative across platforms.")
            else:
                st.warning("➡️ **Market Sentiment: NEUTRAL**")
                st.write("The market sentiment is mixed or neutral.")
        
        with col2:
            if 'cryptocurrency' in df.columns:
                top_crypto = df['cryptocurrency'].value_counts().index[0]
                top_crypto_mentions = df['cryptocurrency'].value_counts().iloc[0]
                st.info(f"🪙 **Most Discussed: {top_crypto}**")
                st.write(f"With {top_crypto_mentions} mentions")
        
        with col3:
            if 'platform' in df.columns:
                most_active_platform = df['platform'].value_counts().index[0]
                platform_mentions = df['platform'].value_counts().iloc[0]
                st.info(f"📱 **Most Active: {most_active_platform}**")
                st.write(f"With {platform_mentions} mentions")
    
    # Footer with last update
    st.divider()
    st.markdown("*Sentiment data refreshed automatically from multiple social media and news platforms*")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 