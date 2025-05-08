"""
Admin tab component for the Watchtower Streamlit application.
Provides administrative functionality for the application.
"""

import streamlit as st
import subprocess
import os
import json
from typing import Dict, List, Optional, Any
import toml
import glob
import pandas as pd
import plotly.express as px
from datetime import datetime

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.utils.file_system import get_project_root


# Define videos data directory
VIDEOS_DATA_DIR = "../../../data/youtube"

# Define available themes
THEMES: Dict[str, Dict[str, str]] = {
    "Default": {
        "primaryColor": "#FF4B4B",
        "backgroundColor": "#1E1E2E",
        "secondaryBackgroundColor": "#2D2B55",
        "textColor": "#E2E8F0",
        "font": "sans serif",
    },
    "Dark": {
        "primaryColor": "#A37FFF",
        "backgroundColor": "#0E1117",
        "secondaryBackgroundColor": "#262730",
        "textColor": "#FAFAFA",
        "font": "sans serif",
    },
    "Blue": {
        "primaryColor": "#1E88E5",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#E3F2FD",
        "textColor": "#262730",
        "font": "sans serif",
    },
    "Green": {
        "primaryColor": "#4CAF50",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#E8F5E9",
        "textColor": "#262730",
        "font": "sans serif",
    },
}


