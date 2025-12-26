"""Classification service for Spanish public aids."""

import logging
from typing import Any

from src.models.spanish_public_aid import (
    AidCategory,
    AidScope,
    AidStatus,
    AidType,
    BeneficiaryType,
    PaymentType,
)


class ClassificationService:
    """Service for classifying Spanish public aids."""

    def __init__(self, debug: bool = False):
        """Initialize classification service.

        Args:
            debug: Enable debug logging
        """
        self.debug = debug

        # Type indicators
        self.type_indicators = {
            AidType.GRANT: ["subven", "ayuda", "beca", "fomento", "apoyo"],
            AidType.LOAN: ["préstamo", "crédito", "financiación"],
            AidType.TAX_BENEFIT: ["bonificación", "deducción", "fiscal"],
            AidType.SERVICE: ["servicio", "asesoramiento", "consultoría"],
            AidType.TRAINING: ["formación", "curso", "taller", "capacitación"],
        }

        # Category indicators
        self.category_indicators = {
            AidCategory.EMPLOYMENT: ["empleo", "trabajo", "contratación", "laboral"],
            AidCategory.EDUCATION: ["educación", "formación", "beca", "estudio"],
            AidCategory.BUSINESS: ["empresa", "emprendedor", "pyme", "comercio"],
            AidCategory.HOUSING: ["vivienda", "alquiler", "vivienda", "alojamiento"],
            AidCategory.RESEARCH: ["investigación", "i+d", "innovación", "proyecto"],
            AidCategory.CULTURE: ["cultura", "arte", "patrimonio", "eventos"],
            AidCategory.ENVIRONMENT: ["medio ambiente", "sostenibilidad", "energía"],
            AidCategory.HEALTH: ["salud", "sanidad", "médico", "bienestar"],
        }

        # Status indicators
        self.status_indicators = {
            AidStatus.OPEN: ["abierta", "convocatoria", "plazo abierto", "inscripción"],
            AidStatus.CLOSED: ["cerrada", "finalizada", "terminada"],
            AidStatus.UPCOMING: ["próximamente", "futura", "próxima"],
        }

        # Beneficiary type indicators
        self.beneficiary_indicators = {
            BeneficiaryType.INDIVIDUAL: ["personas físicas", "particular", "individual"],
            BeneficiaryType.BUSINESS: ["empresas", "pyme", "comerciante", "autónomo"],
            BeneficiaryType.NON_PROFIT: ["asociación", "fundación", "ong", "entidad sin ánimo de lucro"],
            BeneficiaryType.PUBLIC_ADMINISTRATION: ["administración pública", "entidad local"],
        }

    def determine_aid_type(self, title: str, description: str) -> AidType:
        """Determine the type of aid.

        Args:
            title: Aid title
            description: Aid description

        Returns:
            Aid type enum
        """
        text = f"{title} {description}".lower()

        scores = {}
        for aid_type, indicators in self.type_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text)
            scores[aid_type] = score

        if not scores or max(scores.values()) == 0:
            return AidType.GRANT

        return max(scores.items(), key=lambda x: x[1])[0]

    def determine_category(self, title: str, description: str) -> AidCategory:
        """Determine the category of aid.

        Args:
            title: Aid title
            description: Aid description

        Returns:
            Aid category enum
        """
        text = f"{title} {description}".lower()

        scores = {}
        for category, indicators in self.category_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text)
            scores[category] = score

        if not scores or max(scores.values()) == 0:
            return AidCategory.BUSINESS

        return max(scores.items(), key=lambda x: x[1])[0]

    def determine_status(self, title: str, description: str) -> AidStatus:
        """Determine the status of aid.

        Args:
            title: Aid title
            description: Aid description

        Returns:
            Aid status enum
        """
        text = f"{title} {description}".lower()

        # Check for status indicators
        for status, indicators in self.status_indicators.items():
            if any(indicator in text for indicator in indicators):
                return status

        # Default to OPEN if no clear status found
        return AidStatus.OPEN

    def determine_beneficiary_type(self, title: str, description: str) -> BeneficiaryType:
        """Determine the beneficiary type.

        Args:
            title: Aid title
            description: Aid description

        Returns:
            Beneficiary type enum
        """
        text = f"{title} {description}".lower()

        scores = {}
        for beneficiary_type, indicators in self.beneficiary_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text)
            scores[beneficiary_type] = score

        if not scores or max(scores.values()) == 0:
            return BeneficiaryType.INDIVIDUAL

        return max(scores.items(), key=lambda x: x[1])[0]

    def determine_scope_from_source(self, source: str) -> AidScope:
        """Determine scope based on source.

        Args:
            source: Source identifier

        Returns:
            Aid scope enum
        """
        scope_mapping = {
            "bdns": AidScope.NATIONAL,
            "gva": AidScope.AUTONOMOUS_COMMUNITY,
            "labora": AidScope.AUTONOMOUS_COMMUNITY,
            "valencia": AidScope.LOCAL,
        }

        return scope_mapping.get(source, AidScope.REGIONAL)

    def determine_payment_type(self, title: str, description: str) -> PaymentType:
        """Determine the payment type.

        Args:
            title: Aid title
            description: Aid description

        Returns:
            Payment type enum
        """
        text = f"{title} {description}".lower()

        if any(word in text for word in ["reembolsable", "devolución", "retorno"]):
            return PaymentType.REPAYABLE
        elif any(word in text for word in ["no reembolsable", "donación", "regalo"]):
            return PaymentType.NON_REPAYABLE
        else:
            return PaymentType.UNDEFINED
