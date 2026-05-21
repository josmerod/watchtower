"""National Vulnerability Database (NVD) ETL.

Monitors real-time CVEs and cybersecurity threats via NVD REST API 2.0.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
import time

from src.etl.base import BaseETL
from src.exceptions.etl import LoadError
from src.utils.logging import get_logger
from src.etl.proxy_manager import ProxyManager


class NVDEtl(BaseETL):
    """NVD ETL for tracking cybersecurity threats and CVEs."""

    def __init__(self, **kwargs):
        """Initialize NVD CVE ETL."""
        super().__init__(
            name="nvd_cve",
            description="Tracks real-time cybersecurity threats and CVEs",
            **kwargs,
        )
        self.logger = get_logger("ETL.NVD")
        # Ensure we just grab the most recent published CVEs
        # NVD 2.0: use pubStartDate to filter recent vulnerabilities
        from datetime import datetime, timedelta, timezone
        since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00.000")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000")
        self.endpoints = {
            "cves": (
                f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                f"?resultsPerPage=50&pubStartDate={since}&pubEndDate={now}"
                f"&sort=published&dir=desc"
            )
        }
        self.proxy_manager = ProxyManager()

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from NVD REST API."""
        self.logger.info("Extracting data from NVD API")
        extracted_data = []

        try:
            session = self.proxy_manager.get_session(retries=5, backoff_factor=2.0)
            headers = {"User-Agent": "WatchtowerBot/1.0 (Threat Intel Monitor)"}
            
            # NVD 2.0 supports optional API key for higher rate limits.
            # Set NVD_API_KEY env var to increase from 5 to 50 req/30s.
            api_key = os.environ.get("NVD_API_KEY")
            if api_key:
                headers["apiKey"] = api_key
            
            res = session.get(self.endpoints["cves"], headers=headers, timeout=30)
            
            if res.status_code == 404:
                self.logger.warning("NVD API returned 404 — service may be temporarily unavailable. Skipping this run.")
                self.metrics.records_failed += 1
                return []
            
            res.raise_for_status()
            
            vulnerabilities = res.json().get("vulnerabilities", [])
            
            # Filter out historical CVEs — only keep items published in the last 90 days.
            # This guards against NVD returning unexpected results when date filters fail.
            from datetime import datetime, timedelta, timezone
            cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            recent_vulns = []
            for v in vulnerabilities:
                cve = v.get("cve", {})
                pub = cve.get("published", "")
                if pub and pub >= cutoff:
                    recent_vulns.append(cve)
                else:
                    self.logger.debug(f"Skipping historical CVE: {cve.get('id', '?')} (published {pub})")
            
            if not recent_vulns and vulnerabilities:
                self.logger.warning(
                    f"NVD returned {len(vulnerabilities)} CVEs but none are from the last 90 days. "
                    f"The API date filter may be failing. Check NVD API status."
                )
            
            for cve_data in recent_vulns:
                cve_data["data_type"] = "cve"
                extracted_data.append(cve_data)
                
            self.metrics.records_extracted += len(recent_vulns)

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform NVD API CVE data."""
        self.logger.info(f"Transforming {len(data)} NVD CVE records")
        transformed = []
        for record in data:
            try:
                # Extract Description
                description = "No description available."
                for desc in record.get("descriptions", []):
                    if desc.get("lang") == "en":
                        description = desc.get("value")
                        break

                # Extract Metrics / CVSS
                cvss_score = 0.0
                severity = "UNKNOWN"
                metrics = record.get("metrics", {})
                
                # Check CVSS v3.1 first, then v3.0, then v2
                cvss_data = None
                if "cvssMetricV31" in metrics:
                    cvss_data = metrics["cvssMetricV31"][0].get("cvssData", {})
                    severity = metrics["cvssMetricV31"][0].get("baseSeverity", "UNKNOWN")
                elif "cvssMetricV30" in metrics:
                    cvss_data = metrics["cvssMetricV30"][0].get("cvssData", {})
                    severity = metrics["cvssMetricV30"][0].get("baseSeverity", "UNKNOWN")
                elif "cvssMetricV2" in metrics:
                    cvss_data = metrics["cvssMetricV2"][0].get("cvssData", {})
                    severity = metrics["cvssMetricV2"][0].get("baseSeverity", "UNKNOWN")
                
                if cvss_data:
                    cvss_score = cvss_data.get("baseScore", 0.0)

                # NVD specific fields alongside generic Intel Dashboard fields
                cve_id = record.get("id", "Unknown CVE")
                transformed.append({
                    "id": cve_id,
                    "title": f"[{severity}] {cve_id}: CVSS {cvss_score}",
                    "published": record.get("published"),
                    "lastModified": record.get("lastModified"),
                    "vulnStatus": record.get("vulnStatus"),
                    "description": description,
                    "cvss_score": cvss_score,
                    "severity": severity,
                    "data_type": "cve",
                    # Standard Intel Dashboard Fields
                    "content_type": "CVE",
                    "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    "region": "Global"
                })
                self.metrics.records_transformed += 1
            except Exception as e:
                self.logger.error(f"Transform failed for CVE {record.get('id')}: {e}")
                self.metrics.records_failed += 1
            
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load NVD CVE data to output directory."""
        if not data:
            self.logger.info("No NVD CVE data to load.")
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"nvd_cve_{timestamp}.json"
        latest_file = self.output_dir / "nvd_cve_latest.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            
            self.metrics.records_loaded = len(data)
            self.logger.info(f"Successfully saved {len(data)} records to {latest_file}")
            
        except OSError as e:
            self.logger.error(f"Failed to save info to {output_file}: {e}")
            raise LoadError(f"Failed to save data: {e}", destination=str(output_file), destination_type="file") from e
        except Exception as e:
            raise LoadError(f"Unexpected error: {e}", destination=str(output_file), destination_type="file") from e

if __name__ == "__main__":
    etl = NVDEtl()
    etl.run()
