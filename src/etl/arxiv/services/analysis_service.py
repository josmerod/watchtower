"""Analysis services for extracting insights from ArXiv papers."""

import logging
import re
from typing import Any

from src.models.arxiv import ResearchCategory

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for analyzing research papers and extracting insights."""

    def __init__(self, debug: bool = False):
        """Initialize analysis service.

        Args:
            debug: Enable debug logging
        """
        self.debug = debug

        # Common technology keywords
        self.tech_keywords = [
            "python", "tensorflow", "pytorch", "keras", "scikit-learn",
            "caffe", "torch", "mxnet", "theano", "cntk",
            "react", "angular", "vue", "django", "flask", "fastapi",
            "kubernetes", "docker", "aws", "azure", "gcp",
            "mongodb", "postgresql", "mysql", "redis", "elasticsearch",
            "spark", "hadoop", "kafka", " airflow",
            "graphql", "grpc", "rest", "websocket",
            "llvm", "gcc", "clang", "jvm",
        ]

        # Application domains
        self.application_domains = {
            "healthcare": ["medical", "clinical", "health", "diagnosis", "treatment"],
            "finance": ["financial", "trading", "banking", "fraud detection", "risk"],
            "autonomous": ["self-driving", "autonomous vehicle", "driverless"],
            "education": ["learning", "education", "teaching", "student"],
            "entertainment": ["gaming", "entertainment", "media", "recommendation"],
            "manufacturing": ["manufacturing", "production", "quality control"],
            "agriculture": ["agriculture", "farming", "crop", "yield"],
            "energy": ["energy", "power", "smart grid", "renewable"],
            "security": ["security", "cybersecurity", "intrusion detection", "malware"],
        }

        # Methodology indicators
        self.methodology_indicators = {
            "supervised learning": ["supervised", "classification", "regression", "labeled"],
            "unsupervised learning": ["unsupervised", "clustering", "dimensionality reduction", "unlabeled"],
            "reinforcement learning": ["reinforcement learning", "policy", "reward", "agent"],
            "deep learning": ["deep learning", "neural network", "cnn", "rnn", "transformer", "attention"],
            "statistical": ["statistical", "bayesian", "probability", "hypothesis testing"],
            "experimental": ["experimental", "evaluation", "benchmark", "comparison"],
            "theoretical": ["theoretical", "proof", "algorithm", "complexity", "bound"],
            "simulation": ["simulation", "modeling", "synthetic data", " Monte Carlo "],
        }

    def extract_technologies(self, paper_data: dict[str, Any]) -> list[str]:
        """Extract mentioned technologies and frameworks.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            List of extracted technologies
        """
        title = paper_data.get("title", "")
        summary = paper_data.get("summary", "")
        text = f"{title} {summary}".lower()

        found_techs = []
        for tech in self.tech_keywords:
            if tech.lower() in text:
                found_techs.append(tech)

        # Extract version numbers (e.g., "Python 3.8")
        version_pattern = r"\b(" + "|".join(self.tech_keywords[:5]) + r")\s+(\d+\.\d+)"
        versions = re.findall(version_pattern, text, re.IGNORECASE)
        for tech, version in versions:
            found_techs.append(f"{tech.capitalize()} {version}")

        return list(set(found_techs))

    def identify_applications(self, paper_data: dict[str, Any]) -> list[str]:
        """Identify potential application domains.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            List of application domains
        """
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        found_apps = []
        for domain, keywords in self.application_domains.items():
            if any(keyword in text for keyword in keywords):
                found_apps.append(domain.capitalize())

        return found_apps

    def extract_methodologies(self, paper_data: dict[str, Any]) -> list[str]:
        """Extract research methodologies used.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            List of methodologies
        """
        title = paper_data.get("title", "")
        summary = paper_data.get("summary", "")
        text = f"{title} {summary}".lower()

        found_methods = []
        for method, indicators in self.methodology_indicators.items():
            if any(indicator in text for indicator in indicators):
                found_methods.append(method)

        return found_methods

    def classify_research_categories(self, paper_data: dict[str, Any]) -> list[ResearchCategory]:
        """Classify paper into research categories.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            List of research categories
        """
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        categories = paper_data.get("categories", [])
        text = f"{title} {summary}"

        found_categories = []

        # Category mapping from ArXiv categories
        category_mapping = {
            "cs.CV": ResearchCategory.COMPUTER_VISION,
            "cs.CL": ResearchCategory.NATURAL_LANGUAGE,
            "cs.LG": ResearchCategory.MACHINE_LEARNING,
            "cs.AI": ResearchCategory.MACHINE_LEARNING,
            "cs.RO": ResearchCategory.ROBOTICS,
            "cs.DB": ResearchCategory.DATABASE_SYSTEMS,
            "cs.SE": ResearchCategory.SOFTWARE_ENGINEERING,
            "cs.CR": ResearchCategory.SECURITY,
            "cs.NI": ResearchCategory.NETWORKING,
            "cs.DC": ResearchCategory.DISTRIBUTED_SYSTEMS,
        }

        # Map ArXiv categories to research categories
        for arxiv_cat in categories:
            if arxiv_cat in category_mapping:
                research_cat = category_mapping[arxiv_cat]
                if research_cat not in found_categories:
                    found_categories.append(research_cat)

        # Text-based classification for additional categories
        for research_cat, keywords in self.research_category_indicators.items():
            if research_cat not in found_categories:
                if any(keyword in text for keyword in keywords):
                    found_categories.append(research_cat)

        return found_categories

    def calculate_quality_indicators(self, paper_data: dict[str, Any]) -> dict[str, float]:
        """Calculate various quality indicators.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Dictionary of quality indicators
        """
        indicators = {
            "completeness": 0.0,
            "rigor": 0.0,
            "clarity": 0.0,
            "significance": 0.0,
        }

        # Completeness: Check for required sections
        summary = paper_data.get("summary", "")
        if summary and len(summary) > 500:
            indicators["completeness"] += 0.3
        if paper_data.get("authors"):
            indicators["completeness"] += 0.3
        if paper_data.get("categories"):
            indicators["completeness"] += 0.2
        if paper_data.get("journal_ref"):
            indicators["completeness"] += 0.2

        # Rigor: Look for rigorous methodology
        text = f"{paper_data.get('title', '')} {summary}".lower()
        rigor_terms = ["evaluation", "benchmark", "comparison", "validation", "experiment", "analysis"]
        rigor_count = sum(1 for term in rigor_terms if term in text)
        indicators["rigor"] = min(rigor_count * 0.2, 1.0)

        # Clarity: Based on structure and organization
        clarity_terms = ["introduction", "method", "result", "conclusion", "approach"]
        clarity_count = sum(1 for term in clarity_terms if term in text)
        indicators["clarity"] = min(clarity_count * 0.2, 1.0)

        # Significance: Based on novelty indicators
        significance_terms = ["novel", "new", "first", "state-of-the-art", "breakthrough"]
        significance_count = sum(1 for term in significance_terms if term in text)
        indicators["significance"] = min(significance_count * 0.25, 1.0)

        return indicators

    def assess_trends_alignment(self, paper_data: dict[str, Any]) -> dict[str, float]:
        """Assess alignment with current research trends.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Dictionary of trend alignment scores
        """
        trends = {
            "deep_learning": 0.0,
            "transformers": 0.0,
            "generative_ai": 0.0,
            "mlops": 0.0,
            "responsible_ai": 0.0,
        }

        text = f"{paper_data.get('title', '')} {paper_data.get('summary', '')}".lower()

        # Deep learning trends
        dl_keywords = ["neural network", "deep learning", " cnn ", " rnn ", "lstm", "gru"]
        trends["deep_learning"] = min(sum(1 for kw in dl_keywords if kw in text) * 0.3, 1.0)

        # Transformer trends
        transformer_keywords = ["transformer", "attention", "bert", "gpt", "self-attention"]
        trends["transformers"] = min(sum(1 for kw in transformer_keywords if kw in text) * 0.3, 1.0)

        # Generative AI trends
        gen_ai_keywords = ["generative", "gan", "vae", "diffusion", "language model", "llm"]
        trends["generative_ai"] = min(sum(1 for kw in gen_ai_keywords if kw in text) * 0.3, 1.0)

        # MLOps trends
        mlops_keywords = ["deployment", "mlops", "pipeline", "monitoring", "serving"]
        trends["mlops"] = min(sum(1 for kw in mlops_keywords if kw in text) * 0.3, 1.0)

        # Responsible AI trends
        responsible_keywords = ["fairness", "bias", "ethic", "interpretability", "explainability"]
        trends["responsible_ai"] = min(sum(1 for kw in responsible_keywords if kw in text) * 0.3, 1.0)

        return trends
