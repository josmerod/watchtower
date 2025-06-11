"""
Developer Communities Tab Component

This component displays data from various developer communities including:
- DEV.to articles and discussions
- Indie Hackers posts and insights
- Lobsters stories and discussions
- Discord trending communities
- HackerNews Ask discussions
- Stack Overflow trending questions

Provides filtering, sorting, and analytics for community trends.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from web.fullstreamlit.utils.helpers import make_clickable

# Get the project root directory
def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    return project_root

# Define dev communities data paths using absolute paths
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Data source file mappings with absolute paths
DEV_DATA_SOURCES = {
    'dev_community': os.path.join(DATA_DIR, 'dev_community', 'dev_community_latest.json'),
    'indie_hackers': os.path.join(DATA_DIR, 'indie_hackers', 'indiehackers_posts_latest.json'),
    'lobsters': os.path.join(DATA_DIR, 'lobsters', 'lobsters_stories_latest.json'),
    'discord_trending': os.path.join(DATA_DIR, 'discord_trending', 'discord_communities_latest.json'),
    'hackernews_ask': os.path.join(DATA_DIR, 'hackernews_ask', 'hackernews_ask_latest.json'),
    'stackoverflow_trends': os.path.join(DATA_DIR, 'stackoverflow_trends', 'stackoverflow_trends_latest.json')
}

def clean_dataframe_for_caching(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame to avoid unhashable type errors."""
    if df.empty:
        return df
    
    # Create a copy to avoid modifying the original
    df_clean = df.copy()
    
    # Convert any dictionary or list columns to strings
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            # Check if column contains dictionaries or lists
            try:
                # Convert all values that are dict or list to JSON strings
                df_clean[col] = df_clean[col].apply(
                    lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list)) else x
                )
            except (TypeError, ValueError):
                # If there's any issue, convert the entire column to string
                df_clean[col] = df_clean[col].astype(str)
    
    return df_clean

def load_community_data() -> Dict[str, pd.DataFrame]:
    """Load all developer community data sources."""
    community_data = {}
    
    for source_name, file_path in DEV_DATA_SOURCES.items():
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        df = pd.DataFrame(data)
                        # Clean DataFrame to avoid caching issues
                        df = clean_dataframe_for_caching(df)
                        community_data[source_name] = df
                        st.sidebar.success(f"✅ {source_name.replace('_', ' ').title()}: {len(df)} items")
                    else:
                        st.sidebar.warning(f"⚠️ {source_name.replace('_', ' ').title()}: No data")
            else:
                st.sidebar.error(f"❌ {source_name.replace('_', ' ').title()}: File not found")
        except Exception as e:
            st.sidebar.error(f"❌ {source_name.replace('_', ' ').title()}: Error loading data")
    
    return community_data

def display_metrics_overview(community_data: Dict[str, pd.DataFrame]):
    """Display overview metrics for all community data."""
    col1, col2, col3, col4 = st.columns(4)
    
    total_items = sum(len(df) for df in community_data.values())
    
    with col1:
        st.metric("Total Items", f"{total_items:,}")
    
    with col2:
        trending_count = 0
        for df in community_data.values():
            if 'is_trending' in df.columns:
                trending_count += len(df[df['is_trending'] == True])
        st.metric("Trending Items", f"{trending_count:,}")
    
    with col3:
        platforms_count = len(community_data)
        st.metric("Data Sources", f"{platforms_count}")
    
    with col4:
        fresh_count = 0
        for df in community_data.values():
            if 'freshness' in df.columns:
                fresh_count += len(df[df['freshness'].isin(['very_fresh', 'fresh'])])
            elif 'hours_since_posted' in df.columns:
                fresh_count += len(df[df['hours_since_posted'] <= 24])
        st.metric("Fresh Content", f"{fresh_count:,}")

