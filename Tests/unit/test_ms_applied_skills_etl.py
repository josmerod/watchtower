"""Tests for the Microsoft Learn credentials ETL."""

from __future__ import annotations

from typing import Any

from src.etl.courses.ms_applied_skills_etl import MsAppliedSkillsETL


class _Response:
    """Minimal response double for requests.get."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """Simulate a successful HTTP response."""

    def json(self) -> dict[str, Any]:
        """Return the mocked Microsoft Learn catalog payload."""
        return self._payload


def test_extract_includes_applied_skills_and_certifications(monkeypatch) -> None:
    """Certifications should be retained instead of only extracting appliedSkills."""
    payload = {
        "appliedSkills": [
            {
                "title": "Microsoft Applied Skills: Build an app",
                "url": "https://learn.microsoft.com/en-us/credentials/applied-skills/build-app/",
            }
        ],
        "certifications": [
            {
                "title": "Microsoft Certified: Azure Developer Associate",
                "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-developer/",
                "type": "cert",
                "subtitle": "Validate Azure development skills",
            }
        ],
    }

    def fake_get(url: str, timeout: int) -> _Response:
        assert timeout == 30
        assert url == "https://learn.microsoft.com/api/catalog/"
        return _Response(payload)

    monkeypatch.setattr("src.etl.courses.ms_applied_skills_etl.requests.get", fake_get)

    etl = MsAppliedSkillsETL()
    extracted = etl.extract()

    assert [item["title"] for item in extracted] == [
        "Microsoft Applied Skills: Build an app",
        "Microsoft Certified: Azure Developer Associate",
    ]
    assert etl.metrics.records_extracted == 2


def test_transform_preserves_certification_metadata() -> None:
    """Certification catalog records should transform into loadable course models."""
    etl = MsAppliedSkillsETL()

    transformed = etl.transform(
        [
            {
                "title": "Microsoft Certified: Azure Developer Associate",
                "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-developer/",
                "type": "cert",
                "subtitle": "Validate Azure development skills",
                "levels": ["intermediate"],
                "roles": ["developer"],
            }
        ]
    )

    assert len(transformed) == 1
    certification = transformed[0]
    assert certification.title == "Microsoft Certified: Azure Developer Associate"
    assert certification.description == "Validate Azure development skills"
    assert certification.category == "cert"
    assert certification.level == "Intermediate"
    assert certification.roles == ["developer"]
