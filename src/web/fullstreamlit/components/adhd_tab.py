import json
import os
from typing import Any

import streamlit as st

# Add project root to path for module access if not already handled by app.py
# This might be needed if running this component standalone or for robust pathing
from utils.file_system import get_project_root


class ADHDPapersComponent:
    def __init__(self):
        self.project_root = get_project_root()
        # The data_dir should point to the output of the ETL, which is now <project_root>/data/<etl_name>/output
        # For adhd_publications ETL, etl_name is "adhd_publications"
        self.etl_output_dir = os.path.join(
            self.project_root, "data", "adhd_publications", "output"
        )
        self.data_file_path = os.path.join(
            self.etl_output_dir, "json", "latest_papers.json"
        )

    def _load_data(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.data_file_path):
            st.error(
                f"Data file not found: {self.data_file_path}. Please ensure the ADHDPublicationETL has been run."
            )
            return []
        try:
            with open(self.data_file_path, encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            st.error(f"Error loading ADHD data: {e}")
            return []

    def render_paper_card(self, paper: dict[str, Any], index: int):
        with st.expander(f"{paper.get('title', 'N/A')}"):
            st.markdown(f"**Authors:** {', '.join(paper.get('authors', ['N/A']))}")
            st.markdown(f"**Date:** {paper.get('publication_date', 'N/A')}")
            st.markdown(f"**Source:** {paper.get('source', 'N/A')}")
            if paper.get("doi"):
                st.markdown(
                    f"**DOI:** [{paper.get('doi')}](https://doi.org/{paper.get('doi')})"
                )
            if paper.get("url"):
                st.markdown(f"**Link:** [View Paper]({paper.get('url')})")

            # Display abstract, handling potential None or empty strings
            abstract_text = paper.get("abstract", "No abstract available.")
            if not abstract_text:  # Check for empty string as well
                abstract_text = "No abstract available."
            st.write(f"**Abstract:** {abstract_text}")

    def render(self):
        st.title("ADHD Papers and Resources")

        papers = self._load_data()

        if not papers:
            st.warning("No ADHD papers found. Please run the ADHDPublicationETL first.")
            # Optionally, add a button to trigger the ETL if feasible and safe.
            # Example: if st.button("Run ADHD ETL Process"):
            #   st.info("ETL process started... (This is a placeholder)")
            #   # In a real scenario, this would trigger a background task.
            return

        st.markdown(f"Displaying {len(papers)} papers.")

        # Basic search/filter
        search_term = st.text_input("Search by title or abstract:")

        filtered_papers = papers
        if search_term:
            search_term_lower = search_term.lower()
            filtered_papers = [
                p
                for p in papers
                if search_term_lower in p.get("title", "").lower()
                or search_term_lower in p.get("abstract", "").lower()
            ]
            st.markdown(f"Found {len(filtered_papers)} papers matching your search.")

        if not filtered_papers and search_term:  # Only show if a search was performed
            st.info("No papers match your current search criteria.")
            return
        elif not filtered_papers and not search_term:  # No papers loaded and no search
            pass  # The initial "No ADHD papers found" warning handles this.

        for i, paper in enumerate(filtered_papers):
            self.render_paper_card(paper, i)


# Function to be called by app.py
def display():
    component = ADHDPapersComponent()
    component.render()


# For standalone testing of the component
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    display()
