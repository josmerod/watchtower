"""Tests for the BDNS convocatorias section of the Spanish public aid tab.

Pure rendering tests with fixture data — no network, no dash server.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from src.web.dashboard.components import spanish_public_aid_tab as tab


@pytest.fixture()
def bdns_items() -> list[dict]:
    """Fixture normalized items matching the BDNS ETL output shape."""
    soon = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    past = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    return [
        {
            "bdns_id": "926783",
            "title": "Subvenció complementària Aj. Fulleda",
            "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/bdnstrans/convocatorias/926783",
            "org": "DIPUTACIÓN PROVINCIAL DE LLEIDA",
            "org_level": "LOCAL",
            "scope": "ES513 - Lleida",
            "registered_date": "2026-08-27",
            "opening_date": "2026-01-01",
            "deadline_date": "2026-12-31",
            "open_ended": False,
            "amounts": {"total_budget": 2400.76, "currency": "EUR"},
            "beneficiaries": ["PYME"],
            "finalidad": "Otras actuaciones",
            "bases_url": "https://example.com/bases.pdf",
            "enriched": True,
            "raw_ref": "bdns:926783",
        },
        {
            "bdns_id": "926700",
            "title": "Ayudas sin detalle aún",
            "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/bdnstrans/convocatorias/926700",
            "org": "MINISTERIO DE INDUSTRIA",
            "org_level": "ESTATAL",
            "scope": "ESTATAL",
            "registered_date": "2026-08-26",
            "opening_date": None,
            "deadline_date": soon,
            "open_ended": False,
            "amounts": {"total_budget": None, "currency": "EUR"},
            "beneficiaries": [],
            "finalidad": "",
            "bases_url": "",
            "enriched": False,
            "raw_ref": "bdns:926700",
        },
        {
            "bdns_id": "926650",
            "title": "Convocatoria cerrada",
            "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/bdnstrans/convocatorias/926650",
            "org": "AYUNTAMIENTO DE CARTAGENA",
            "org_level": "LOCAL",
            "scope": "ES630 - Murcia",
            "registered_date": "2026-08-20",
            "opening_date": None,
            "deadline_date": past,
            "open_ended": False,
            "amounts": {"total_budget": 1000000.0, "currency": "EUR"},
            "beneficiaries": [],
            "finalidad": "",
            "bases_url": "",
            "enriched": True,
            "raw_ref": "bdns:926650",
        },
    ]


class TestFormatHelpers:
    """Amount and deadline formatting helpers."""

    def test_amount_none(self):
        assert tab._format_bdns_amount({"amounts": {"total_budget": None}}) == "—"
        assert tab._format_bdns_amount({}) == "—"

    def test_amount_spanish_format(self):
        assert tab._format_bdns_amount({"amounts": {"total_budget": 2400.76}}) == "2.400,76 €"
        assert tab._format_bdns_amount({"amounts": {"total_budget": 1000000.0}}) == "1.000.000,00 €"

    def test_days_left_missing(self):
        assert tab._bdns_days_left({}) == "—"
        assert tab._bdns_days_left({"deadline_date": None}) == "—"

    def test_days_left_future_and_past(self):
        soon = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        # deadline lands at midnight, so 3 calendar days ahead counts as 2-3 remaining
        assert tab._bdns_days_left({"deadline_date": soon}) in (2, 3)
        past = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert tab._bdns_days_left({"deadline_date": past}) == 0


class TestCreateBdnsSection:
    """Section rendering with fixture data."""

    def test_empty_state(self):
        section = tab.create_bdns_section([])
        rendered = str(section)
        assert "bdns-convocatorias-table" not in rendered
        assert "Sin datos de BDNS" in rendered
        assert "bdns_convocatorias_etl.py" in rendered

    def test_renders_table_with_items(self, bdns_items):
        section = tab.create_bdns_section(bdns_items)
        rendered = str(section)
        assert "bdns-convocatorias-table" in rendered
        assert "BDNS — Convocatorias recientes" in rendered
        # linked title (markdown), org, scope and formatted amounts
        assert "[Subvenció complementària Aj. Fulleda](" in rendered
        assert "DIPUTACIÓN PROVINCIAL DE LLEIDA" in rendered
        assert "ES513 - Lleida" in rendered
        assert "2.400,76 €" in rendered
        assert "1.000.000,00 €" in rendered
        assert "926783" in rendered

    def test_badge_counts(self, bdns_items):
        section = tab.create_bdns_section(bdns_items)
        rendered = str(section)
        assert "Total: 3" in rendered
        assert "Con plazo: 3" in rendered
        assert "Con cuantía: 2" in rendered


class TestRepositoryTransform:
    """BdnsConvocatoriasRepository.transform_data shapes."""

    def test_list_passthrough(self):
        repo = tab.BdnsConvocatoriasRepository()
        items = [{"bdns_id": "1"}, {"bdns_id": "2"}, "not-a-dict"]
        assert repo.transform_data(items) == [{"bdns_id": "1"}, {"bdns_id": "2"}]

    def test_dict_with_items_key(self):
        repo = tab.BdnsConvocatoriasRepository()
        assert repo.transform_data({"items": [{"bdns_id": "1"}]}) == [{"bdns_id": "1"}]

    def test_garbage(self):
        repo = tab.BdnsConvocatoriasRepository()
        assert repo.transform_data(None) == []
        assert repo.transform_data("nope") == []
        assert repo.transform_data({"no": "items"}) == []


class TestLoadBdnsConvocatorias:
    """Loader must never raise and delegate to the repository."""

    def test_delegates_to_repo(self, monkeypatch, bdns_items):
        monkeypatch.setattr(tab.bdns_convocatorias_repo, "get", Mock(return_value=bdns_items))
        assert tab.load_bdns_convocatorias() == bdns_items

    def test_repo_error_returns_empty(self, monkeypatch):
        monkeypatch.setattr(tab.bdns_convocatorias_repo, "get", Mock(side_effect=RuntimeError("boom")))
        assert tab.load_bdns_convocatorias() == []

    def test_none_returns_empty(self, monkeypatch):
        monkeypatch.setattr(tab.bdns_convocatorias_repo, "get", Mock(return_value=None))
        assert tab.load_bdns_convocatorias() == []


if __name__ == "__main__":
    pytest.main([__file__])
