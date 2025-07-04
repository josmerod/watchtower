"""Enhanced ArXiv watcher with expanded topic coverage and intelligence features."""

import json
import os
from datetime import datetime, timedelta
from typing import Any

import feedparser

from watchers.base_watcher import BaseWatcher


class EnhancedArxivWatcher(BaseWatcher):
    """Enhanced watcher for ArXiv papers with expanded topic coverage.

    This watcher monitors ArXiv for papers in AI/ML, software engineering,
    data engineering, architecture, and related technical fields.
    """

    # ArXiv API URL
    ARXIV_API_BASE = "http://export.arxiv.org/api/query"

    # Comprehensive categories covering multiple technical domains
    TECHNICAL_CATEGORIES = {
        # Core Computer Science
        "cs.AI": "Artificial Intelligence",
        "cs.LG": "Machine Learning",
        "cs.CL": "Computation and Language (NLP)",
        "cs.CV": "Computer Vision",
        "cs.NE": "Neural and Evolutionary Computing",
        "cs.IR": "Information Retrieval",
        "cs.HC": "Human-Computer Interaction",
        "cs.RO": "Robotics",

        # Software Engineering & Architecture
        "cs.SE": "Software Engineering",
        "cs.PL": "Programming Languages",
        "cs.SY": "Systems and Control",
        "cs.DC": "Distributed, Parallel, and Cluster Computing",
        "cs.AR": "Hardware Architecture",
        "cs.OS": "Operating Systems",
        "cs.NI": "Networking and Internet Architecture",
        "cs.PF": "Performance",

        # Data & Databases
        "cs.DB": "Databases",
        "cs.DS": "Data Structures and Algorithms",
        "cs.IT": "Information Theory",
        "cs.DM": "Discrete Mathematics",

        # Security & Cryptography
        "cs.CR": "Cryptography and Security",
        "cs.CY": "Computers and Society",

        # Emerging Technologies
        "cs.ET": "Emerging Technologies",
        "cs.GT": "Computer Science and Game Theory",
        "cs.LO": "Logic in Computer Science",
        "cs.CC": "Computational Complexity",
        "cs.CG": "Computational Geometry",
        "cs.NA": "Numerical Analysis",

        # Statistics & Machine Learning
        "stat.ML": "Statistics - Machine Learning",
        "stat.AP": "Statistics - Applications",
        "stat.CO": "Statistics - Computation",
        "stat.ME": "Statistics - Methodology",

        # Mathematics relevant to tech
        "math.OC": "Optimization and Control",
        "math.PR": "Probability",
        "math.ST": "Statistics Theory",
        "math.NA": "Numerical Analysis",
        "math.CO": "Combinatorics",
        "math.DS": "Dynamical Systems",

        # Physics relevant to computing
        "quant-ph": "Quantum Physics",
        "cond-mat.dis-nn": "Disordered Systems and Neural Networks",

        # Economics and Finance (for algorithmic trading, fintech)
        "econ.EM": "Econometrics",
        "q-fin.CP": "Computational Finance",
        "q-fin.ST": "Statistical Finance",
        "q-fin.TR": "Trading and Market Microstructure",
        "q-fin.RM": "Risk Management",
    }

    # Keywords for additional filtering to catch relevant papers
    RELEVANT_KEYWORDS = [
        # AI & ML
        "artificial intelligence", "machine learning", "deep learning", "neural network",
        "natural language processing", "computer vision", "reinforcement learning",
        "generative ai", "large language model", "transformer", "gpt", "llm",
        "ai safety", "ai ethics", "explainable ai", "federated learning",

        # Software Engineering
        "software architecture", "microservices", "api design", "devops", "ci/cd",
        "software testing", "code quality", "software metrics", "refactoring",
        "design patterns", "software maintenance", "technical debt", "agile",
        "continuous integration", "continuous deployment", "containerization",
        "docker", "kubernetes", "serverless", "cloud native",

        # Data Engineering
        "data pipeline", "data warehouse", "data lake", "etl", "real-time processing",
        "stream processing", "big data", "apache spark", "hadoop", "kafka",
        "data governance", "data quality", "data mesh", "data fabric",
        "data engineering", "data architecture", "olap", "oltp",

        # Solution & Enterprise Architecture
        "solution architecture", "enterprise architecture", "system design",
        "distributed systems", "scalability", "high availability", "fault tolerance",
        "load balancing", "caching", "database design", "performance optimization",
        "cloud architecture", "hybrid cloud", "multi-cloud", "edge computing",
        "service mesh", "event-driven architecture", "messaging patterns",

        # Security
        "cybersecurity", "information security", "vulnerability", "threat detection",
        "intrusion detection", "malware analysis", "cryptography", "blockchain",
        "zero trust", "privacy", "gdpr", "compliance", "secure coding",

        # Emerging Technologies
        "quantum computing", "blockchain", "iot", "edge computing", "5g",
        "augmented reality", "virtual reality", "digital twin", "automation",
        "robotic process automation", "low-code", "no-code",

        # Business & Technology
        "digital transformation", "technology adoption", "innovation management",
        "startup", "venture capital", "product management", "user experience",
        "business intelligence", "analytics", "data science", "fintech",

        # Programming & Development
        "programming language", "compiler", "interpreter", "runtime",
        "framework", "library", "sdk", "api", "rest", "graphql", "grpc",
        "functional programming", "object-oriented", "reactive programming",
    ]

    def __init__(
        self,
        name: str = "enhanced_arxiv",
        check_interval: int = 86400,  # Default: check once per day
        max_results: int = 200,  # Increased for expanded coverage
        days_back: int = 7,
        enable_keyword_filtering: bool = True
    ):
        """Initialize the Enhanced ArXiv watcher.

        Args:
            name (str): Unique name for this watcher
            check_interval (int): Time in seconds between checks (default: 1 day)
            max_results (int): Maximum number of papers to retrieve per check
            days_back (int): Number of days back to search for papers
            enable_keyword_filtering (bool): Whether to apply keyword filtering
        """
        # Construct the API URL with comprehensive search parameters
        categories = " OR ".join(self.TECHNICAL_CATEGORIES.keys())

        # Calculate date for papers published since days_back
        date_since = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Build the complete search URL with expanded categories
        search_query = f"cat:({categories}) AND submittedDate:[{date_since}000000 TO 999999999999]"

        # Add keyword-based search if enabled
        if enable_keyword_filtering:
            # Create keyword search for titles and abstracts
            keyword_query = " OR ".join([f'"{keyword}"' for keyword in self.RELEVANT_KEYWORDS[:20]])  # Limit to avoid URL length issues
            search_query += f" AND (ti:({keyword_query}) OR abs:({keyword_query}))"

        self.api_url = f"{self.ARXIV_API_BASE}?search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"

        self.max_results = max_results
        self.days_back = days_back
        self.enable_keyword_filtering = enable_keyword_filtering

        # Initialize the base watcher
        super().__init__(name, self.api_url, check_interval)

    def extract_value(self, xml_content: str) -> list[dict[str, Any]]:
        """Extract papers from the ArXiv API response with enhanced metadata.

        Args:
            xml_content (str): XML response from ArXiv API

        Returns:
            List[Dict[str, Any]]: List of papers with enhanced metadata
        """
        self.logger.info("Parsing enhanced ArXiv API response")
        feed = feedparser.parse(xml_content)

        papers = []
        for entry in feed.entries:
            # Extract authors
            authors = [author.name for author in entry.authors]

            # Extract categories with descriptions
            categories = []
            category_descriptions = []
            if hasattr(entry, 'tags'):
                for tag in entry.tags:
                    categories.append(tag.term)
                    category_descriptions.append(
                        self.TECHNICAL_CATEGORIES.get(tag.term, tag.term)
                    )

            # Extract and process summary for keyword presence
            summary = entry.summary
            title = entry.title
            combined_text = f"{title.lower()} {summary.lower()}"

            # Identify relevant keywords present in the paper
            found_keywords = [
                keyword for keyword in self.RELEVANT_KEYWORDS
                if keyword.lower() in combined_text
            ]

            # Calculate relevance score based on keyword matches and categories
            relevance_score = self._calculate_relevance_score(
                categories, found_keywords, title, summary
            )

            # Extract technical concepts
            technical_concepts = self._extract_technical_concepts(combined_text)

            # Determine primary research areas
            research_areas = self._classify_research_areas(categories, found_keywords)

            # Create enhanced paper entry
            paper = {
                # Core ArXiv fields
                "id": entry.id.split("/")[-1],
                "title": title,
                "authors": authors,
                "categories": categories,
                "category_descriptions": category_descriptions,
                "summary": summary,
                "published": entry.published,
                "updated": entry.updated,
                "link": entry.link,
                "pdf_url": next(
                    (link.href for link in entry.links
                     if link.rel == "alternate" and link.type == "application/pdf"),
                    None
                ),
                "comment": getattr(entry, 'arxiv_comment', None),

                # Enhanced metadata
                "found_keywords": found_keywords,
                "relevance_score": relevance_score,
                "technical_concepts": technical_concepts,
                "research_areas": research_areas,
                "primary_category": categories[0] if categories else None,
                "is_ai_ml": any(cat.startswith(('cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'stat.ML'))
                               for cat in categories),
                "is_software_engineering": any(cat.startswith(('cs.SE', 'cs.PL', 'cs.SY'))
                                              for cat in categories),
                "is_data_engineering": any(cat.startswith(('cs.DB', 'cs.DS', 'cs.IR'))
                                          for cat in categories),
                "is_architecture": any(cat.startswith(('cs.DC', 'cs.AR', 'cs.NI'))
                                      for cat in categories),
                "is_security": any(cat.startswith(('cs.CR', 'cs.CY'))
                                  for cat in categories),

                # Processing metadata
                "extraction_timestamp": datetime.now().isoformat(),
                "watcher_version": "enhanced_v1.0"
            }

            papers.append(paper)

        # Sort papers by relevance score (highest first)
        papers.sort(key=lambda x: x['relevance_score'], reverse=True)

        self.logger.info(f"Found {len(papers)} enhanced papers")
        if papers:
            self.logger.info(f"Top relevance scores: {[p['relevance_score'] for p in papers[:5]]}")

        return papers

    def _calculate_relevance_score(self, categories: list[str], keywords: list[str],
                                  title: str, summary: str) -> float:
        """Calculate relevance score based on multiple factors."""
        score = 0.0

        # Base score from categories
        high_value_categories = [
            'cs.AI', 'cs.LG', 'cs.SE', 'cs.DB', 'cs.DC', 'cs.AR', 'cs.CR'
        ]
        for cat in categories:
            if cat in high_value_categories:
                score += 2.0
            else:
                score += 1.0

        # Keyword bonus
        score += len(keywords) * 0.5

        # Title keyword bonus (more important)
        title_lower = title.lower()
        for keyword in self.RELEVANT_KEYWORDS:
            if keyword in title_lower:
                score += 1.0

        # Specific high-impact terms
        high_impact_terms = [
            "breakthrough", "novel", "state-of-the-art", "scalable",
            "production", "enterprise", "real-world", "practical"
        ]
        combined_text = f"{title} {summary}".lower()
        for term in high_impact_terms:
            if term in combined_text:
                score += 1.5

        return round(score, 2)

    def _extract_technical_concepts(self, text: str) -> list[str]:
        """Extract technical concepts from paper text."""
        concepts = []

        # Common technical concepts to look for
        concept_patterns = [
            "neural network", "transformer", "attention mechanism", "deep learning",
            "machine learning", "artificial intelligence", "natural language processing",
            "computer vision", "reinforcement learning", "supervised learning",
            "unsupervised learning", "transfer learning", "federated learning",
            "microservices", "api", "rest", "graphql", "docker", "kubernetes",
            "cloud computing", "edge computing", "distributed system", "blockchain",
            "data pipeline", "etl", "real-time processing", "stream processing",
            "big data", "data warehouse", "data lake", "nosql", "sql",
            "cybersecurity", "encryption", "authentication", "authorization",
            "load balancing", "caching", "database", "scalability", "performance"
        ]

        for concept in concept_patterns:
            if concept in text:
                concepts.append(concept)

        return list(set(concepts))  # Remove duplicates

    def _classify_research_areas(self, categories: list[str], keywords: list[str]) -> list[str]:
        """Classify papers into research areas based on categories and keywords."""
        areas = []

        # Category-based classification
        category_mapping = {
            'AI/ML': ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'stat.ML'],
            'Software Engineering': ['cs.SE', 'cs.PL'],
            'Systems & Architecture': ['cs.DC', 'cs.AR', 'cs.OS', 'cs.NI', 'cs.SY'],
            'Data & Databases': ['cs.DB', 'cs.DS', 'cs.IR'],
            'Security': ['cs.CR', 'cs.CY'],
            'HCI & Robotics': ['cs.HC', 'cs.RO'],
            'Theory': ['cs.CC', 'cs.LO', 'cs.GT'],
            'Statistics': ['stat.AP', 'stat.CO', 'stat.ME'],
            'Mathematics': ['math.OC', 'math.PR', 'math.ST'],
            'Quantum Computing': ['quant-ph'],
            'Finance': ['q-fin.CP', 'q-fin.ST', 'q-fin.TR']
        }

        for area, cats in category_mapping.items():
            if any(cat in categories for cat in cats):
                areas.append(area)

        # Keyword-based additional classification
        keyword_mapping = {
            'Generative AI': ['generative ai', 'llm', 'large language model', 'gpt'],
            'DevOps': ['devops', 'ci/cd', 'continuous integration', 'docker', 'kubernetes'],
            'Data Engineering': ['data pipeline', 'etl', 'data warehouse', 'big data'],
            'Cloud Computing': ['cloud', 'aws', 'azure', 'serverless'],
            'Blockchain': ['blockchain', 'smart contract'],
            'IoT': ['iot', 'internet of things', 'edge computing'],
            'Enterprise': ['enterprise', 'solution architecture', 'digital transformation']
        }

        for area, kws in keyword_mapping.items():
            if any(kw in keywords for kw in kws) and area not in areas:
                areas.append(area)

        return areas

    def fetch_page(self) -> str:
        """Fetch the ArXiv API response with dynamic date updates.

        Returns:
            str: XML content from ArXiv API
        """
        # Update the date range to always be relative to current time
        date_since = (datetime.now() - timedelta(days=self.days_back)).strftime('%Y-%m-%d')
        categories = " OR ".join(self.TECHNICAL_CATEGORIES.keys())
        search_query = f"cat:({categories}) AND submittedDate:[{date_since}000000 TO 999999999999]"

        # Add keyword filtering if enabled
        if self.enable_keyword_filtering:
            keyword_query = " OR ".join([f'"{keyword}"' for keyword in self.RELEVANT_KEYWORDS[:20]])
            search_query += f" AND (ti:({keyword_query}) OR abs:({keyword_query}))"

        current_url = f"{self.ARXIV_API_BASE}?search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results={self.max_results}"
        self.url = current_url

        return super().fetch_page()

    def trigger_alarm(self, old_papers: list[dict[str, Any]], new_papers: list[dict[str, Any]]):
        """Enhanced alarm processing for new papers.

        Args:
            old_papers: Previously fetched papers
            new_papers: Currently fetched papers
        """
        # Call parent method for basic processing
        super().trigger_alarm(old_papers, new_papers)

        # Additional enhanced processing
        old_ids = {paper["id"] for paper in old_papers} if old_papers else set()

        # Identify high-impact new papers
        new_high_impact_papers = [
            paper for paper in new_papers
            if paper["id"] not in old_ids and paper.get("relevance_score", 0) >= 5.0
        ]

        if new_high_impact_papers:
            self.logger.warning(f"HIGH-IMPACT PAPERS DETECTED: {len(new_high_impact_papers)} papers with high relevance scores")

            # Save high-impact papers separately
            self._save_papers(new_high_impact_papers, "high_impact_papers")

            # Log details about high-impact papers
            for paper in new_high_impact_papers:
                self.logger.info(
                    f"High-impact paper: {paper['title'][:100]}... "
                    f"(Score: {paper['relevance_score']}, Areas: {paper['research_areas']})"
                )

    def _save_papers(self, papers: list[dict[str, Any]], filename: str):
        """Save papers to a JSON file with enhanced metadata.

        Args:
            papers (List[Dict[str, Any]]): Papers to save
            filename (str): Filename without extension
        """
        filepath = os.path.join(self.data_dir, f"{filename}.json")

        # Add summary metadata
        enhanced_data = {
            "metadata": {
                "total_papers": len(papers),
                "collection_timestamp": datetime.now().isoformat(),
                "watcher_name": self.name,
                "categories_covered": list(self.TECHNICAL_CATEGORIES.keys()),
                "keyword_filtering_enabled": self.enable_keyword_filtering,
                "average_relevance_score": sum(p.get("relevance_score", 0) for p in papers) / len(papers) if papers else 0,
                "research_areas_distribution": self._calculate_area_distribution(papers)
            },
            "papers": papers
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(papers)} enhanced papers to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving enhanced papers to {filepath}: {e!s}")

    def _calculate_area_distribution(self, papers: list[dict[str, Any]]) -> dict[str, int]:
        """Calculate distribution of papers across research areas."""
        distribution = {}
        for paper in papers:
            for area in paper.get("research_areas", []):
                distribution[area] = distribution.get(area, 0) + 1
        return distribution

    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Determine if the ArXiv papers have changed significantly enough to trigger an alarm.

        Args:
            old_value: Previously extracted papers (can be None for first run)
            new_value: Currently extracted papers

        Returns:
            bool: True if changes are significant enough to trigger an alarm
        """
        # Convert to lists if needed
        old_papers = old_value if isinstance(old_value, list) else []
        new_papers = new_value if isinstance(new_value, list) else []

        # If this is the first run (no old papers), only trigger if we have new papers
        if old_papers is None or len(old_papers) == 0:
            return len(new_papers) > 0

        # If new papers list is empty but old papers existed, that's a change
        if len(new_papers) == 0:
            return True

        # Create sets of paper IDs for comparison
        old_ids = {paper["id"] for paper in old_papers if isinstance(paper, dict) and "id" in paper}
        new_ids = {paper["id"] for paper in new_papers if isinstance(paper, dict) and "id" in paper}

        # Check for new papers (papers in new_papers but not in old_papers)
        new_paper_ids = new_ids - old_ids

        # Trigger alarm if:
        # 1. There are new papers
        # 2. There are high-relevance new papers (score >= 4.0)
        # 3. The total number of papers has changed significantly (more than 10% change)

        has_new_papers = len(new_paper_ids) > 0

        if has_new_papers:
            # Check if any new papers have high relevance scores
            high_relevance_new_papers = [
                paper for paper in new_papers
                if isinstance(paper, dict) and paper.get("id") in new_paper_ids and paper.get("relevance_score", 0) >= 4.0
            ]

            # Log information about changes
            self.logger.info(f"Paper comparison: {len(old_papers)} old vs {len(new_papers)} new papers")
            self.logger.info(f"New papers detected: {len(new_paper_ids)}")
            if high_relevance_new_papers:
                self.logger.info(f"High-relevance new papers: {len(high_relevance_new_papers)}")

            # Trigger alarm if there are new papers (any new papers are interesting for ArXiv monitoring)
            return True

        # Check for significant changes in paper count (might indicate API issues or major events)
        old_count = len(old_papers)
        new_count = len(new_papers)
        count_change_percentage = abs(new_count - old_count) / old_count if old_count > 0 else 0

        if count_change_percentage > 0.5:  # More than 50% change in paper count
            self.logger.info(f"Significant change in paper count: {old_count} -> {new_count} ({count_change_percentage:.1%})")
            return True

        # No significant changes detected
        return False
