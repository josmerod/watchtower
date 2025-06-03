"""Streamlit component for advanced ArXiv paper search.

This module provides the `ArxivSearchComponent` class, which allows users
to search through a collection of ArXiv papers using text queries,
category filters, and date range filters. It uses TF-IDF for relevance ranking.
"""
import os
import sys
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Add project root to path
from src.utils.file_system import get_project_root


class ArxivSearchComponent:
    """
    Advanced search component for ArXiv papers.
    """
    
    def __init__(self):
        """Initialize the ArXiv search component."""
        self.project_root = get_project_root()
        self.data_dir = os.path.join(self.project_root, "data/arxiv")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        
        # Initialize search index
        self.papers = []
        self.vectorizer = None
        self.paper_vectors = None
        self.search_index_built = False
        
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
            return papers
        except Exception as e:
            st.error(f"Error loading papers: {str(e)}")
            return []
    
    def _build_search_index(self):
        """Build a search index for the papers."""
        if self.search_index_built:
            return
            
        # Load papers if not already loaded
        if not self.papers:
            self.papers = self._load_papers()
            
        if not self.papers:
            return
            
        # Create document texts
        texts = []
        for paper in self.papers:
            title = paper.get("title", "")
            abstract = paper.get("summary", "")
            authors = " ".join(paper.get("authors", []))
            categories = " ".join(paper.get("categories", []))
            
            # Get extracted keywords and cluster keywords if available
            keywords = " ".join(paper.get("extracted_keywords", []))
            cluster_keywords = " ".join(paper.get("cluster_keywords", []))
            
            # Combine all fields with different weights
            # Title and keywords are most important, then abstract, then authors/categories
            text = f"{title} {title} {abstract} {keywords} {keywords} {cluster_keywords} {categories} {authors}"
            texts.append(text)
        
        # Create TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_df=0.8,
            min_df=2
        )
        
        # Create TF-IDF matrix
        self.paper_vectors = self.vectorizer.fit_transform(texts)
        
        # Mark search index as built
        self.search_index_built = True
        
    def search(
        self, 
        query: str, 
        categories: Optional[List[str]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        max_results: int = 20,
        min_similarity: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Search for papers matching the query.
        
        Args:
            query (str): Search query
            categories (Optional[List[str]]): List of categories to filter by
            date_range (Optional[Tuple[str, str]]): Start and end dates to filter by
            max_results (int): Maximum number of results to return
            min_similarity (float): Minimum similarity threshold
            
        Returns:
            List[Dict[str, Any]]: List of matching papers with similarity scores
        """
        # Build search index if needed
        self._build_search_index()
        
        if not self.search_index_built or not query:
            return []
        
        # Transform query to vector
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarity to all papers
        similarities = cosine_similarity(query_vector, self.paper_vectors).flatten()
        
        # Create list of paper indices and similarities
        paper_similarities = []
        for i, sim in enumerate(similarities):
            if sim >= min_similarity:
                paper = self.papers[i]
                
                # Apply category filter if specified
                if categories and not any(cat in paper.get("categories", []) for cat in categories):
                    continue
                
                # Apply date filter if specified
                if date_range:
                    start_date, end_date = date_range
                    pub_date = paper.get("published", "")
                    
                    # Skip if published date is outside range
                    if not start_date <= pub_date <= end_date:
                        continue
                
                paper_similarities.append({
                    "paper": paper,
                    "similarity": float(sim)
                })
        
        # Sort by similarity (descending)
        paper_similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top matches
        return paper_similarities[:max_results]
    
    def render(self):
        """Render the search component."""
        st.title("🔍 Advanced ArXiv Paper Search")
        
        # Load papers
        papers = self._load_papers()
        
        if not papers:
            st.warning("No papers available. Run the ArXiv ETL pipeline first.")
            return
        
        # Build search index
        self._build_search_index()
        
        # Get available categories
        all_categories = set()
        for paper in papers:
            all_categories.update(paper.get("categories", []))
        
        # Display search form
        with st.form("arxiv_search_form"):
            # Text query
            query = st.text_input(
                "Search query",
                help="Enter keywords to search in titles, abstracts, and more"
            )
            
            col1, col2 = st.columns(2)
            
            # Category filter
            with col1:
                selected_categories = st.multiselect(
                    "Filter by categories",
                    options=sorted(list(all_categories)),
                    help="Select categories to filter results"
                )
            
            # Date range filter
            with col2:
                date_range = st.date_input(
                    "Filter by date range",
                    value=[],
                    help="Select date range for publications"
                )
                
                # Convert date range to strings if provided
                if date_range and len(date_range) == 2:
                    date_range_str = (
                        date_range[0].strftime("%Y-%m-%d"),
                        date_range[1].strftime("%Y-%m-%d")
                    )
                else:
                    date_range_str = None
            
            # Search settings
            col1, col2 = st.columns(2)
            
            with col1:
                max_results = st.slider(
                    "Maximum results",
                    min_value=5,
                    max_value=100,
                    value=20,
                    step=5
                )
            
            with col2:
                min_similarity = st.slider(
                    "Minimum relevance",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.1,
                    step=0.05
                )
            
            # Submit button
            submitted = st.form_submit_button("Search")
        
        # Display results if form submitted
        if submitted and query:
            with st.spinner("Searching..."):
                results = self.search(
                    query=query,
                    categories=selected_categories if selected_categories else None,
                    date_range=date_range_str,
                    max_results=max_results,
                    min_similarity=min_similarity
                )
            
            # Display results count
            if not results:
                st.info("No matching papers found.")
            else:
                st.markdown(f"### Found {len(results)} matching papers")
                
                # Display results
                for result in results:
                    paper = result["paper"]
                    similarity = result["similarity"]
                    
                    # Format similarity as percentage
                    relevance = int(similarity * 100)
                    
                    # Create paper card
                    with st.container():
                        # Add relevance indicator
                        st.markdown(f"**Relevance: {relevance}%** - {paper.get('published', '').split('T')[0]}")
                        
                        # Title with link
                        st.markdown(f"### [{paper['title']}]({paper['link']})")
                        
                        # Authors 
                        authors = ", ".join(paper.get("authors", [])[:3])
                        if len(paper.get("authors", [])) > 3:
                            authors += " et al."
                        st.markdown(f"**Authors:** {authors}")
                        
                        # Categories
                        categories = ", ".join(paper.get("categories", []))
                        st.markdown(f"**Categories:** {categories}")
                        
                        # Show abstract in expander
                        with st.expander("Abstract"):
                            st.markdown(paper.get("summary", "No abstract available"))
                            
                            # Keywords if available
                            keywords = paper.get("extracted_keywords", [])
                            if keywords:
                                st.markdown(f"**Keywords:** {', '.join(keywords)}")
                        
                        st.divider()


def display():
    """Display the ArXiv search component."""
    component = ArxivSearchComponent()
    component.render()
    
    
if __name__ == "__main__":
    display() 