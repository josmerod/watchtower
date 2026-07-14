"""ETL module for fetching, processing, and classifying research papers from ArXiv."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd

# Optional import; not required for basic latest files generation
try:
    from paperswithcode import PapersWithCodeClient  # type: ignore
except Exception:
    PapersWithCodeClient = None  # type: ignore

from src.etl.base import BaseETL
from src.utils.github_utils import find_github_links_in_text, get_github_repo_info
from src.utils.nlp_classifier import NLPContentClassifier
from src.watchers.arxiv_watcher import ArxivWatcher


class ArxivETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """ETL process for ArXiv papers using BaseETL framework.

    This ETL:
    1. Collects papers from ArXiv using the ArxivWatcher
    2. Processes and classifies the papers using NLP
    3. Transforms the data into structured formats
    4. Loads the processed data for use by other systems
    """

    def __init__(
        self,
        days_back: int = 7,
        max_results: int = 100,
        n_clusters: int = 10,
        **kwargs,
    ):
        """Initialize the ArXiv ETL.

        Args:
            days_back: Number of days back to collect papers
            max_results: Maximum number of papers to retrieve
            n_clusters: Number of clusters for the classifier
            **kwargs: Additional arguments for BaseETL
        """
        super().__init__(
            name="arxiv",
            description="ArXiv research papers ETL with NLP classification",
            **kwargs,
        )

        # Initialize watcher
        self.watcher = ArxivWatcher(
            name="arxiv",
            days_back=days_back,
            max_results=max_results,
            check_interval=86400,  # Run daily
        )

        # Initialize classifier
        self.classifier = NLPContentClassifier(name="arxiv_classifier")
        self.n_clusters = n_clusters

        self.logger.info(f"ArxivETL initialized with {days_back} days back, {max_results} max results")

    def extract(self) -> list[dict[str, Any]]:
        """Extract papers from ArXiv.

        Returns:
            List of papers with metadata
        """
        self.logger.info("Starting extraction phase")

        # Run the watcher once to collect papers
        self.watcher.run(continuous=False, max_runs=1)

        # Load papers from watcher output
        papers_file = self.watcher.data_dir / "latest_papers.json"
        self.logger.info(f"Attempting to load papers from: {papers_file}")

        if not papers_file.exists():
            self.logger.warning(f"File not found: {papers_file}. No papers found from watcher.")
            # List directory contents for debugging
            try:
                dir_contents = list(self.watcher.data_dir.iterdir())
                self.logger.info(f"Contents of {self.watcher.data_dir}: {dir_contents}")
            except Exception as e_ls:
                self.logger.error(f"Could not list directory {self.watcher.data_dir}: {e_ls}")
            return []

        try:
            papers = json.loads(papers_file.read_text(encoding="utf-8"))
            self.logger.info(f"Loaded {len(papers)} papers from watcher")
            return papers
        except Exception as e:
            self.logger.error(f"Error loading papers: {e!s}")
            return []

    def transform(self, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform and enrich papers with NLP classification and GitHub repository info.

        Args:
            papers: Raw papers from extraction phase

        Returns:
            Transformed papers with classification and GitHub info
        """
        if not papers:
            self.logger.warning("No papers to transform")
            return []

        self.logger.info(f"Starting transformation of {len(papers)} papers")

        # Extract text from papers for classification
        texts_for_classification = [f"{paper.get('title', '')} {paper.get('summary', '')}" for paper in papers]

        # Train or load classifier
        # Ensure models_dir is a Path object for proper path joining
        from pathlib import Path

        models_dir = Path(self.classifier.models_dir)
        model_path = models_dir / "model.pkl"
        if not model_path.exists():
            self.logger.info("Training new classifier")
            self.classifier.train_classifier(texts_for_classification, n_clusters=self.n_clusters)
            self.classifier.save_model()
        else:
            if not self.classifier.load_model():
                self.logger.info("Training new classifier (failed to load existing)")
                self.classifier.train_classifier(texts_for_classification, n_clusters=self.n_clusters)
                self.classifier.save_model()

        # Classify all papers
        classifications = self.classifier.batch_classify(texts_for_classification)

        # Merge classifications and GitHub info with papers
        transformed_papers = []
        github_token = None  # Configure via environment if needed

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
            text_to_search_github = f"{paper.get('summary', '')} {paper.get('comment', '')}"
            github_urls = find_github_links_in_text(text_to_search_github)

            if github_urls:
                self.logger.info(f"Found GitHub links for paper {paper.get('id', 'N/A')}: {github_urls}")
                fetched_repo_info = get_github_repo_info(github_urls[0], github_token=github_token)
                if fetched_repo_info:
                    self.logger.info(f"Fetched GitHub info for {github_urls[0]}")
                    github_info.update(fetched_repo_info)
                else:
                    self.logger.warning(f"Failed to fetch GitHub info for {github_urls[0]}")

            # Create transformed paper with classification and GitHub data
            transformed_paper = {
                **paper,
                "cluster_id": classification["cluster_id"],
                "cluster_label": classification["cluster_label"],
                "cluster_keywords": classification["cluster_keywords"],
                "extracted_keywords": classification["document_keywords"],
                **github_info,
                "processed_date": datetime.now().isoformat(),
            }

            transformed_papers.append(transformed_paper)

        self.logger.info(f"Transformed {len(transformed_papers)} papers into {len({c['cluster_id'] for c in classifications})} clusters")
        return transformed_papers

    def load(self, transformed_papers: list[dict[str, Any]]) -> None:
        """Load the transformed papers into various formats.

        Args:
            transformed_papers: Transformed papers with classification and GitHub info
        """
        if not transformed_papers:
            self.logger.warning("No papers to load")
            return

        self.logger.info(f"Loading {len(transformed_papers)} transformed papers")

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create processed subdirectories
        json_dir = self.output_dir / "json"
        csv_dir = self.output_dir / "csv"
        json_dir.mkdir(parents=True, exist_ok=True)
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        json_file = json_dir / f"papers_{timestamp}.json"
        try:
            json_file.write_text(
                json.dumps(transformed_papers, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.logger.info(f"Saved JSON to {json_file}")
        except Exception as e:
            self.logger.error(f"Error saving JSON: {e!s}")

        # Save as CSV
        try:
            df = pd.DataFrame(transformed_papers)

            # Handle nested/complex fields for CSV (flatten lists/dicts to strings)
            cols_to_flatten_simple_list = [
                "authors",
                "categories",
                "cluster_keywords",
                "extracted_keywords",
                "github_topics",
            ]
            for col in cols_to_flatten_simple_list:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x)

            if "github_languages" in df.columns:
                df["github_languages"] = df["github_languages"].apply(lambda x: ", ".join([f"{k}:{v}" for k, v in x.items()]) if isinstance(x, dict) else x)

            # Save DataFrame
            csv_file = csv_dir / f"papers_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding="utf-8")
            self.logger.info(f"Saved CSV to {csv_file}")
        except Exception as e:
            self.logger.error(f"Error saving CSV: {e!s}")

        # Save latest aliases for easy access (dashboard)
        try:
            latest_json = json_dir / "latest_papers.json"
            latest_json.write_text(
                json.dumps(transformed_papers, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            latest_csv = csv_dir / "latest_papers.csv"
            df.to_csv(latest_csv, index=False, encoding="utf-8")

            # Canonical latest files for dashboard tabs
            dashboard_latest_all = self.data_dir / "arxiv_papers_latest.json"
            dashboard_latest_all.write_text(
                json.dumps(transformed_papers, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            # Simple per-category splits
            def by_cat(prefix: str):
                return [p for p in transformed_papers if any(prefix in c for c in p.get("categories", []))]

            splits = {
                "arxiv_machine_learning_latest.json": by_cat("cs.LG") + by_cat("stat.ML"),
                "arxiv_computer_vision_latest.json": by_cat("cs.CV"),
                "arxiv_natural_language_latest.json": by_cat("cs.CL"),
                "arxiv_neural_networks_latest.json": by_cat("cs.NE"),
                "arxiv_robotics_latest.json": by_cat("cs.RO"),
                "arxiv_reinforcement_learning_latest.json": by_cat("cs.AI"),
            }
            for filename, items in splits.items():
                (self.data_dir / filename).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

            self.logger.info("Updated latest ArXiv dashboard files")
        except Exception as e:
            self.logger.error(f"Error updating latest files: {e!s}")

        # Generate cluster statistics
        self._generate_cluster_statistics(transformed_papers)

    def _generate_cluster_statistics(self, papers: list[dict[str, Any]]):
        """Generate statistics about the paper clusters.

        Args:
            papers: Transformed papers with cluster information
        """
        if not papers:
            return

        # Count papers per cluster
        cluster_counts = {}
        for paper in papers:
            cluster_id = paper.get("cluster_id")
            if cluster_id is not None:
                # Ensure cluster_id is an integer for dictionary key
                try:
                    cluster_id = int(cluster_id)
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid cluster_id {cluster_id}, skipping")
                    continue
                cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1

        # Get cluster labels
        cluster_labels = {}
        for paper in papers:
            cluster_id = paper.get("cluster_id")
            if cluster_id is not None:
                try:
                    cluster_id = int(cluster_id)
                except (ValueError, TypeError):
                    continue
                if cluster_id not in cluster_labels:
                    cluster_labels[cluster_id] = paper.get("cluster_label", f"Cluster {cluster_id}")

        # Create statistics with type safety
        total_papers = len(papers)
        statistics = {
            "total_papers": total_papers,
            "total_clusters": len(cluster_counts),
            "clusters": [
                {
                    "id": cluster_id,
                    "label": cluster_labels.get(cluster_id, f"Cluster {cluster_id}"),
                    "paper_count": count,
                    "percentage": (round(count / total_papers * 100, 2) if total_papers > 0 else 0.0),
                }
                for cluster_id, count in sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)
            ],
            "generated_at": datetime.now().isoformat(),
        }

        # Save statistics
        processed_dir = self.output_dir.parent / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        stats_file = processed_dir / "cluster_statistics.json"
        try:
            stats_file.write_text(json.dumps(statistics, ensure_ascii=False, indent=2), encoding="utf-8")
            self.logger.info(f"Saved cluster statistics to {stats_file}")
        except Exception as e:
            self.logger.error(f"Error saving cluster statistics: {e!s}")


if __name__ == "__main__":
    # Run the ETL pipeline
    etl = ArxivETL(days_back=7, max_results=100, n_clusters=8)
    etl.run()
