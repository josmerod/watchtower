"""ETL module for fetching, processing, and classifying research papers from ArXiv."""

import json
import os
import sys
from datetime import datetime
from typing import Any

import pandas as pd

# Optional import; not required for basic latest files generation
try:
    from paperswithcode import PapersWithCodeClient  # type: ignore
except Exception:  # noqa: BLE001
    PapersWithCodeClient = None  # type: ignore

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.github_utils import find_github_links_in_text, get_github_repo_info
from src.utils.logging import get_logger
from src.utils.nlp_classifier import NLPContentClassifier
from src.utils.pwc_utils import get_pwc_details_for_paper
from src.watchers.arxiv_watcher import ArxivWatcher

# from paperswithcode import PapersWithCodeClient # Commented out for testing


class ArxivETL:
    """ETL process for ArXiv papers.

    This ETL:
    1. Collects papers from ArXiv using the ArxivWatcher
    2. Processes and classifies the papers using NLP
    3. Transforms the data into structured formats
    4. Loads the processed data for use by other systems
    """

    def __init__(
        self,
        name: str = "arxiv",
        days_back: int = 7,
        max_results: int = 100,
        n_clusters: int = 10,
    ):
        """Initialize the ArXiv ETL.

        Args:
            name (str): Name for this ETL process
            days_back (int): Number of days back to collect papers
            max_results (int): Maximum number of papers to retrieve
            n_clusters (int): Number of clusters for the classifier
        """
        self.name = name
        self.logger = get_logger(f"ETL_{name}")

        # Initialize paths
        self.project_root = get_project_root()
        self.data_dir = os.path.join(self.project_root, f"data/{name}")
        self.processed_dir = os.path.join(self.data_dir, "processed")

        # Ensure directories exist
        ensure_directories(
            [
                f"data/{name}",
                f"data/{name}/processed",
                f"data/{name}/processed/csv",
                f"data/{name}/processed/json",
            ]
        )

        # Initialize components
        self.watcher = ArxivWatcher(
            name=name,
            days_back=days_back,
            max_results=max_results,
            check_interval=86400,  # Run daily
        )

        self.classifier = NLPContentClassifier(name=f"{name}_classifier")
        self.n_clusters = n_clusters
        # self.pwc_client = PapersWithCodeClient() # Commented out for testing

        self.logger.info(
            f"ArxivETL initialized with {days_back} days back, {max_results} max results"
        )

    def extract(self) -> list[dict[str, Any]]:
        """Extract papers from ArXiv.

        Returns:
            List[Dict[str, Any]]: List of papers with metadata
        """
        self.logger.info("Starting extraction phase")

        # Run the watcher once to collect papers
        self.watcher.run(continuous=False, max_runs=1)

        # Load papers from watcher output
        papers_file = os.path.join(self.watcher.data_dir, "latest_papers.json")
        self.logger.info(
            f"Attempting to load papers from: {papers_file}"
        )  # Detailed log

        if not os.path.exists(papers_file):
            self.logger.warning(
                f"File not found: {papers_file}. No papers found from watcher."
            )  # Detailed log
            # Listing directory contents for debugging
            try:
                dir_contents = os.listdir(self.watcher.data_dir)
                self.logger.info(f"Contents of {self.watcher.data_dir}: {dir_contents}")
            except Exception as e_ls:
                self.logger.error(
                    f"Could not list directory {self.watcher.data_dir}: {e_ls}"
                )
            return []

        try:
            with open(papers_file, encoding="utf-8") as f:
                papers = json.load(f)
            self.logger.info(f"Loaded {len(papers)} papers from watcher")
            return papers
        except Exception as e:
            self.logger.error(f"Error loading papers: {e!s}")
            return []

    def transform(self, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform and enrich papers with NLP classification, GitHub repository info, and PapersWithCode data.

        Args:
            papers (List[Dict[str, Any]]): Raw papers from extraction phase

        Returns:
            List[Dict[str, Any]]: Transformed papers with classification, GitHub, and PapersWithCode info
        """
        if not papers:
            self.logger.warning("No papers to transform")
            return []

        self.logger.info(f"Starting transformation of {len(papers)} papers")

        # Extract text from papers for classification
        texts_for_classification = [
            f"{paper.get('title', '')} {paper.get('summary', '')}" for paper in papers
        ]

        # Check if classifier is already trained
        model_path = os.path.join(self.classifier.models_dir, "model.pkl")
        if not os.path.exists(model_path):
            # Train new classifier
            self.logger.info("Training new classifier")
            self.classifier.train_classifier(
                texts_for_classification, n_clusters=self.n_clusters
            )
            self.classifier.save_model()
        else:
            # Try to load existing model
            if not self.classifier.load_model():
                # If loading fails, train a new one
                self.logger.info("Training new classifier (failed to load existing)")
                self.classifier.train_classifier(
                    texts_for_classification, n_clusters=self.n_clusters
                )
                self.classifier.save_model()

        # Classify all papers
        classifications = self.classifier.batch_classify(texts_for_classification)

        # Merge classifications, GitHub info, and PapersWithCode info with papers
        transformed_papers = []
        github_token = os.getenv("GITHUB_TOKEN")  # For authenticated GitHub requests

        for i, paper in enumerate(papers):
            classification = classifications[i]

            # Initialize GitHub fields
            github_info = {
                "github_html_url": None,
                "github_description": None,
                "github_stars": None,
                "github_forks": None,
                "github_watchers": None,
                "github_open_issues": None,
                "github_last_updated": None,
                "github_created_at": None,
                "github_language": None,
                "github_languages": None,
                "github_topics": None,
                "github_has_issues": None,
                "github_has_projects": None,
                "github_has_wiki": None,
                "github_has_pages": None,
                "github_default_branch": None,
            }

            # Find and process GitHub links
            text_to_search_github = (
                f"{paper.get('summary', '')} {paper.get('comment', '')}"
            )
            github_urls = find_github_links_in_text(text_to_search_github)

            if github_urls:
                self.logger.info(
                    f"Found GitHub links for paper {paper.get('id', 'N/A')}: {github_urls}"
                )
                fetched_repo_info = get_github_repo_info(
                    github_urls[0], github_token=github_token
                )
                if fetched_repo_info:
                    self.logger.info(f"Fetched GitHub info for {github_urls[0]}")
                    github_info.update(fetched_repo_info)
                else:
                    self.logger.warning(
                        f"Failed to fetch GitHub info for {github_urls[0]}"
                    )

            # Initialize PapersWithCode fields (Commented out for testing)
            # pwc_data = {
            #     "pwc_id": None,
            #     "pwc_url": None,
            #     "pwc_title": None,
            #     "pwc_proceeding": None,
            #     "pwc_repositories": [],
            #     "pwc_datasets": [],
            #     "pwc_tasks_and_metrics": [],
            #     "pwc_methods": [],
            # }

            # Fetch PapersWithCode data (Commented out for testing)
            # arxiv_id_url = paper.get(
            #     "id"
            # )  # This is often the arxiv URL like http://arxiv.org/abs/xxxx.xxxx
            # paper_title = paper.get("title")

            # if arxiv_id_url or paper_title:
            #     self.logger.info(
            #         f"Fetching PwC data for paper ArXiv ID: {arxiv_id_url if arxiv_id_url else 'N/A'}, Title: {paper_title if paper_title else 'N/A'} (PwC integration temporarily disabled)"
            #     )
            # fetched_pwc_info = get_pwc_details_for_paper(
            #     arxiv_id_url=arxiv_id_url,
            #     title=paper_title,
            #     pwc_client=self.pwc_client, # This would error as self.pwc_client is commented out
            # )
            # if fetched_pwc_info:
            #     self.logger.info(
            #         f"Fetched PwC info for paper {arxiv_id_url if arxiv_id_url else paper_title}"
            #     )
            #     pwc_data.update(fetched_pwc_info)
            # else:
            #     self.logger.warning(
            #         f"No PwC info found for paper {arxiv_id_url if arxiv_id_url else paper_title}"
            #     )

            # Create transformed paper with classification, GitHub, and PwC data
            transformed_paper = {
                **paper,
                "cluster_id": classification["cluster_id"],
                "cluster_label": classification["cluster_label"],
                "cluster_keywords": classification["cluster_keywords"],
                "extracted_keywords": classification["document_keywords"],
                **github_info,
                # **pwc_data,  # Add PapersWithCode information (Commented out for testing)
                "processed_date": datetime.now().isoformat(),
            }

            transformed_papers.append(transformed_paper)

        self.logger.info(
            f"Transformed {len(transformed_papers)} papers into {len(set(c['cluster_id'] for c in classifications))} clusters, enriched with GitHub and PapersWithCode data."
        )
        return transformed_papers

    def load(self, transformed_papers: list[dict[str, Any]]):
        """Load the transformed papers into various formats.

        Args:
            transformed_papers (List[Dict[str, Any]]): Transformed papers with classification, GitHub, and PwC info
        """
        if not transformed_papers:
            self.logger.warning("No papers to load")
            return

        self.logger.info(f"Loading {len(transformed_papers)} transformed papers")

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = os.path.join(self.processed_dir, f"json/papers_{timestamp}.json")
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(transformed_papers, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved JSON to {json_file}")
        except Exception as e:
            self.logger.error(f"Error saving JSON: {e!s}")

        # Save as CSV
        try:
            # Convert to DataFrame
            df = pd.DataFrame(transformed_papers)

            # Handle nested/complex fields for CSV (flatten lists/dicts to strings)
            # Original fields: authors, categories, cluster_keywords, extracted_keywords
            # GitHub fields: github_languages (dict), github_topics (list)
            # PwC fields: pwc_repositories (list of dicts), pwc_datasets (list of dicts),
            #             pwc_tasks_and_metrics (list of dicts), pwc_methods (list of str)

            cols_to_flatten_simple_list = [
                "authors",
                "categories",
                "cluster_keywords",
                "extracted_keywords",
                "github_topics",
                "pwc_methods",
            ]
            for col in cols_to_flatten_simple_list:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x
                    )

            if "github_languages" in df.columns:
                df["github_languages"] = df["github_languages"].apply(
                    lambda x: (
                        ", ".join([f"{k}:{v}" for k, v in x.items()])
                        if isinstance(x, dict)
                        else x
                    )
                )

            # Flatten lists of dictionaries for PwC fields
            list_of_dicts_cols = [
                "pwc_repositories",
                "pwc_datasets",
                "pwc_tasks_and_metrics",
            ]
            for col in list_of_dicts_cols:
                if col in df.columns:
                    # Convert list of dicts to a string representation of JSON or simplify
                    # For CSV, a simple string representation of list of dicts might be too complex.
                    # Let's try to make it a |-separated list of key aspects, e.g. name or id.
                    # Or convert the whole list of dicts to a JSON string.
                    df[col] = df[col].apply(
                        lambda x: (
                            json.dumps(x)
                            if isinstance(x, list) and x
                            else (x if not isinstance(x, list) else None)
                        )
                    )

            # Save DataFrame
            csv_file = os.path.join(self.processed_dir, f"csv/papers_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding="utf-8")
            self.logger.info(f"Saved CSV to {csv_file}")
        except Exception as e:
            self.logger.error(f"Error saving CSV: {e!s}")

        # Save latest aliases for easy access (dashboard)
        try:
            latest_json = os.path.join(self.processed_dir, "json/latest_papers.json")
            with open(latest_json, "w", encoding="utf-8") as f:
                json.dump(transformed_papers, f, ensure_ascii=False, indent=2)

            latest_csv = os.path.join(self.processed_dir, "csv/latest_papers.csv")
            df.to_csv(latest_csv, index=False, encoding="utf-8")

            # Canonical latest files for dashboard tabs
            dashboard_latest_all = os.path.join(
                self.data_dir, "arxiv_papers_latest.json"
            )
            with open(dashboard_latest_all, "w", encoding="utf-8") as f:
                json.dump(transformed_papers, f, ensure_ascii=False, indent=2)

            # Simple per-category splits (best-effort)
            def by_cat(prefix: str):
                return [
                    p
                    for p in transformed_papers
                    if any(prefix in c for c in p.get("categories", []))
                ]

            splits = {
                "arxiv_machine_learning_latest.json": by_cat("cs.LG")
                + by_cat("stat.ML"),
                "arxiv_computer_vision_latest.json": by_cat("cs.CV"),
                "arxiv_natural_language_latest.json": by_cat("cs.CL"),
                "arxiv_neural_networks_latest.json": by_cat("cs.NE"),
                "arxiv_robotics_latest.json": by_cat("cs.RO"),
                "arxiv_reinforcement_learning_latest.json": by_cat("cs.AI"),
            }
            for filename, items in splits.items():
                with open(
                    os.path.join(self.data_dir, filename), "w", encoding="utf-8"
                ) as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)

            self.logger.info("Updated latest ArXiv dashboard files")
        except Exception as e:
            self.logger.error(f"Error updating latest files: {e!s}")

        # Generate cluster statistics
        self._generate_cluster_statistics(transformed_papers)

    def _generate_cluster_statistics(self, papers: list[dict[str, Any]]):
        """Generate statistics about the paper clusters.

        Args:
            papers (List[Dict[str, Any]]): Transformed papers with cluster information
        """
        if not papers:
            return

        # Count papers per cluster
        cluster_counts = {}
        for paper in papers:
            cluster_id = paper.get("cluster_id")
            if cluster_id is not None:
                cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1

        # Get cluster labels
        cluster_labels = {}
        for paper in papers:
            cluster_id = paper.get("cluster_id")
            if cluster_id is not None and cluster_id not in cluster_labels:
                cluster_labels[cluster_id] = paper.get(
                    "cluster_label", f"Cluster {cluster_id}"
                )

        # Create statistics
        statistics = {
            "total_papers": len(papers),
            "total_clusters": len(cluster_counts),
            "clusters": [
                {
                    "id": cluster_id,
                    "label": cluster_labels.get(cluster_id, f"Cluster {cluster_id}"),
                    "paper_count": count,
                    "percentage": round(count / len(papers) * 100, 2),
                }
                for cluster_id, count in sorted(
                    cluster_counts.items(), key=lambda x: x[1], reverse=True
                )
            ],
            "generated_at": datetime.now().isoformat(),
        }

        # Save statistics
        stats_file = os.path.join(self.processed_dir, "cluster_statistics.json")
        try:
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(statistics, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved cluster statistics to {stats_file}")
        except Exception as e:
            self.logger.error(f"Error saving cluster statistics: {e!s}")

    def run(self):
        """Run the complete ETL pipeline."""
        self.logger.info("Starting ArXiv ETL pipeline")

        try:
            # Extract
            papers = self.extract()
            if not papers:
                self.logger.warning("No papers extracted, stopping pipeline")
                return

            # Transform
            transformed_papers = self.transform(papers)
            if not transformed_papers:
                self.logger.warning("No papers transformed, stopping pipeline")
                return

            # Load
            self.load(transformed_papers)

            self.logger.info("ArXiv ETL pipeline completed successfully")

        except Exception as e:
            self.logger.error(f"Error in ETL pipeline: {e!s}")
            raise  # Re-raise the exception


if __name__ == "__main__":
    # Run the ETL pipeline
    etl = ArxivETL(days_back=7, max_results=100, n_clusters=8)
    etl.run()
