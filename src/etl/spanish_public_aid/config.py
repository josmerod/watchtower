"""Configuration for Spanish Public Aid ETL."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpanishPublicAidConfig:
    """Configuration for Spanish Public Aid ETL process."""

    # Source configuration
    bdns_enabled: bool = True
    gva_enabled: bool = True
    valencia_enabled: bool = True
    labora_enabled: bool = True

    # Extraction limits
    max_aids_per_source: int = 20
    request_delay_seconds: float = 2.0

    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("data/spanish_public_aid"))

    # Checkpointing
    enable_checkpointing: bool = True
    checkpoint_interval: int = 10

    # Retry settings
    max_retries: int = 3
    retry_delay: int = 10
    batch_size: int = 20

    # Debug
    debug: bool = False


# Default configuration
DEFAULT_CONFIG = SpanishPublicAidConfig()