def display_dev_community_data(df: pd.DataFrame):
    """Display DEV Community data."""
    st.subheader("🔥 DEV Community Articles")
    
    if df.empty:
        st.warning("No DEV Community data available")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        content_types = ['All'] + list(df['content_type'].unique()) if 'content_type' in df.columns else ['All']
        selected_type = st.selectbox("Content Type", content_types, key="dev_content_type")
    
    with col2:
        # Handle tags - ensure they are processed as lists when they might be strings or lists
        if 'tag_list' in df.columns:
            # Process tags regardless of whether they are strings or lists
            all_tags = []
            for tag_data in df['tag_list'].dropna():
                if isinstance(tag_data, str):
                    all_tags.extend(tag_data.split(', '))
                elif isinstance(tag_data, list):
                    all_tags.extend(tag_data)
            
            tags = ['All'] + list(pd.Series(all_tags).value_counts().head(20).index)
        else:
            tags = ['All']
        
        selected_tag = st.selectbox("Tag", tags, key="dev_tag")
    
    with col3:
        popularity = ['All'] + list(df['popularity_category'].unique()) if 'popularity_category' in df.columns else ['All']
        selected_popularity = st.selectbox("Popularity", popularity, key="dev_popularity")
    
    # Apply filters
    filtered_df = df.copy()
    if selected_type != 'All' and 'content_type' in df.columns:
        filtered_df = filtered_df[filtered_df['content_type'] == selected_type]
    if selected_tag != 'All' and 'tag_list' in df.columns:
        filtered_df = filtered_df[filtered_df['tag_list'].str.contains(selected_tag, na=False)]
    if selected_popularity != 'All' and 'popularity_category' in df.columns:
        filtered_df = filtered_df[filtered_df['popularity_category'] == selected_popularity]
    
    # Display articles
    for _, article in filtered_df.head(10).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**[{article.get('title', 'No Title')}]({article.get('url', '#')})**")
                st.write(f"👤 {article.get('author', 'Unknown')} | "
                        f"❤️ {article.get('reactions_count', 0)} | "
                        f"💬 {article.get('comments_count', 0)} | "
                        f"📖 {article.get('reading_time_minutes', 0)} min")
                
                # Tags
                tag_data = article.get('tag_list', [])
                if isinstance(tag_data, str):
                    tags = tag_data.split(', ') if tag_data else []
                elif isinstance(tag_data, list):
                    tags = tag_data
                else:
                    tags = []
                
                if tags:
                    tag_html = ' '.join([f"<span style='background-color: #E3F2FD; color: #1976D2; padding: 2px 6px; border-radius: 12px; font-size: 12px;'>{tag}</span>" for tag in tags[:4]])
                    st.markdown(tag_html, unsafe_allow_html=True)
            
            with col2:
                engagement_score = article.get('engagement_score', 0)
                st.metric("Engagement", f"{engagement_score:.1f}")
                
                content_type = article.get('content_type', 'article')
                st.markdown(f'<span style="background-color: #E8F5E8; color: #2E7D32; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 500;">{content_type.title()}</span>', unsafe_allow_html=True)
        
        st.divider()

def display_stackoverflow_trends(df: pd.DataFrame):
    """Display Stack Overflow trending questions."""
    st.subheader("❓ Stack Overflow Trending Questions")
    
    if df.empty:
        st.warning("No Stack Overflow data available")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tech_categories = ['All'] + list(df['tech_category'].unique()) if 'tech_category' in df.columns else ['All']
        selected_tech = st.selectbox("Technology", tech_categories, key="so_tech")
    
    with col2:
        difficulties = ['All'] + list(df['difficulty'].unique()) if 'difficulty' in df.columns else ['All']
        selected_difficulty = st.selectbox("Difficulty", difficulties, key="so_difficulty")
    
    with col3:
        answer_status = ['All'] + list(df['answer_status'].unique()) if 'answer_status' in df.columns else ['All']
        selected_status = st.selectbox("Answer Status", answer_status, key="so_status")
    
    # Apply filters
    filtered_df = df.copy()
    if selected_tech != 'All' and 'tech_category' in df.columns:
        filtered_df = filtered_df[filtered_df['tech_category'] == selected_tech]
    if selected_difficulty != 'All' and 'difficulty' in df.columns:
        filtered_df = filtered_df[filtered_df['difficulty'] == selected_difficulty]
    if selected_status != 'All' and 'answer_status' in df.columns:
        filtered_df = filtered_df[filtered_df['answer_status'] == selected_status]
    
    # Display questions
    for _, question in filtered_df.head(10).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**[{question.get('title', 'No Title')}]({question.get('link', '#')})**")
                
                metrics_text = f"⬆️ {question.get('score', 0)} | "
                metrics_text += f"👀 {question.get('view_count', 0):,} views | "
                metrics_text += f"💬 {question.get('answer_count', 0)} answers"
                st.write(metrics_text)
                
                tags = question.get('tags', []) if isinstance(question.get('tags'), list) else []
                if tags:
                    tag_html = ' '.join([f"<span style='background-color: #FFF3E0; color: #F57C00; padding: 2px 6px; border-radius: 12px; font-size: 12px;'>{tag}</span>" for tag in tags[:5]])
                    st.markdown(tag_html, unsafe_allow_html=True)
            
            with col2:
                trending_score = question.get('trending_score', 0)
                st.metric("Trending Score", f"{trending_score:.1f}")
                
                difficulty = question.get('difficulty', 'intermediate')
                if difficulty == 'beginner':
                    st.success("🟢 Beginner")
                elif difficulty == 'advanced':
                    st.error("🔴 Advanced")
                else:
                    st.warning("🟡 Intermediate")
        
        st.divider()

