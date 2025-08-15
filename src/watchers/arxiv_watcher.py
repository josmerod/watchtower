"""ArXiv Watcher for monitoring new research papers.

This module provides the `ArxivWatcher` class, which periodically checks
ArXiv for new papers in specified AI/ML and computer science categories.
It extracts paper metadata and saves information about new or updated papers.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import feedparser

from src.watchers.base_watcher import BaseWatcher


class ArxivWatcher(BaseWatcher):
    """
    Watcher for ArXiv papers related to AI/ML, Programming, Cloud Architecture, and Enterprise Architecture.

    This watcher monitors ArXiv for new papers in AI/ML categories and related computer science
    domains including programming languages, software engineering, distributed computing,
    networking, and systems architecture.
    """

    # ArXiv API URL with AI/ML categories
    ARXIV_API_BASE = "http://export.arxiv.org/api/query"

    # AI, ML, Programming, Cloud Architecture, and Enterprise Architecture related categories
    AI_ML_CATEGORIES = [
        # Core AI/ML Categories
        "cs.AI",  # Artificial Intelligence
        "cs.LG",  # Machine Learning
        "cs.CL",  # Computation and Language (NLP)
        "cs.CV",  # Computer Vision
        "cs.NE",  # Neural and Evolutionary Computing
        "stat.ML",  # Statistics - Machine Learning
        # Programming and Software Engineering
        "cs.PL",  # Programming Languages
        "cs.SE",  # Software Engineering
        "cs.LO",  # Logic in Computer Science
        "cs.FL",  # Formal Languages and Automata Theory
        "cs.DS",  # Data Structures and Algorithms
        # Cloud Architecture and Distributed Systems
        "cs.DC",  # Distributed, Parallel, and Cluster Computing
        "cs.NI",  # Networking and Internet Architecture
        "cs.OS",  # Operating Systems
        "cs.AR",  # Hardware Architecture
        "cs.SY",  # Systems and Control
        "cs.PF",  # Performance
        # Enterprise Architecture and Related Systems
        "cs.DB",  # Databases
        "cs.CY",  # Computers and Society
        "cs.ET",  # Emerging Technologies
        "cs.CR",  # Cryptography and Security
        "cs.SI",  # Social and Information Networks
        "cs.CE",  # Computational Engineering, Finance, and Science
    ]

    def __init__(
        self,
        name: str = "arxiv",
        check_interval: int = 86400,  # Default: check once per day
        max_results: int = 50,
        days_back: int = 7,
    ):
        """
        Initialize the ArXiv watcher.

        Args:
            name (str): Unique name for this watcher
            check_interval (int): Time in seconds between checks (default: 1 day)
            max_results (int): Maximum number of papers to retrieve per check
            days_back (int): Number of days back to search for papers
        """
        # Construct the API URL with search parameters
        categories = " OR ".join(self.AI_ML_CATEGORIES)

        # Calculate date for papers published since days_back
        date_since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Build the complete search URL
        search_query = (
            f"cat:({categories}) AND submittedDate:[{date_since}000000 TO 999999999999]"
        )
        self.api_url = f"{self.ARXIV_API_BASE}?search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"

        self.max_results = max_results
        self.days_back = days_back

        # Initialize the base watcher
        super().__init__(name, self.api_url, check_interval)

    def extract_value(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Extract papers from the ArXiv API response.

        Args:
            xml_content (str): XML response from ArXiv API

        Returns:
            List[Dict[str, Any]]: List of papers with their metadata
        """
        self.logger.info("Parsing ArXiv API response")
        feed = feedparser.parse(xml_content)

        papers = []
        for entry in feed.entries:
            # Extract authors
            authors = [author.name for author in entry.authors]

            # Extract categories
            categories = (
                [tag.term for tag in entry.tags] if hasattr(entry, "tags") else []
            )

            # Create paper entry
            paper = {
                "id": entry.id.split("/")[-1],
                "title": entry.title,
                "authors": authors,
                "categories": categories,
                "summary": entry.summary,
                "published": entry.published,
                "updated": entry.updated,
                "link": entry.link,
                "pdf_url": next(
                    (
                        link.href
                        for link in entry.links
                        if link.rel == "alternate" and link.type == "application/pdf"
                    ),
                    None,
                ),
            }

            papers.append(paper)

        self.logger.info(f"Found {len(papers)} papers")
        return papers

    def has_changed(
        self, old_papers: List[Dict[str, Any]], new_papers: List[Dict[str, Any]]
    ) -> bool:
        """
        Determine if there are new papers or changes in the papers.

        Args:
            old_papers: Previously fetched papers
            new_papers: Currently fetched papers

        Returns:
            bool: True if there are new papers or updates
        """
        if not old_papers:
            return True

        # Extract IDs of papers we already have
        old_ids = {paper["id"] for paper in old_papers}
        new_ids = {paper["id"] for paper in new_papers}

        # Check if there are new papers
        added_papers = new_ids - old_ids

        if added_papers:
            self.logger.info(f"Found {len(added_papers)} new papers")
            return True

        # Even if no new papers, check if any existing papers have been updated
        for new_paper in new_papers:
            paper_id = new_paper["id"]
            if paper_id in old_ids:
                old_paper = next((p for p in old_papers if p["id"] == paper_id), None)
                if old_paper and new_paper["updated"] != old_paper["updated"]:
                    self.logger.info(f"Paper {paper_id} has been updated")
                    return True

        self.logger.info("No changes detected in ArXiv papers")
        return False

    def trigger_alarm(
        self, old_papers: List[Dict[str, Any]], new_papers: List[Dict[str, Any]]
    ):
        """
        Process new papers when detected.

        Args:
            old_papers: Previously fetched papers
            new_papers: Currently fetched papers
        """
        old_ids = {paper["id"] for paper in old_papers} if old_papers else set()

        # Identify new papers
        new_ids = set()
        updated_ids = set()

        for paper in new_papers:
            paper_id = paper["id"]
            if paper_id not in old_ids:
                new_ids.add(paper_id)
            else:
                # Check if existing paper was updated
                old_paper = next((p for p in old_papers if p["id"] == paper_id), None)
                if old_paper and paper["updated"] != old_paper["updated"]:
                    updated_ids.add(paper_id)

        # Log the changes
        if new_ids:
            self.logger.warning(f"NEW PAPERS DETECTED: {len(new_ids)} new papers found")

            # Save new papers separately for easy access
            new_papers_list = [p for p in new_papers if p["id"] in new_ids]
            self._save_papers(new_papers_list, "new_papers")

            # Save detailed information for each new paper
            for paper in new_papers_list:
                paper_id = paper["id"]
                self._save_paper_detail(paper, paper_id)

        if updated_ids:
            self.logger.warning(
                f"UPDATED PAPERS DETECTED: {len(updated_ids)} papers updated"
            )

        # Record the event with details about changes
        event_details = {
            "new_papers": list(new_ids),
            "updated_papers": list(updated_ids),
            "total_papers": len(new_papers),
        }

        super()._record_event(
            event_type="papers_changed",
            old_value=old_papers,
            new_value=new_papers,
            details=event_details,
        )

        # Save all papers for reference
        self._save_papers(new_papers, "latest_papers")

    def _save_papers(self, papers: List[Dict[str, Any]], filename: str):
        """
        Save papers to a JSON file.

        Args:
            papers (List[Dict[str, Any]]): Papers to save
            filename (str): Filename without extension
        """
        self.logger.info(
            f"Attempting to save papers to {filename}.json in {self.data_dir}"
        )
        filepath = os.path.join(self.data_dir, f"{filename}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(papers)} papers to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving papers to {filepath}: {str(e)}")

    def _save_paper_detail(self, paper: Dict[str, Any], paper_id: str):
        """
        Save detailed information for a single paper.

        Args:
            paper (Dict[str, Any]): Paper data
            paper_id (str): Paper ID
        """
        # Create directory for individual papers if it doesn't exist
        papers_dir = os.path.join(self.data_dir, "papers")
        if not os.path.exists(papers_dir):
            os.makedirs(papers_dir)

        filepath = os.path.join(papers_dir, f"{paper_id}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(paper, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving paper detail to {filepath}: {str(e)}")

    def fetch_page(self) -> str:
        """
        Fetch the ArXiv API response.

        Overrides the base method to use the API URL that may change based on dates.

        Returns:
            str: XML content from ArXiv API
        """
        # Update the date range to always be relative to current time
        date_since = (datetime.now() - timedelta(days=self.days_back)).strftime(
            "%Y-%m-%d"
        )
        categories = " OR ".join(self.AI_ML_CATEGORIES)
        search_query = (
            f"cat:({categories}) AND submittedDate:[{date_since}000000 TO 999999999999]"
        )

        current_url = f"{self.ARXIV_API_BASE}?search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results={self.max_results}"
        self.url = current_url

        return super().fetch_page()
