"""Data models for security vulnerabilities and threat intelligence."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, HttpUrl, computed_field, field_validator

from models.base import TimestampedModel


class RiskLevel(str, Enum):
    """Vulnerability risk level enumeration."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityStatus(str, Enum):
    """Vulnerability status enumeration."""

    ACTIVE = "active"
    PATCHED = "patched"
    MITIGATED = "mitigated"
    IGNORED = "ignored"
    FALSE_POSITIVE = "false_positive"


class AttackVector(str, Enum):
    """CVSS attack vector enumeration."""

    NETWORK = "network"
    ADJACENT = "adjacent"
    LOCAL = "local"
    PHYSICAL = "physical"


class AttackComplexity(str, Enum):
    """CVSS attack complexity enumeration."""

    LOW = "low"
    HIGH = "high"


class PrivilegesRequired(str, Enum):
    """CVSS privileges required enumeration."""

    NONE = "none"
    LOW = "low"
    HIGH = "high"


class UserInteraction(str, Enum):
    """CVSS user interaction enumeration."""

    NONE = "none"
    REQUIRED = "required"


class VulnerabilitySourceModel(TimestampedModel):
    """Model for vulnerability data sources."""

    name: str = Field(description="Source name")
    description: str | None = Field(default=None, description="Source description")
    url: HttpUrl = Field(description="Source URL")
    source_type: str = Field(description="Type of source (cve, github, npm, etc.)")

    # Configuration
    active: bool = Field(default=True, description="Whether source is active")
    fetch_interval: int = Field(
        default=3600, ge=300, le=86400, description="Fetch interval in seconds"
    )

    # Metadata
    last_fetched_at: datetime | None = Field(
        default=None, description="Last successful fetch timestamp"
    )
    last_error: str | None = Field(default=None, description="Last error message")
    total_vulnerabilities_fetched: int = Field(
        default=0, ge=0, description="Total vulnerabilities fetched from this source"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that URL is accessible.

        Args:
            v: URL to validate.

        Returns:
            Validated URL.
        """
        parsed = urlparse(str(v))
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        return v


class VulnerabilityModel(TimestampedModel):
    """Model for security vulnerabilities."""

    # Core vulnerability info
    cve_id: str | None = Field(default=None, description="CVE identifier")
    vulnerability_id: str = Field(description="Unique vulnerability identifier")
    title: str = Field(description="Vulnerability title/summary")
    description: str = Field(description="Detailed vulnerability description")

    # Source info
    source_name: str = Field(description="Source that reported this vulnerability")
    source_url: HttpUrl | None = Field(default=None, description="Source URL")
    source_id: str | None = Field(default=None, description="Source-specific ID")

    # CVSS Scoring
    cvss_version: str | None = Field(
        default=None, description="CVSS version (e.g., '3.1')"
    )
    cvss_vector: str | None = Field(default=None, description="CVSS vector string")
    cvss_base_score: float | None = Field(
        default=None, ge=0.0, le=10.0, description="CVSS base score"
    )
    cvss_temporal_score: float | None = Field(
        default=None, ge=0.0, le=10.0, description="CVSS temporal score"
    )
    cvss_environmental_score: float | None = Field(
        default=None, ge=0.0, le=10.0, description="CVSS environmental score"
    )

    # CVSS Metrics
    attack_vector: AttackVector | None = Field(
        default=None, description="CVSS attack vector"
    )
    attack_complexity: AttackComplexity | None = Field(
        default=None, description="CVSS attack complexity"
    )
    privileges_required: PrivilegesRequired | None = Field(
        default=None, description="CVSS privileges required"
    )
    user_interaction: UserInteraction | None = Field(
        default=None, description="CVSS user interaction"
    )

    # Watchtower-specific scoring
    severity_score: float = Field(
        ge=0.0, le=10.0, description="Watchtower calculated severity score"
    )
    risk_level: RiskLevel = Field(description="Risk level classification")

    # Affected components
    affected_packages: list[str] = Field(
        default=[], description="List of affected packages/components"
    )
    affected_versions: list[str] = Field(
        default=[], description="List of affected versions"
    )
    technology_stack: list[str] = Field(
        default=[], description="Technology stack categories"
    )

    # Patch and mitigation info
    patch_available: bool = Field(
        default=False, description="Whether patch is available"
    )
    patch_version: str | None = Field(default=None, description="Version with patch")
    patch_url: HttpUrl | None = Field(default=None, description="Patch download URL")
    estimated_fix_time: str | None = Field(
        default=None, description="Estimated time to fix (e.g., '24h', '1w')"
    )
    mitigation_strategies: list[str] = Field(
        default=[], description="List of mitigation strategies"
    )

    # Publication info
    published_date: datetime = Field(description="Vulnerability publication date")
    disclosed_date: datetime | None = Field(
        default=None, description="Vulnerability disclosure date"
    )
    modified_date: datetime | None = Field(
        default=None, description="Last modification date"
    )

    # Status and tracking
    status: VulnerabilityStatus = Field(
        default=VulnerabilityStatus.ACTIVE, description="Vulnerability status"
    )
    exploitability: str | None = Field(
        default=None, description="Exploitability assessment"
    )
    exploit_available: bool = Field(
        default=False, description="Whether public exploit is available"
    )

    # Reference links
    references: list[HttpUrl] = Field(default=[], description="Reference URLs")
    advisory_urls: list[HttpUrl] = Field(
        default=[], description="Security advisory URLs"
    )

    # Additional metadata
    tags: list[str] = Field(default=[], description="Vulnerability tags")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional vulnerability metadata"
    )

    @computed_field
    @property
    def is_critical(self) -> bool:
        """Check if vulnerability is critical."""
        return self.severity_score >= 9.0 and self.risk_level == RiskLevel.CRITICAL

    @computed_field
    @property
    def days_since_published(self) -> int:
        """Calculate days since vulnerability was published."""
        return (datetime.utcnow() - self.published_date).days

    @computed_field
    @property
    def is_recent(self) -> bool:
        """Check if vulnerability was published in the last 30 days."""
        return self.days_since_published <= 30

    @computed_field
    @property
    def needs_urgent_attention(self) -> bool:
        """Check if vulnerability needs urgent attention."""
        return (
            self.is_critical
            and self.exploit_available
            and not self.patch_available
            and self.days_since_published <= 7
        )

    @field_validator("cve_id")
    @classmethod
    def validate_cve_id(cls, v: str | None) -> str | None:
        """Validate CVE ID format.

        Args:
            v: CVE ID to validate.

        Returns:
            Validated CVE ID.
        """
        if v is None:
            return v

        # CVE format: CVE-YYYY-NNNN
        import re

        if not re.match(r"^CVE-\d{4}-\d{4,}$", v):
            raise ValueError("Invalid CVE ID format. Expected CVE-YYYY-NNNN")
        return v

    @field_validator("severity_score")
    @classmethod
    def validate_severity_score(cls, v: float) -> float:
        """Validate severity score is within bounds.

        Args:
            v: Severity score to validate.

        Returns:
            Validated severity score.
        """
        if not 0.0 <= v <= 10.0:
            raise ValueError("Severity score must be between 0.0 and 10.0")
        return round(v, 1)

    @field_validator("risk_level", mode="before")
    @classmethod
    def auto_assign_risk_level(cls, v: RiskLevel | None, info) -> RiskLevel:
        """Auto-assign risk level based on severity score if not provided.

        Args:
            v: Current risk level value.
            info: Validation info with other field values.

        Returns:
            Risk level.
        """
        if v is not None:
            return v

        # Get severity score from info.data
        data = info.data if hasattr(info, "data") else {}
        severity_score = data.get("severity_score", 0.0)

        if severity_score >= 9.0:
            return RiskLevel.CRITICAL
        elif severity_score >= 7.0:
            return RiskLevel.HIGH
        elif severity_score >= 4.0:
            return RiskLevel.MEDIUM
        elif severity_score >= 0.1:
            return RiskLevel.LOW
        else:
            return RiskLevel.INFO

    class Config:
        """Pydantic configuration."""

        schema_extra = {
            "examples": [
                {
                    "vulnerability_id": "WTWR-2025-001",
                    "cve_id": "CVE-2025-1234",
                    "title": "Remote Code Execution in Example Package",
                    "description": "A critical remote code execution vulnerability...",
                    "source_name": "GitHub Security Advisories",
                    "cvss_base_score": 9.8,
                    "severity_score": 9.5,
                    "risk_level": "critical",
                    "affected_packages": ["example-package"],
                    "affected_versions": ["< 2.1.0"],
                    "technology_stack": ["javascript", "node.js"],
                    "patch_available": True,
                    "patch_version": "2.1.0",
                    "published_date": "2025-03-01T10:00:00Z",
                }
            ]
        }


class ThreatIntelligenceModel(TimestampedModel):
    """Model for threat intelligence data."""

    threat_id: str = Field(description="Unique threat identifier")
    threat_type: str = Field(description="Type of threat")
    threat_name: str = Field(description="Threat name")
    description: str = Field(description="Threat description")

    # Threat characteristics
    severity: RiskLevel = Field(description="Threat severity")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level (0-1)")
    probability: float = Field(
        ge=0.0, le=1.0, description="Probability of occurrence (0-1)"
    )

    # Affected systems
    affected_technologies: list[str] = Field(
        default=[], description="Affected technologies"
    )
    affected_platforms: list[str] = Field(default=[], description="Affected platforms")

    # Timeline
    first_observed: datetime = Field(description="First observation date")
    last_observed: datetime | None = Field(
        default=None, description="Last observation date"
    )
    estimated_timeline: str | None = Field(
        default=None, description="Estimated timeline for threat"
    )

    # Mitigation
    mitigation_strategies: list[str] = Field(
        default=[], description="Recommended mitigation strategies"
    )
    indicators_of_compromise: list[str] = Field(
        default=[], description="Indicators of compromise"
    )

    # References
    sources: list[str] = Field(default=[], description="Intelligence sources")
    references: list[HttpUrl] = Field(default=[], description="Reference URLs")

    # Additional data
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional threat metadata"
    )
