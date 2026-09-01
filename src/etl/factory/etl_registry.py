"""ETL Registry - Centralized registration of all ETLs.

This module registers all available ETLs with the ETLFactory for dynamic
instantiation. Entries whose module or class cannot be imported are skipped
with a warning instead of aborting the whole registration.
"""

import importlib
import logging
from typing import Any

from src.etl.base import BaseETL
from src.etl.factory.etl_factory import ETLFactory

logger = logging.getLogger(__name__)

# (factory name, fully-qualified class path, default config) for every ETL to
# register. Each class must inherit from BaseETL; configs are passed as kwargs
# to the ETL constructor by ETLFactory.create(), so only include kwargs the
# constructor actually accepts (an empty dict means "no-arg constructor").
_ETL_REGISTRATIONS: list[tuple[str, str, dict[str, Any]]] = [
    ("arxiv", "src.etl.arxiv.arxiv_etl.ArxivETL", {"batch_size": 100, "enable_checkpointing": True}),
    ("anthropic", "src.etl.ai_platforms.anthropic_etl.AnthropicETL", {"enable_checkpointing": True, "batch_size": 20}),
    ("spanish_public_aid", "src.etl.spanish_public_aid.spanish_public_aid_etl.SpanishPublicAidETL", {}),
    ("virtual_museums", "src.etl.museums.museum_etl.VirtualMuseumsETL", {}),
]


def register_all_etls() -> None:
    """Register all ETLs listed in _ETL_REGISTRATIONS with the factory.

    Entries that cannot be imported or do not subclass BaseETL are skipped
    with a warning so a single bad entry never breaks the registry.
    """
    for name, class_path, config in _ETL_REGISTRATIONS:
        module_path, _, class_name = class_path.rpartition(".")
        try:
            module = importlib.import_module(module_path)
            etl_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.warning("Skipping ETL '%s': cannot import %s (%s)", name, class_path, e)
            continue

        if not (isinstance(etl_class, type) and issubclass(etl_class, BaseETL)):
            logger.warning("Skipping ETL '%s': %s does not inherit from BaseETL", name, class_path)
            continue

        ETLFactory.register(name, etl_class, config=config or None)

    logger.info("Registered %d ETLs with factory: %s", len(ETLFactory.list_etls()), ETLFactory.list_etls())


# Auto-register on import
register_all_etls()