def update_theme_config(theme_name: str) -> bool:
    """
    Update the Streamlit config.toml file with the selected theme.
    
    Args:
        theme_name: Name of the theme to apply
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Define path to config.toml relative to the application
        config_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../../../../.streamlit/config.toml"
        ))
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Load existing config if it exists
        if os.path.exists(config_path):
            config = toml.load(config_path)
        else:
            config = {}
        
        # Make sure theme section exists
        if "theme" not in config:
            config["theme"] = {}
        
        # Update theme settings
        theme_settings = THEMES[theme_name]
        for key, value in theme_settings.items():
            config["theme"][key] = value
        
        # Write updated config
        with open(config_path, "w") as f:
            toml.dump(config, f)
        
        return True
    except Exception as e:
        st.error(f"Error updating theme: {str(e)}")
        return False


def render(logger):
    """
    Render the Admin tab.
    
    Args:
        logger: Logger instance for this component
    """
    st.markdown("## ⚙️ Admin Panel")
    
    # Get the project root directory
    project_root = get_project_root()
    
    # Create tabs for different admin sections
    tab1, tab2, tab3 = st.tabs(["📈 Estadísticas", "👤 Usuarios ArXiv", "🛠️ Mantenimiento"])
    
    # Statistics tab
    with tab1:
        st.markdown("### Estadísticas generales")
        
        # Stats container
        col1, col2, col3, col4 = st.columns(4)
        
        # Load some stats
        try:
            # Check how many ETL processes are configured 
            etl_dirs = [d for d in os.listdir(os.path.join(project_root, "src/etl")) 
                        if os.path.isdir(os.path.join(project_root, "src/etl", d))]
            
            # Check how many watcher processes are configured
            watcher_files = glob.glob(os.path.join(project_root, "src/watchers/*.py"))
            watcher_files = [f for f in watcher_files if not f.endswith("base_watcher.py") and not f.endswith("__init__.py")]
            
            # Get ArXiv papers stats
            arxiv_papers = []
            arxiv_papers_file = os.path.join(project_root, "data/arxiv/processed/json/latest_papers.json")
            if os.path.exists(arxiv_papers_file):
                with open(arxiv_papers_file, 'r', encoding='utf-8') as f:
                    arxiv_papers = json.load(f)
            
            # Get user profiles stats
            user_profiles = []
            user_profiles_dir = os.path.join(project_root, "data/users/profiles")
            if os.path.exists(user_profiles_dir):
                user_profiles = glob.glob(os.path.join(user_profiles_dir, "*.json"))
            
            # Display stats
            with col1:
                st.metric("ETL Processes", len(etl_dirs))
                
            with col2:
                st.metric("Watchers", len(watcher_files))
                
            with col3:
                st.metric("ArXiv Papers", len(arxiv_papers))
                
            with col4:
                st.metric("User Profiles", len(user_profiles))
            
            # Show ArXiv stats if available
            if arxiv_papers:
                st.markdown("### ArXiv Papers Statistics")
                
                # Get categories distribution
                categories = {}
                for paper in arxiv_papers:
                    for category in paper.get("categories", []):
                        categories[category] = categories.get(category, 0) + 1
                
                # Create bar chart for categories
                categories_df = pd.DataFrame({
                    "Category": list(categories.keys()),
                    "Count": list(categories.values())
                })
                categories_df = categories_df.sort_values("Count", ascending=False).head(10)
                
                fig = px.bar(
                    categories_df,
                    x="Category",
                    y="Count",
                    title="Top 10 ArXiv Categories"
                )
                st.plotly_chart(fig)
                
                # Get cluster distribution
                clusters = {}
                for paper in arxiv_papers:
                    cluster_id = paper.get("cluster_id")
                    cluster_label = paper.get("cluster_label", f"Cluster {cluster_id}")
                    if cluster_id is not None:
                        clusters[cluster_label] = clusters.get(cluster_label, 0) + 1
                
                # Create pie chart for clusters
                if clusters:
                    clusters_df = pd.DataFrame({
                        "Cluster": list(clusters.keys()),
                        "Count": list(clusters.values())
                    })
                    
                    fig = px.pie(
                        clusters_df,
                        values="Count",
                        names="Cluster",
                        title="Papers by Cluster"
                    )
                    st.plotly_chart(fig)
                
        except Exception as e:
            st.error(f"Error loading statistics: {str(e)}")
    
    # ArXiv Users tab
    with tab2:
        st.markdown("### 👤 User Profiles")
        
        # Load user profiles
        user_profiles_dir = os.path.join(project_root, "data/users/profiles")
        user_profiles = []
        
        if os.path.exists(user_profiles_dir):
            profile_files = glob.glob(os.path.join(user_profiles_dir, "*.json"))
            
            for profile_file in profile_files:
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                        user_profiles.append(profile)
                except Exception as e:
                    st.error(f"Error loading profile {profile_file}: {str(e)}")
        
        if not user_profiles:
            st.info("No user profiles found")
        else:
            # Display user profiles in a table
            profiles_data = []
            for profile in user_profiles:
                profiles_data.append({
                    "User ID": profile.get("user_id", "Unknown"),
                    "Interests": len(profile.get("interests", [])),
                    "Viewed Items": len(profile.get("viewed_items", [])),
                    "Rated Items": len(profile.get("rated_items", {})),
                    "Categories": len(profile.get("preferred_categories", [])),
                    "Last Updated": profile.get("updated_at", "")[:10] if profile.get("updated_at") else ""
                })
            
            profiles_df = pd.DataFrame(profiles_data)
            st.dataframe(profiles_df)
            
            # Show user interests word cloud
            if any(len(profile.get("interests", [])) > 0 for profile in user_profiles):
                st.markdown("### User Interests")
                
                # Collect all interests
                all_interests = []
                for profile in user_profiles:
                    all_interests.extend(profile.get("interests", []))
                
                if all_interests:
                    # Count interests
                    interest_counts = {}
                    for interest in all_interests:
                        interest_counts[interest] = interest_counts.get(interest, 0) + 1
                    
                    # Create bar chart for top interests
                    interests_df = pd.DataFrame({
                        "Interest": list(interest_counts.keys()),
                        "Count": list(interest_counts.values())
                    })
                    interests_df = interests_df.sort_values("Count", ascending=False).head(15)
                    
                    fig = px.bar(
                        interests_df,
                        x="Interest",
                        y="Count",
                        title="Top User Interests"
                    )
                    st.plotly_chart(fig)
            
            # Show user activity over time
            if any("viewed_items" in profile and profile["viewed_items"] for profile in user_profiles):
                st.markdown("### User Activity")
                
                # Show top viewed papers
                paper_views = {}
                for profile in user_profiles:
                    for item_id in profile.get("viewed_items", []):
                        paper_views[item_id] = paper_views.get(item_id, 0) + 1
                
                # Show top 10 viewed papers
                if paper_views:
                    top_papers = sorted(paper_views.items(), key=lambda x: x[1], reverse=True)[:10]
                    
                    # Create dataframe
                    top_papers_df = pd.DataFrame({
                        "Paper ID": [p[0] for p in top_papers],
                        "Views": [p[1] for p in top_papers]
                    })
                    
                    fig = px.bar(
                        top_papers_df,
                        x="Paper ID",
                        y="Views",
                        title="Top Viewed Papers"
                    )
                    st.plotly_chart(fig)
    
    # Maintenance tab
    with tab3:
        st.markdown("### 🛠️ Mantenimiento")
        
        # ETL Maintenance
        st.subheader("ETL Maintenance")
        
        # Run ArXiv ETL
        if st.button("Run ArXiv ETL"):
            st.info("Starting ArXiv ETL process...")
            
            try:
                from src.etl.arxiv.arxiv_etl import ArxivETL
                
                with st.spinner("Running ETL..."):
                    etl = ArxivETL(days_back=7, max_results=50)
                    etl.run()
                    
                st.success("ArXiv ETL process completed!")
            except Exception as e:
                st.error(f"Error running ArXiv ETL: {str(e)}")
        
        # Run Humble Bundle ETL
        if st.button("Run Humble Bundle ETL"):
            st.info("Starting Humble Bundle ETL process...")
            try:
                from src.etl.games.games_get_humblebundles import main as run_humble
                with st.spinner("Running Humble Bundle ETL..."):
                    run_humble()
                st.success("Humble Bundle ETL process completed!")
            except Exception as e:
                st.error(f"Error running Humble Bundle ETL: {str(e)}")

        # Run Subreddits ETL
        if st.button("Run Subreddits ETL"):
            st.info("Starting Subreddits ETL process...")
            try:
                from src.etl.news.news_get_subreddits import main as run_subreddits
                with st.spinner("Running Subreddits ETL..."):
                    run_subreddits()
                st.success("Subreddits ETL process completed!")
            except Exception as e:
                st.error(f"Error running Subreddits ETL: {str(e)}")

        # Run Media RSS ETL
        if st.button("Run Media RSS ETL"):
            st.info("Starting Media RSS ETL process...")
            try:
                from src.etl.news.news_get_media_rss import main as run_media_rss
                with st.spinner("Running Media RSS ETL..."):
                    run_media_rss()
                st.success("Media RSS ETL process completed!")
            except Exception as e:
                st.error(f"Error running Media RSS ETL: {str(e)}")
        
        # Clear user profiles
        st.subheader("User Profiles Maintenance")
        
        if st.button("Clear All User Profiles"):
            user_profiles_dir = os.path.join(project_root, "data/users/profiles")
            
            if os.path.exists(user_profiles_dir):
                try:
                    profile_files = glob.glob(os.path.join(user_profiles_dir, "*.json"))
                    
                    for profile_file in profile_files:
                        os.remove(profile_file)
                    
                    st.success(f"Removed {len(profile_files)} user profiles")
                except Exception as e:
                    st.error(f"Error removing profiles: {str(e)}")
            else:
                st.info("No profiles directory found")
