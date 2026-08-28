"""BDNS (SNPSAP) convocatorias ETL — recent calls with real dates and amounts.

Uses the public, keyless SNPSAP API that powers the BDNS transversal portal
(https://www.pap.hacienda.gob.es/bdnstrans), documented in its OpenAPI spec
(``/bdnstrans/estaticos/doc/snpsap-api.json`` — "API de SNPSAP"). This fixes
spec 09 issue A1: the scraped sources never fill ``closing_date``/``amount``,
while BDNS records carry real application deadlines and budgets.

Pipeline (probe-verified 2026-08-28):

1. ``GET /bdnstrans/api/convocatorias/busqueda`` — convocatorias registered in
   the last N days, newest first (query dates use Spanish ``dd/MM/yyyy``).
2. ``GET /bdnstrans/api/convocatorias?numConv=...`` — per-call detail with
   ``fechaFinSolicitud`` (deadline), ``presupuestoTotal`` (budget), ``organo``,
   ``regiones`` and ``tiposBeneficiarios``. Rate-limited and capped to stay
   polite with the government endpoint.
3. Normalized items are persisted to
   ``data/spanish_public_aid/output/bdns_convocatorias_latest.json``.
"""

import json
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests
from pydantic import BaseModel, Field

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.base import BaseETL

# --- API endpoints (SNPSAP v-public, keyless) ---
BDNS_API_BASE = "https://www.pap.hacienda.gob.es/bdnstrans/api"
BDNS_SEARCH_URL = f"{BDNS_API_BASE}/convocatorias/busqueda"
BDNS_DETAIL_URL = f"{BDNS_API_BASE}/convocatorias"

# Public portal page for a single convocatoria (used as the item URL).
BDNS_PORTAL_URL_TEMPLATE = "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/bdnstrans/convocatorias/{bdns_id}"

# --- Politeness / volume knobs (keep runs small: max ~27 requests per run) ---
BDNS_PAGE_SIZE = 50
BDNS_MAX_PAGES = 2  # → up to 100 convocatorias per run
BDNS_DAYS_LOOKBACK = 14
BDNS_MAX_DETAILS = 25  # per-call detail enrichments, newest first
BDNS_PAGE_DELAY_SECONDS = 1.5
BDNS_DETAIL_DELAY_SECONDS = 1.0
BDNS_TIMEOUT_SECONDS = 30


class BdnsAmountsModel(BaseModel):
    """Amount information extracted from a BDNS convocatoria."""

    total_budget: float | None = Field(default=None, description="Presupuesto total de la convocatoria (EUR)")
    currency: str = Field(default="EUR", description="Currency code")


class BdnsConvocatoriaModel(BaseModel):
    """Normalized BDNS convocatoria (spec 09 M1 shape)."""

    bdns_id: str = Field(description="BDNS code (numeroConvocatoria / codigoBDNS)")
    title: str = Field(description="Convocatoria title")
    url: str = Field(description="Public BDNS portal URL for the convocatoria")
    org: str = Field(default="", description="Convocating body (organo nivel3)")
    org_level: str = Field(default="", description="Administration level (ESTATAL, LOCAL, ...)")
    scope: str = Field(default="", description="Territorial scope (regiones de impacto)")
    registered_date: date | None = Field(default=None, description="fechaRecepcion")
    opening_date: date | None = Field(default=None, description="fechaInicioSolicitud")
    deadline_date: date | None = Field(default=None, description="fechaFinSolicitud (plazo)")
    open_ended: bool = Field(default=False, description="abierto: solicitable indefinidamente")
    amounts: BdnsAmountsModel = Field(default_factory=BdnsAmountsModel, description="Amounts")
    beneficiaries: list[str] = Field(default_factory=list, description="tiposBeneficiarios")
    finalidad: str = Field(default="", description="Spending policy purpose")
    bases_url: str = Field(default="", description="URL of the reguladoras bases")
    enriched: bool = Field(default=False, description="Whether the detail endpoint was fetched")
    raw_ref: str = Field(default="", description="Stable raw reference, e.g. 'bdns:926783'")


