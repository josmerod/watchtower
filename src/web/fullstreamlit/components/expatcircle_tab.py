"""
ExpatCircle News Tab Component

This component displays data from ExpatCircle News, an expat-focused news aggregation site.
Provides filtering, sorting, and analytics for expat community discussions and news.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
from src.web.fullstreamlit.utils.helpers import make_clickable

# Get the project root directory
def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    return project_root


@st.cache_data(ttl=3600)
def load_expatcircle_data():
    """Load ExpatCircle News data from JSON file."""
    try:
        project_root = get_project_root()
        data_file = os.path.join(project_root, "data", "expatcircle", "expatcircle_posts.json")
        
        if not os.path.exists(data_file):
            return pd.DataFrame()
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return pd.DataFrame()
        
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Error loading ExpatCircle data: {str(e)}")
        return pd.DataFrame()


def display_expatcircle_metrics(df: pd.DataFrame):
    """Display overview metrics for ExpatCircle data."""
    if df.empty:
        st.warning("No ExpatCircle News data available")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_posts = len(df)
        st.metric("Total Posts", f"{total_posts:,}")
    
    with col2:
        if 'engagement_score' in df.columns:
            avg_engagement = df['engagement_score'].mean()
            st.metric("Avg Engagement", f"{avg_engagement:.1f}")
        else:
            st.metric("Avg Engagement", "N/A")
    
    with col3:
        if 'is_trending' in df.columns:
            trending_count = len(df[df['is_trending'] == True])
            st.metric("Trending Posts", f"{trending_count}")
        else:
            st.metric("Trending Posts", "N/A")
    
    with col4:
        if 'category' in df.columns:
            categories_count = df['category'].nunique()
            st.metric("Categories", f"{categories_count}")
        else:
            st.metric("Categories", "N/A")


def display_expatcircle_posts(df: pd.DataFrame):
    """Display ExpatCircle posts with filtering and sorting."""
    st.subheader("🌍 ExpatCircle News Posts")
    
    if df.empty:
        st.warning("No ExpatCircle posts available")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = ['All'] + list(df['category'].unique()) if 'category' in df.columns else ['All']
        selected_category = st.selectbox("Category", categories, key="expatcircle_category")
    
    with col2:
        content_types = ['All'] + list(df['content_type'].unique()) if 'content_type' in df.columns else ['All']
        selected_content = st.selectbox("Content Type", content_types, key="expatcircle_content")
    
    with col3:
        trending_filter = st.selectbox("Trending", ['All', 'Trending Only', 'Non-Trending'], key="expatcircle_trending")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_category != 'All' and 'category' in df.columns:
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    if selected_content != 'All' and 'content_type' in df.columns:
        filtered_df = filtered_df[filtered_df['content_type'] == selected_content]
    
    if trending_filter == 'Trending Only' and 'is_trending' in df.columns:
        filtered_df = filtered_df[filtered_df['is_trending'] == True]
    elif trending_filter == 'Non-Trending' and 'is_trending' in df.columns:
        filtered_df = filtered_df[filtered_df['is_trending'] == False]
    
    # Sort by priority score or engagement
    sort_column = 'priority_score' if 'priority_score' in filtered_df.columns else 'engagement_score'
    if sort_column in filtered_df.columns:
        filtered_df = filtered_df.sort_values(sort_column, ascending=False)
    
    # Display posts
    for _, post in filtered_df.head(15).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                title = post.get('title', 'No Title')
                url = post.get('url', '#')
                author = post.get('author', 'Unknown')
                category = post.get('category', 'general')
                
                st.markdown(f"**[{title}]({url})**")
                st.write(f"👤 {author} | 📂 {category.replace('_', ' ').title()}")
                
                # Display points and engagement
                points = post.get('points', 0)
                comments = post.get('comments_count', 0)
                site_domain = post.get('site_domain', '')
                
                metrics_text = f"⬆️ {points} points"
                if comments > 0:
                    metrics_text += f" | 💬 {comments} comments"
                if site_domain:
                    metrics_text += f" | 🌐 {site_domain}"
                
                st.write(metrics_text)
                
                # Discuss link
                discuss_url = post.get('discuss_url', '')
                if discuss_url:
                    st.markdown(f"[💬 Discuss]({discuss_url})")
            
            with col2:
                # Priority score or engagement score
                if 'priority_score' in post:
                    score = post['priority_score']
                    st.metric("Priority", f"{score:.1f}")
                elif 'engagement_score' in post:
                    score = post['engagement_score']
                    st.metric("Engagement", f"{score:.1f}")
                
                # Content type badge
                content_type = post.get('content_type', 'unknown')
                if content_type == 'discussion':
                    st.success("💬 Discussion")
                elif content_type == 'external_link':
                    st.info("🔗 External Link")
                
                # Trending indicator
                if post.get('is_trending', False):
                    st.warning("🔥 Trending")
        
        st.divider()


def display_category_distribution(df: pd.DataFrame):
    """Display category distribution chart."""
    if df.empty or 'category' not in df.columns:
        return
    
    st.subheader("📊 Category Distribution")
    
    category_counts = df['category'].value_counts()
    
    fig = px.pie(
        values=category_counts.values,
        names=[cat.replace('_', ' ').title() for cat in category_counts.index],
        title="Posts by Category"
    )
    st.plotly_chart(fig, use_container_width=True)


def display_engagement_analysis(df: pd.DataFrame):
    """Display engagement analysis charts."""
    if df.empty:
        return
    
    st.subheader("📈 Engagement Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'engagement_score' in df.columns:
            fig = px.histogram(
                df,
                x='engagement_score',
                title="Engagement Score Distribution",
                nbins=20
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'category' in df.columns and 'engagement_score' in df.columns:
            avg_engagement = df.groupby('category')['engagement_score'].mean().sort_values(ascending=False)
            
            fig = px.bar(
                x=[cat.replace('_', ' ').title() for cat in avg_engagement.index],
                y=avg_engagement.values,
                title="Average Engagement by Category"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)


def display_trending_analysis(df: pd.DataFrame):
    """Display trending posts analysis."""
    if df.empty or 'is_trending' not in df.columns:
        return
    
    st.subheader("🔥 Trending Analysis")
    
    trending_df = df[df['is_trending'] == True]
    
    if trending_df.empty:
        st.info("No trending posts found.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🔥 Top Trending Posts:**")
        for _, post in trending_df.head(5).iterrows():
            title = post.get('title', 'No Title')
            url = post.get('url', '#')
            engagement = post.get('engagement_score', 0)
            
            st.markdown(f"• **[{title[:60]}...]({url})** - {engagement:.1f}")
    
    with col2:
        if 'category' in trending_df.columns:
            trending_categories = trending_df['category'].value_counts()
            
            fig = px.bar(
                x=[cat.replace('_', ' ').title() for cat in trending_categories.index],
                y=trending_categories.values,
                title="Trending Posts by Category"
            )
            st.plotly_chart(fig, use_container_width=True)


def create_insights_summary(df: pd.DataFrame):
    """Create insights summary for ExpatCircle data."""
    if df.empty:
        return
    
    st.subheader("💡 Key Insights")
    
    insights = []
    
    # Total posts insight
    total_posts = len(df)
    insights.append(f"📊 **{total_posts}** total posts collected from ExpatCircle News")
    
    # Most popular category
    if 'category' in df.columns:
        most_popular_category = df['category'].value_counts().index[0]
        category_count = df['category'].value_counts().iloc[0]
        insights.append(f"🏆 **{most_popular_category.replace('_', ' ').title()}** is the most discussed category with {category_count} posts")
    
    # Engagement insights
    if 'engagement_score' in df.columns:
        avg_engagement = df['engagement_score'].mean()
        insights.append(f"💬 Average engagement score is **{avg_engagement:.1f}**")
        
        if 'is_trending' in df.columns:
            trending_count = len(df[df['is_trending'] == True])
            trending_pct = (trending_count / total_posts * 100) if total_posts > 0 else 0
            insights.append(f"🔥 **{trending_count}** posts ({trending_pct:.1f}%) are currently trending")
    
    # Content type distribution
    if 'content_type' in df.columns:
        discussion_count = len(df[df['content_type'] == 'discussion'])
        external_count = len(df[df['content_type'] == 'external_link'])
        
        if discussion_count > external_count:
            insights.append(f"💬 Community prefers **discussions** ({discussion_count}) over external links ({external_count})")
        else:
            insights.append(f"🔗 More **external content** ({external_count}) than discussions ({discussion_count})")
    
    # Display insights
    for insight in insights:
        st.markdown(insight)


def render(logger):
    """Render the ExpatCircle News tab."""
    
    st.header("🌍 ExpatCircle News")
    st.markdown("Expat community discussions and news from around the world")
    
    # Load data
    with st.spinner("Loading ExpatCircle News data..."):
        df = load_expatcircle_data()
    
    if df.empty:
        st.warning("No ExpatCircle News data available. Please run the ETL process first.")
        st.info("Run: `python src/etl/news/news_get_expatcircle.py` to collect ExpatCircle data.")
        return
    
    # Display overview metrics
    display_expatcircle_metrics(df)
    
    st.divider()
    
    # Create tabs for different views
    tabs = st.tabs(["📰 Posts", "📊 Analytics", "🔥 Trending", "💡 Insights"])
    
    with tabs[0]:
        display_expatcircle_posts(df)
    
    with tabs[1]:
        display_category_distribution(df)
        st.divider()
        display_engagement_analysis(df)
    
    with tabs[2]:
        display_trending_analysis(df)
    
    with tabs[3]:
        create_insights_summary(df)
    
    # Footer with last update
    st.divider()
    st.markdown("*Data refreshed from ExpatCircle News community*")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    # For testing the component
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils.logging import get_logger
    
    logger = get_logger("expatcircle_tab_test")
    render(logger) 