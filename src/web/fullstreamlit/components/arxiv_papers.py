"""Streamlit component for displaying ArXiv papers.

This module provides the `ArxivPapersComponent` class, which handles
the loading, processing, and display of ArXiv research papers,
including classification, clustering, and personalized recommendations.
"""
import os
import sys
import json
import pandas as pd
from typing import Dict, List, Any, Optional
import streamlit as st
import plotly.express as px

# Add project root to path
from src.utils.file_system import get_project_root
from src.utils.recommender import PersonalRecommender


class ArxivPapersComponent:
    """
    Streamlit component to display ArXiv papers and their classification.
    """
    
    def __init__(self):
        """Initialize the ArXiv papers component."""
        self.project_root = get_project_root()
        self.data_dir = os.path.join(self.project_root, "data/arxiv")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        
        # Initialize recommender system
        self.recommender = PersonalRecommender(name="arxiv_recommender")
        
    def _load_papers(self) -> List[Dict[str, Any]]:
        """
        Load the latest processed papers.
        
        Returns:
            List[Dict[str, Any]]: List of papers with metadata and classification
        """
        papers_file = os.path.join(self.processed_dir, "json/latest_papers.json")
        
        if not os.path.exists(papers_file):
            return []
        
        try:
            with open(papers_file, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            
            # Load papers into recommender system
            self.recommender.load_items(papers)
            
            return papers
        except Exception as e:
            st.error(f"Error loading papers: {str(e)}")
            return []
    
    def _load_cluster_stats(self) -> Dict[str, Any]:
        """
        Load cluster statistics.
        
        Returns:
            Dict[str, Any]: Cluster statistics
        """
        stats_file = os.path.join(self.processed_dir, "cluster_statistics.json")
        
        if not os.path.exists(stats_file):
            return {}
        
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            return stats
        except Exception as e:
            st.error(f"Error loading cluster statistics: {str(e)}")
            return {}
    
    def _convert_authors_to_string(self, authors: List[str], max_authors: int = 3) -> str:
        """
        Convert author list to a readable string.
        
        Args:
            authors (List[str]): List of author names
            max_authors (int): Maximum number of authors to display
            
        Returns:
            str: Formatted author string
        """
        if not authors:
            return "Unknown"
            
        if len(authors) <= max_authors:
            return ", ".join(authors)
        else:
            return f"{', '.join(authors[:max_authors])} et al."
    
    def render_paper_card(self, paper: Dict[str, Any], user_id: Optional[str] = None, section: str = "default"):
        """
        Render a card for a single paper.
        
        Args:
            paper (Dict[str, Any]): Paper data
            user_id (Optional[str]): User ID for tracking views
            section (str): Section identifier to create unique widget keys
        """
        paper_id = paper.get('id', '')
        
        with st.container():
            # Title with link
            st.markdown(f"### [{paper['title']}]({paper['link']})")
            
            # Authors and date
            authors_str = self._convert_authors_to_string(paper['authors'])
            st.markdown(f"**Authors:** {authors_str}")
            
            # Published date
            st.markdown(f"**Published:** {paper.get('published', 'Unknown')}")
            
            # Categories
            categories = ", ".join(paper.get('categories', []))
            st.markdown(f"**Categories:** {categories}")
            
            # Cluster information
            st.markdown(f"**Cluster:** {paper.get('cluster_label', 'Uncategorized')}")
            
            # Keywords
            keywords = ", ".join(paper.get('extracted_keywords', []))
            st.markdown(f"**Keywords:** {keywords}")
            
            # PDF link
            if paper.get('pdf_url'):
                st.markdown(f"[PDF]({paper['pdf_url']}) | [ArXiv]({paper['link']})")
                
            # Summary (collapsible)
            with st.expander("Abstract"):
                st.markdown(paper.get('summary', 'No abstract available'))
            
            # User interactions
            if user_id:
                col1, col2, col3 = st.columns([1, 1, 3])
                
                # Mark as read button - use section in the key
                with col1:
                    if st.button(f"📖 Read", key=f"{section}_read_{paper_id}"):
                        self.recommender.record_item_view(user_id, paper_id)
                        st.success("Marked as read!")
                
                # Rating - use section in the key
                with col2:
                    rating = st.select_slider(
                        "Rate",
                        options=[1, 2, 3, 4, 5],
                        value=3,
                        key=f"{section}_rate_{paper_id}"
                    )
                    if st.button("Submit", key=f"{section}_submit_{paper_id}"):
                        self.recommender.record_item_rating(user_id, paper_id, rating)
                        st.success("Rating submitted!")
                
                # Save keywords - use section in the key
                with col3:
                    if st.button("➕ Add keywords to your interests", key=f"{section}_keywords_{paper_id}"):
                        keywords_list = paper.get('extracted_keywords', [])
                        if keywords_list:
                            self.recommender.update_user_interests(user_id, keywords_list)
                            st.success(f"Added keywords to your profile!")
                        else:
                            st.info("No keywords found for this paper")
                
            st.divider()
    
    def render_paper_list(self, papers: List[Dict[str, Any]], cluster_id: Optional[int] = None, user_id: Optional[str] = None):
        """
        Render a list of papers, optionally filtered by cluster.
        
        Args:
            papers (List[Dict[str, Any]]): List of papers
            cluster_id (Optional[int]): Cluster ID to filter by, or None for all papers
            user_id (Optional[str]): User ID for tracking views and interactions
        """
        # Create a section identifier based on cluster_id
        section = f"cluster_{cluster_id}" if cluster_id is not None else "all_papers"
        
        if cluster_id is not None:
            filtered_papers = [p for p in papers if p.get('cluster_id') == cluster_id]
            if not filtered_papers:
                st.info(f"No papers found in cluster {cluster_id}")
                return
            papers_to_show = filtered_papers
        else:
            papers_to_show = papers
            
        # Sort papers by publication date (newest first)
        sorted_papers = sorted(
            papers_to_show,
            key=lambda p: p.get('published', ''),
            reverse=True
        )
        
        # Show paper count
        st.markdown(f"### Showing {len(sorted_papers)} papers")
        
        # Render each paper
        for paper in sorted_papers:
            self.render_paper_card(paper, user_id, section=section)
    
    def render_cluster_visualization(self, cluster_stats: Dict[str, Any]):
        """
        Render visualization of paper clusters.
        
        Args:
            cluster_stats (Dict[str, Any]): Cluster statistics
        """
        if not cluster_stats or 'clusters' not in cluster_stats:
            st.warning("No cluster statistics available")
            return
            
        # Create data for pie chart
        clusters = cluster_stats['clusters']
        fig = px.pie(
            values=[c['paper_count'] for c in clusters],
            names=[c['label'] for c in clusters],
            title="Distribution of Papers by Topic Cluster"
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show cluster table
        clusters_df = pd.DataFrame(clusters)
        if not clusters_df.empty:
            st.dataframe(clusters_df[['label', 'paper_count', 'percentage']], hide_index=True)
    
    def _safe_recommend_for_user(self, user_id: str, n_recommendations: int = 5, exclude_viewed: bool = True) -> List[Dict[str, Any]]:
        """
        Safely call the recommender's recommend_for_user method with error handling.
        
        Args:
            user_id (str): User ID
            n_recommendations (int): Number of recommendations to show
            exclude_viewed (bool): Whether to exclude viewed items
            
        Returns:
            List[Dict[str, Any]]: List of recommendations
        """
        try:
            # Check if the recommender has items loaded
            if (not hasattr(self.recommender, 'item_vectors') or 
                self.recommender.item_vectors is None or 
                not hasattr(self.recommender, 'item_ids') or 
                len(self.recommender.item_ids) == 0):
                return []
            
            return self.recommender.recommend_for_user(
                user_id=user_id,
                n_recommendations=n_recommendations,
                exclude_viewed=exclude_viewed
            )
        except Exception as e:
            st.error(f"Error generating recommendations: {str(e)}")
            return []
    
    def render_personalized_recommendations(self, papers: List[Dict[str, Any]], user_id: str, n_recommendations: int = 5):
        """
        Render personalized paper recommendations for the user.
        
        Args:
            papers (List[Dict[str, Any]]): List of all papers
            user_id (str): User ID
            n_recommendations (int): Number of recommendations to show
        """
        st.markdown("## 🔍 Personalized Recommendations")
        
        # Check if the recommender has items loaded (directly check attributes instead of using has_items)
        if (not hasattr(self.recommender, 'item_vectors') or 
            self.recommender.item_vectors is None or 
            not hasattr(self.recommender, 'item_ids') or 
            len(self.recommender.item_ids) == 0):
            st.warning("No papers loaded in the recommender system. Please check your data.")
            return
        
        # Get recommendations using the safe method
        recommendations = self._safe_recommend_for_user(
            user_id=user_id,
            n_recommendations=n_recommendations,
            exclude_viewed=True
        )
        
        if not recommendations:
            st.info("Start interacting with papers to get personalized recommendations!")
            
            # Show user profile setup form
            st.markdown("### ✏️ Set your research interests")
            with st.form("user_interests_form"):
                interests = st.text_area(
                    "Enter your research interests (comma-separated keywords)",
                    help="Example: machine learning, natural language processing, reinforcement learning"
                )
                
                categories = st.multiselect(
                    "Select your preferred categories",
                    options=["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.NE", "stat.ML", "cs.RO", "cs.IR"],
                    default=["cs.AI"]
                )
                
                submitted = st.form_submit_button("Save Interests")
                
                if submitted:
                    # Split interests by commas
                    interest_list = [i.strip() for i in interests.split(",") if i.strip()]
                    
                    # Update user profile
                    if interest_list:
                        self.recommender.update_user_interests(user_id, interest_list)
                    
                    if categories:
                        self.recommender.update_preferred_categories(user_id, categories)
                    
                    st.success("Profile updated! Refresh to see your recommendations")
            
            return
            
        # Display recommendations with similarity scores
        for i, rec in enumerate(recommendations):
            paper = rec["item"]
            similarity = rec["similarity"]
            
            # Create a colored badge based on similarity score
            if similarity > 0.7:
                match_quality = "🟢 Strong Match"
                match_color = "success"
            elif similarity > 0.4:
                match_quality = "🟡 Good Match"
                match_color = "warning"
            else:
                match_quality = "🔵 Potential Interest"
                match_color = "info"
                
            with st.container():
                # Add match quality badge
                st.markdown(f"<span style='padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-size: 0.8rem; background-color: var(--{match_color}-50); color: var(--{match_color}-700);'>{match_quality}</span>", unsafe_allow_html=True)
                
                # Render paper with user ID for interaction tracking 
                # Use a recommendation-specific section with the recommendation index
                self.render_paper_card(paper, user_id, section=f"rec_{i}")
    
    def render(self):
        """Render the ArXiv papers component."""
        st.title("ArXiv AI/ML Research Papers")
        
        # Load data
        papers = self._load_papers()
        cluster_stats = self._load_cluster_stats()
        
        if not papers:
            st.warning("No papers available. Run the ArXiv ETL pipeline first.")
            # Show a button to run the ETL
            if st.button("🔄 Fetch Latest Papers"):
                st.info("Starting paper collection... This may take a few minutes.")
                with st.spinner("Fetching papers from ArXiv..."):
                    # Import here to avoid circular imports
                    from src.etl.arxiv.arxiv_etl import ArxivETL
                    etl = ArxivETL(days_back=7, max_results=50)
                    etl.run()
                st.success("✅ Paper collection complete! Refresh the page to see results.")
                st.experimental_rerun()
            return
        
        # Display statistics
        if cluster_stats:
            st.markdown(f"Found **{cluster_stats.get('total_papers', len(papers))}** papers in **{cluster_stats.get('total_clusters', 0)}** topic clusters")
        
        # User ID input for personalization
        with st.sidebar:
            st.subheader("User Settings")
            user_id = st.text_input("Enter your user ID:", value="user1")
            st.caption("Use this ID to get personalized recommendations")
            
            # Display user profile
            st.subheader("Your Profile")
            profile = self.recommender.load_user_profile(user_id)
            
            interests = profile.get("interests", [])
            if interests:
                st.write("**Interests:**")
                st.markdown(", ".join(interests))
            
            categories = profile.get("preferred_categories", [])
            if categories:
                st.write("**Categories:**")
                st.markdown(", ".join(categories))
            
            viewed = profile.get("viewed_items", [])
            if viewed:
                st.write(f"**Papers read:** {len(viewed)}")
            
            ratings = profile.get("rated_items", {})
            if ratings:
                avg_rating = sum(ratings.values()) / len(ratings) if ratings else 0
                st.write(f"**Papers rated:** {len(ratings)} (avg: {avg_rating:.1f}/5)")
            
            # Reset profile button
            if st.button("Reset Profile"):
                # Create empty profile with same user_id
                empty_profile = {
                    "user_id": user_id,
                    "interests": [],
                    "viewed_items": [],
                    "rated_items": {},
                    "preferred_categories": [],
                    "created_at": "",
                    "updated_at": ""
                }
                self.recommender.save_user_profile(user_id, empty_profile)
                st.success("Profile reset successfully!")
                st.experimental_rerun()
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["Recommendations", "All Papers", "By Cluster", "Visualizations"])
        
        with tab1:
            # Show personalized recommendations
            self.render_personalized_recommendations(papers, user_id)
        
        with tab2:
            # Show all papers
            self.render_paper_list(papers, user_id=user_id)
        
        with tab3:
            # Show papers by cluster
            if cluster_stats and 'clusters' in cluster_stats:
                # Create a dropdown to select cluster
                cluster_options = [
                    {"label": f"{c['label']} ({c['paper_count']} papers)", "value": c['id']} 
                    for c in cluster_stats['clusters']
                ]
                selected_cluster = st.selectbox(
                    "Select a cluster",
                    options=[c['id'] for c in cluster_stats['clusters']],
                    format_func=lambda x: next(
                        (c['label'] for c in cluster_stats['clusters'] if c['id'] == x),
                        f"Cluster {x}"
                    )
                )
                
                if selected_cluster is not None:
                    self.render_paper_list(papers, cluster_id=selected_cluster, user_id=user_id)
        
        with tab4:
            # Show visualizations
            self.render_cluster_visualization(cluster_stats)
            
            # Show other visualizations if we have enough papers
            if len(papers) > 10:
                # Count papers by category
                categories = {}
                for paper in papers:
                    for category in paper.get('categories', []):
                        categories[category] = categories.get(category, 0) + 1
                
                # Create bar chart for top categories
                top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]
                fig = px.bar(
                    x=[c[0] for c in top_categories],
                    y=[c[1] for c in top_categories],
                    labels={"x": "Category", "y": "Number of Papers"},
                    title="Top ArXiv Categories"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Publication timeline (if we have dates)
                if all('published' in p for p in papers):
                    # Extract dates and convert to datetime
                    try:
                        import pandas as pd
                        from datetime import datetime
                        
                        dates = [
                            pd.to_datetime(p['published']).date()
                            for p in papers if 'published' in p
                        ]
                        
                        date_counts = pd.Series(dates).value_counts().sort_index()
                        fig = px.line(
                            x=date_counts.index,
                            y=date_counts.values,
                            labels={"x": "Date", "y": "Papers Published"},
                            title="Paper Publication Timeline"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Could not generate timeline: {str(e)}")


def display():
    """Display the ArXiv papers component."""
    component = ArxivPapersComponent()
    component.render()
    
    
if __name__ == "__main__":
    display() 