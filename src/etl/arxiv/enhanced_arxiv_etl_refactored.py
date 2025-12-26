"""Refactored Enhanced ArXiv ETL with clean architecture.

This ETL provides advanced intelligence features for ArXiv papers including:
- Impact scoring and analysis
- Technology readiness assessment
- Commercial potential evaluation
- External integrations (GitHub, PapersWithCode)
"""

import json
import os
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.exceptions.etl import ExtractionError, LoadError, TransformationError
from src.models.arxiv import (
    CommercialPotential,
    EnhancedArxivPaperModel,
    GitHubRepositoryModel,
    PapersWithCodeModel,
    TechnologyReadinessLevel,
)
from src.utils.nlp_classifier import NLPContentClassifier
from src.watchers.enhanced_arxiv_watcher import EnhancedArxivWatcher

from .config import DEFAULT_CONFIG, EnhancedArxivConfig
from .services import AnalysisService, IntegrationService, ScoringService


class EnhancedArxivETLRefactored(BaseETL):
    """Refactored Enhanced ArXiv ETL with service layer architecture.

    This refactored version separates concerns into focused services:
    - ScoringService: Calculates impact, TRL, commercial, innovation scores
    - AnalysisService: Extracts technologies, applications, methodologies
    - IntegrationService: Handles GitHub and PapersWithCode integrations
    """

    def __init__(
        self,
        config: EnhancedArxivConfig | None = None,
        **kwargs,
    ):
        """Initialize the refactored Enhanced ArXiv ETL.

        Args:
            config: ETL configuration
            **kwargs: Additional arguments for base class
        """
        if config is None:
            config = DEFAULT_CONFIG

        super().__init__(config.name, **kwargs)

        self.config = config
        self.days_back = config.days_back
        self.max_results = config.max_results
        self.n_clusters = config.n_clusters
        self.enable_advanced_scoring = config.enable_advanced_scoring
        self.enable_github_integration = config.enable_github_integration
        self.enable_pwc_integration = config.enable_pwc_integration

        # Initialize services
        self.scoring_service = ScoringService(debug=config.debug)
        self.analysis_service = AnalysisService(debug=config.debug)
        self.integration_service = IntegrationService(
            enable_github=config.enable_github_integration,
            enable_pwc=config.enable_pwc_integration,
            debug=config.debug,
        )

        # Initialize NLP classifier
        self.classifier = NLPContentClassifier(name=f"{config.name}_classifier")

        # Initialize watcher
        self.watcher = EnhancedArxivWatcher(
            name=f"{config.name}_watcher",
            days_back=config.days_back,
            max_results=config.max_results,
            check_interval=86400,
        )

        self.logger.info("Refactored Enhanced ArXiv ETL initialized with service layer")

    def extract(self) -> list[dict[str, Any]]:
        """Extract papers from ArXiv using the enhanced watcher.

        Returns:
            List of enhanced paper dictionaries
        """
        try:
            self.logger.info("Starting enhanced extraction phase")

            # Run the enhanced watcher
            self.watcher.run(continuous=False, max_runs=1)

            # Load papers from watcher output
            papers_file = os.path.join(self.watcher.data_dir, "latest_papers.json")

            if not os.path.exists(papers_file):
                self.logger.warning("No papers found from enhanced watcher")
                return []

            with open(papers_file, encoding="utf-8") as f:
                watcher_data = json.load(f)

            # Extract papers from enhanced format
            if isinstance(watcher_data, dict) and "papers" in watcher_data:
                papers = watcher_data["papers"]
                metadata = watcher_data.get("metadata", {})
                self.logger.info(f"Loaded {len(papers)} papers with metadata: {metadata.get('average_relevance_score', 'N/A')} avg relevance")
            else:
                papers = watcher_data
                self.logger.info(f"Loaded {len(papers)} papers from watcher")

            return papers

        except Exception as e:
            raise ExtractionError(
                f"Failed to extract papers from enhanced ArXiv watcher: {e!s}",
                source_type="arxiv_api",
                context={"days_back": self.days_back, "max_results": self.max_results},
            )

    def transform(self, papers: list[dict[str, Any]]) -> list[EnhancedArxivPaperModel]:
        """Transform papers with advanced intelligence features.

        Args:
            papers: Raw papers from extraction phase

        Returns:
            List of enhanced paper models
        """
        if not papers:
            self.logger.warning("No papers to transform")
            return []

        try:
            self.logger.info(f"Starting enhanced transformation of {len(papers)} papers")

            # Prepare classifier if needed
            if self.enable_advanced_scoring:
                self._ensure_classifier_ready(papers)

            enhanced_papers = []
            github_token = os.getenv("GITHUB_TOKEN")

            for i, paper_data in enumerate(papers):
                try:
                    enhanced_paper = self._transform_single_paper(paper_data, i, github_token)
                    if enhanced_paper:
                        enhanced_papers.append(enhanced_paper)

                except Exception as e:
                    self.logger.error(f"Failed to transform paper {paper_data.get('id', 'unknown')}: {e!s}")
                    self.metrics.records_failed += 1
                    continue

            self.logger.info(f"Successfully transformed {len(enhanced_papers)} papers")
            return enhanced_papers

        except Exception as e:
            raise TransformationError(
                f"Failed to transform papers: {e!s}",
                context={"total_papers": len(papers)},
            )

    def _transform_single_paper(
        self, paper_data: dict[str, Any], index: int, github_token: str | None
    ) -> EnhancedArxivPaperModel | None:
        """Transform a single paper using services.

        Args:
            paper_data: Raw paper data
            index: Paper index in batch
            github_token: GitHub API token

        Returns:
            Enhanced paper model or None
        """
        # Extract basic information
        paper_id = paper_data.get("id", "")
        title = paper_data.get("title", "")
        summary = paper_data.get("summary", "")

        if not title or not summary:
            self.logger.warning(f"Paper {paper_id} missing title or summary, skipping")
            return None

        # Get clustering information
        cluster_info = self._get_cluster_info(paper_data, index)

        # Calculate intelligence scores using ScoringService
        if self.enable_advanced_scoring:
            impact_score = self.scoring_service.calculate_industry_impact(paper_data)
            trl_level = self.scoring_service.assess_technology_readiness(paper_data)
            commercial_potential = self.scoring_service.assess_commercial_potential(paper_data)
            innovation_score = self.scoring_service.calculate_innovation_score(paper_data)
            citation_potential = self.scoring_service.predict_citation_potential(paper_data)
            reproducibility_score = self.scoring_service.assess_reproducibility(paper_data)
        else:
            impact_score = 0.0
            trl_level = None
            commercial_potential = CommercialPotential.RESEARCH
            innovation_score = 0.0
            citation_potential = 0.0
            reproducibility_score = 0.0

        # Extract insights using AnalysisService
        related_technologies = self.analysis_service.extract_technologies(paper_data)
        potential_applications = self.analysis_service.identify_applications(paper_data)
        methodologies = self.analysis_service.extract_methodologies(paper_data)
        research_categories = self.analysis_service.classify_research_categories(paper_data)
        quality_indicators = self.analysis_service.calculate_quality_indicators(paper_data)
        trends_alignment = self.analysis_service.assess_trends_alignment(paper_data)

        # Get external integrations using IntegrationService
        github_info = self.integration_service.get_github_info(paper_data, github_token)
        papers_with_code_info = self.integration_service.get_papers_with_code_info(paper_data)

        # Parse datetime fields
        try:
            published = datetime.fromisoformat(paper_data["published"].replace("Z", "+00:00"))
            updated = datetime.fromisoformat(paper_data["updated"].replace("Z", "+00:00"))
        except (ValueError, KeyError) as e:
            self.logger.warning(f"Failed to parse dates for paper {paper_id}: {e}")
            published = datetime.now()
            updated = datetime.now()

        # Create enhanced paper model
        try:
            enhanced_paper = EnhancedArxivPaperModel(
                # Base fields
                arxiv_id=paper_id,
                title=title,
                authors=paper_data.get("authors", []),
                categories=paper_data.get("categories", []),
                summary=summary,
                published=published,
                updated=updated,
                link=paper_data.get("link", ""),
                pdf_url=paper_data.get("pdf_url"),
                comment=paper_data.get("comment"),
                # Classification
                cluster_id=cluster_info.get("cluster_id"),
                cluster_label=cluster_info.get("cluster_label"),
                cluster_keywords=cluster_info.get("cluster_keywords", []),
                extracted_keywords=cluster_info.get("extracted_keywords", []),
                research_categories=research_categories,
                # Intelligence scores
                industry_impact_score=impact_score,
                technology_readiness_level=trl_level,
                commercial_potential=commercial_potential,
                innovation_score=innovation_score,
                citation_potential=citation_potential,
                reproducibility_score=reproducibility_score,
                # Technology analysis
                related_technologies=related_technologies,
                potential_applications=potential_applications,
                technical_concepts=paper_data.get("technical_concepts", []),
                methodologies=methodologies,
                # External integrations
                github_info=github_info,
                papers_with_code_info=papers_with_code_info,
                # Metadata
                quality_indicators=quality_indicators,
                trends_alignment=trends_alignment,
            )

            return enhanced_paper

        except Exception as e:
            self.logger.error(f"Failed to create enhanced paper model for {paper_id}: {e!s}")
            return None

    def _ensure_classifier_ready(self, papers: list[dict[str, Any]]):
        """Ensure the NLP classifier is ready for use."""
        texts_for_classification = [
            f"{paper.get('title', '')} {paper.get('summary', '')}" for paper in papers
        ]

        model_path = os.path.join(self.classifier.models_dir, "model.pkl")
        if not os.path.exists(model_path):
            self.logger.info("Training new classifier for enhanced features")
            self.classifier.train_classifier(
                texts_for_classification, n_clusters=self.n_clusters
            )
            self.classifier.save_model()
        else:
            if not self.classifier.load_model():
                self.logger.info("Retraining classifier (failed to load existing)")
                self.classifier.train_classifier(
                    texts_for_classification, n_clusters=self.n_clusters
                )
                self.classifier.save_model()

    def _get_cluster_info(self, paper_data: dict[str, Any], index: int) -> dict[str, Any]:
        """Get clustering information for a paper."""
        if self.enable_advanced_scoring:
            text = f"{paper_data.get('title', '')} {paper_data.get('summary', '')}"
            classification = self.classifier.classify_text(text)
            return {
                "cluster_id": classification.get("cluster_id"),
                "cluster_label": classification.get("cluster_label"),
                "cluster_keywords": classification.get("cluster_keywords", []),
                "extracted_keywords": classification.get("document_keywords", []),
            }
        else:
            return {
                "cluster_id": None,
                "cluster_label": None,
                "cluster_keywords": [],
                "extracted_keywords": [],
            }

    def load(self, papers: list[EnhancedArxivPaperModel]) -> bool:
        """Load enhanced papers into storage.

        Args:
            papers: List of enhanced paper models

        Returns:
            True if loading successful
        """
        try:
            self.logger.info(f"Loading {len(papers)} enhanced papers")

            # Convert to list of dicts
            papers_data = [paper.model_dump() for paper in papers]

            # Save JSON
            if self.config.save_json:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_file = os.path.join(
                    self.config.output_dir, f"enhanced_arxiv_{timestamp}.json"
                )
                os.makedirs(self.config.output_dir, exist_ok=True)
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(papers_data, f, indent=2, ensure_ascii=False, default=str)
                self.logger.info(f"Saved JSON to {json_file}")

            # Save CSV (optional)
            if self.config.save_csv:
                import pandas as pd

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_file = os.path.join(
                    self.config.output_dir, f"enhanced_arxiv_{timestamp}.csv"
                )
                df = pd.DataFrame(papers_data)
                df.to_csv(csv_file, index=False)
                self.logger.info(f"Saved CSV to {csv_file}")

            self.metrics.records_loaded = len(papers)
            return True

        except Exception as e:
            raise LoadError(f"Failed to load enhanced papers: {e!s}")
