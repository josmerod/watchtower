import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.watchers.arxiv_watcher import ArxivWatcher
from src.utils.nlp_classifier import NLPContentClassifier
from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root


class ArxivETL:
    """
    ETL process for ArXiv papers.
    
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
        n_clusters: int = 10
    ):
        """
        Initialize the ArXiv ETL.
        
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
        ensure_directories([
            f"data/{name}",
            f"data/{name}/processed",
            f"data/{name}/processed/csv",
            f"data/{name}/processed/json"
        ])
        
        # Initialize components
        self.watcher = ArxivWatcher(
            name=name,
            days_back=days_back,
            max_results=max_results,
            check_interval=86400  # Run daily
        )
        
        self.classifier = NLPContentClassifier(name=f"{name}_classifier")
        self.n_clusters = n_clusters
        
        self.logger.info(f"ArxivETL initialized with {days_back} days back, {max_results} max results")
    
    def extract(self) -> List[Dict[str, Any]]:
        """
        Extract papers from ArXiv.
        
        Returns:
            List[Dict[str, Any]]: List of papers with metadata
        """
        self.logger.info("Starting extraction phase")
        
        # Run the watcher once to collect papers
        self.watcher.run(continuous=False, max_runs=1)
        
        # Load papers from watcher output
        papers_file = os.path.join(self.watcher.data_dir, "latest_papers.json")
        
        if not os.path.exists(papers_file):
            self.logger.warning("No papers found from watcher")
            return []
            
        try:
            with open(papers_file, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            self.logger.info(f"Loaded {len(papers)} papers from watcher")
            return papers
        except Exception as e:
            self.logger.error(f"Error loading papers: {str(e)}")
            return []
    
    def transform(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform and enrich papers with NLP classification.
        
        Args:
            papers (List[Dict[str, Any]]): Raw papers from extraction phase
            
        Returns:
            List[Dict[str, Any]]: Transformed papers with classification
        """
        if not papers:
            self.logger.warning("No papers to transform")
            return []
            
        self.logger.info(f"Starting transformation of {len(papers)} papers")
        
        # Extract text from papers for classification
        texts = [
            f"{paper['title']} {paper['summary']}"
            for paper in papers
        ]
        
        # Check if classifier is already trained
        model_path = os.path.join(self.classifier.models_dir, "model.pkl")
        if not os.path.exists(model_path):
            # Train new classifier
            self.logger.info("Training new classifier")
            self.classifier.train_classifier(texts, n_clusters=self.n_clusters)
            
            # Save the model
            self.classifier.save_model()
        else:
            # Try to load existing model
            if not self.classifier.load_model():
                # If loading fails, train a new one
                self.logger.info("Training new classifier (failed to load existing)")
                self.classifier.train_classifier(texts, n_clusters=self.n_clusters)
                self.classifier.save_model()
        
        # Classify all papers
        classifications = self.classifier.batch_classify(texts)
        
        # Merge classifications with papers
        transformed_papers = []
        for i, paper in enumerate(papers):
            classification = classifications[i]
            
            # Create transformed paper with classification data
            transformed_paper = {
                **paper,  # Include all original fields
                "cluster_id": classification["cluster_id"],
                "cluster_label": classification["cluster_label"],
                "cluster_keywords": classification["cluster_keywords"],
                "extracted_keywords": classification["document_keywords"],
                "processed_date": datetime.now().isoformat()
            }
            
            transformed_papers.append(transformed_paper)
        
        self.logger.info(f"Transformed {len(transformed_papers)} papers into {len(set(c['cluster_id'] for c in classifications))} clusters")
        return transformed_papers
    
    def load(self, transformed_papers: List[Dict[str, Any]]):
        """
        Load the transformed papers into various formats.
        
        Args:
            transformed_papers (List[Dict[str, Any]]): Transformed papers with classification
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
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(transformed_papers, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved JSON to {json_file}")
        except Exception as e:
            self.logger.error(f"Error saving JSON: {str(e)}")
        
        # Save as CSV
        try:
            # Convert to DataFrame
            df = pd.DataFrame(transformed_papers)
            
            # Handle nested fields (flatten lists to strings)
            for col in ['authors', 'categories', 'cluster_keywords', 'extracted_keywords']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
            
            # Save DataFrame
            csv_file = os.path.join(self.processed_dir, f"csv/papers_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding='utf-8')
            self.logger.info(f"Saved CSV to {csv_file}")
        except Exception as e:
            self.logger.error(f"Error saving CSV: {str(e)}")
        
        # Save latest version for easy access
        try:
            latest_json = os.path.join(self.processed_dir, "json/latest_papers.json")
            with open(latest_json, 'w', encoding='utf-8') as f:
                json.dump(transformed_papers, f, ensure_ascii=False, indent=2)
                
            latest_csv = os.path.join(self.processed_dir, "csv/latest_papers.csv")
            df.to_csv(latest_csv, index=False, encoding='utf-8')
            
            self.logger.info("Updated latest paper files")
        except Exception as e:
            self.logger.error(f"Error updating latest files: {str(e)}")
        
        # Generate cluster statistics
        self._generate_cluster_statistics(transformed_papers)
    
    def _generate_cluster_statistics(self, papers: List[Dict[str, Any]]):
        """
        Generate statistics about the paper clusters.
        
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
                cluster_labels[cluster_id] = paper.get("cluster_label", f"Cluster {cluster_id}")
        
        # Create statistics
        statistics = {
            "total_papers": len(papers),
            "total_clusters": len(cluster_counts),
            "clusters": [
                {
                    "id": cluster_id,
                    "label": cluster_labels.get(cluster_id, f"Cluster {cluster_id}"),
                    "paper_count": count,
                    "percentage": round(count / len(papers) * 100, 2)
                }
                for cluster_id, count in sorted(
                    cluster_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
            ],
            "generated_at": datetime.now().isoformat()
        }
        
        # Save statistics
        stats_file = os.path.join(self.processed_dir, "cluster_statistics.json")
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(statistics, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved cluster statistics to {stats_file}")
        except Exception as e:
            self.logger.error(f"Error saving cluster statistics: {str(e)}")
    
    def run(self):
        """Run the complete ETL pipeline."""
        self.logger.info(f"Starting ArXiv ETL pipeline")
        
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
            
            self.logger.info(f"ArXiv ETL pipeline completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in ETL pipeline: {str(e)}")


if __name__ == "__main__":
    # Run the ETL pipeline
    etl = ArxivETL(days_back=7, max_results=100, n_clusters=8)
    etl.run() 