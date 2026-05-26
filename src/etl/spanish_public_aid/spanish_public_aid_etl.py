"""Spanish Public Aid ETL system for scraping public aid convocations."""

import json
import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

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


class SpanishPublicAidETL(SimpleETL):
    """ETL process for Spanish public aid convocations."""

    def __init__(self):
        super().__init__(
            name="spanish_public_aid",
            description="ETL process for scraping Spanish public aid convocations",
            batch_size=20,
            enable_checkpointing=True,
            max_retries=3,
            retry_delay=10,
        )

        # Get configuration
        self.config = self.settings.spanish_public_aid

        # Sources configuration with updated working URLs
        self.sources = {
            "bdns": {
                "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/inicio",
                "name": "Base de Datos Nacional de Subvenciones",
                "scope": AidScope.NATIONAL,
                "enabled": self._is_source_enabled("bdns"),
            },
            "gva": {
                "url": "https://www.gva.es/es/inicio/procedimientos",
                "search_url": "https://www.gva.es/es/inicio/procedimientos",  # Updated working URL
                "name": "Generalitat Valenciana",
                "scope": AidScope.AUTONOMOUS_COMMUNITY,
                "enabled": self._is_source_enabled("gva"),
            },
            "dogv": {
                "url": "https://dogv.gva.es/es/resultats-temes?interestTheme=grants",
                "name": "Diari Oficial de la Generalitat Valenciana (DOGV)",
                "scope": AidScope.AUTONOMOUS_COMMUNITY,
                "enabled": self._is_source_enabled("dogv"),
            },
            "valencia": {
                "url": "https://www.valencia.es/cas/tramites/tramites-subvenciones",
                "name": "Ayuntamiento de Valencia",
                "scope": AidScope.LOCAL,
                "enabled": self._is_source_enabled("valencia"),
            },
            "burjassot": {
                "url": "https://transparencia.burjassot.org/contrataciones-convenios-y-subvenciones/subvenciones-y-ayudas/subvenciones-y-ayudas-ano-2025/",
                "fallback_urls": [
                    "https://www.burjassot.org/tag/ayudas/",
                    "https://www.burjassot.org/servicios-sociales/prestaciones-becas-y-ayudas/",
                ],
                "name": "Ajuntament de Burjassot",
                "scope": AidScope.LOCAL,
                "enabled": self._is_source_enabled("burjassot"),
            },
            "labora": {
                "url": "https://labora.gva.es/es/empreses/busque-ajudes-subvencions/ajudes-foment-de-l-ocupacio-2025",
                "name": "LABORA - Servicio Valenciano de Empleo",
                "scope": AidScope.AUTONOMOUS_COMMUNITY,
                "enabled": self._is_source_enabled("labora"),
            },
        }

        # Headers for requests
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _is_source_enabled(self, source_key: str) -> bool:
        """Return whether a source is enabled by the allow-list and source flag."""
        enabled_sources = set(getattr(self.config, "enabled_sources", []) or [])
        source_flag = getattr(self.config, f"{source_key}_enabled", True)
        return source_key in enabled_sources and source_flag

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from all configured sources."""
        self.logger.info("Starting Spanish public aid data extraction")
        all_extracted_data = []

        for source_key, source_config in self.sources.items():
            if not source_config.get("enabled", True):
                self.logger.info(f"Skipping disabled source: {source_key}")
                continue

            self.logger.info(f"Extracting from source: {source_config['name']}")

            try:
                source_data = self._extract_from_source(source_key, source_config)
                self.logger.info(f"Extracted {len(source_data)} items from {source_key}")
                all_extracted_data.extend(source_data)

                # Respectful delay between sources
                time.sleep(self.config.request_delay_seconds)

            except Exception as e:
                self.logger.error(f"Error extracting from {source_key}: {e}")
                self.metrics.error_count += 1
                continue

        self.logger.info(f"Total extracted items: {len(all_extracted_data)}")
        return all_extracted_data

    def _extract_from_source(self, source_key: str, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract data from a specific source."""
        if source_key == "bdns":
            return self._extract_from_bdns(source_config)
        elif source_key == "gva":
            return self._extract_from_gva(source_config)
        elif source_key == "dogv":
            return self._extract_from_dogv(source_config)
        elif source_key == "valencia":
            return self._extract_from_valencia(source_config)
        elif source_key == "burjassot":
            return self._extract_from_burjassot(source_config)
        elif source_key == "labora":
            return self._extract_from_labora(source_config)
        else:
            self.logger.warning(f"Unknown source: {source_key}")
            return []

    def _extract_from_bdns(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from Base de Datos Nacional de Subvenciones."""
        extracted_data = []

        try:
            # Try the main BDNS portal
            main_url = source_config["url"]

            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for various possible aid/subsidy elements
            aid_elements = (
                soup.find_all(
                    "div",
                    class_=re.compile(r".*convocatoria.*|.*ayuda.*|.*subvencion.*", re.I),
                )
                or soup.find_all(
                    "li",
                    class_=re.compile(r".*convocatoria.*|.*ayuda.*|.*subvencion.*", re.I),
                )
                or soup.find_all(
                    "a",
                    href=re.compile(r".*convocatoria.*|.*ayuda.*|.*subvencion.*", re.I),
                )
                or soup.find_all("div", attrs={"data-type": re.compile(r".*grant.*|.*aid.*", re.I)})
                or soup.find_all("article")
                or soup.find_all("div", class_=re.compile(r".*item.*|.*entry.*|.*post.*", re.I))
            )

            self.logger.info(f"Found {len(aid_elements)} potential aid elements in BDNS")

            for element in aid_elements[: self.config.max_aids_per_source]:  # Configurable limit
                try:
                    aid_data = self._parse_bdns_aid(element, source_config)
                    if aid_data and aid_data.get("title"):
                        extracted_data.append(aid_data)
                except Exception as e:
                    self.logger.debug(f"Error parsing BDNS aid element: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting from BDNS: {e}")

        return extracted_data

    def _extract_from_gva(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from Generalitat Valenciana."""
        extracted_data = []

        try:
            # Search for aid listings in GVA using working URLs
            search_urls = [
                "https://dadesobertes.gva.es/es/dataset/eco-gvo-subv-2025",  # Open data subsidies
                "https://www.gva.es/es/inicio/procedimientos",  # Main procedures page (updated working URL)
                "https://sede.gva.es/es/procedimientos",  # Alternative procedures URL
            ]

            for url in search_urls:
                try:
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, "html.parser")

                    # Find aid listings with more flexible selectors
                    aid_elements = (
                        soup.find_all(
                            ["div", "article", "li"],
                            class_=re.compile(r".*ayuda.*|.*subven.*|.*procedure.*|.*dataset.*", re.I),
                        )
                        or soup.find_all(
                            "a",
                            href=re.compile(r".*ayuda.*|.*subven.*|.*procedimiento.*", re.I),
                        )
                        or soup.find_all("h3")  # Often titles are in h3 tags
                        or soup.find_all(
                            ["div", "article"],
                            attrs={"data-type": re.compile(r".*grant.*|.*aid.*", re.I)},
                        )
                    )

                    self.logger.info(f"Found {len(aid_elements)} potential aid elements in GVA from {url}")

                    for element in aid_elements[: self.config.max_aids_per_source]:  # Configurable limit
                        try:
                            aid_data = self._parse_gva_aid(element, source_config)
                            if aid_data and aid_data.get("title"):
                                extracted_data.append(aid_data)
                        except Exception as e:
                            self.logger.debug(f"Error parsing GVA aid element: {e}")
                            continue

                except Exception as e:
                    self.logger.warning(f"Error fetching from GVA URL {url}: {e}")
                    self.logger.info("Continuing with next URL...")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting from GVA: {e}")

        return extracted_data

    def _extract_from_dogv(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract aid notices from DOGV's grants topic page."""
        return self._extract_links_from_urls(
            [source_config["url"]],
            source_config,
            organizing_entity="Generalitat Valenciana",
        )

    def _extract_from_valencia(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from Ayuntamiento de Valencia."""
        extracted_data = []

        try:
            # Valencia city council aids using the working URL
            main_url = source_config["url"]  # https://www.valencia.es/cas/tramites/tramites-subvenciones

            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Find aid listings - look for links in the subsidies section
            aid_links = soup.find_all("a", href=True)

            # Filter for actual subsidy-related links with better criteria
            subsidy_links = []
            for link in aid_links:
                text = link.get_text(strip=True)
                # Skip if too short or generic
                if len(text) < 15:
                    continue

                # Check if it looks like a specific subsidy/aid (not just "Subvenciones")
                if (
                    any(
                        keyword in text.lower()
                        for keyword in [
                            "ayuda",
                            "subven",
                            "beca",
                            "fomento",
                            "2025",
                            "apoyo",
                            "convocatoria",
                        ]
                    )
                    and text.lower().strip() not in ["subvenciones", "ayudas", "tramites"]
                    and len(text) > 20
                ):  # Must be descriptive
                    subsidy_links.append(link)

            self.logger.info(f"Found {len(subsidy_links)} specific aid links in Valencia")

            for link in subsidy_links[: self.config.max_aids_per_source]:  # Configurable limit
                try:
                    # Get the detailed page for better data
                    aid_data = self._parse_valencia_aid_detailed(link, source_config)
                    if aid_data and aid_data.get("title") and len(aid_data["title"]) > 20:
                        extracted_data.append(aid_data)
                except Exception as e:
                    self.logger.debug(f"Error parsing Valencia aid link: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting from Valencia: {e}")

        return extracted_data

    def _extract_from_burjassot(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract local Burjassot aid calls from transparency and news pages."""
        urls = [source_config["url"], *source_config.get("fallback_urls", [])]
        return self._extract_links_from_urls(
            urls,
            source_config,
            organizing_entity="Ajuntament de Burjassot",
            municipality="Burjassot",
        )

    def _extract_links_from_urls(
        self,
        urls: list[str],
        source_config: dict[str, Any],
        organizing_entity: str,
        municipality: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract subsidy-like links from one or more listing pages."""
        extracted_data = []
        seen_urls = set()
        keywords = [
            "ayuda",
            "ayudas",
            "subven",
            "beca",
            "becas",
            "convocatoria",
            "prestaciones",
            "premios",
            "fomento",
            "financiación",
        ]

        for url in urls:
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")

                aid_links = []
                for link in soup.find_all("a", href=True):
                    if not isinstance(link, Tag):
                        continue
                    text = " ".join(link.get_text(" ", strip=True).split())
                    if len(text) < 15:
                        continue
                    if not any(keyword in text.lower() for keyword in keywords):
                        continue

                    href = str(link["href"])
                    full_url = urljoin(url, href)
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    aid_links.append((text, full_url, link))

                self.logger.info(f"Found {len(aid_links)} aid-like links in {source_config['name']} from {url}")

                for title_text, full_url, link in aid_links[: self.config.max_aids_per_source]:
                    description = self._extract_detail_description(full_url)
                    extracted_data.append(
                        {
                            "title": title_text,
                            "description": description,
                            "source_url": full_url,
                            "source_name": source_config["name"],
                            "source_scope": source_config["scope"],
                            "organizing_entity": organizing_entity,
                            "municipality": municipality,
                            "raw_element": str(link)[:1000],
                        }
                    )
            except Exception as e:
                self.logger.warning(f"Error fetching {source_config['name']} URL {url}: {e}")
                continue

        return extracted_data

    def _extract_detail_description(self, url: str) -> str:
        """Best-effort extraction of a short description from a detail page."""
        try:
            detail_response = self.session.get(url, timeout=15)
            if detail_response.status_code != 200:
                return ""

            detail_soup = BeautifulSoup(detail_response.content, "html.parser")
            desc_elem = (
                detail_soup.find("meta", attrs={"name": "description"})
                or detail_soup.find(["p", "div"], class_=re.compile(r".*desc.*|.*resumen.*|.*content.*|.*entry.*", re.I))
                or detail_soup.find(["p", "div"], string=re.compile(r".{50,}", re.I))
            )
            if not isinstance(desc_elem, Tag):
                return ""
            if desc_elem.name == "meta":
                content = desc_elem.get("content", "")
                return str(content)[:500]
            return desc_elem.get_text(" ", strip=True)[:500]
        except Exception:
            return ""

    def _extract_from_labora(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from LABORA."""
        extracted_data = []

        try:
            # LABORA employment programs using the working 2025 URL
            main_url = source_config["url"]  # https://labora.gva.es/es/empreses/busque-ajudes-subvencions/ajudes-foment-de-l-ocupacio-2025

            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for specific aid links with detailed titles
            aid_links = soup.find_all("a", href=True)

            # Filter for employment-related aid links
            employment_links = []
            for link in aid_links:
                text = link.get_text(strip=True)
                # Skip if too short or generic
                if len(text) < 20:
                    continue

                # Check if it looks like a specific employment aid
                if any(
                    keyword in text.lower()
                    for keyword in [
                        "empleo",
                        "contratación",
                        "formación",
                        "laboral",
                        "trabajo",
                        "desempleo",
                        "fomento",
                        "incentivo",
                        "beca",
                        "ayuda",
                        "subven",
                    ]
                ) and text.lower().strip() not in [
                    "busco ayudas - subvenciones",
                    "ayudas",
                    "subvenciones",
                ]:
                    employment_links.append(link)

            self.logger.info(f"Found {len(employment_links)} specific employment aid links in LABORA")

            for link in employment_links[: self.config.max_aids_per_source]:  # Configurable limit
                try:
                    # Get detailed data from the link
                    aid_data = self._parse_labora_aid_detailed(link, source_config)
                    if aid_data and aid_data.get("title") and len(aid_data["title"]) > 20:
                        extracted_data.append(aid_data)
                except Exception as e:
                    self.logger.debug(f"Error parsing LABORA aid link: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting from LABORA: {e}")

        return extracted_data

    def _parse_bdns_aid(self, element: BeautifulSoup, source_config: dict[str, Any]) -> dict[str, Any] | None:
        """Parse BDNS aid element."""
        try:
            # More flexible title extraction
            title_elem = (
                element.find(["h2", "h3", "h4"], class_=re.compile(r".*titulo.*|.*title.*", re.I))
                or element.find("a", href=True)
                or element.find(["span", "div"], class_=re.compile(r".*name.*|.*title.*", re.I))
                or element
            )

            title_text = title_elem.get_text(strip=True) if title_elem else ""

            # Skip if title is too short or doesn't look like a subsidy
            if len(title_text) < 10 or not any(
                keyword in title_text.lower()
                for keyword in [
                    "ayuda",
                    "subven",
                    "beca",
                    "fomento",
                    "apoyo",
                    "grant",
                    "aid",
                ]
            ):
                return None

            # More flexible description extraction
            description_elem = (
                element.find(
                    ["p", "div"],
                    class_=re.compile(r".*desc.*|.*resumen.*|.*content.*", re.I),
                )
                or element.find_next_sibling(["p", "div"])
                or element.parent.find(["p", "div"])
                if element.parent
                else None
            )

            description = description_elem.get_text(strip=True) if description_elem else ""

            # Extract link
            link_elem = element.find("a", href=True) or element if element.name == "a" else None
            link = urljoin(source_config["url"], link_elem["href"]) if link_elem and link_elem.get("href") else source_config["url"]

            return {
                "title": title_text,
                "description": description,
                "source_url": link,
                "source_name": source_config["name"],
                "source_scope": source_config["scope"],
                "organizing_entity": "Administración General del Estado",
                "raw_element": str(element)[:1000],  # Store limited raw HTML for debugging
            }

        except Exception as e:
            self.logger.debug(f"Error parsing BDNS element: {e}")
            return None

    def _parse_gva_aid(self, element: BeautifulSoup, source_config: dict[str, Any]) -> dict[str, Any] | None:
        """Parse GVA aid element."""
        try:
            # More flexible title extraction for GVA
            title_elem = (
                element.find(["h2", "h3", "h4"], class_=re.compile(r".*titulo.*|.*title.*", re.I))
                or element.find("a", href=True)
                or element.find(["span", "div"], class_=re.compile(r".*name.*|.*title.*", re.I))
                or element
            )

            title_text = title_elem.get_text(strip=True) if title_elem else ""

            # Skip if title is too short or doesn't look like a subsidy
            if len(title_text) < 10 or not any(
                keyword in title_text.lower()
                for keyword in [
                    "ayuda",
                    "subven",
                    "beca",
                    "fomento",
                    "apoyo",
                    "procedimiento",
                    "grant",
                    "aid",
                    "2025",
                ]
            ):
                return None

            # More flexible description extraction
            description_elem = (
                element.find(
                    ["p", "div"],
                    class_=re.compile(r".*desc.*|.*resumen.*|.*content.*", re.I),
                )
                or element.find_next_sibling(["p", "div"])
                or element.parent.find(["p", "div"])
                if element.parent
                else None
            )

            description = description_elem.get_text(strip=True) if description_elem else ""

            # Extract link
            link_elem = element.find("a", href=True) or element if element.name == "a" else None
            link = urljoin("https://www.gva.es", link_elem["href"]) if link_elem and link_elem.get("href") else source_config["url"]

            return {
                "title": title_text,
                "description": description,
                "source_url": link,
                "source_name": source_config["name"],
                "source_scope": source_config["scope"],
                "organizing_entity": "Generalitat Valenciana",
                "raw_element": str(element)[:1000],
            }

        except Exception as e:
            self.logger.debug(f"Error parsing GVA element: {e}")
            return None

    def _parse_valencia_aid(self, element: BeautifulSoup, source_config: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Valencia city aid element."""
        try:
            # More flexible title extraction for Valencia
            title_elem = element.find(["h2", "h3", "h4"]) or element if element.name == "a" else element.find("a", href=True) or element.find(["span", "div"])

            title_text = title_elem.get_text(strip=True) if title_elem else ""

            # Skip if title is too short or doesn't look like a subsidy
            if len(title_text) < 10 or not any(
                keyword in title_text.lower()
                for keyword in [
                    "ayuda",
                    "subven",
                    "beca",
                    "fomento",
                    "apoyo",
                    "grant",
                    "aid",
                    "2025",
                    "municipal",
                ]
            ):
                return None

            # More flexible description extraction
            description_elem = (
                element.find(
                    ["p", "div"],
                    class_=re.compile(r".*desc.*|.*resumen.*|.*content.*", re.I),
                )
                or element.find_next_sibling(["p", "div"])
                or element.parent.find(["p", "div"])
                if element.parent
                else None
            )

            description = description_elem.get_text(strip=True) if description_elem else ""

            # Extract link
            link_elem = element.find("a", href=True) or element if element.name == "a" else None
            link = urljoin("https://www.valencia.es", link_elem["href"]) if link_elem and link_elem.get("href") else source_config["url"]

            return {
                "title": title_text,
                "description": description,
                "source_url": link,
                "source_name": source_config["name"],
                "source_scope": source_config["scope"],
                "organizing_entity": "Ayuntamiento de Valencia",
                "raw_element": str(element)[:1000],
            }

        except Exception as e:
            self.logger.debug(f"Error parsing Valencia element: {e}")
            return None

    def _parse_labora_aid(self, element: BeautifulSoup, source_config: dict[str, Any]) -> dict[str, Any] | None:
        """Parse LABORA aid element."""
        try:
            # More flexible title extraction for LABORA
            title_elem = element.find(["h2", "h3", "h4"]) or element if element.name == "a" else element.find("a", href=True) or element.find(["span", "div"], class_=re.compile(r".*title.*|.*name.*", re.I))

            title_text = title_elem.get_text(strip=True) if title_elem else ""

            # Skip if title is too short or doesn't look like an employment aid
            if len(title_text) < 10 or not any(
                keyword in title_text.lower()
                for keyword in [
                    "ayuda",
                    "subven",
                    "empleo",
                    "contratación",
                    "fomento",
                    "beca",
                    "formación",
                    "laboral",
                    "2025",
                ]
            ):
                return None

            # Look for status information (ABIERTO/CERRADO)
            status_text = ""
            status_elem = element.find(string=re.compile(r"ABIERTO|CERRADO|OPEN|CLOSED", re.I))
            if status_elem:
                status_text = f" [{status_elem.strip()}]"

            # More flexible description extraction
            description_elem = (
                element.find(
                    ["p", "div"],
                    class_=re.compile(r".*desc.*|.*resumen.*|.*content.*", re.I),
                )
                or element.find_next_sibling(["p", "div"])
                or element.parent.find(["p", "div"])
                if element.parent
                else None
            )

            description = description_elem.get_text(strip=True) if description_elem else ""
            description += status_text  # Add status to description

            # Extract link
            link_elem = element.find("a", href=True) or element if element.name == "a" else None
            link = urljoin("https://labora.gva.es", link_elem["href"]) if link_elem and link_elem.get("href") else source_config["url"]

            return {
                "title": title_text,
                "description": description,
                "source_url": link,
                "source_name": source_config["name"],
                "source_scope": source_config["scope"],
                "organizing_entity": "LABORA",
                "raw_element": str(element)[:1000],
            }

        except Exception as e:
            self.logger.debug(f"Error parsing LABORA element: {e}")
            return None

    def _parse_valencia_aid_detailed(self, link_element, source_config: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Valencia aid by following the link for detailed information."""
        try:
            title_text = link_element.get_text(strip=True)
            href = link_element.get("href", "")

            # Build full URL
            if href.startswith("/"):
                full_url = urljoin("https://www.valencia.es", href)
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = urljoin(source_config["url"], href)

            # Try to get more details from the page
            description = ""
            try:
                detail_response = self.session.get(full_url, timeout=15)
                if detail_response.status_code == 200:
                    detail_soup = BeautifulSoup(detail_response.content, "html.parser")

                    # Look for description in common places
                    desc_elem = (
                        detail_soup.find(
                            ["p", "div"],
                            class_=re.compile(r".*desc.*|.*resumen.*|.*content.*", re.I),
                        )
                        or detail_soup.find("meta", attrs={"name": "description"})
                        or detail_soup.find(["p", "div"], string=re.compile(r".{50,}", re.I))  # Long text
                    )

                    if desc_elem:
                        if desc_elem.name == "meta":
                            description = desc_elem.get("content", "")
                        else:
                            description = desc_elem.get_text(strip=True)[:500]  # Limit length
            except Exception:
                pass  # If we can't get details, continue with what we have

            return {
                "title": title_text,
                "description": description,
                "source_url": full_url,
                "source_name": source_config["name"],
                "source_scope": source_config["scope"],
                "organizing_entity": "Ayuntamiento de Valencia",
                "raw_element": str(link_element)[:500],
            }

        except Exception as e:
            self.logger.debug(f"Error parsing Valencia detailed aid: {e}")
            return None

    def _parse_labora_aid_detailed(self, link_element, source_config: dict[str, Any]) -> dict[str, Any] | None:
        """Parse LABORA aid by following the link for detailed information."""
        try:
            title_text = link_element.get_text(strip=True)
            href = link_element.get("href", "")

            # Build full URL
            if href.startswith("/"):
                full_url = urljoin("https://labora.gva.es", href)
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = urljoin(source_config["url"], href)

            # Try to get more details from the page
            description = ""
            status_text = ""
            try:
                detail_response = self.session.get(full_url, timeout=15)
                if detail_response.status_code == 200:
                    detail_soup = BeautifulSoup(detail_response.content, "html.parser")

                    # Look for description
                    desc_elem = (
                        detail_soup.find(
                            ["p", "div"],
                            class_=re.compile(r".*desc.*|.*resumen.*|.*content.*", re.I),
                        )
                        or detail_soup.find("meta", attrs={"name": "description"})
                        or detail_soup.find(["p", "div"], string=re.compile(r".{50,}", re.I))
                    )

                    if desc_elem:
                        if desc_elem.name == "meta":
                            description = desc_elem.get("content", "")
                        else:
                            description = desc_elem.get_text(strip=True)[:500]

                    # Look for status
                    status_elem = detail_soup.find(string=re.compile(r"ABIERTO|CERRADO|OPEN|CLOSED", re.I))
                    if status_elem:
                        status_text = f" [{status_elem.strip()}]"
            except Exception:
                pass

            return {
                "title": title_text,
                "description": description + status_text,
                "source_url": full_url,
                "source_name": source_config["name"],
                "source_scope": source_config["scope"],
                "organizing_entity": "LABORA",
                "raw_element": str(link_element)[:500],
            }

        except Exception as e:
            self.logger.debug(f"Error parsing LABORA detailed aid: {e}")
            return None

    def transform(self, data: list[dict[str, Any]]) -> list[SpanishPublicAidModel]:
        """Transform extracted data into SpanishPublicAidModel objects."""
        self.logger.info(f"Starting transformation of {len(data)} raw items")

        transformed_models = []
        failed_count = 0

        for item_data in data:
            try:
                # Enhanced data for model creation
                enhanced_data = self._enhance_aid_data(item_data)

                if not enhanced_data.get("title"):
                    self.logger.warning(f"Skipping item due to missing title: {item_data.get('source_url', 'Unknown URL')}")
                    failed_count += 1
                    continue

                # Check quality threshold
                if enhanced_data.get("data_quality_score", 0) < self.config.data_quality_threshold:
                    self.logger.debug(f"Skipping item due to low quality score: {enhanced_data['data_quality_score']:.2f}")
                    failed_count += 1
                    continue

                model_instance = SpanishPublicAidModel(**enhanced_data)
                transformed_models.append(model_instance)

            except ValidationError as e:
                failed_count += 1
                self.logger.error(f"Validation error transforming item: {item_data.get('source_url', 'Unknown item')}")
                self.logger.debug(f"Pydantic errors: {e.errors()}")

            except Exception as e:
                failed_count += 1
                self.logger.error(f"Unexpected error transforming item: {item_data.get('source_url', 'Unknown item')}: {e}")

        self.logger.info(f"Successfully transformed {len(transformed_models)} items")
        if failed_count > 0:
            self.logger.warning(f"{failed_count} items failed validation or transformation")

        return transformed_models

    def _enhance_aid_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Enhance raw data with additional fields required by the model."""
        # Determine aid type based on title and description
        aid_type = self._determine_aid_type(raw_data.get("title", ""), raw_data.get("description", ""))

        # Determine category
        category = self._determine_category(raw_data.get("title", ""), raw_data.get("description", ""))

        # Create geographic scope
        scope = GeographicScopeModel(
            scope=raw_data.get("source_scope", AidScope.NATIONAL),
            autonomous_community=("Comunitat Valenciana" if raw_data.get("source_scope") == AidScope.AUTONOMOUS_COMMUNITY else None),
            municipality=(raw_data.get("municipality") or ("Valencia" if raw_data.get("source_scope") == AidScope.LOCAL else None)),
        )

        # Create amount model with default values
        amount = AmountModel(
            payment_type=PaymentType.LUMP_SUM,
            currency="EUR",  # Default value
        )

        # Determine status
        status = self._determine_status(raw_data.get("title", ""), raw_data.get("description", ""))

        # Determine beneficiary type
        beneficiary_type = self._determine_beneficiary_type(raw_data.get("title", ""), raw_data.get("description", ""))

        enhanced_data = {
            "title": raw_data.get("title", ""),
            "description": raw_data.get("description", ""),
            "aid_type": aid_type,
            "category": category,
            "scope": scope,
            "organizing_entity": raw_data.get("organizing_entity", ""),
            "beneficiary_type": beneficiary_type,
            "amount": amount,
            "status": status,
            "source_url": raw_data.get("source_url", ""),
            "source_name": raw_data.get("source_name", ""),
            "scraping_timestamp": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "is_verified": False,
            "data_quality_score": self._calculate_quality_score(raw_data),
            "tags": self._generate_tags(raw_data),
            "keywords": self._generate_keywords(raw_data),
        }

        return enhanced_data

    def _determine_aid_type(self, title: str, description: str) -> AidType:
        """Determine aid type from title and description."""
        text = (title + " " + description).lower()

        if any(word in text for word in ["beca", "becas", "scholarship"]):
            return AidType.SCHOLARSHIP
        elif any(word in text for word in ["prestamo", "préstamo", "credito", "crédito"]):
            return AidType.LOAN
        elif any(word in text for word in ["fiscal", "deduccion", "deducción", "descuento"]):
            return AidType.TAX_BENEFIT
        elif any(word in text for word in ["prestacion", "prestación", "social"]):
            return AidType.SOCIAL_BENEFIT
        elif any(word in text for word in ["pago", "directo", "transferencia"]):
            return AidType.DIRECT_PAYMENT
        elif any(word in text for word in ["subvencion", "subvención"]):
            return AidType.SUBSIDY
        else:
            return AidType.GRANT

    def _determine_category(self, title: str, description: str) -> AidCategory:
        """Determine aid category from title and description."""
        text = (title + " " + description).lower()

        if any(word in text for word in ["vivienda", "alquiler", "hipoteca", "housing"]):
            return AidCategory.HOUSING
        elif any(word in text for word in ["empleo", "trabajo", "desempleo", "employment", "laboral"]):
            return AidCategory.EMPLOYMENT
        elif any(word in text for word in ["educacion", "educación", "formacion", "formación", "estudios"]):
            return AidCategory.EDUCATION
        elif any(word in text for word in ["salud", "sanitario", "medico", "médico", "health"]):
            return AidCategory.HEALTH
        elif any(word in text for word in ["joven", "jovenes", "jóvenes", "youth"]):
            return AidCategory.YOUTH
        elif any(word in text for word in ["mayor", "mayores", "elderly", "tercera edad"]):
            return AidCategory.ELDERLY
        elif any(word in text for word in ["discapacidad", "disability", "diversidad funcional"]):
            return AidCategory.DISABILITY
        elif any(word in text for word in ["familia", "familiar", "family"]):
            return AidCategory.FAMILY
        elif any(word in text for word in ["emergencia", "dana", "emergency"]):
            return AidCategory.EMERGENCY
        elif any(word in text for word in ["empresa", "negocio", "business", "comercio"]):
            return AidCategory.BUSINESS
        elif any(word in text for word in ["cultura", "cultural", "arte", "artistic"]):
            return AidCategory.CULTURE
        elif any(word in text for word in ["ambiente", "ambiental", "environment", "ecologia"]):
            return AidCategory.ENVIRONMENT
        elif any(word in text for word in ["transporte", "transport", "movilidad"]):
            return AidCategory.TRANSPORT
        elif any(word in text for word in ["tecnologia", "tecnología", "technology", "digital"]):
            return AidCategory.TECHNOLOGY
        else:
            return AidCategory.OTHER

    def _determine_status(self, title: str, description: str) -> AidStatus:
        """Determine aid status from title and description."""
        text = (title + " " + description).lower()

        if any(word in text for word in ["cerrada", "closed", "finalizada"]):
            return AidStatus.CLOSED
        elif any(word in text for word in ["evaluacion", "evaluación", "evaluation"]):
            return AidStatus.IN_EVALUATION
        elif any(word in text for word in ["resuelta", "resolved", "concedida"]):
            return AidStatus.RESOLVED
        elif any(word in text for word in ["suspendida", "suspended"]):
            return AidStatus.SUSPENDED
        elif any(word in text for word in ["cancelada", "cancelled"]):
            return AidStatus.CANCELLED
        elif any(word in text for word in ["proxima", "próxima", "upcoming"]):
            return AidStatus.UPCOMING
        else:
            return AidStatus.OPEN  # Default to open

    def _determine_beneficiary_type(self, title: str, description: str) -> BeneficiaryType:
        """Determine beneficiary type from title and description."""
        text = (title + " " + description).lower()

        if any(word in text for word in ["empresa", "empresas", "company", "business"]):
            return BeneficiaryType.COMPANY
        elif any(word in text for word in ["ong", "ngo", "asociacion", "asociación"]):
            return BeneficiaryType.NGO
        elif any(word in text for word in ["ayuntamiento", "entidad publica", "administracion"]):
            return BeneficiaryType.PUBLIC_ENTITY
        elif any(word in text for word in ["universidad", "escuela", "educational"]):
            return BeneficiaryType.EDUCATIONAL_INSTITUTION
        else:
            return BeneficiaryType.INDIVIDUAL  # Default for individuals

    def _generate_tags(self, raw_data: dict[str, Any]) -> list[str]:
        """Generate tags from raw data."""
        tags = []

        # Add source-based tags
        if raw_data.get("source_scope") == AidScope.NATIONAL:
            tags.append("nacional")
        elif raw_data.get("source_scope") == AidScope.AUTONOMOUS_COMMUNITY:
            tags.append("comunidad-valenciana")
        elif raw_data.get("source_scope") == AidScope.LOCAL:
            tags.append("valencia")

        # Add organizing entity tag
        if raw_data.get("organizing_entity"):
            tags.append(raw_data["organizing_entity"].lower().replace(" ", "-"))

        return tags

    def _generate_keywords(self, raw_data: dict[str, Any]) -> list[str]:
        """Generate keywords from title and description."""
        text = (raw_data.get("title", "") + " " + raw_data.get("description", "")).lower()

        # Common keywords to extract
        keyword_patterns = [
            r"\b(ayuda|ayudas)\b",
            r"\b(subvencion|subvención|subvenciones)\b",
            r"\b(beca|becas)\b",
            r"\b(empleo|trabajo|laboral)\b",
            r"\b(vivienda|alquiler)\b",
            r"\b(joven|jovenes|jóvenes)\b",
            r"\b(familia|familiar)\b",
            r"\b(discapacidad)\b",
            r"\b(empresa|empresas)\b",
        ]

        keywords = []
        for pattern in keyword_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)

        return list(set(keywords))  # Remove duplicates

    def _calculate_quality_score(self, raw_data: dict[str, Any]) -> float:
        """Calculate data quality score based on completeness and content quality."""
        score = 0.0
        total_factors = 0

        # Title quality (weight: 0.3)
        if raw_data.get("title"):
            title_len = len(raw_data["title"])
            if title_len > 10:
                score += 0.3
            elif title_len > 5:
                score += 0.15
            total_factors += 0.3

        # Description quality (weight: 0.25)
        if raw_data.get("description"):
            desc_len = len(raw_data["description"])
            if desc_len > 100:
                score += 0.25
            elif desc_len > 50:
                score += 0.15
            elif desc_len > 20:
                score += 0.1
            total_factors += 0.25

        # Source URL quality (weight: 0.2)
        if raw_data.get("source_url"):
            url = raw_data["source_url"]
            if url.startswith("https://"):
                score += 0.2
            elif url.startswith("http://"):
                score += 0.15
            total_factors += 0.2

        # Organizing entity (weight: 0.1)
        if raw_data.get("organizing_entity"):
            score += 0.1
            total_factors += 0.1

        # Source name (weight: 0.1)
        if raw_data.get("source_name"):
            score += 0.1
            total_factors += 0.1

        # Raw element content (weight: 0.05)
        if raw_data.get("raw_element"):
            score += 0.05
            total_factors += 0.05

        # Calculate final score
        final_score = score / total_factors if total_factors > 0 else 0.0
        return min(1.0, max(0.0, final_score))

    def load(self, data: list[SpanishPublicAidModel]) -> None:
        """Load transformed data to JSON files."""
        if not data:
            self.logger.info("No data to load")
            return

        # Convert models to dictionaries for JSON serialization
        json_data = [aid.model_dump() for aid in data]

        # Save main data file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        main_file = self.output_dir / f"spanish_public_aid_{timestamp}.json"

        with open(main_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"Saved {len(data)} aids to {main_file}")

        # Save latest file (overwrite)
        latest_file = self.output_dir / "spanish_public_aid_latest.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

        # Save summary statistics
        stats = self._generate_statistics(data)
        stats_file = self.output_dir / f"spanish_public_aid_stats_{timestamp}.json"

        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"Saved statistics to {stats_file}")

    def _generate_statistics(self, data: list[SpanishPublicAidModel]) -> dict[str, Any]:
        """Generate statistics from the data."""
        if not data:
            return {}

        stats = {
            "total_aids": len(data),
            "active_aids": sum(1 for aid in data if aid.is_active),
            "by_category": {},
            "by_scope": {},
            "by_status": {},
            "by_beneficiary_type": {},
            "closing_soon": sum(1 for aid in data if aid.is_urgent),
            "last_updated": datetime.utcnow().isoformat(),
        }

        # Count by category - handle both enum and string values
        for aid in data:
            category_key = aid.category.value if hasattr(aid.category, "value") else str(aid.category)
            stats["by_category"][category_key] = stats["by_category"].get(category_key, 0) + 1

            scope_key = aid.scope.scope.value if hasattr(aid.scope.scope, "value") else str(aid.scope.scope)
            stats["by_scope"][scope_key] = stats["by_scope"].get(scope_key, 0) + 1

            status_key = aid.status.value if hasattr(aid.status, "value") else str(aid.status)
            stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1

            beneficiary_key = aid.beneficiary_type.value if hasattr(aid.beneficiary_type, "value") else str(aid.beneficiary_type)
            stats["by_beneficiary_type"][beneficiary_key] = stats["by_beneficiary_type"].get(beneficiary_key, 0) + 1

        return stats


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Starting Spanish Public Aid ETL script execution")

    etl_process = SpanishPublicAidETL()
    metrics = etl_process.run()

    logger.info("Spanish Public Aid ETL script finished. Metrics:")
    logger.info(metrics.model_dump_json(indent=2))

    if metrics.is_successful:
        logger.info("ETL completed successfully")
    else:
        logger.error(f"ETL failed with {metrics.error_count} errors")
