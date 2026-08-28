"""Tests for the BDNS convocatorias ETL (spec 09 M1).

All tests are fixture-based — no network access. Fixtures under
``Tests/etl/fixtures/`` were trimmed from real SNPSAP API payloads captured
during the T-076 probe (2026-08-28).
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.etl.spanish_public_aid.bdns_convocatorias_etl import (
    BDNS_PAGE_SIZE,
    BdnsConvocatoriaModel,
    BdnsConvocatoriasETL,
    parse_bdns_date,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def search_page_payload() -> dict:
    """Load the trimmed search page fixture."""
    with open(FIXTURES_DIR / "bdns_search_page.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def detail_payload() -> dict:
    """Load the trimmed convocatoria detail fixture."""
    with open(FIXTURES_DIR / "bdns_convocatoria_detail.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def etl_instance() -> BdnsConvocatoriasETL:
    """Create an ETL instance for testing (no network in these tests)."""
    return BdnsConvocatoriasETL()


def _response(payload: dict, status: int = 200) -> Mock:
    """Build a fake requests.Response returning JSON."""
    response = Mock()
    response.status_code = status
    response.headers = {"Content-Type": "application/json"}
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


class TestParseBdnsDate:
    """Date parsing must handle ISO payloads and dd/MM/yyyy query-format strings."""

    def test_iso_format(self):
        assert parse_bdns_date("2026-08-27") == date(2026, 8, 27)

    def test_spanish_format(self):
        assert parse_bdns_date("27/08/2026") == date(2026, 8, 27)

    def test_spanish_short_year(self):
        assert parse_bdns_date("27/08/26") == date(2026, 8, 27)

    def test_missing_values(self):
        assert parse_bdns_date(None) is None
        assert parse_bdns_date("") is None
        assert parse_bdns_date("   ") is None

    def test_garbage_is_tolerated(self):
        assert parse_bdns_date("not-a-date") is None
        assert parse_bdns_date("31/31/2026") is None

    def test_datetime_objects(self):
        assert parse_bdns_date(datetime(2026, 8, 27, 12, 0)) == date(2026, 8, 27)
        assert parse_bdns_date(date(2026, 8, 27)) == date(2026, 8, 27)


class TestSearchParams:
    """Search query must ask for dd/MM/yyyy dates (API requirement)."""

    def test_fecha_desde_format(self, etl_instance):
        params = etl_instance._build_search_params(page=1)
        assert params["fechaDesde"].count("/") == 2
        day, month, year = params["fechaDesde"].split("/")
        assert len(day) == 2 and len(month) == 2 and len(year) == 4
        parsed = datetime.strptime(params["fechaDesde"], "%d/%m/%Y")
        expected_window = date.today() - timedelta(days=14)
        assert abs((parsed.date() - expected_window).days) <= 1

    def test_paging_and_order(self, etl_instance):
        params = etl_instance._build_search_params(page=2)
        assert params["page"] == 2
        assert params["pageSize"] == BDNS_PAGE_SIZE
        assert params["order"] == "fechaRecepcion"
        assert params["direccion"] == "desc"  # codespell:ignore -- BDNS API query param


class TestNormalizeItem:
    """Raw list entries + details must map to the normalized spec-09 shape."""

    def test_full_item_with_detail(self, etl_instance, search_page_payload, detail_payload):
        raw = dict(search_page_payload["content"][0])
        raw["_detail"] = detail_payload

        model = etl_instance._normalize_item(raw)

        assert isinstance(model, BdnsConvocatoriaModel)
        assert model.bdns_id == "926783"
        assert model.raw_ref == "bdns:926783"
        assert "Fulleda" in model.title
        assert model.url == "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/bdnstrans/convocatorias/926783"
        assert model.org == "DIPUTACIÓN PROVINCIAL DE LLEIDA"
        assert model.org_level == "LOCAL"
        assert model.scope == "ES513 - Lleida"
        assert model.registered_date == date(2026, 8, 27)
        assert model.deadline_date == date(2026, 12, 31)
        assert model.opening_date == date(2026, 1, 1)
        assert model.amounts.total_budget == pytest.approx(2400.76)
        assert model.enriched is True
        assert model.beneficiaries  # tiposBeneficiarios mapped

    def test_item_without_detail(self, etl_instance, search_page_payload):
        raw = dict(search_page_payload["content"][1])
        raw["_detail"] = None

        model = etl_instance._normalize_item(raw)

        assert model is not None
        assert model.enriched is False
        assert model.deadline_date is None
        assert model.amounts.total_budget is None
        # scope falls back to the administration level
        assert model.scope == raw["nivel1"]
        assert model.registered_date == date(2026, 8, 27)
        assert model.url.endswith(raw["numeroConvocatoria"])

    def test_missing_title_or_id_dropped(self, etl_instance):
        assert etl_instance._normalize_item({"_detail": None}) is None
        assert etl_instance._normalize_item({"descripcion": "Sin código", "_detail": None}) is None
        assert etl_instance._normalize_item({"numeroConvocatoria": "123", "_detail": None}) is None

    def test_missing_fields_tolerated(self, etl_instance):
        model = etl_instance._normalize_item(
            {
                "numeroConvocatoria": "999",
                "descripcion": "Ayuda mínima",
                "_detail": {"descripcion": "Ayuda mínima", "codigoBDNS": "999", "regiones": None, "organo": None, "presupuestoTotal": "no-numérico"},
            }
        )
        assert model is not None
        assert model.scope == ""
        assert model.org == ""
        assert model.amounts.total_budget is None
        assert model.beneficiaries == []


class TestTransform:
    """Transform must normalize, drop unusable items and sort newest first."""

    def test_transform_sorts_newest_first(self, etl_instance, search_page_payload, detail_payload):
        raws = []
        for item in search_page_payload["content"]:
            raw = dict(item)
            raw["_detail"] = detail_payload if item["numeroConvocatoria"] == detail_payload["codigoBDNS"] else None
            raws.append(raw)
        raws.append({"_detail": None})  # unusable item

        models = etl_instance.transform(raws)

        assert len(models) == len(raws) - 1
        registered = [m.registered_date for m in models]
        assert registered == sorted(registered, reverse=True)
        assert all(isinstance(m, BdnsConvocatoriaModel) for m in models)

    def test_transform_empty(self, etl_instance):
        assert etl_instance.transform([]) == []


class TestExtract:
    """Extraction with a mocked HTTP session: paging, detail cap, resilience."""

    def test_extract_pages_and_enriches(self, etl_instance, search_page_payload, detail_payload):
        page1 = dict(search_page_payload)
        page1["last"] = True  # single page

        def fake_get(url, params=None, timeout=None):
            if "busqueda" in url:
                return _response(page1)
            if params and params.get("numConv") == detail_payload["codigoBDNS"]:
                return _response(detail_payload)
            raise ConnectionError("no detail for this one")

        session = Mock()
        session.get.side_effect = fake_get
        etl_instance.session = session

        with patch("src.etl.spanish_public_aid.bdns_convocatorias_etl.time.sleep"):
            raws = etl_instance.extract()

        assert len(raws) == len(search_page_payload["content"])
        enriched = [r for r in raws if r.get("_detail")]
        assert len(enriched) == 1
        assert enriched[0]["_detail"]["codigoBDNS"] == detail_payload["codigoBDNS"]
        # one search request + one detail request per list item
        assert session.get.call_count == 1 + len(search_page_payload["content"])

    def test_extract_stops_when_last_page(self, etl_instance, search_page_payload):
        page1 = dict(search_page_payload, last=True)
        session = Mock()
        session.get.return_value = _response(page1)
        etl_instance.session = session

        with patch("src.etl.spanish_public_aid.bdns_convocatorias_etl.time.sleep"):
            etl_instance.extract()

        # must not fetch a second page when the API says last=True
        assert session.get.call_count == 1 + len(search_page_payload["content"])

    def test_extract_search_failure_returns_empty(self, etl_instance):
        session = Mock()
        session.get.side_effect = ConnectionError("boom")
        etl_instance.session = session

        with patch("src.etl.spanish_public_aid.bdns_convocatorias_etl.time.sleep"):
            assert etl_instance.extract() == []

    def test_extract_detail_failure_tolerated(self, etl_instance, search_page_payload):
        page1 = dict(search_page_payload, last=True)
        session = Mock()
        session.get.side_effect = [_response(page1), ConnectionError("detail boom")]
        etl_instance.session = session

        with patch("src.etl.spanish_public_aid.bdns_convocatorias_etl.time.sleep"):
            raws = etl_instance.extract()

        assert len(raws) == len(search_page_payload["content"])
        assert all(r.get("_detail") is None for r in raws)


class TestLoad:
    """Load must persist latest + stamped JSON plus stats to the output dir."""

    def test_load_writes_latest_and_stats(self, etl_instance, search_page_payload, detail_payload, tmp_path):
        etl_instance.output_dir = tmp_path
        raw = dict(search_page_payload["content"][0])
        raw["_detail"] = detail_payload
        models = etl_instance.transform([raw])

        etl_instance.load(models)

        latest = tmp_path / "bdns_convocatorias_latest.json"
        assert latest.exists()
        items = json.loads(latest.read_text(encoding="utf-8"))
        assert len(items) == 1
        assert items[0]["bdns_id"] == "926783"
        assert items[0]["raw_ref"] == "bdns:926783"
        assert items[0]["deadline_date"] == "2026-12-31"
        assert items[0]["amounts"]["total_budget"] == pytest.approx(2400.76)

        stamped = list(tmp_path.glob("bdns_convocatorias_2*.json"))
        assert len(stamped) == 1

        stats = json.loads((tmp_path / "bdns_convocatorias_stats_latest.json").read_text(encoding="utf-8"))
        assert stats["total_convocatorias"] == 1
        assert stats["enriched_with_details"] == 1
        assert stats["with_deadline"] == 1
        assert stats["with_budget"] == 1

    def test_load_empty_writes_nothing(self, etl_instance, tmp_path):
        etl_instance.output_dir = tmp_path
        etl_instance.load([])
        assert not (tmp_path / "bdns_convocatorias_latest.json").exists()


if __name__ == "__main__":
    pytest.main([__file__])