def parse_bdns_date(value: Any) -> date | None:
    """Parse a BDNS date string tolerantly.

    The API returns ISO ``yyyy-MM-dd`` dates in payloads but expects Spanish
    ``dd/MM/yyyy`` in query parameters; both are accepted here, and anything
    unusable (None, empty, garbage) yields ``None`` instead of raising.

    Args:
        value: Raw date value from the API.

    Returns:
        Parsed date, or None when missing/unparsable.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class BdnsConvocatoriasETL(BaseETL[dict[str, Any], BdnsConvocatoriaModel]):
    """ETL fetching the most recent BDNS convocatorias via the public SNPSAP API."""

    def __init__(self):
        """Initialize the ETL against the shared spanish_public_aid output dir."""
        super().__init__(
            name="spanish_public_aid",
            description="ETL fetching recent BDNS convocatorias (fees, deadlines, amounts) via the public SNPSAP API",
            batch_size=BDNS_PAGE_SIZE,
            enable_checkpointing=False,
            max_retries=2,
            retry_delay=10,
        )

        self.config = self.settings.spanish_public_aid
        # Cap items with the shared per-source limit (default 100).
        self.max_items = min(getattr(self.config, "max_aids_per_source", 100), BDNS_PAGE_SIZE * BDNS_MAX_PAGES)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": SCRAPER_DEFAULT_USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Referer": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/bdnstrans/convocatorias",
            }
        )

    # --- Extract ---

    def _build_search_params(self, page: int) -> dict[str, Any]:
        """Build query params for the convocatorias search endpoint.

        Args:
            page: 1-based page number.

        Returns:
            Query parameters (dates in Spanish dd/MM/yyyy as the API requires).
        """
        fecha_desde = (date.today() - timedelta(days=BDNS_DAYS_LOOKBACK)).strftime("%d/%m/%Y")
        return {
            "page": page,
            "pageSize": BDNS_PAGE_SIZE,
            "order": "fechaRecepcion",
            "direccion": "desc",  # codespell:ignore -- BDNS API query param (Spanish, verified live)
            "fechaDesde": fecha_desde,
            "vpd": "GE",
        }

    def _fetch_search_page(self, page: int) -> dict[str, Any]:
        """Fetch one search page and validate the envelope.

        Args:
            page: 1-based page number.

        Returns:
            Parsed JSON envelope (dict with 'content').

        Raises:
            ValueError: When the response is not a valid search envelope.
        """
        response = self.session.get(BDNS_SEARCH_URL, params=self._build_search_params(page), timeout=BDNS_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
            raise ValueError(f"Unexpected BDNS search payload shape: {type(payload).__name__}")
        return payload

    def extract(self) -> list[dict[str, Any]]:
        """Extract recent convocatorias (last 14 days, newest first) + capped details.

        Returns:
            Raw items: list-entry dicts plus an '_detail' key when enriched.
        """
        self.logger.info("Starting BDNS convocatorias extraction (lookback %s days)", BDNS_DAYS_LOOKBACK)
        raw_items: list[dict[str, Any]] = []

        for page in range(1, BDNS_MAX_PAGES + 1):
            try:
                payload = self._fetch_search_page(page)
            except Exception as e:
                self.logger.error("BDNS search page %s failed: %s", page, e)
                self.metrics.error_count += 1
                break

            content = payload["content"]
            raw_items.extend(content)
            self.logger.info("BDNS search page %s: %s items (totalElements=%s)", page, len(content), payload.get("totalElements"))

            if len(raw_items) >= self.max_items or payload.get("last") or not content:
                break
            time.sleep(BDNS_PAGE_DELAY_SECONDS)

        raw_items = raw_items[: self.max_items]

        # Enrich the newest items with per-call details (deadline, budget, scope).
        enriched = 0
        for item in raw_items[:BDNS_MAX_DETAILS]:
            num_conv = str(item.get("numeroConvocatoria") or "").strip()
            if not num_conv:
                item["_detail"] = None
                continue
            if enriched > 0:
                time.sleep(BDNS_DETAIL_DELAY_SECONDS)
            try:
                detail_response = self.session.get(BDNS_DETAIL_URL, params={"numConv": num_conv, "vpd": "GE"}, timeout=BDNS_TIMEOUT_SECONDS)
                detail_response.raise_for_status()
                detail = detail_response.json()
                item["_detail"] = detail if isinstance(detail, dict) else None
                enriched += 1
            except Exception as e:
                self.logger.warning("BDNS detail fetch failed for %s: %s", num_conv, e)
                item["_detail"] = None

        self.logger.info("Extracted %s BDNS convocatorias (%s enriched with details)", len(raw_items), enriched)
        return raw_items

    # --- Transform ---

    def _normalize_item(self, raw: dict[str, Any]) -> BdnsConvocatoriaModel | None:
        """Normalize one raw item (+optional detail) into the output model.

        Args:
            raw: List-entry dict with an '_detail' key (dict or None).

        Returns:
            Validated model, or None when title/BDNS id are missing.
        """
        detail = raw.get("_detail") or {}
        title = str(detail.get("descripcion") or raw.get("descripcion") or "").strip()
        bdns_id = str(detail.get("codigoBDNS") or raw.get("numeroConvocatoria") or "").strip()
        if not title or not bdns_id:
            return None

        raw_organo = detail.get("organo")
        organo: dict[str, Any] = raw_organo if isinstance(raw_organo, dict) else {}
        org = str(organo.get("nivel3") or raw.get("nivel3") or organo.get("nivel2") or raw.get("nivel2") or "").strip()
        org_level = str(organo.get("nivel1") or raw.get("nivel1") or "").strip()

        regiones = [str(r.get("descripcion")).strip() for r in (detail.get("regiones") or []) if isinstance(r, dict) and r.get("descripcion")]
        scope = "; ".join(regiones) if regiones else org_level

        budget = detail.get("presupuestoTotal")
        amounts = BdnsAmountsModel(total_budget=float(budget) if isinstance(budget, (int, float)) else None)

        beneficiaries = [str(b.get("descripcion")).strip() for b in (detail.get("tiposBeneficiarios") or []) if isinstance(b, dict) and b.get("descripcion")]

        return BdnsConvocatoriaModel(
            bdns_id=bdns_id,
            title=title,
            url=BDNS_PORTAL_URL_TEMPLATE.format(bdns_id=bdns_id),
            org=org,
            org_level=org_level,
            scope=scope,
            registered_date=parse_bdns_date(detail.get("fechaRecepcion") or raw.get("fechaRecepcion")),
            opening_date=parse_bdns_date(detail.get("fechaInicioSolicitud")),
            deadline_date=parse_bdns_date(detail.get("fechaFinSolicitud")),
            open_ended=bool(detail.get("abierto")),
            amounts=amounts,
            beneficiaries=beneficiaries,
            finalidad=str(detail.get("descripcionFinalidad") or "").strip(),
            bases_url=str(detail.get("urlBasesReguladoras") or "").strip(),
            enriched=bool(detail),
            raw_ref=f"bdns:{bdns_id}",
        )

    def transform(self, data: list[dict[str, Any]]) -> list[BdnsConvocatoriaModel]:
        """Normalize raw extracted items, newest first, dropping unusable ones.

        Args:
            data: Raw items from extract().

        Returns:
            List of validated BdnsConvocatoriaModel instances.
        """
        models: list[BdnsConvocatoriaModel] = []
        skipped = 0
        for raw in data:
            model = self._normalize_item(raw)
            if model is None:
                skipped += 1
                continue
            models.append(model)

        # Defensive re-sort by registration date (newest first), API-order tolerant.
        models.sort(key=lambda m: m.registered_date or date.min, reverse=True)

        if skipped:
            self.logger.warning("Skipped %s BDNS items without title/BDNS id", skipped)
        self.logger.info("Normalized %s BDNS convocatorias", len(models))
        return models

    # --- Load ---

    def load(self, data: list[BdnsConvocatoriaModel]) -> None:
        """Persist normalized convocatorias to timestamped + latest JSON files.

        Args:
            data: Validated models from transform().
        """
        if not data:
            self.logger.info("No BDNS data to load")
            return

        json_items = [model.model_dump(mode="json") for model in data]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        stamped_file = self.output_dir / f"bdns_convocatorias_{timestamp}.json"
        latest_file = self.output_dir / "bdns_convocatorias_latest.json"
        for target in (stamped_file, latest_file):
            with open(target, "w", encoding="utf-8") as f:
                json.dump(json_items, f, ensure_ascii=False, indent=2)
        self.logger.info("Saved %s BDNS convocatorias to %s", len(data), latest_file)

        stats = {
            "component": "bdns_convocatorias",
            "total_convocatorias": len(data),
            "enriched_with_details": sum(1 for m in data if m.enriched),
            "with_deadline": sum(1 for m in data if m.deadline_date),
            "with_budget": sum(1 for m in data if m.amounts.total_budget is not None),
            "lookback_days": BDNS_DAYS_LOOKBACK,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        stats_file = self.output_dir / "bdns_convocatorias_stats_latest.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        self.logger.info("Saved BDNS stats to %s", stats_file)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    runner = BdnsConvocatoriasETL()
    run_metrics = runner.run()
    print(run_metrics.model_dump_json(indent=2))
