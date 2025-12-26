"""Scraping service for Spanish public aid sources."""

import logging
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.models.spanish_public_aid import AidScope


class ScrapingService:
    """Service for scraping Spanish public aid websites."""

    def __init__(self, config: dict[str, Any], request_delay: float = 2.0, debug: bool = False):
        """Initialize scraping service.

        Args:
            config: Source configuration dictionary
            request_delay: Delay between requests in seconds
            debug: Enable debug logging
        """
        self.config = config
        self.request_delay = request_delay
        self.debug = debug

        # Headers for requests
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "es-ES,es;q=0.9",
            "Connection": "keep-alive",
        }

        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def extract_from_source(self, source_key: str, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract data from a specific source.

        Args:
            source_key: Source identifier (bdns, gva, valencia, labora)
            source_config: Source configuration

        Returns:
            List of extracted aid data
        """
        extractors = {
            "bdns": self._extract_from_bdns,
            "gva": self._extract_from_gva,
            "valencia": self._extract_from_valencia,
            "labora": self._extract_from_labora,
        }

        extractor = extractors.get(source_key)
        if extractor:
            return extractor(source_config)

        logging.warning(f"Unknown source: {source_key}")
        return []

    def _extract_from_bdns(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from Base de Datos Nacional de Subvenciones."""
        extracted_data = []

        try:
            main_url = source_config["url"]
            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for aid elements
            aid_elements = (
                soup.find_all("div", class_=re.compile(r".*convocatoria.*|.*ayuda.*|.*subvencion.*", re.I))
                or soup.find_all("li", class_=re.compile(r".*convocatoria.*|.*ayuda.*|.*subvencion.*", re.I))
                or soup.find_all("a", href=re.compile(r".*convocatoria.*|.*ayuda.*|.*subvencion.*", re.I))
                or soup.find_all("article")
                or soup.find_all("div", class_=re.compile(r".*item.*|.*entry.*|.*post.*", re.I))
            )

            logging.info(f"Found {len(aid_elements)} potential aid elements in BDNS")

            for element in aid_elements[:source_config.get("max_aids_per_source", 20)]:
                try:
                    aid_data = self._parse_element(element, "bdns")
                    if aid_data and aid_data.get("title"):
                        extracted_data.append(aid_data)
                except Exception as e:
                    logging.debug(f"Error parsing BDNS aid element: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting from BDNS: {e}")

        return extracted_data

    def _extract_from_gva(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from Generalitat Valenciana."""
        extracted_data = []

        try:
            search_urls = [
                "https://dadesobertes.gva.es/es/dataset/eco-gvo-subv-2025",
                "https://www.gva.es/es/inicio/procedimientos",
                "https://sede.gva.es/es/procedimientos",
            ]

            for url in search_urls:
                try:
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, "html.parser")

                    aid_elements = (
                        soup.find_all(["div", "article", "li"], class_=re.compile(r".*ayuda.*|.*subven.*", re.I))
                        or soup.find_all("a", href=re.compile(r".*ayuda.*|.*subven.*", re.I))
                        or soup.find_all("h3")
                    )

                    logging.info(f"Found {len(aid_elements)} potential aid elements in GVA from {url}")

                    for element in aid_elements[:source_config.get("max_aids_per_source", 20)]:
                        try:
                            aid_data = self._parse_element(element, "gva")
                            if aid_data and aid_data.get("title"):
                                extracted_data.append(aid_data)
                        except Exception as e:
                            logging.debug(f"Error parsing GVA aid element: {e}")
                            continue

                    time.sleep(self.request_delay)

                except Exception as e:
                    logging.warning(f"Error fetching from GVA URL {url}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting from GVA: {e}")

        return extracted_data

    def _extract_from_valencia(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from Ayuntamiento de Valencia."""
        extracted_data = []

        try:
            main_url = source_config["url"]
            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            aid_links = soup.find_all("a", href=True)

            # Filter for subsidy-related links
            subsidy_links = []
            for link in aid_links:
                text = link.get_text(strip=True)
                href = link.get("href", "")

                if len(text) < 15:
                    continue

                if any(
                    keyword in text.lower()
                    for keyword in ["ayuda", "subven", "beca", "fomento", "convocatoria"]
                ) and text.lower().strip() not in ["subvenciones", "ayudas", "tramites"]:
                    subsidy_links.append(link)

            logging.info(f"Found {len(subsidy_links)} specific aid links in Valencia")

            for link in subsidy_links[:source_config.get("max_aids_per_source", 20)]:
                try:
                    aid_data = self._parse_element(link, "valencia")
                    if aid_data and aid_data.get("title") and len(aid_data["title"]) > 20:
                        extracted_data.append(aid_data)
                except Exception as e:
                    logging.debug(f"Error parsing Valencia aid link: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting from Valencia: {e}")

        return extracted_data

    def _extract_from_labora(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract from LABORA."""
        extracted_data = []

        try:
            main_url = source_config["url"]
            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            aid_links = soup.find_all("a", href=True)

            # Filter for employment-related aid links
            employment_links = []
            for link in aid_links:
                text = link.get_text(strip=True)

                if len(text) < 20:
                    continue

                if any(
                    keyword in text.lower()
                    for keyword in [
                        "empleo", "contratación", "formación", "laboral",
                        "trabajo", "fomento", "incentivo", "beca", "ayuda",
                    ]
                ):
                    employment_links.append(link)

            logging.info(f"Found {len(employment_links)} specific employment aid links in LABORA")

            for link in employment_links[:source_config.get("max_aids_per_source", 20)]:
                try:
                    aid_data = self._parse_element(link, "labora")
                    if aid_data and aid_data.get("title") and len(aid_data["title"]) > 20:
                        extracted_data.append(aid_data)
                except Exception as e:
                    logging.debug(f"Error parsing LABORA aid link: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting from LABORA: {e}")

        return extracted_data

    def _parse_element(self, element: BeautifulSoup, source: str) -> dict[str, Any] | None:
        """Parse an aid element from any source.

        Args:
            element: BeautifulSoup element
            source: Source identifier

        Returns:
            Parsed aid data or None
        """
        try:
            # Extract title
            title_elem = (
                element.find(["h2", "h3", "h4"], class_=re.compile(r".*titulo.*|.*title.*", re.I))
                or element.find("a", href=True)
                or element.find(["span", "div"], class_=re.compile(r".*name.*|.*title.*", re.I))
                or element
            )

            title_text = title_elem.get_text(strip=True) if title_elem else ""

            if len(title_text) < 10:
                return None

            # Extract description
            description_elem = (
                element.find(["p", "div"], class_=re.compile(r".*desc.*|.*resumen.*", re.I))
                or element.find_next_sibling(["p", "div"])
            )

            description_text = description_elem.get_text(strip=True) if description_elem else ""

            # Extract URL
            url_elem = element.find("a", href=True)
            url = url_elem.get("href", "") if url_elem else ""

            # Extract any dates
            date_pattern = re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b")
            dates = date_pattern.findall(title_text + " " + description_text)

            return {
                "title": title_text[:200],
                "description": description_text[:500],
                "url": url,
                "source": source,
                "dates": dates,
                "raw_html": str(element)[:500],
            }

        except Exception as e:
            logging.debug(f"Error parsing element: {e}")
            return None