def display_discord_communities(df: pd.DataFrame):
    """Display Discord trending communities."""
    st.subheader("💬 Discord Trending Communities")
    
    if df.empty:
        st.warning("No Discord communities data available")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        community_types = ['All'] + list(df['community_type'].unique()) if 'community_type' in df.columns else ['All']
        selected_type = st.selectbox("Community Type", community_types, key="discord_type")
    
    with col2:
        size_categories = ['All'] + list(df['size_category'].unique()) if 'size_category' in df.columns else ['All']
        selected_size = st.selectbox("Size Category", size_categories, key="discord_size")
    
    with col3:
        activity_levels = ['All'] + list(df['activity_level'].unique()) if 'activity_level' in df.columns else ['All']
        selected_activity = st.selectbox("Activity Level", activity_levels, key="discord_activity")
    
    # Apply filters
    filtered_df = df.copy()
    if selected_type != 'All' and 'community_type' in df.columns:
        filtered_df = filtered_df[filtered_df['community_type'] == selected_type]
    if selected_size != 'All' and 'size_category' in df.columns:
        filtered_df = filtered_df[filtered_df['size_category'] == selected_size]
    if selected_activity != 'All' and 'activity_level' in df.columns:
        filtered_df = filtered_df[filtered_df['activity_level'] == selected_activity]
    
    # Display communities
    for _, community in filtered_df.head(8).iterrows():
        with st.container():
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**{community.get('name', 'No Name')}**")
                st.write(community.get('description', 'No description available')[:150] + '...')
                
                metrics_text = f"👥 {community.get('member_count', 0):,} members | "
                metrics_text += f"🟢 {community.get('online_members', 0):,} online | "
                metrics_text += f"📈 +{community.get('daily_growth', 0)} daily"
                st.write(metrics_text)
                
                if community.get('verified'):
                    st.success("✅ Verified")
                elif community.get('partnered'):
                    st.info("🤝 Partnered")
            
            with col2:
                trending_score = community.get('trending_score', 0)
                st.metric("Trending Score", f"{trending_score:.1f}")
                
                engagement_rate = community.get('engagement_rate', 0)
                st.metric("Engagement Rate", f"{engagement_rate:.1f}%")
        
        st.divider()

def render(logger, community_data: Dict[str, pd.DataFrame] = None):
    """Render the Developer Communities tab."""
    
    st.header("👨‍💻 Developer Communities")
    st.markdown("Discover trending discussions, questions, and communities from the developer ecosystem")
    
    # Load data if not provided
    if community_data is None:
        with st.spinner("Loading community data..."):
            community_data = load_community_data()
    
    if not community_data:
        st.warning("No community data available. Please run the ETL processes first.")
        return
    
    # Display overview metrics
    display_metrics_overview(community_data)
    
    st.divider()
    
    # Create tabs for different data sources
    tab_names = []
    available_data = {}
    
    if 'dev_community' in community_data:
        tab_names.append("🔥 DEV.to")
        available_data['dev'] = community_data['dev_community']
    
    if 'stackoverflow_trends' in community_data:
        tab_names.append("❓ Stack Overflow")
        available_data['stackoverflow'] = community_data['stackoverflow_trends']
    
    if 'discord_trending' in community_data:
        tab_names.append("💬 Discord")
        available_data['discord'] = community_data['discord_trending']
    
    if 'hackernews_ask' in community_data:
        tab_names.append("🗣️ Ask HN")
        available_data['askhn'] = community_data['hackernews_ask']
    
    if 'indie_hackers' in community_data:
        tab_names.append("🚀 Indie Hackers")
        available_data['indie'] = community_data['indie_hackers']
    
    if 'lobsters' in community_data:
        tab_names.append("🦞 Lobsters")
        available_data['lobsters'] = community_data['lobsters']
    
    if not tab_names:
        st.warning("No community data sources available.")
        return
    
    # Create tabs
    tabs = st.tabs(tab_names)
    
    # DEV.to tab
    if 'dev' in available_data:
        with tabs[list(available_data.keys()).index('dev')]:
            display_dev_community_data(available_data['dev'])
    
    # Stack Overflow tab
    if 'stackoverflow' in available_data:
        with tabs[list(available_data.keys()).index('stackoverflow')]:
            display_stackoverflow_trends(available_data['stackoverflow'])
    
    # Discord tab
    if 'discord' in available_data:
        with tabs[list(available_data.keys()).index('discord')]:
            display_discord_communities(available_data['discord'])
    
    # Other tabs (simplified display)
    for key, data in available_data.items():
        if key not in ['dev', 'stackoverflow', 'discord']:
            with tabs[list(available_data.keys()).index(key)]:
                st.subheader(f"{key.replace('_', ' ').title()} Data")
                
                if not data.empty:
                    # Display basic metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Items", len(data))
                    
                    with col2:
                        if 'engagement_score' in data.columns:
                            avg_engagement = data['engagement_score'].mean()
                            st.metric("Avg Engagement", f"{avg_engagement:.1f}")
                        elif 'score' in data.columns:
                            avg_score = data['score'].mean()
                            st.metric("Avg Score", f"{avg_score:.1f}")
                    
                    with col3:
                        if 'is_trending' in data.columns:
                            trending_count = len(data[data['is_trending'] == True])
                            st.metric("Trending", trending_count)
                    
                    # Display top items
                    st.subheader("Top Items")
                    for _, item in data.head(5).iterrows():
                        title = item.get('title', 'No Title')
                        url = item.get('url', '#')
                        score = item.get('engagement_score', item.get('score', 0))
                        
                        st.markdown(f"**[{title}]({url})** - Score: {score:.1f}")
                else:
                    st.warning(f"No data available for {key.replace('_', ' ').title()}")
    
    # Footer with last update
    if community_data:
        st.divider()
        st.markdown("*Data refreshed automatically from multiple developer community sources*")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 