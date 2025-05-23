"""
Innovation & Tech Trends Tab Component

This component displays data from innovation and tech trend sources including:
- Product Hunt launches and innovations
- GitHub trending repositories
- Tech Jobs market trends and insights

Provides filtering, sorting, and analytics for technology innovation trends.
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

# Define innovation data paths using absolute paths
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Data source file mappings with absolute paths
DATA_SOURCES = {
    'product_hunt': os.path.join(DATA_DIR, 'product_hunt', 'producthunt_products_latest.json'),
    'github_trends': os.path.join(DATA_DIR, 'github_trends', 'github_trending_latest.json'),
    'tech_jobs': os.path.join(DATA_DIR, 'tech_jobs', 'tech_jobs_latest.json')
}

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

def load_innovation_data() -> Dict[str, pd.DataFrame]:
    """Load all innovation and tech trend data sources."""
    innovation_data = {}
    
    for source_name, file_path in DATA_SOURCES.items():
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        df = pd.DataFrame(data)
                        # Clean DataFrame to avoid caching issues
                        df = clean_dataframe_for_caching(df)
                        innovation_data[source_name] = df
                        st.sidebar.success(f"✅ {source_name.replace('_', ' ').title()}: {len(df)} items")
                    else:
                        st.sidebar.warning(f"⚠️ {source_name.replace('_', ' ').title()}: No data")
            else:
                st.sidebar.error(f"❌ {source_name.replace('_', ' ').title()}: File not found")
        except Exception as e:
            st.sidebar.error(f"❌ {source_name.replace('_', ' ').title()}: Error loading data")
    
    return innovation_data

def display_innovation_metrics(innovation_data: Dict[str, pd.DataFrame]):
    """Display overview metrics for innovation data."""
    col1, col2, col3, col4 = st.columns(4)
    
    total_items = sum(len(df) for df in innovation_data.values())
    
    with col1:
        st.metric("Total Items", f"{total_items:,}")
    
    with col2:
        trending_count = 0
        for df in innovation_data.values():
            if 'is_trending' in df.columns:
                trending_count += len(df[df['is_trending'] == True])
        st.metric("Trending", f"{trending_count:,}")
    
    with col3:
        # Calculate average scores across all platforms
        avg_score = 0
        score_count = 0
        for df in innovation_data.values():
            if 'launch_score' in df.columns:
                avg_score += df['launch_score'].mean()
                score_count += 1
            elif 'activity_score' in df.columns:
                avg_score += df['activity_score'].mean()
                score_count += 1
            elif 'score' in df.columns:
                avg_score += df['score'].mean()
                score_count += 1
        
        if score_count > 0:
            avg_score = avg_score / score_count
            st.metric("Avg Score", f"{avg_score:.1f}")
        else:
            st.metric("Avg Score", "N/A")
    
    with col4:
        platforms_count = len(innovation_data)
        st.metric("Data Sources", f"{platforms_count}")

def display_product_hunt_data(df: pd.DataFrame):
    """Display Product Hunt data."""
    st.subheader("🚀 Product Hunt Launches")
    
    if df.empty:
        st.warning("No Product Hunt data available")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = ['All'] + list(df['category'].unique()) if 'category' in df.columns else ['All']
        selected_category = st.selectbox("Category", categories, key="ph_category")
    
    with col2:
        launch_success = ['All'] + list(df['launch_success'].unique()) if 'launch_success' in df.columns else ['All']
        selected_success = st.selectbox("Launch Success", launch_success, key="ph_success")
    
    with col3:
        innovation_levels = ['All'] + list(df['innovation_level'].unique()) if 'innovation_level' in df.columns else ['All']
        selected_innovation = st.selectbox("Innovation Level", innovation_levels, key="ph_innovation")
    
    # Apply filters
    filtered_df = df.copy()
    if selected_category != 'All' and 'category' in df.columns:
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if selected_success != 'All' and 'launch_success' in df.columns:
        filtered_df = filtered_df[filtered_df['launch_success'] == selected_success]
    if selected_innovation != 'All' and 'innovation_level' in df.columns:
        filtered_df = filtered_df[filtered_df['innovation_level'] == selected_innovation]
    
    # Display products
    for _, product in filtered_df.head(10).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**[{product.get('name', 'No Name')}]({product.get('url', '#')})**")
                st.write(product.get('tagline', 'No tagline available'))
                
                metrics_text = f"⬆️ {product.get('votes', 0)} votes | "
                metrics_text += f"💬 {product.get('comments_count', 0)} comments | "
                metrics_text += f"🏆 #{product.get('rank', 'N/A')} today"
                st.write(metrics_text)
                
                # Topics/tags
                topics = product.get('topics', []) if isinstance(product.get('topics'), list) else []
                if topics:
                    tag_html = ' '.join([f"<span style='background-color: #F3E5F5; color: #7B1FA2; padding: 2px 6px; border-radius: 12px; font-size: 12px;'>{topic}</span>" for topic in topics[:4]])
                    st.markdown(tag_html, unsafe_allow_html=True)
            
            with col2:
                launch_score = product.get('launch_score', 0)
                st.metric("Launch Score", f"{launch_score:.1f}")
                
                innovation_level = product.get('innovation_level', 'medium')
                if innovation_level == 'high':
                    st.success("🔥 High Innovation")
                elif innovation_level == 'medium':
                    st.warning("⚡ Medium Innovation")
                else:
                    st.info("💡 Standard Innovation")
        
        st.divider()

def display_github_trends_data(df: pd.DataFrame):
    """Display GitHub trending repositories."""
    st.subheader("⭐ GitHub Trending Repositories")
    
    if df.empty:
        st.warning("No GitHub trends data available")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        languages = ['All'] + list(df['language'].unique()) if 'language' in df.columns else ['All']
        selected_language = st.selectbox("Language", languages, key="gh_language")
    
    with col2:
        categories = ['All'] + list(df['repository_category'].unique()) if 'repository_category' in df.columns else ['All']
        selected_repo_category = st.selectbox("Category", categories, key="gh_category")
    
    with col3:
        maturities = ['All'] + list(df['project_maturity'].unique()) if 'project_maturity' in df.columns else ['All']
        selected_maturity = st.selectbox("Maturity", maturities, key="gh_maturity")
    
    # Apply filters
    filtered_df = df.copy()
    if selected_language != 'All' and 'language' in df.columns:
        filtered_df = filtered_df[filtered_df['language'] == selected_language]
    if selected_repo_category != 'All' and 'repository_category' in df.columns:
        filtered_df = filtered_df[filtered_df['repository_category'] == selected_repo_category]
    if selected_maturity != 'All' and 'project_maturity' in df.columns:
        filtered_df = filtered_df[filtered_df['project_maturity'] == selected_maturity]
    
    # Display repositories
    for _, repo in filtered_df.head(10).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                repo_name = repo.get('name', 'No Name')
                repo_url = repo.get('url', '#')
                st.markdown(f"**[{repo_name}]({repo_url})**")
                st.write(repo.get('description', 'No description available'))
                
                metrics_text = f"⭐ {repo.get('stars', 0):,} stars | "
                metrics_text += f"🍴 {repo.get('forks', 0):,} forks | "
                metrics_text += f"📈 +{repo.get('stars_today', 0)} today"
                if repo.get('language'):
                    metrics_text += f" | 💻 {repo.get('language')}"
                st.write(metrics_text)
            
            with col2:
                activity_score = repo.get('activity_score', 0)
                st.metric("Activity Score", f"{activity_score:.1f}")
                
                project_maturity = repo.get('project_maturity', 'unknown')
                if project_maturity == 'mature':
                    st.success("🟢 Mature")
                elif project_maturity == 'growing':
                    st.warning("🟡 Growing")
                elif project_maturity == 'new':
                    st.info("🔵 New")
                else:
                    st.error("🔴 Experimental")
        
        st.divider()

def display_tech_jobs_data(df: pd.DataFrame):
    """Display tech jobs market data."""
    st.subheader("💼 Tech Jobs Market")
    
    if df.empty:
        st.warning("No tech jobs data available")
        return
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_jobs = len(df)
        st.metric("Total Jobs", f"{total_jobs:,}")
    
    with col2:
        if 'salary_min' in df.columns and 'salary_max' in df.columns:
            avg_salary = ((df['salary_min'].fillna(0) + df['salary_max'].fillna(0)) / 2).mean()
            st.metric("Avg Salary", f"${avg_salary:,.0f}")
        else:
            st.metric("Avg Salary", "N/A")
    
    with col3:
        remote_count = len(df[df['is_remote'] == True]) if 'is_remote' in df.columns else 0
        remote_pct = (remote_count / total_jobs * 100) if total_jobs > 0 else 0
        st.metric("Remote Jobs", f"{remote_pct:.1f}%")
    
    with col4:
        if 'demand_level' in df.columns:
            high_demand = len(df[df['demand_level'] == 'high'])
            st.metric("High Demand", f"{high_demand}")
        else:
            st.metric("High Demand", "N/A")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        roles = ['All'] + list(df['role_category'].unique()) if 'role_category' in df.columns else ['All']
        selected_role = st.selectbox("Role Category", roles, key="jobs_role")
    
    with col2:
        locations = ['All'] + list(df['location'].unique()) if 'location' in df.columns else ['All']
        selected_location = st.selectbox("Location", locations[:20], key="jobs_location")  # Limit to avoid UI overflow
    
    with col3:
        seniorities = ['All'] + list(df['seniority_level'].unique()) if 'seniority_level' in df.columns else ['All']
        selected_seniority = st.selectbox("Seniority", seniorities, key="jobs_seniority")
    
    # Apply filters
    filtered_df = df.copy()
    if selected_role != 'All' and 'role_category' in df.columns:
        filtered_df = filtered_df[filtered_df['role_category'] == selected_role]
    if selected_location != 'All' and 'location' in df.columns:
        filtered_df = filtered_df[filtered_df['location'] == selected_location]
    if selected_seniority != 'All' and 'seniority_level' in df.columns:
        filtered_df = filtered_df[filtered_df['seniority_level'] == selected_seniority]
    
    # Display jobs
    for _, job in filtered_df.head(8).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                job_title = job.get('title', 'No Title')
                company = job.get('company', 'Unknown Company')
                job_url = job.get('url', '#')
                st.markdown(f"**[{job_title} at {company}]({job_url})**")
                
                location = job.get('location', 'Unknown Location')
                remote_text = " (Remote)" if job.get('is_remote') else ""
                st.write(f"📍 {location}{remote_text}")
                
                # Salary info
                salary_min = job.get('salary_min', 0)
                salary_max = job.get('salary_max', 0)
                if salary_min and salary_max:
                    st.write(f"💰 ${salary_min:,} - ${salary_max:,}")
                elif salary_min:
                    st.write(f"💰 ${salary_min:,}+")
                
                # Required skills
                skills = job.get('required_skills', []) if isinstance(job.get('required_skills'), list) else []
                if skills:
                    skill_html = ' '.join([f"<span style='background-color: #E1F5FE; color: #0277BD; padding: 2px 6px; border-radius: 12px; font-size: 12px;'>{skill}</span>" for skill in skills[:5]])
                    st.markdown(skill_html, unsafe_allow_html=True)
            
            with col2:
                market_score = job.get('market_score', 0)
                st.metric("Market Score", f"{market_score:.1f}")
                
                demand_level = job.get('demand_level', 'medium')
                if demand_level == 'high':
                    st.success("🔥 High Demand")
                elif demand_level == 'medium':
                    st.warning("⚡ Medium Demand")
                else:
                    st.info("💡 Standard Demand")
        
        st.divider()

def create_innovation_charts(innovation_data: Dict[str, pd.DataFrame]):
    """Create charts for innovation data visualization."""
    st.subheader("📊 Innovation Analytics")
    
    # Create tabs for different charts
    chart_tabs = st.tabs(["🚀 Product Hunt", "⭐ GitHub Trends", "💼 Job Market"])
    
    # Product Hunt charts
    if 'product_hunt' in innovation_data:
        with chart_tabs[0]:
            df = innovation_data['product_hunt']
            if not df.empty and 'category' in df.columns:
                # Category distribution
                col1, col2 = st.columns(2)
                
                with col1:
                    category_counts = df['category'].value_counts().head(10)
                    fig = px.bar(
                        x=category_counts.index,
                        y=category_counts.values,
                        title="Top Product Categories",
                        labels={'x': 'Category', 'y': 'Count'}
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    if 'launch_score' in df.columns:
                        fig = px.histogram(
                            df,
                            x='launch_score',
                            title="Launch Score Distribution",
                            nbins=20
                        )
                        st.plotly_chart(fig, use_container_width=True)
    
    # GitHub Trends charts
    if 'github_trends' in innovation_data:
        with chart_tabs[1]:
            df = innovation_data['github_trends']
            if not df.empty and 'language' in df.columns:
                # Language distribution
                col1, col2 = st.columns(2)
                
                with col1:
                    lang_counts = df['language'].value_counts().head(10)
                    fig = px.pie(
                        values=lang_counts.values,
                        names=lang_counts.index,
                        title="Programming Languages Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    if 'stars' in df.columns:
                        fig = px.scatter(
                            df.head(50),
                            x='stars',
                            y='forks',
                            color='language',
                            title="Stars vs Forks",
                            hover_data=['name']
                        )
                        st.plotly_chart(fig, use_container_width=True)
    
    # Job Market charts
    if 'tech_jobs' in innovation_data:
        with chart_tabs[2]:
            df = innovation_data['tech_jobs']
            if not df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'role_category' in df.columns:
                        role_counts = df['role_category'].value_counts().head(10)
                        fig = px.bar(
                            x=role_counts.values,
                            y=role_counts.index,
                            orientation='h',
                            title="Top Job Roles"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    if 'salary_min' in df.columns and 'salary_max' in df.columns:
                        df['avg_salary'] = (df['salary_min'].fillna(0) + df['salary_max'].fillna(0)) / 2
                        df_salary = df[df['avg_salary'] > 0]
                        if not df_salary.empty:
                            fig = px.histogram(
                                df_salary,
                                x='avg_salary',
                                title="Salary Distribution",
                                nbins=20
                            )
                            st.plotly_chart(fig, use_container_width=True)

def render(logger, innovation_data: Dict[str, pd.DataFrame] = None):
    """Render the Innovation & Tech Trends tab."""
    
    st.header("🚀 Innovation & Tech Trends")
    st.markdown("Discover the latest innovations, trending repositories, and job market insights")
    
    # Load data if not provided
    if innovation_data is None:
        with st.spinner("Loading innovation data..."):
            innovation_data = load_innovation_data()
    
    if not innovation_data:
        st.warning("No innovation data available. Please run the ETL processes first.")
        return
    
    # Display overview metrics
    display_innovation_metrics(innovation_data)
    
    st.divider()
    
    # Create tabs for different data sources
    tab_names = []
    available_data = {}
    
    if 'product_hunt' in innovation_data:
        tab_names.append("🚀 Product Hunt")
        available_data['product_hunt'] = innovation_data['product_hunt']
    
    if 'github_trends' in innovation_data:
        tab_names.append("⭐ GitHub Trends")
        available_data['github_trends'] = innovation_data['github_trends']
    
    if 'tech_jobs' in innovation_data:
        tab_names.append("💼 Tech Jobs")
        available_data['tech_jobs'] = innovation_data['tech_jobs']
    
    # Add analytics tab if we have any data
    if available_data:
        tab_names.append("📊 Analytics")
    
    if not tab_names:
        st.warning("No innovation data sources available.")
        return
    
    # Create tabs
    tabs = st.tabs(tab_names)
    
    tab_index = 0
    
    # Product Hunt tab
    if 'product_hunt' in available_data:
        with tabs[tab_index]:
            display_product_hunt_data(available_data['product_hunt'])
        tab_index += 1
    
    # GitHub Trends tab
    if 'github_trends' in available_data:
        with tabs[tab_index]:
            display_github_trends_data(available_data['github_trends'])
        tab_index += 1
    
    # Tech Jobs tab
    if 'tech_jobs' in available_data:
        with tabs[tab_index]:
            display_tech_jobs_data(available_data['tech_jobs'])
        tab_index += 1
    
    # Analytics tab
    if available_data:
        with tabs[tab_index]:
            create_innovation_charts(innovation_data)
    
    # Footer with last update
    if innovation_data:
        st.divider()
        st.markdown("*Innovation data refreshed automatically from multiple tech platforms*")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 