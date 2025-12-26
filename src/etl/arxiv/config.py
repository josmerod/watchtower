"""Configuration for Enhanced ArXiv ETL."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EnhancedArxivConfig:
    """Configuration for Enhanced ArXiv ETL process."""

    # Basic settings
    name: str = "enhanced_arxiv"
    days_back: int = 7
    max_results: int = 200

    # Advanced features
    enable_advanced_scoring: bool = True
    enable_github_integration: bool = True
    enable_pwc_integration: bool = True

    # Classification settings
    n_clusters: int = 15

    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("data/arxiv/enhanced"))
    save_csv: bool = True
    save_json: bool = True

    # Debug settings
    debug: bool = False

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of validation error messages
        """
        errors = []

        if self.days_back < 1:
            errors.append("days_back must be at least 1")

        if self.max_results < 1:
            errors.append("max_results must be at least 1")

        if self.n_clusters < 2:
            errors.append("n_clusters must be at least 2")

        if self.days_back > 365:
            errors.append("days_back cannot exceed 365")

        return errors

    def __post_init__(self):
        """Validate configuration after initialization."""
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")


# Default configuration
DEFAULT_CONFIG = EnhancedArxivConfig()
