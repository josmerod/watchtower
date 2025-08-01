"""Models for Spanish public aid data structures."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import Field, HttpUrl, field_validator

from .base import TimestampedModel


class AidScope(str, Enum):
    """Geographic scope of the aid."""
    
    NATIONAL = "nacional"
    AUTONOMOUS_COMMUNITY = "autonomica"
    PROVINCIAL = "provincial"
    LOCAL = "local"
    EUROPEAN = "europea"


class AidType(str, Enum):
    """Type of aid."""
    
    SUBSIDY = "subvencion"
    GRANT = "ayuda"
    LOAN = "prestamo"
    TAX_BENEFIT = "beneficio_fiscal"
    SOCIAL_BENEFIT = "prestacion_social"
    SCHOLARSHIP = "beca"
    DIRECT_PAYMENT = "pago_directo"


class AidCategory(str, Enum):
    """Category of aid."""
    
    HOUSING = "vivienda"
    EMPLOYMENT = "empleo"
    EDUCATION = "educacion"
    HEALTH = "salud"
    SOCIAL_SERVICES = "servicios_sociales"
    YOUTH = "juventud"
    ELDERLY = "mayores"
    DISABILITY = "discapacidad"
    FAMILY = "familia"
    EMERGENCY = "emergencia"
    AGRICULTURE = "agricultura"
    BUSINESS = "empresa"
    CULTURE = "cultura"
    ENVIRONMENT = "medio_ambiente"
    TRANSPORT = "transporte"
    TECHNOLOGY = "tecnologia"
    OTHER = "otros"


class AidStatus(str, Enum):
    """Status of the aid convocation."""
    
    OPEN = "abierta"
    CLOSED = "cerrada"
    IN_EVALUATION = "en_evaluacion"
    RESOLVED = "resuelta"
    SUSPENDED = "suspendida"
    CANCELLED = "cancelada"
    UPCOMING = "proxima"


class BeneficiaryType(str, Enum):
    """Type of beneficiary."""
    
    INDIVIDUAL = "persona_fisica"
    COMPANY = "empresa"
    NGO = "ong"
    PUBLIC_ENTITY = "entidad_publica"
    EDUCATIONAL_INSTITUTION = "institucion_educativa"
    MIXED = "mixto"


class PaymentType(str, Enum):
    """Type of payment."""
    
    LUMP_SUM = "pago_unico"
    MONTHLY = "mensual"
    QUARTERLY = "trimestral"
    ANNUAL = "anual"
    REIMBURSEMENT = "reembolso"
    DIRECT_SERVICE = "servicio_directo"


class RequirementModel(TimestampedModel):
    """Model for aid requirements."""
    
    title: str = Field(description="Requirement title")
    description: str = Field(description="Detailed requirement description")
    is_mandatory: bool = Field(default=True, description="Whether requirement is mandatory")
    documentation_needed: list[str] = Field(
        default_factory=list, description="List of required documents"
    )
    verification_method: str | None = Field(
        default=None, description="How requirement is verified"
    )


class DocumentModel(TimestampedModel):
    """Model for required documents."""
    
    name: str = Field(description="Document name")
    description: str | None = Field(default=None, description="Document description")
    is_mandatory: bool = Field(default=True, description="Whether document is mandatory")
    format: str | None = Field(default=None, description="Required format (PDF, etc.)")
    template_url: HttpUrl | None = Field(default=None, description="URL to document template")
    max_size_mb: float | None = Field(default=None, description="Maximum file size in MB")


class ContactInfoModel(TimestampedModel):
    """Model for contact information."""
    
    office_name: str = Field(description="Office or department name")
    phone: str | None = Field(default=None, description="Contact phone")
    email: str | None = Field(default=None, description="Contact email")
    address: str | None = Field(default=None, description="Physical address")
    website: HttpUrl | None = Field(default=None, description="Website URL")
    office_hours: str | None = Field(default=None, description="Office hours")


class AmountModel(TimestampedModel):
    """Model for aid amounts."""
    
    min_amount: Decimal | None = Field(default=None, description="Minimum aid amount")
    max_amount: Decimal | None = Field(default=None, description="Maximum aid amount")
    fixed_amount: Decimal | None = Field(default=None, description="Fixed aid amount")
    percentage: float | None = Field(default=None, description="Percentage of eligible costs")
    currency: str = Field(default="EUR", description="Currency code")
    payment_type: PaymentType = Field(description="Type of payment")
    total_budget: Decimal | None = Field(default=None, description="Total budget available")
    
    @field_validator("min_amount", "max_amount", "fixed_amount", "total_budget")
    @classmethod
    def validate_positive_amounts(cls, v: Decimal | None) -> Decimal | None:
        """Validate that amounts are positive."""
        if v is not None and v < 0:
            raise ValueError("Amounts must be positive")
        return v


class GeographicScopeModel(TimestampedModel):
    """Model for geographic scope."""
    
    scope: AidScope = Field(description="Geographic scope level")
    country: str = Field(default="España", description="Country")
    autonomous_community: str | None = Field(
        default=None, description="Autonomous community"
    )
    province: str | None = Field(default=None, description="Province")
    municipality: str | None = Field(default=None, description="Municipality")
    postal_codes: list[str] = Field(
        default_factory=list, description="Specific postal codes if applicable"
    )


class SpanishPublicAidModel(TimestampedModel):
    """Model for Spanish public aid convocations."""
    
    # Basic information
    title: str = Field(description="Aid title")
    description: str = Field(description="Detailed description")
    summary: str | None = Field(default=None, description="Brief summary")
    
    # Classification
    aid_type: AidType = Field(description="Type of aid")
    category: AidCategory = Field(description="Aid category")
    scope: GeographicScopeModel = Field(description="Geographic scope")
    
    # Organizing entity
    organizing_entity: str = Field(description="Entity organizing the aid")
    organizing_entity_type: str | None = Field(
        default=None, description="Type of organizing entity"
    )
    ministry_department: str | None = Field(
        default=None, description="Ministry or department"
    )
    
    # Beneficiaries
    beneficiary_type: BeneficiaryType = Field(description="Type of beneficiary")
    target_population: str | None = Field(
        default=None, description="Specific target population"
    )
    age_requirements: dict[str, Any] | None = Field(
        default=None, description="Age requirements (min/max)"
    )
    income_requirements: dict[str, Any] | None = Field(
        default=None, description="Income requirements"
    )
    
    # Financial information
    amount: AmountModel = Field(description="Aid amount information")
    compatibility: str | None = Field(
        default=None, description="Compatibility with other aids"
    )
    
    # Requirements and documentation
    requirements: list[RequirementModel] = Field(
        default_factory=list, description="List of requirements"
    )
    required_documents: list[DocumentModel] = Field(
        default_factory=list, description="Required documents"
    )
    
    # Dates and deadlines
    publication_date: datetime | None = Field(
        default=None, description="Publication date"
    )
    opening_date: datetime | None = Field(
        default=None, description="Application opening date"
    )
    closing_date: datetime | None = Field(
        default=None, description="Application closing date"
    )
    resolution_date: datetime | None = Field(
        default=None, description="Expected resolution date"
    )
    payment_date: datetime | None = Field(
        default=None, description="Expected payment date"
    )
    validity_period: dict[str, Any] | None = Field(
        default=None, description="Validity period information"
    )
    
    # Status and tracking
    status: AidStatus = Field(description="Current status")
    bdns_id: str | None = Field(
        default=None, description="BDNS identifier"
    )
    boe_reference: str | None = Field(
        default=None, description="BOE reference"
    )
    official_reference: str | None = Field(
        default=None, description="Official reference number"
    )
    
    # Application process
    application_method: str | None = Field(
        default=None, description="How to apply"
    )
    application_url: HttpUrl | None = Field(
        default=None, description="Online application URL"
    )
    forms_url: HttpUrl | None = Field(
        default=None, description="Forms download URL"
    )
    
    # Contact and additional information
    contact_info: ContactInfoModel | None = Field(
        default=None, description="Contact information"
    )
    additional_info_url: HttpUrl | None = Field(
        default=None, description="Additional information URL"
    )
    legal_framework: str | None = Field(
        default=None, description="Legal framework or regulation"
    )
    
    # Metadata
    source_url: HttpUrl = Field(description="Source URL where information was found")
    source_name: str = Field(description="Name of the source")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    scraping_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When data was scraped"
    )
    data_quality_score: float | None = Field(
        default=None, description="Data quality score (0-1)"
    )
    is_verified: bool = Field(
        default=False, description="Whether information has been verified"
    )
    
    # Tags and search
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization"
    )
    keywords: list[str] = Field(
        default_factory=list, description="Keywords for search"
    )
    
    @field_validator("data_quality_score")
    @classmethod
    def validate_quality_score(cls, v: float | None) -> float | None:
        """Validate quality score is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Quality score must be between 0 and 1")
        return v
    
    @property
    def is_active(self) -> bool:
        """Check if aid is currently active."""
        now = datetime.utcnow()
        if self.status not in [AidStatus.OPEN, AidStatus.UPCOMING]:
            return False
        if self.closing_date and now > self.closing_date:
            return False
        if self.opening_date and now < self.opening_date:
            return False
        return True
    
    @property
    def days_until_closing(self) -> int | None:
        """Calculate days until closing."""
        if not self.closing_date:
            return None
        now = datetime.utcnow()
        delta = self.closing_date - now
        return max(0, delta.days)
    
    @property
    def is_urgent(self) -> bool:
        """Check if aid is urgent (closing within 7 days)."""
        days_left = self.days_until_closing
        return days_left is not None and days_left <= 7


