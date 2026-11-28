"""Tests for the Microsoft Learn credentials ETL."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import pytest

from src.config.settings import get_settings
from src.etl.courses import ms_applied_skills_etl as ms
from src.etl.courses.ms_applied_skills_etl import MsAppliedSkillsETL


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path, monkeypatch):
    """Send every BaseETL write (data, checkpoints, circuit breaker, run summaries) to tmp_path instead of the real data/."""
    monkeypatch.setattr(get_settings(), "project_root", str(tmp_path))
    yield


class _Response:
    """Minimal response double for requests.get."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """Simulate a successful HTTP response."""

    def json(self) -> dict[str, Any]:
        """Return the mocked Microsoft Learn catalog payload."""
        return self._payload


def _warning(body: str, closing: str = "To earn this credential, learners build a chat bot.") -> str:
    """A description that opens with the warning box the catalog puts on a retired credential."""
    return f'<div class="WARNING">\n<p>Warning</p>\n<p>{body}</p>\n</div>\n<p>{closing}</p>\n'


CURRENT_DESCRIPTION = "<p>As a candidate for this certification, you:</p>\n<ul>\n<li>Design solutions.</li>\n<li>Administer resources.</li>\n</ul>\n"
LEGACY_DESCRIPTION = "<div><strong>This version of the certification is no longer available. If you have this version of the certification, you will automatically be granted the latest version of the certification.<br/><br/>You only have to renew the newer version.</strong></div>"
RELATED_EXAMS_NOTE = (
    "<p>As a candidate for this certification, you administer Windows Server.</p>\n"
    '<div class="NOTE">\n<p>Note</p>\n<p>Related exams Exam <a href="/credentials/certifications/exams/az-800/">AZ-800</a> and '
    'Exam <a href="/credentials/certifications/exams/az-801/">AZ-801</a> were retired on September 30, 2026. You can view the replacement exam.</p>\n</div>\n'
)


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


# --- Retirement notice -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        pytest.param(_warning("This certification, related exam, and renewal assessments was retired on June 30, 2026. You will no longer be able to earn or renew it."), (True, "2026-06-30"), id="retired-with-date"),
        pytest.param(_warning("This Applied Skills assessment has been retired. Explore other Applied Skills to keep building your skills."), (True, None), id="retired-without-date"),
        pytest.param(_warning("This certification and the renewal assessment are retired."), (True, None), id="renewal-retired-without-date"),
        pytest.param(CURRENT_DESCRIPTION, (False, None), id="current"),
        pytest.param("", (False, None), id="empty"),
        pytest.param(None, (False, None), id="none"),
    ],
)
def test_retirement_notice(description: str | None, expected: tuple[bool, str | None]) -> None:
    """A retired credential is told by its notice, with the date when the notice has one."""
    assert ms.retirement_notice(description) == expected


def test_retirement_notice_is_read_at_the_end_of_the_description() -> None:
    """The catalog also appends the warning box after the description of the credential."""
    description = "<p>As a candidate for this certification, you aspire to understand customer engagement apps.</p>\n<p>It is not a prerequisite for any of them.</p>\n" + _warning("This certification is retired.", closing="")

    assert ms.retirement_notice(description) == (True, None)


def test_superseded_version_is_retired() -> None:
    assert ms.retirement_notice(LEGACY_DESCRIPTION) == (True, None)


def test_retired_exams_do_not_retire_the_credential() -> None:
    """A note about the exams of a credential that is still current is not a retirement notice."""
    assert ms.retirement_notice(RELATED_EXAMS_NOTE) == (False, None)


def test_announced_retirement_counts_from_the_day_after_the_date() -> None:
    description = _warning("This certification, related exam, and renewal assessments will be retired on February 1, 2027.")

    announced = ms.retirement_notice(description, today=datetime.date(2027, 1, 31))
    due = ms.retirement_notice(description, today=datetime.date(2027, 2, 1))
    retired = ms.retirement_notice(description, today=datetime.date(2027, 2, 2))

    assert announced == (False, "2027-02-01")
    assert due == (False, "2027-02-01")
    assert retired == (True, "2027-02-01")


def test_notice_date_that_cannot_be_read_leaves_the_credential_retired_without_one() -> None:
    assert ms.retirement_notice(_warning("This certification was retired on Jun 30, 2026.")) == (True, None)


def test_transform_stores_the_description_as_plain_text() -> None:
    etl = MsAppliedSkillsETL()

    (skill,) = etl.transform([{"title": "Microsoft Certified: Fabric Analyst", "url": "https://learn.microsoft.com/en-us/credentials/certifications/fabric-analyst/", "type": "cert", "summary": CURRENT_DESCRIPTION}])

    assert skill.description == "As a candidate for this certification, you: Design solutions. Administer resources."
    assert "<" not in skill.description


def test_load_writes_the_retirement_fields_of_every_record(tmp_path: Path) -> None:
    etl = MsAppliedSkillsETL()
    records = [
        {"title": "Microsoft Certified: Power Platform Functional Consultant Associate", "url": "https://learn.microsoft.com/en-us/credentials/certifications/power-platform-functional-consultant-associate/", "type": "cert", "summary": _warning("This certification, related exam, and renewal assessments was retired on August 31, 2026.")},
        {"title": "Microsoft Certified: Azure Developer Associate (Legacy)", "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-developer-legacy/", "type": "cert", "summary": LEGACY_DESCRIPTION},
        {"title": "Microsoft Certified: Azure Solutions Architect Expert", "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-solutions-architect/", "type": "cert", "summary": CURRENT_DESCRIPTION},
        {"title": "Microsoft Applied Skills: Create an AI agent", "url": "https://learn.microsoft.com/en-us/credentials/applied-skills/create-ai-agent/", "summary": _warning("This Applied Skills assessment has been retired. Explore other Applied Skills to keep building your skills.")},
    ]

    etl.load(etl.transform(records))

    written = json.loads((tmp_path / "data" / "courses" / "ms_applied_skills.json").read_text(encoding="utf-8"))
    assert [(row["retired"], row["retirement_date"]) for row in written] == [(True, "2026-08-31"), (True, None), (False, None), (True, None)]
    assert all("<" not in row["description"] for row in written)
    assert etl.output_file == tmp_path / "data" / "courses" / "ms_applied_skills.json"
