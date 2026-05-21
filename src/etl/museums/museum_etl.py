import logging  # Keep logging for the __main__ block, if needed, or for specific logger instances
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# BaseModel might not be directly needed if VirtualMuseumModel and SimpleETL handle it
from pydantic import ValidationError

# Actual imports:
from src.etl.base import SimpleETL

# , ETLMetrics # ETLMetrics is part of BaseETL/SimpleETL typically
from src.models.museums import VirtualMuseumModel

# WIKIDATA_SPARQL_URL can be defined before the class or within if it's specific
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"


class VirtualMuseumsETL(SimpleETL):
    def __init__(self):
        super().__init__(
            name="virtual_museums_etl",
            description="ETL process for fetching virtual museum data from Wikidata.",
        )

    def extract(self) -> list[dict[str, Any]]:
        self.logger.info("Starting data extraction for virtual museums from Wikidata.")

        sparql_query = """
        SELECT
          ?museum ?museumLabel ?museumDescription
          ?website ?virtualTourURL
          ?countryLabel ?cityLabel
          ?mainSubjectLabel ?image ?coordinates
        WHERE {
          ?museum wdt:P31 wd:Q33506;
          { ?museum wdt:P4969 ?virtualTourURL. }
          UNION
          { ?museum wdt:P4837 ?virtualTourURL. }
          OPTIONAL { ?museum wdt:P856 ?website. }
          OPTIONAL { ?museum wdt:P18 ?image. }
          OPTIONAL { ?museum wdt:P625 ?coordinates. }
          OPTIONAL { ?museum wdt:P17 ?country. }
          OPTIONAL { ?museum wdt:P131 ?city. }
          OPTIONAL { ?museum wdt:P921 ?mainSubject. }
          SERVICE wikibase:label {
            bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".
            ?museum rdfs:label ?museumLabel.
            ?museum schema:description ?museumDescription.
            ?country rdfs:label ?countryLabel.
            ?city rdfs:label ?cityLabel.
            ?mainSubject rdfs:label ?mainSubjectLabel.
          }
        }
        LIMIT 200
        """

        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "VirtualMuseumsETL/0.1 (https://example.org/etl; mail@example.org)",  # Good practice to set User-Agent
        }
        params = {"query": sparql_query}

        extracted_items: list[dict[str, Any]] = []

        try:
            self.logger.info(f"Querying Wikidata SPARQL endpoint: {WIKIDATA_SPARQL_URL}")

            @retry(stop=stop_after_attempt(3),
                   wait=wait_exponential(multiplier=2, min=5, max=60),
                   retry=retry_if_exception_type((requests.exceptions.ConnectionError,
                                                  requests.exceptions.HTTPError)))
            def _fetch():
                r = requests.get(WIKIDATA_SPARQL_URL, headers=headers, params=params, timeout=30)
                r.raise_for_status()
                return r.json()

            data = _fetch()
            results = data.get("results", {}).get("bindings", [])
            self.logger.info(f"Received {len(results)} items from Wikidata.")

            for item in results:
                # Helper to get value, returns None if key is missing
                def get_value(key: str):
                    return item.get(key, {}).get("value")

                # Extract coordinates if available
                latitude, longitude = None, None
                coordinates_str = get_value("coordinates")
                if coordinates_str:
                    # Format is "Point(Longitude Latitude)"
                    try:
                        parts = coordinates_str.replace("Point(", "").replace(")", "").split()
                        if len(parts) == 2:
                            longitude = float(parts[0])
                            latitude = float(parts[1])
                    except ValueError:
                        self.logger.warning(f"Could not parse coordinates: {coordinates_str} for {get_value('museum')}")

                processed_item = {
                    "wikidata_url": get_value("museum"),
                    "name": get_value("museumLabel"),
                    "description": get_value("museumDescription"),
                    "website_url": get_value("website"),
                    "virtual_tour_url": get_value("virtualTourURL"),
                    "country_label": get_value("countryLabel"),
                    "city_label": get_value("cityLabel"),
                    "main_subject_label": get_value("mainSubjectLabel"),
                    "image_url": get_value("image"),
                    "latitude": latitude,
                    "longitude": longitude,
                    # data_source and retrieved_at will be set during transformation/model creation
                }
                extracted_items.append(processed_item)

            self.logger.info(f"Successfully extracted and processed {len(extracted_items)} items.")

        except requests.exceptions.Timeout:
            self.logger.error("Wikidata query timed out.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during data extraction from Wikidata: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during extraction: {e}", exc_info=True)

        return extracted_items

    def transform(self, data: list[dict[str, Any]]) -> list[VirtualMuseumModel]:
        self.logger.info(f"Starting data transformation for {len(data)} raw items.")

        transformed_models: list[VirtualMuseumModel] = []
        failed_count = 0

        for item_data in data:
            try:
                # Ensure 'name' is present, as it's a mandatory field in VirtualMuseumModel
                # The SPARQL query should provide ?museumLabel for 'name'.
                # If 'name' is None or missing from item_data due to an issue upstream,
                # Pydantic will raise a ValidationError, which is caught below.
                if item_data.get("name") is None:
                    self.logger.warning(f"Skipping item due to missing 'name': {item_data.get('wikidata_url', 'Unknown Wikidata URL')}")
                    failed_count += 1
                    continue

                model_instance = VirtualMuseumModel(**item_data)
                transformed_models.append(model_instance)
            except ValidationError as e:
                failed_count += 1
                self.logger.error(f"Validation error transforming item: {item_data.get('wikidata_url', 'Unknown item')}")
                # self.logger.debug(f"Problematic data: {item_data}") # Potentially verbose
                self.logger.debug(f"Pydantic errors: {e.errors()}")
            except Exception as e:
                failed_count += 1
                self.logger.error(
                    f"Unexpected error transforming item: {item_data.get('wikidata_url', 'Unknown item')}: {e}",
                    exc_info=True,
                )

        self.logger.info(f"Successfully transformed {len(transformed_models)} items.")
        if failed_count > 0:
            self.logger.warning(f"{failed_count} items failed validation or transformation.")

        return transformed_models

    def load(self, data: list) -> None:
        """Override default load to also write museums_latest.json for dashboard consumption."""
        import json as _json
        from datetime import datetime as _dt

        serialized = _json.dumps(
            [item.model_dump() if hasattr(item, "model_dump") else item for item in data],
            ensure_ascii=False, indent=2, default=str,
        )

        # Save timestamped file
        out_f = self.output_dir / f"{self.name}_{_dt.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_f.write_text(serialized, encoding="utf-8")
        self.logger.info(f"Data saved to {out_f}")

        # Also write a stable 'museums_latest.json' that MUSEUMS_CONFIG expects
        latest_path = self.output_dir / "museums_latest.json"
        latest_path.write_text(serialized, encoding="utf-8")
        self.logger.info(f"Latest copy saved to {latest_path}")


if __name__ == "__main__":
    logging.info("Starting Virtual Museums ETL script execution.")

    etl_process = VirtualMuseumsETL()
    metrics = etl_process.run()

    logging.info("Virtual Museums ETL script finished. Metrics:")
    logging.info(metrics.model_dump_json(indent=2))

    # Example of how to check status and handle results
    if metrics.is_successful:
        logging.info("ETL completed successfully.")
    else:
        logging.error(f"ETL failed with {metrics.error_count} errors")