class AidStatisticsModel(TimestampedModel):
    """Model for aid statistics and analytics."""
    
    total_aids: int = Field(description="Total number of aids")
    active_aids: int = Field(description="Number of active aids")
    by_category: dict[str, int] = Field(
        default_factory=dict, description="Aids by category"
    )
    by_scope: dict[str, int] = Field(
        default_factory=dict, description="Aids by geographic scope"
    )
    by_status: dict[str, int] = Field(
        default_factory=dict, description="Aids by status"
    )
    total_budget: Decimal | None = Field(
        default=None, description="Total budget available"
    )
    average_amount: Decimal | None = Field(
        default=None, description="Average aid amount"
    )
    closing_soon: int = Field(
        default=0, description="Number of aids closing within 7 days"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Statistics update timestamp"
    )


class AidSearchFilter(TimestampedModel):
    """Model for aid search filters."""
    
    keywords: list[str] = Field(default_factory=list, description="Search keywords")
    categories: list[AidCategory] = Field(
        default_factory=list, description="Filter by categories"
    )
    scopes: list[AidScope] = Field(
        default_factory=list, description="Filter by geographic scope"
    )
    statuses: list[AidStatus] = Field(
        default_factory=list, description="Filter by status"
    )
    min_amount: Decimal | None = Field(
        default=None, description="Minimum aid amount"
    )
    max_amount: Decimal | None = Field(
        default=None, description="Maximum aid amount"
    )
    autonomous_community: str | None = Field(
        default=None, description="Specific autonomous community"
    )
    municipality: str | None = Field(
        default=None, description="Specific municipality"
    )
    beneficiary_types: list[BeneficiaryType] = Field(
        default_factory=list, description="Filter by beneficiary type"
    )
    closing_within_days: int | None = Field(
        default=None, description="Filter aids closing within X days"
    )
    only_active: bool = Field(
        default=True, description="Only show active aids"
    )