"""Enhanced ArXiv ETL with advanced intelligence features."""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.exceptions.etl import ExtractionError, LoadError, TransformationError
from src.models.arxiv import (
    CommercialPotential,
    EnhancedArxivPaperModel,
    GitHubRepositoryModel,
    PapersWithCodeModel,
    ResearchCategory,
    TechnologyReadinessLevel,
)
from src.utils.github_utils import find_github_links_in_text, get_github_repo_info
from src.utils.nlp_classifier import NLPContentClassifier
from src.utils.pwc_utils import get_pwc_details_for_paper
from src.watchers.enhanced_arxiv_watcher import EnhancedArxivWatcher

try:
    from paperswithcode import PapersWithCodeClient
except ImportError:
    PapersWithCodeClient = None


class EnhancedArxivETL(BaseETL):
    """Enhanced ETL process for ArXiv papers with advanced intelligence features.

    This ETL provides:
    1. Comprehensive paper collection across technical domains
    2. Advanced impact analysis and scoring
    3. Technology readiness level assessment
    4. Commercial viability assessment
    5. Research category classification
    6. Enhanced metadata extraction
    """

    def __init__(
        self,
        name: str = "enhanced_arxiv",
        days_back: int = 7,
        max_results: int = 200,
        n_clusters: int = 15,
        enable_advanced_scoring: bool = True,
        enable_github_integration: bool = True,
        enable_pwc_integration: bool = True,
        **kwargs,
    ):
        """Initialize the Enhanced ArXiv ETL.

        Args:
            name: Name for this ETL process
            days_back: Number of days back to collect papers
            max_results: Maximum number of papers to retrieve
            n_clusters: Number of clusters for the classifier
            enable_advanced_scoring: Whether to enable advanced impact scoring
            enable_github_integration: Whether to fetch GitHub repository info
            enable_pwc_integration: Whether to fetch Papers With Code info
            **kwargs: Additional arguments for base class
        """
        super().__init__(name, **kwargs)

        self.days_back = days_back
        self.max_results = max_results
        self.n_clusters = n_clusters
        self.enable_advanced_scoring = enable_advanced_scoring
        self.enable_github_integration = enable_github_integration
        self.enable_pwc_integration = enable_pwc_integration

        # Initialize components
        self.watcher = EnhancedArxivWatcher(
            name=f"{name}_watcher",
            days_back=days_back,
            max_results=max_results,
            check_interval=86400,
        )

        self.classifier = NLPContentClassifier(name=f"{name}_classifier")

        # Initialize Papers With Code client if available
        self.pwc_client = None
        if PapersWithCodeClient and self.enable_pwc_integration:
            try:
                self.pwc_client = PapersWithCodeClient()
            except Exception as e:
                self.logger.warning(
                    f"Failed to initialize Papers With Code client: {e}"
                )

        # Industry impact keywords with weights
        self.impact_keywords = {
            # High-impact indicators (weight 3.0)
            "breakthrough": 3.0,
            "novel": 2.5,
            "unprecedented": 3.0,
            "revolutionary": 3.0,
            "game-changing": 3.0,
            "paradigm shift": 3.0,
            # Significant improvement indicators (weight 2.0-2.5)
            "significant improvement": 2.5,
            "state-of-the-art": 2.5,
            "best performance": 2.0,
            "superior performance": 2.0,
            "outperforms": 2.0,
            "substantial improvement": 2.5,
            # Practical application indicators (weight 1.5-2.5)
            "real-world": 2.5,
            "production": 2.5,
            "enterprise": 2.0,
            "practical": 2.0,
            "scalable": 2.0,
            "deployment": 2.0,
            "implementation": 1.5,
            "commercial": 2.5,
            "industry": 2.0,
            # Technical quality indicators (weight 1.5-2.0)
            "robust": 1.5,
            "efficient": 1.5,
            "optimized": 1.5,
            "reliable": 1.5,
            "stable": 1.5,
            "fast": 1.5,
            "lightweight": 1.5,
            "high-performance": 2.0,
            # Research impact indicators (weight 1.0-2.0)
            "comprehensive": 1.5,
            "extensive": 1.5,
            "thorough": 1.5,
            "empirical": 1.0,
            "experimental": 1.0,
            "evaluation": 1.0,
            "benchmark": 2.0,
            "dataset": 1.5,
            "open source": 2.0,
        }

        # Technology readiness indicators
        self.trl_indicators = {
            TechnologyReadinessLevel.TRL_1: [
                "basic research",
                "theoretical",
                "fundamental",
                "principle",
            ],
            TechnologyReadinessLevel.TRL_2: [
                "concept",
                "formulated",
                "hypothesis",
                "proposed",
            ],
            TechnologyReadinessLevel.TRL_3: [
                "proof of concept",
                "experimental",
                "prototype",
                "preliminary",
            ],
            TechnologyReadinessLevel.TRL_4: [
                "validation",
                "laboratory",
                "controlled",
                "tested",
            ],
            TechnologyReadinessLevel.TRL_5: [
                "relevant environment",
                "simulation",
                "realistic",
                "validated",
            ],
            TechnologyReadinessLevel.TRL_6: [
                "demonstration",
                "pilot",
                "beta",
                "field test",
            ],
            TechnologyReadinessLevel.TRL_7: [
                "system prototype",
                "pre-commercial",
                "alpha",
            ],
            TechnologyReadinessLevel.TRL_8: [
                "complete system",
                "production ready",
                "commercial",
            ],
            TechnologyReadinessLevel.TRL_9: [
                "proven system",
                "deployed",
                "operational",
                "production",
            ],
        }

        # Commercial potential indicators
        self.commercial_indicators = {
            CommercialPotential.HIGH: [
                "commercial",
                "industry",
                "enterprise",
                "production",
                "deployment",
                "market",
                "business",
                "revenue",
                "startup",
                "venture",
                "patent",
                "licensing",
                "product",
                "customer",
                "user",
                "adoption",
            ],
            CommercialPotential.MEDIUM: [
                "application",
                "practical",
                "real-world",
                "implementation",
                "prototype",
                "demonstration",
                "pilot",
                "feasibility",
            ],
            CommercialPotential.LOW: [
                "experimental",
                "preliminary",
                "exploratory",
                "investigation",
            ],
            CommercialPotential.RESEARCH: [
                "theoretical",
                "fundamental",
                "basic research",
                "academic",
                "mathematical",
                "analytical",
                "formal",
                "abstract",
            ],
        }

        self.logger.info("Enhanced ArXiv ETL initialized with advanced features")

    def extract(self) -> list[dict[str, Any]]:
        """Extract papers from ArXiv using the enhanced watcher.

        Returns:
            List of enhanced paper dictionaries
        """
        try:
            self.logger.info("Starting enhanced extraction phase")

            # Run the enhanced watcher to collect papers
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
                self.logger.info(
                    f"Loaded {len(papers)} papers with metadata: {metadata.get('average_relevance_score', 'N/A')} avg relevance"
                )
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
            self.logger.info(
                f"Starting enhanced transformation of {len(papers)} papers"
            )

            # Prepare text for classification if needed
            if self.enable_advanced_scoring:
                self._ensure_classifier_ready(papers)

            enhanced_papers = []
            github_token = os.getenv("GITHUB_TOKEN")

            for i, paper_data in enumerate(papers):
                try:
                    enhanced_paper = self._transform_single_paper(
                        paper_data, i, github_token
                    )
                    if enhanced_paper:
                        enhanced_papers.append(enhanced_paper)

                except Exception as e:
                    self.logger.error(
                        f"Failed to transform paper {paper_data.get('id', 'unknown')}: {e!s}"
                    )
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
        """Transform a single paper with all intelligence features."""
        # Extract basic paper information
        paper_id = paper_data.get("id", "")
        title = paper_data.get("title", "")
        summary = paper_data.get("summary", "")

        if not title or not summary:
            self.logger.warning(f"Paper {paper_id} missing title or summary, skipping")
            return None

        # Get clustering information if available
        cluster_info = self._get_cluster_info(paper_data, index)

        # Calculate intelligence scores
        if self.enable_advanced_scoring:
            impact_score = self._calculate_industry_impact(paper_data)
            trl_level = self._assess_technology_readiness(paper_data)
            commercial_potential = self._assess_commercial_potential(paper_data)
            innovation_score = self._calculate_innovation_score(paper_data)
            citation_potential = self._predict_citation_potential(paper_data)
            reproducibility_score = self._assess_reproducibility(paper_data)
        else:
            impact_score = 0.0
            trl_level = None
            commercial_potential = CommercialPotential.RESEARCH
            innovation_score = 0.0
            citation_potential = 0.0
            reproducibility_score = 0.0

        # Extract technologies and applications
        related_technologies = self._extract_technologies(paper_data)
        potential_applications = self._identify_applications(paper_data)
        technical_concepts = paper_data.get("technical_concepts", [])
        methodologies = self._extract_methodologies(paper_data)

        # Classify research categories
        research_categories = self._classify_research_categories(paper_data)

        # Get external integrations
        github_info = None
        if self.enable_github_integration:
            github_info = self._get_github_info(paper_data, github_token)

        papers_with_code_info = None
        if self.enable_pwc_integration and self.pwc_client:
            papers_with_code_info = self._get_pwc_info(paper_data)

        # Calculate quality indicators and trends alignment
        quality_indicators = self._calculate_quality_indicators(paper_data)
        trends_alignment = self._assess_trends_alignment(paper_data)

        # Parse datetime fields
        try:
            published = datetime.fromisoformat(
                paper_data["published"].replace("Z", "+00:00")
            )
            updated = datetime.fromisoformat(
                paper_data["updated"].replace("Z", "+00:00")
            )
        except (ValueError, KeyError) as e:
            self.logger.warning(f"Failed to parse dates for paper {paper_id}: {e}")
            published = datetime.now()
            updated = datetime.now()

        # Create enhanced paper model
        try:
            enhanced_paper = EnhancedArxivPaperModel(
                # Base paper fields
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
                # Classification fields
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
                technical_concepts=technical_concepts,
                methodologies=methodologies,
                # External integrations
                github_info=github_info,
                papers_with_code_info=papers_with_code_info,
                # Additional metadata
                quality_indicators=quality_indicators,
                trends_alignment=trends_alignment,
            )

            return enhanced_paper

        except Exception as e:
            self.logger.error(
                f"Failed to create enhanced paper model for {paper_id}: {e!s}"
            )
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

    def _get_cluster_info(
        self, paper_data: dict[str, Any], index: int
    ) -> dict[str, Any]:
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

    def _calculate_industry_impact(self, paper_data: dict[str, Any]) -> float:
        """Calculate potential industry impact using advanced NLP analysis."""
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        impact_score = 0.0

        # Keyword-based scoring
        for keyword, weight in self.impact_keywords.items():
            if keyword in text:
                impact_score += weight

        # Category-based scoring
        categories = paper_data.get("categories", [])
        high_impact_categories = ["cs.AI", "cs.LG", "cs.SE", "cs.CR", "cs.DB"]
        for cat in categories:
            if cat in high_impact_categories:
                impact_score += 1.5

        # Relevance score boost
        relevance_score = paper_data.get("relevance_score", 0)
        impact_score += relevance_score * 0.3

        # GitHub integration boost
        if paper_data.get("found_keywords") and any(
            "github" in kw.lower() for kw in paper_data.get("found_keywords", [])
        ):
            impact_score += 1.0

        # Normalize to 0-10 scale
        normalized_score = min(impact_score / 3.0, 10.0)
        return round(normalized_score, 2)

    def _assess_technology_readiness(
        self, paper_data: dict[str, Any]
    ) -> TechnologyReadinessLevel | None:
        """Assess technology readiness level based on content analysis."""
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        # Score each TRL level based on indicator presence
        trl_scores = {}
        for trl_level, indicators in self.trl_indicators.items():
            score = 0
            for indicator in indicators:
                if indicator in text:
                    score += 1
            trl_scores[trl_level] = score

        # Find the TRL level with the highest score
        if not trl_scores or max(trl_scores.values()) == 0:
            return None

        best_trl = max(trl_scores.items(), key=lambda x: x[1])[0]
        return best_trl

    def _assess_commercial_potential(
        self, paper_data: dict[str, Any]
    ) -> CommercialPotential:
        """Assess commercial viability potential."""
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        # Score each commercial potential level
        potential_scores = {}
        for potential, indicators in self.commercial_indicators.items():
            score = 0
            for indicator in indicators:
                if indicator in text:
                    score += 1
            potential_scores[potential] = score

        # Adjust based on categories
        categories = paper_data.get("categories", [])
        applied_categories = ["cs.SE", "cs.DB", "cs.CR", "cs.AR", "cs.NI"]
        if any(cat in applied_categories for cat in categories):
            potential_scores[CommercialPotential.HIGH] += 1
            potential_scores[CommercialPotential.MEDIUM] += 1

        # Find the potential with the highest score
        if not potential_scores or max(potential_scores.values()) == 0:
            return CommercialPotential.RESEARCH

        best_potential = max(potential_scores.items(), key=lambda x: x[1])[0]
        return best_potential

    def _calculate_innovation_score(self, paper_data: dict[str, Any]) -> float:
        """Calculate innovation potential score."""
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        innovation_terms = [
            "novel",
            "new",
            "innovative",
            "breakthrough",
            "first",
            "pioneer",
            "revolutionary",
            "paradigm",
            "unprecedented",
            "original",
            "creative",
        ]

        score = 0.0
        for term in innovation_terms:
            if term in text:
                score += 1.0

        # Boost for technical novelty indicators
        technical_novelty = [
            "algorithm",
            "method",
            "approach",
            "technique",
            "framework",
            "architecture",
            "model",
            "system",
            "protocol",
        ]

        novelty_count = sum(1 for term in technical_novelty if term in text)
        score += novelty_count * 0.5

        # Category boost
        innovative_categories = ["cs.AI", "cs.LG", "cs.ET", "quant-ph"]
        categories = paper_data.get("categories", [])
        if any(cat in innovative_categories for cat in categories):
            score += 1.0

        return min(score, 10.0)

    def _predict_citation_potential(self, paper_data: dict[str, Any]) -> float:
        """Predict citation potential based on various factors."""
        score = 0.0

        # Author count (more authors often means more citations)
        authors = paper_data.get("authors", [])
        if len(authors) > 3:
            score += 1.0
        elif len(authors) > 1:
            score += 0.5

        # Title length and complexity
        title = paper_data.get("title", "")
        if 50 < len(title) < 150:  # Optimal title length
            score += 1.0

        # Abstract length and detail
        summary = paper_data.get("summary", "")
        if 800 < len(summary) < 2000:  # Detailed but not too long
            score += 1.0

        # Category popularity
        popular_categories = ["cs.LG", "cs.AI", "cs.CL", "cs.CV"]
        categories = paper_data.get("categories", [])
        if any(cat in popular_categories for cat in categories):
            score += 2.0

        # Research area alignment
        areas = paper_data.get("research_areas", [])
        if "AI/ML" in areas:
            score += 1.5

        return min(score, 10.0)

    def _assess_reproducibility(self, paper_data: dict[str, Any]) -> float:
        """Assess reproducibility based on content indicators."""
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        reproducibility_indicators = [
            "code",
            "github",
            "implementation",
            "dataset",
            "benchmark",
            "experiment",
            "evaluation",
            "baseline",
            "comparison",
            "open source",
            "available",
            "reproduce",
            "replication",
        ]

        score = 0.0
        for indicator in reproducibility_indicators:
            if indicator in text:
                score += 1.0

        # Boost for Papers With Code presence
        if paper_data.get("pwc_id") or "papers with code" in text:
            score += 2.0

        # Boost for GitHub links
        if any("github" in kw.lower() for kw in paper_data.get("found_keywords", [])):
            score += 2.0

        return min(score, 10.0)

    def _extract_technologies(self, paper_data: dict[str, Any]) -> list[str]:
        """Extract related technologies from paper content."""
        text = f"{paper_data.get('title', '')} {paper_data.get('summary', '')}".lower()

        technology_patterns = [
            "python",
            "javascript",
            "java",
            "c++",
            "go",
            "rust",
            "scala",
            "tensorflow",
            "pytorch",
            "keras",
            "scikit-learn",
            "pandas",
            "docker",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "cloud",
            "microservices",
            "api",
            "rest",
            "graphql",
            "grpc",
            "blockchain",
            "ethereum",
            "bitcoin",
            "smart contract",
            "react",
            "angular",
            "vue",
            "node.js",
            "express",
            "mongodb",
            "postgresql",
            "mysql",
            "redis",
            "elasticsearch",
            "apache spark",
            "hadoop",
            "kafka",
            "airflow",
            "transformer",
            "bert",
            "gpt",
            "llm",
            "neural network",
        ]

        found_technologies = []
        for tech in technology_patterns:
            if tech in text:
                found_technologies.append(tech)

        return found_technologies

    def _identify_applications(self, paper_data: dict[str, Any]) -> list[str]:
        """Identify potential real-world applications."""
        text = f"{paper_data.get('title', '')} {paper_data.get('summary', '')}".lower()

        application_areas = [
            "healthcare",
            "medical",
            "diagnosis",
            "treatment",
            "finance",
            "trading",
            "banking",
            "fintech",
            "autonomous",
            "self-driving",
            "robotics",
            "automation",
            "education",
            "learning",
            "teaching",
            "training",
            "security",
            "fraud detection",
            "cybersecurity",
            "recommendation",
            "personalization",
            "search",
            "translation",
            "language",
            "nlp",
            "chatbot",
            "image recognition",
            "computer vision",
            "detection",
            "optimization",
            "scheduling",
            "resource allocation",
            "predictive",
            "forecasting",
            "analytics",
        ]

        found_applications = []
        for app in application_areas:
            if app in text:
                found_applications.append(app)

        return found_applications

    def _extract_methodologies(self, paper_data: dict[str, Any]) -> list[str]:
        """Extract research methodologies used."""
        text = f"{paper_data.get('title', '')} {paper_data.get('summary', '')}".lower()

        methodologies = [
            "supervised learning",
            "unsupervised learning",
            "reinforcement learning",
            "deep learning",
            "machine learning",
            "neural network",
            "transformer",
            "attention",
            "convolution",
            "lstm",
            "gru",
            "classification",
            "regression",
            "clustering",
            "detection",
            "generation",
            "optimization",
            "search",
            "evolution",
            "simulation",
            "modeling",
            "analysis",
            "synthesis",
            "benchmark",
            "evaluation",
            "comparison",
            "ablation",
        ]

        found_methodologies = []
        for method in methodologies:
            if method in text:
                found_methodologies.append(method)

        return found_methodologies

    def _classify_research_categories(
        self, paper_data: dict[str, Any]
    ) -> list[ResearchCategory]:
        """Classify papers into research categories."""
        categories = paper_data.get("categories", [])
        keywords = paper_data.get("found_keywords", [])
        text = f"{paper_data.get('title', '')} {paper_data.get('summary', '')}".lower()

        research_categories = []

        # Category-based classification
        category_mapping = {
            "cs.AI": [ResearchCategory.ARTIFICIAL_INTELLIGENCE],
            "cs.LG": [
                ResearchCategory.MACHINE_LEARNING,
                ResearchCategory.DEEP_LEARNING,
            ],
            "cs.CL": [ResearchCategory.NATURAL_LANGUAGE_PROCESSING],
            "cs.CV": [ResearchCategory.COMPUTER_VISION],
            "cs.NE": [ResearchCategory.NEURAL_NETWORKS],
            "cs.SE": [ResearchCategory.SOFTWARE_ENGINEERING],
            "cs.AR": [ResearchCategory.SOLUTION_ARCHITECTURE],
            "cs.DC": [ResearchCategory.DISTRIBUTED_SYSTEMS],
            "cs.DB": [ResearchCategory.DATA_ENGINEERING],
            "cs.CR": [ResearchCategory.CYBERSECURITY],
            "quant-ph": [ResearchCategory.QUANTUM_COMPUTING],
        }

        for cat in categories:
            if cat in category_mapping:
                research_categories.extend(category_mapping[cat])

        # Keyword-based classification
        keyword_mapping = {
            "generative ai": ResearchCategory.GENERATIVE_AI,
            "large language model": ResearchCategory.GENERATIVE_AI,
            "llm": ResearchCategory.GENERATIVE_AI,
            "microservices": ResearchCategory.MICROSERVICES,
            "devops": ResearchCategory.DEVOPS,
            "blockchain": ResearchCategory.BLOCKCHAIN,
            "iot": ResearchCategory.IOT,
            "edge computing": ResearchCategory.EDGE_COMPUTING,
        }

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in keyword_mapping:
                research_categories.append(keyword_mapping[keyword_lower])

        # Text-based classification
        if "survey" in text or "review" in text:
            research_categories.append(ResearchCategory.SURVEY)
        if "benchmark" in text:
            research_categories.append(ResearchCategory.BENCHMARK)
        if "theoretical" in text or "theory" in text:
            research_categories.append(ResearchCategory.THEORETICAL)
        if "empirical" in text or "experimental" in text:
            research_categories.append(ResearchCategory.EMPIRICAL)

        return list(set(research_categories))  # Remove duplicates

    def _get_github_info(
        self, paper_data: dict[str, Any], github_token: str | None
    ) -> GitHubRepositoryModel | None:
        """Get GitHub repository information."""
        try:
            text_to_search = (
                f"{paper_data.get('summary', '')} {paper_data.get('comment', '')}"
            )
            github_urls = find_github_links_in_text(text_to_search)

            if github_urls:
                repo_info = get_github_repo_info(
                    github_urls[0], github_token=github_token
                )
                if repo_info:
                    return GitHubRepositoryModel(**repo_info)

            return None

        except Exception as e:
            self.logger.warning(
                f"Failed to get GitHub info for paper {paper_data.get('id')}: {e}"
            )
            return None

    def _get_pwc_info(
        self, paper_data: dict[str, Any]
    ) -> PapersWithCodeModel | None:
        """Get Papers With Code information."""
        try:
            arxiv_id_url = paper_data.get("id")
            paper_title = paper_data.get("title")

            if arxiv_id_url or paper_title:
                pwc_info = get_pwc_details_for_paper(
                    arxiv_id_url=arxiv_id_url,
                    title=paper_title,
                    pwc_client=self.pwc_client,
                )
                if pwc_info:
                    return PapersWithCodeModel(**pwc_info)

            return None

        except Exception as e:
            self.logger.warning(
                f"Failed to get PWC info for paper {paper_data.get('id')}: {e}"
            )
            return None

    def _calculate_quality_indicators(
        self, paper_data: dict[str, Any]
    ) -> dict[str, float]:
        """Calculate various quality indicators."""
        indicators = {}

        # Relevance score from watcher
        indicators["relevance"] = paper_data.get("relevance_score", 0.0)

        # Author reputation (simplified)
        authors = paper_data.get("authors", [])
        indicators["author_count"] = float(len(authors))

        # Content quality
        summary = paper_data.get("summary", "")
        indicators["abstract_length"] = float(len(summary))
        indicators["abstract_quality"] = min(len(summary) / 1000.0, 10.0)

        # Technical depth
        technical_concepts = paper_data.get("technical_concepts", [])
        indicators["technical_depth"] = float(len(technical_concepts))

        return indicators

    def _assess_trends_alignment(self, paper_data: dict[str, Any]) -> dict[str, float]:
        """Assess alignment with current technology trends."""
        text = f"{paper_data.get('title', '')} {paper_data.get('summary', '')}".lower()

        trends = {
            "ai_ml_trend": [
                "artificial intelligence",
                "machine learning",
                "deep learning",
                "neural network",
            ],
            "llm_trend": [
                "large language model",
                "llm",
                "gpt",
                "transformer",
                "generative ai",
            ],
            "cloud_trend": [
                "cloud",
                "serverless",
                "microservices",
                "kubernetes",
                "docker",
            ],
            "data_trend": [
                "big data",
                "data pipeline",
                "real-time",
                "stream processing",
            ],
            "security_trend": ["cybersecurity", "zero trust", "privacy", "encryption"],
            "edge_trend": ["edge computing", "iot", "5g", "mobile edge"],
            "quantum_trend": [
                "quantum computing",
                "quantum algorithm",
                "quantum machine learning",
            ],
        }

        alignment = {}
        for trend_name, keywords in trends.items():
            score = sum(1.0 for keyword in keywords if keyword in text)
            alignment[trend_name] = min(score, 10.0)

        return alignment

    def load(self, enhanced_papers: list[EnhancedArxivPaperModel]) -> None:
        """Load enhanced papers with comprehensive output formats.

        Args:
            enhanced_papers: List of enhanced paper models
        """
        if not enhanced_papers:
            self.logger.warning("No enhanced papers to load")
            return

        try:
            self.logger.info(f"Loading {len(enhanced_papers)} enhanced papers")

            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Convert to dictionaries for JSON serialization
            papers_data = [paper.dict() for paper in enhanced_papers]

            # Save enhanced JSON with metadata
            enhanced_data = {
                "metadata": {
                    "total_papers": len(enhanced_papers),
                    "processing_timestamp": datetime.now().isoformat(),
                    "etl_version": "enhanced_v1.0",
                    "features_enabled": {
                        "advanced_scoring": self.enable_advanced_scoring,
                        "github_integration": self.enable_github_integration,
                        "pwc_integration": self.enable_pwc_integration,
                    },
                    "statistics": self._generate_enhanced_statistics(enhanced_papers),
                },
                "papers": papers_data,
            }

            # Save to various locations
            json_file = os.path.join(
                self.output_dir, f"enhanced_papers_{timestamp}.json"
            )
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(enhanced_data, f, ensure_ascii=False, indent=2, default=str)
            self.logger.info(f"Saved enhanced JSON to {json_file}")

            # Save latest version
            latest_json = os.path.join(self.output_dir, "latest_enhanced_papers.json")
            with open(latest_json, "w", encoding="utf-8") as f:
                json.dump(enhanced_data, f, ensure_ascii=False, indent=2, default=str)

            # Save CSV for analysis
            self._save_enhanced_csv(enhanced_papers, timestamp)

            # Generate intelligence reports
            self._generate_intelligence_reports(enhanced_papers)

            self.logger.info("Enhanced papers loading completed successfully")

        except Exception as e:
            raise LoadError(
                f"Failed to load enhanced papers: {e!s}",
                destination_type="file_system",
                records_failed=len(enhanced_papers),
            )

    def _save_enhanced_csv(self, papers: list[EnhancedArxivPaperModel], timestamp: str):
        """Save papers as CSV with flattened structure."""
        try:
            import pandas as pd

            # Flatten papers for CSV
            flattened_data = []
            for paper in papers:
                paper_dict = paper.dict()

                # Flatten complex fields
                paper_dict["authors"] = ", ".join(paper_dict.get("authors", []))
                paper_dict["categories"] = ", ".join(paper_dict.get("categories", []))
                paper_dict["research_categories"] = ", ".join(
                    [cat.value for cat in paper_dict.get("research_categories", [])]
                )
                paper_dict["related_technologies"] = ", ".join(
                    paper_dict.get("related_technologies", [])
                )
                paper_dict["potential_applications"] = ", ".join(
                    paper_dict.get("potential_applications", [])
                )
                paper_dict["technical_concepts"] = ", ".join(
                    paper_dict.get("technical_concepts", [])
                )
                paper_dict["methodologies"] = ", ".join(
                    paper_dict.get("methodologies", [])
                )
                paper_dict["cluster_keywords"] = ", ".join(
                    paper_dict.get("cluster_keywords", [])
                )
                paper_dict["extracted_keywords"] = ", ".join(
                    paper_dict.get("extracted_keywords", [])
                )

                # Flatten nested models
                if paper_dict.get("github_info"):
                    github_info = paper_dict.pop("github_info")
                    for key, value in github_info.items():
                        paper_dict[f"github_{key}"] = value

                if paper_dict.get("papers_with_code_info"):
                    pwc_info = paper_dict.pop("papers_with_code_info")
                    for key, value in pwc_info.items():
                        paper_dict[f"pwc_{key}"] = value

                # Flatten quality indicators and trends
                if paper_dict.get("quality_indicators"):
                    quality = paper_dict.pop("quality_indicators")
                    for key, value in quality.items():
                        paper_dict[f"quality_{key}"] = value

                if paper_dict.get("trends_alignment"):
                    trends = paper_dict.pop("trends_alignment")
                    for key, value in trends.items():
                        paper_dict[f"trend_{key}"] = value

                flattened_data.append(paper_dict)

            # Create DataFrame and save
            df = pd.DataFrame(flattened_data)
            csv_file = os.path.join(self.output_dir, f"enhanced_papers_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding="utf-8")

            latest_csv = os.path.join(self.output_dir, "latest_enhanced_papers.csv")
            df.to_csv(latest_csv, index=False, encoding="utf-8")

            self.logger.info(f"Saved enhanced CSV to {csv_file}")

        except Exception as e:
            self.logger.error(f"Failed to save enhanced CSV: {e!s}")

    def _generate_enhanced_statistics(
        self, papers: list[EnhancedArxivPaperModel]
    ) -> dict[str, Any]:
        """Generate comprehensive statistics for enhanced papers."""
        if not papers:
            return {}

        stats = {
            "total_papers": len(papers),
            "average_scores": {
                "industry_impact": sum(p.industry_impact_score for p in papers)
                / len(papers),
                "innovation": sum(p.innovation_score for p in papers) / len(papers),
                "citation_potential": sum(p.citation_potential for p in papers)
                / len(papers),
                "reproducibility": sum(p.reproducibility_score for p in papers)
                / len(papers),
                "overall_significance": sum(
                    p.overall_significance_score for p in papers
                )
                / len(papers),
            },
            "trl_distribution": {},
            "commercial_potential_distribution": {},
            "research_categories_distribution": {},
            "breakthrough_papers": sum(1 for p in papers if p.is_breakthrough),
            "github_integration": sum(1 for p in papers if p.github_info is not None),
            "pwc_integration": sum(
                1 for p in papers if p.papers_with_code_info is not None
            ),
        }

        # Calculate TRL distribution
        trl_counts = Counter(
            p.technology_readiness_level for p in papers if p.technology_readiness_level
        )
        stats["trl_distribution"] = {
            str(trl): count for trl, count in trl_counts.items()
        }

        # Calculate commercial potential distribution
        commercial_counts = Counter(p.commercial_potential for p in papers)
        stats["commercial_potential_distribution"] = {
            cp.value: count for cp, count in commercial_counts.items()
        }

        # Calculate research categories distribution
        all_categories = []
        for paper in papers:
            all_categories.extend([cat.value for cat in paper.research_categories])
        category_counts = Counter(all_categories)
        stats["research_categories_distribution"] = dict(
            category_counts.most_common(10)
        )

        return stats

    def _generate_intelligence_reports(self, papers: list[EnhancedArxivPaperModel]):
        """Generate intelligence reports and insights."""
        try:
            # High-impact papers report
            high_impact_papers = [p for p in papers if p.industry_impact_score >= 7.0]
            if high_impact_papers:
                report_file = os.path.join(
                    self.output_dir, "high_impact_papers_report.json"
                )
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(
                        [p.dict() for p in high_impact_papers], f, indent=2, default=str
                    )
                self.logger.info(
                    f"Generated high-impact papers report with {len(high_impact_papers)} papers"
                )

            # Breakthrough papers report
            breakthrough_papers = [p for p in papers if p.is_breakthrough]
            if breakthrough_papers:
                report_file = os.path.join(
                    self.output_dir, "breakthrough_papers_report.json"
                )
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(
                        [p.dict() for p in breakthrough_papers],
                        f,
                        indent=2,
                        default=str,
                    )
                self.logger.info(
                    f"Generated breakthrough papers report with {len(breakthrough_papers)} papers"
                )

            # Commercial potential report
            commercial_papers = [
                p
                for p in papers
                if p.commercial_potential
                in [CommercialPotential.HIGH, CommercialPotential.MEDIUM]
            ]
            if commercial_papers:
                report_file = os.path.join(
                    self.output_dir, "commercial_potential_report.json"
                )
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(
                        [p.dict() for p in commercial_papers], f, indent=2, default=str
                    )
                self.logger.info(
                    f"Generated commercial potential report with {len(commercial_papers)} papers"
                )

        except Exception as e:
            self.logger.error(f"Failed to generate intelligence reports: {e!s}")


if __name__ == "__main__":
    # Example usage
    etl = EnhancedArxivETL(
        days_back=7,
        max_results=100,
        n_clusters=12,
        enable_advanced_scoring=True,
        enable_github_integration=True,
        enable_pwc_integration=True,
    )

    try:
        metrics = etl.run()
        print("Enhanced ArXiv ETL completed successfully!")
        print(f"Processed: {metrics.records_loaded} papers")
        print(f"Duration: {metrics.duration_seconds:.2f} seconds")
    except Exception as e:
        print(f"ETL failed: {e!s}")
