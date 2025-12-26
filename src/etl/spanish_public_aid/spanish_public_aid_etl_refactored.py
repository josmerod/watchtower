"""Refactored Spanish Public Aid ETL with clean architecture.

This ETL scrapes Spanish public aid convocations from multiple sources.
"""

import logging
from typing import Any

from src.etl.base import SimpleETL
from src.models.spanish_public_aid import (
    AidCategory,
    AidScope,
    AidStatus,
    AidType,
    AmountModel,
    BeneficiaryType,
    GeographicScopeModel,
    PaymentType,
    SpanishPublicAidModel,
)

from .classification_service import ClassificationService
from .config import DEFAULT_CONFIG, SpanishPublicAidConfig
from .enhancement_service import EnhancementService
from .scraping_service import ScrapingService


class SpanishPublicAidETLRefactored(SimpleETL):
    """Refactored ETL for Spanish public aid convocations.

    This refactored version separates concerns into focused services:
    - ScrapingService: Handles HTTP requests and HTML parsing
    - ClassificationService: Determines aid type, category, status, beneficiary
    - EnhancementService: Adds tags, keywords, quality scores
    """

    def __init__(self, config: SpanishPublicAidConfig | None = None):
        """Initialize the refactored Spanish Public Aid ETL.

        Args:
            config: ETL configuration
        """
        if config is None:
            config = DEFAULT_CONFIG

        super().__init__(
            name="spanish_public_aid",
            description="Refactored ETL for Spanish public aid convocations",
            batch_size=config.batch_size,
            enable_checkpointing=config.enable_checkpointing,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )

        self.config = config

        # Initialize services
        self.scraping_service = ScrapingService(
            config=config,
            request_delay=config.request_delay_seconds,
            debug=config.debug,
        )
        self.classification_service = ClassificationService(debug=config.debug)
        self.enhancement_service = EnhancementService(debug=config.debug)

        # Sources configuration
        self.sources = {
            "bdns": {
                "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/inicio",
                "name": "Base de Datos Nacional de Subvenciones",
                "scope": AidScope.NATIONAL,
                "enabled": config.bdns_enabled,
                "max_aids_per_source": config.max_aids_per_source,
            },
            "gva": {
                "url": "https://www.gva.es/es/inicio/procedimientos",
                "name": "Generalitat Valenciana",
                "scope": AidScope.AUTONOMOUS_COMMUNITY,
                "enabled": config.gva_enabled,
                "max_aids_per_source": config.max_aids_per_source,
            },
            "valencia": {
                "url": "https://www.valencia.es/cas/tramites/tramites-subvenciones",
                "name": "Ayuntamiento de Valencia",
                "scope": AidScope.LOCAL,
                "enabled": config.valencia_enabled,
                "max_aids_per_source": config.max_aids_per_source,
            },
            "labora": {
                "url": "https://labora.gva.es/es/empreses/busque-ajudes-subvencions/ajudes-foment-de-l-ocupacio-2025",
                "name": "LABORA - Servicio Valenciano de Empleo",
                "scope": AidScope.AUTONOMOUS_COMMUNITY,
                "enabled": config.labora_enabled,
                "max_aids_per_source": config.max_aids_per_source,
            },
        }

        logging.info("Refactored Spanish Public Aid ETL initialized with service layer")

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from all configured sources."""
        logging.info("Starting Spanish public aid data extraction")
        all_extracted_data = []

        for source_key, source_config in self.sources.items():
            if not source_config.get("enabled", True):
                logging.info(f"Skipping disabled source: {source_key}")
                continue

            logging.info(f"Extracting from source: {source_config['name']}")

            try:
                source_data = self.scraping_service.extract_from_source(source_key, source_config)
                logging.info(f"Extracted {len(source_data)} items from {source_key}")
                all_extracted_data.extend(source_data)

            except Exception as e:
                logging.error(f"Error extracting from {source_key}: {e}")
                self.metrics.error_count += 1
                continue

        logging.info(f"Total extracted items: {len(all_extracted_data)}")
        return all_extracted_data

    def transform(self, raw_data: list[dict[str, Any]]) -> list[SpanishPublicAidModel]:
        """Transform raw data into aid models.

        Args:
            raw_data: List of raw aid dictionaries

        Returns:
            List of SpanishPublicAidModel
        """
        if not raw_data:
            logging.warning("No data to transform")
            return []

        try:
            logging.info(f"Starting transformation of {len(raw_data)} items")
            transformed_models = []

            for item in raw_data:
                try:
                    model = self._transform_single_item(item)
                    if model:
                        transformed_models.append(model)
                        self.metrics.records_loaded += 1
                except Exception as e:
                    logging.error(f"Error transforming item: {e}")
                    self.metrics.records_failed += 1
                    continue

            logging.info(f"Successfully transformed {len(transformed_models)} items")
            return transformed_models

        except Exception as e:
            logging.error(f"Error in transformation: {e}")
            raise

    def _transform_single_item(self, raw_data: dict[str, Any]) -> SpanishPublicAidModel | None:
        """Transform a single aid item.

        Args:
            raw_data: Raw aid data

        Returns:
            SpanishPublicAidModel or None
        """
        try:
            # Enhance data first
            enhanced_data = self.enhancement_service.enhance_aid_data(raw_data)

            # Extract basic fields
            title = enhanced_data.get("title", "")
            description = enhanced_data.get("description", "")
            url = enhanced_data.get("url", "")
            source = enhanced_data.get("source", "")

            # Classify aid
            aid_type = self.classification_service.determine_aid_type(title, description)
            category = self.classification_service.determine_category(title, description)
            status = self.classification_service.determine_status(title, description)
            beneficiary_type = self.classification_service.determine_beneficiary_type(title, description)
            scope = self.classification_service.determine_scope_from_source(source)
            payment_type = self.classification_service.determine_payment_type(title, description)

            # Extract dates
            dates = enhanced_data.get("dates", [])
            deadline_date = dates[0] if dates else None

            # Create geographic scope
            geo_scope = GeographicScopeModel(
                national=(scope == AidScope.NATIONAL),
                regional=(scope == AidScope.REGIONAL),
                autonomous_community=(scope == AidScope.AUTONOMOUS_COMMUNITY),
                local=(scope == AidScope.LOCAL),
            )

            # Create amount model (placeholder)
            amount = AmountModel(
                amount=0.0,
                currency="EUR",
                is_defined=False,
            )

            # Create model
            model = SpanishPublicAidModel(
                title=title,
                description=description,
                url=url,
                source=source,
                aid_type=aid_type,
                category=category,
                status=status,
                beneficiary_type=beneficiary_type,
                scope=scope,
                geographic_scope=geo_scope,
                payment_type=payment_type,
                amount=amount,
                deadline_date=deadline_date,
                tags=enhanced_data.get("tags", []),
                keywords=enhanced_data.get("keywords", []),
                quality_score=enhanced_data.get("quality_score", 0.0),
            )

            return model

        except Exception as e:
            logging.error(f"Error creating model for item: {e}")
            return None

    def generate_statistics(self, data: list[SpanishPublicAidModel]) -> dict[str, Any]:
        """Generate statistics from processed data.

        Args:
            data: List of aid models

        Returns:
            Statistics dictionary
        """
        return self.enhancement_service.generate_statistics(data)
