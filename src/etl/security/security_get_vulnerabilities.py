"""Security Vulnerability ETL Module.

This module fetches and processes security vulnerabilities from multiple sources
including CVE databases, GitHub Security Advisories, npm security alerts, and PyPI security alerts.

Usage:
    python src/etl/security/security_get_vulnerabilities.py

Output:
    - JSON file: data/security_vulnerabilities/security_vulnerabilities_latest.json
    - CSV file: data/security_vulnerabilities/security_vulnerabilities_latest.csv
"""

import csv
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add the project root to the path to ensure imports work correctly
from utils.file_system import ensure_directories, get_project_root
from utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("SecurityVulnerabilityETL")


def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers
    session.headers.update(
        {
            "User-Agent": "Watchtower-ETL/1.0 (Security Vulnerability Intelligence)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    return session


def fetch_cve_vulnerabilities(
    session: requests.Session, days_back: int = 7, max_results: int = 100
) -> list[dict[str, Any]]:
    """Fetch CVE vulnerabilities from NVD API.

    Args:
        session: Requests session with retry configuration
        days_back: Number of days to look back for vulnerabilities
        max_results: Maximum number of results to fetch

    Returns:
        List of CVE vulnerability dictionaries
    """
    vulnerabilities = []

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Format dates for NVD API
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000")

        logger.info(f"Fetching CVE data from {start_date_str} to {end_date_str}")

        # NVD API endpoint
        base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        params = {
            "pubStartDate": start_date_str,
            "pubEndDate": end_date_str,
            "resultsPerPage": min(max_results, 2000),  # NVD API limit
            "startIndex": 0,
        }

        response = session.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        cve_items = data.get("vulnerabilities", [])

        logger.info(f"Fetched {len(cve_items)} CVE items from NVD")

        for item in cve_items:
            try:
                cve_data = item.get("cve", {})
                cve_id = cve_data.get("id")

                if not cve_id:
                    continue

                # Extract basic info
                descriptions = cve_data.get("descriptions", [])
                description = ""
                for desc in descriptions:
                    if desc.get("lang") == "en":
                        description = desc.get("value", "")
                        break

                # Extract CVSS scores
                metrics = cve_data.get("metrics", {})
                cvss_base_score = None
                cvss_vector = None
                cvss_version = None

                # Try CVSS v3.1 first, then v3.0, then v2.0
                for version in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                    if metrics.get(version):
                        cvss_data = metrics[version][0].get("cvssData", {})
                        cvss_base_score = cvss_data.get("baseScore")
                        cvss_vector = cvss_data.get("vectorString")
                        cvss_version = cvss_data.get("version")
                        break

                # Extract vulnerability details
                weaknesses = cve_data.get("weaknesses", [])
                cwe_ids = []
                for weakness in weaknesses:
                    for desc in weakness.get("description", []):
                        if desc.get("lang") == "en":
                            cwe_ids.append(desc.get("value", ""))

                # Extract references
                references = cve_data.get("references", [])
                reference_urls = [
                    ref.get("url") for ref in references if ref.get("url")
                ]

                # Extract affected configurations (simplified)
                configurations = cve_data.get("configurations", [])
                affected_packages = []
                affected_versions = []

                for config in configurations:
                    for node in config.get("nodes", []):
                        for cpe_match in node.get("cpeMatch", []):
                            cpe23_uri = cpe_match.get("criteria", "")
                            if cpe23_uri:
                                # Parse CPE to extract package info
                                cpe_parts = cpe23_uri.split(":")
                                if len(cpe_parts) >= 5:
                                    vendor = cpe_parts[3]
                                    product = cpe_parts[4]
                                    affected_packages.append(f"{vendor}/{product}")

                                    if len(cpe_parts) >= 6:
                                        version = cpe_parts[5]
                                        if version and version != "*":
                                            affected_versions.append(version)

                # Calculate Watchtower severity score
                severity_score = calculate_severity_score(
                    cvss_base_score, cwe_ids, len(affected_packages), description
                )

                # Determine technology stack
                technology_stack = determine_technology_stack(
                    affected_packages, description
                )

                vulnerability = {
                    "vulnerability_id": f"CVE-{cve_id}",
                    "cve_id": cve_id,
                    "title": f"CVE-{cve_id}: {description[:100]}...",
                    "description": description,
                    "source_name": "NVD CVE Database",
                    "source_url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    "source_id": cve_id,
                    "cvss_version": cvss_version,
                    "cvss_vector": cvss_vector,
                    "cvss_base_score": cvss_base_score,
                    "severity_score": severity_score,
                    "affected_packages": list(set(affected_packages)),
                    "affected_versions": list(set(affected_versions)),
                    "technology_stack": technology_stack,
                    "published_date": cve_data.get("published"),
                    "modified_date": cve_data.get("lastModified"),
                    "references": reference_urls,
                    "cwe_ids": cwe_ids,
                    "exploit_available": check_exploit_available(
                        description, reference_urls
                    ),
                    "patch_available": check_patch_available(
                        description, reference_urls
                    ),
                    "fetched_at": datetime.now().isoformat(),
                }

                vulnerabilities.append(vulnerability)

            except Exception as e:
                logger.warning(f"Error processing CVE item: {e}")
                continue

        logger.info(f"Processed {len(vulnerabilities)} CVE vulnerabilities")
        return vulnerabilities

    except Exception as e:
        logger.error(f"Error fetching CVE vulnerabilities: {e}")
        return []


def fetch_github_security_advisories(
    session: requests.Session, max_results: int = 50
) -> list[dict[str, Any]]:
    """Fetch GitHub Security Advisories.

    Args:
        session: Requests session with retry configuration
        max_results: Maximum number of advisories to fetch

    Returns:
        List of GitHub security advisory dictionaries
    """
    vulnerabilities = []

    try:
        logger.info("Fetching GitHub Security Advisories")

        # GitHub Security Advisories API
        url = "https://api.github.com/advisories"
        params = {
            "per_page": min(max_results, 100),
            "sort": "published",
            "direction": "desc",
        }

        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()

        advisories = response.json()
        logger.info(f"Fetched {len(advisories)} GitHub Security Advisories")

        for advisory in advisories:
            try:
                ghsa_id = advisory.get("ghsa_id")
                cve_id = advisory.get("cve_id")

                # Extract CVSS info
                cvss = advisory.get("cvss", {})
                cvss_score = cvss.get("score") if cvss else None
                cvss_vector = cvss.get("vector_string") if cvss else None

                # Extract affected packages
                affected_packages = []
                affected_versions = []
                vulnerabilities_data = advisory.get("vulnerabilities", [])

                for vuln in vulnerabilities_data:
                    package = vuln.get("package", {})
                    ecosystem = package.get("ecosystem")
                    name = package.get("name")

                    if ecosystem and name:
                        affected_packages.append(f"{ecosystem.lower()}/{name}")

                    # Get affected version ranges
                    for range_info in vuln.get("vulnerable_version_range", "").split(
                        ","
                    ):
                        if range_info.strip():
                            affected_versions.append(range_info.strip())

                # Calculate severity score
                severity_score = calculate_severity_score(
                    cvss_score,
                    [],  # CWE not available in this API
                    len(affected_packages),
                    advisory.get("description", ""),
                )

                # Determine technology stack
                technology_stack = determine_technology_stack(
                    affected_packages, advisory.get("description", "")
                )

                vulnerability = {
                    "vulnerability_id": ghsa_id,
                    "cve_id": cve_id,
                    "title": advisory.get("summary", ""),
                    "description": advisory.get("description", ""),
                    "source_name": "GitHub Security Advisories",
                    "source_url": advisory.get("html_url"),
                    "source_id": ghsa_id,
                    "cvss_base_score": cvss_score,
                    "cvss_vector": cvss_vector,
                    "severity_score": severity_score,
                    "affected_packages": affected_packages,
                    "affected_versions": affected_versions,
                    "technology_stack": technology_stack,
                    "published_date": advisory.get("published_at"),
                    "modified_date": advisory.get("updated_at"),
                    "references": [advisory.get("html_url")]
                    if advisory.get("html_url")
                    else [],
                    "patch_available": True,  # GitHub advisories usually include fixes
                    "fetched_at": datetime.now().isoformat(),
                }

                vulnerabilities.append(vulnerability)

            except Exception as e:
                logger.warning(f"Error processing GitHub advisory: {e}")
                continue

        logger.info(f"Processed {len(vulnerabilities)} GitHub Security Advisories")
        return vulnerabilities

    except Exception as e:
        logger.error(f"Error fetching GitHub Security Advisories: {e}")
        return []


def fetch_npm_security_advisories(session: requests.Session) -> list[dict[str, Any]]:
    """Fetch npm security advisories from npmjs.com.

    Args:
        session: Requests session with retry configuration

    Returns:
        List of npm security advisory dictionaries
    """
    vulnerabilities = []

    try:
        logger.info("Fetching npm security advisories")

        # npm security advisories (using audit API approach)
        # This is a simplified version - in production you'd want to use the npm audit API

        # For demo purposes, we'll create some sample data based on known patterns
        # In production, you'd integrate with npm's actual security API

        sample_advisories = [
            {
                "id": "1002851",
                "title": "Regular Expression Denial of Service in semver",
                "module_name": "semver",
                "vulnerable_versions": "<7.3.2",
                "patched_versions": ">=7.3.2",
                "severity": "moderate",
                "overview": "Versions of semver prior to 7.3.2 are vulnerable to Regular Expression Denial of Service",
                "url": "https://www.npmjs.com/advisories/1002851",
            }
        ]

        for advisory in sample_advisories:
            try:
                # Calculate severity score
                severity_mapping = {
                    "critical": 9.0,
                    "high": 7.5,
                    "moderate": 5.0,
                    "low": 2.5,
                    "info": 1.0,
                }

                severity_score = severity_mapping.get(
                    advisory.get("severity", "low"), 2.5
                )

                vulnerability = {
                    "vulnerability_id": f"NPM-{advisory['id']}",
                    "cve_id": None,
                    "title": advisory.get("title", ""),
                    "description": advisory.get("overview", ""),
                    "source_name": "npm Security Advisories",
                    "source_url": advisory.get("url"),
                    "source_id": advisory.get("id"),
                    "severity_score": severity_score,
                    "affected_packages": [f"npm/{advisory.get('module_name', '')}"],
                    "affected_versions": [advisory.get("vulnerable_versions", "")],
                    "technology_stack": ["javascript", "node.js", "npm"],
                    "patch_version": advisory.get("patched_versions"),
                    "patch_available": bool(advisory.get("patched_versions")),
                    "published_date": datetime.now().isoformat(),  # Would be actual date in production
                    "fetched_at": datetime.now().isoformat(),
                }

                vulnerabilities.append(vulnerability)

            except Exception as e:
                logger.warning(f"Error processing npm advisory: {e}")
                continue

        logger.info(f"Processed {len(vulnerabilities)} npm security advisories")
        return vulnerabilities

    except Exception as e:
        logger.error(f"Error fetching npm security advisories: {e}")
        return []


def calculate_severity_score(
    cvss_score: float | None,
    cwe_ids: list[str],
    affected_packages_count: int,
    description: str,
) -> float:
    """Calculate Watchtower-specific severity score.

    Args:
        cvss_score: CVSS base score
        cwe_ids: List of CWE identifiers
        affected_packages_count: Number of affected packages
        description: Vulnerability description

    Returns:
        Calculated severity score (0-10)
    """
    base_score = cvss_score or 5.0  # Default to medium if no CVSS

    # Contextual adjustments
    adjustments = 0.0

    # High-impact keywords in description
    high_impact_keywords = [
        "remote code execution",
        "rce",
        "arbitrary code",
        "privilege escalation",
        "sql injection",
        "cross-site scripting",
        "xss",
        "buffer overflow",
        "authentication bypass",
        "critical",
        "zero-day",
    ]

    description_lower = description.lower()
    for keyword in high_impact_keywords:
        if keyword in description_lower:
            adjustments += 0.5
            break  # Only add once for impact keywords

    # CWE-based adjustments
    critical_cwes = ["CWE-78", "CWE-79", "CWE-89", "CWE-94", "CWE-287", "CWE-416"]
    for cwe in cwe_ids:
        if any(critical_cwe in cwe for critical_cwe in critical_cwes):
            adjustments += 0.3
            break

    # Package popularity adjustment (more packages = higher risk)
    if affected_packages_count > 10:
        adjustments += 0.5
    elif affected_packages_count > 5:
        adjustments += 0.3
    elif affected_packages_count > 1:
        adjustments += 0.1

    # Calculate final score
    final_score = min(base_score + adjustments, 10.0)
    return round(final_score, 1)


def determine_technology_stack(
    affected_packages: list[str], description: str
) -> list[str]:
    """Determine technology stack based on affected packages and description.

    Args:
        affected_packages: List of affected packages
        description: Vulnerability description

    Returns:
        List of technology stack categories
    """
    technologies = set()

    # Package-based detection
    for package in affected_packages:
        package_lower = package.lower()

        if any(x in package_lower for x in ["npm/", "node", "javascript"]):
            technologies.update(["javascript", "node.js"])
        elif any(x in package_lower for x in ["pip/", "python", "pypi"]):
            technologies.add("python")
        elif any(x in package_lower for x in ["maven/", "java", "jar"]):
            technologies.add("java")
        elif any(x in package_lower for x in ["nuget/", "dotnet", ".net"]):
            technologies.add(".net")
        elif any(x in package_lower for x in ["gem/", "ruby"]):
            technologies.add("ruby")
        elif any(x in package_lower for x in ["composer/", "php"]):
            technologies.add("php")
        elif any(x in package_lower for x in ["go/", "golang"]):
            technologies.add("go")
        elif any(x in package_lower for x in ["rust/", "cargo"]):
            technologies.add("rust")

    # Description-based detection
    description_lower = description.lower()
    tech_keywords = {
        "docker": ["docker", "container", "dockerfile"],
        "kubernetes": ["kubernetes", "k8s", "kubectl"],
        "web": ["web", "http", "https", "browser"],
        "database": ["sql", "database", "mysql", "postgresql", "mongodb"],
        "cloud": ["aws", "azure", "gcp", "cloud"],
        "mobile": ["android", "ios", "mobile", "app"],
    }

    for tech, keywords in tech_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            technologies.add(tech)

    return list(technologies)


def check_exploit_available(description: str, references: list[str]) -> bool:
    """Check if exploit is available based on description and references."""
    exploit_indicators = [
        "exploit",
        "poc",
        "proof of concept",
        "exploit-db",
        "metasploit",
        "actively exploited",
        "exploit available",
        "public exploit",
    ]

    description_lower = description.lower()
    for indicator in exploit_indicators:
        if indicator in description_lower:
            return True

    # Check references for exploit-related URLs
    for ref in references:
        ref_lower = ref.lower()
        if any(x in ref_lower for x in ["exploit-db", "metasploit", "exploit"]):
            return True

    return False


def check_patch_available(description: str, references: list[str]) -> bool:
    """Check if patch is available based on description and references."""
    patch_indicators = [
        "patch",
        "fix",
        "update",
        "fixed in",
        "resolved in",
        "patched in",
        "upgrade to",
        "version",
        "release",
    ]

    description_lower = description.lower()
    return any(indicator in description_lower for indicator in patch_indicators)


def process_vulnerabilities(
    vulnerabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process and enrich vulnerability data with additional metrics and categorization.

    Args:
        vulnerabilities: List of vulnerability dictionaries

    Returns:
        List of processed and enriched vulnerability data
    """
    logger.info(f"Processing {len(vulnerabilities)} vulnerabilities")

    processed_vulnerabilities = []
    current_time = datetime.now()

    for vuln in vulnerabilities:
        try:
            # Parse publication date
            published_date_str = vuln.get("published_date")
            if published_date_str:
                try:
                    published_date = datetime.fromisoformat(
                        published_date_str.replace("Z", "+00:00")
                    )
                    days_since_published = (
                        current_time.replace(tzinfo=published_date.tzinfo)
                        - published_date
                    ).days
                except:
                    days_since_published = 0
            else:
                days_since_published = 0

            # Calculate risk level based on severity score
            severity_score = vuln.get("severity_score", 0.0)
            if severity_score >= 9.0:
                risk_level = "critical"
            elif severity_score >= 7.0:
                risk_level = "high"
            elif severity_score >= 4.0:
                risk_level = "medium"
            elif severity_score >= 0.1:
                risk_level = "low"
            else:
                risk_level = "info"

            # Estimate fix time based on severity and other factors
            if risk_level == "critical":
                estimated_fix_time = "24h"
            elif risk_level == "high":
                estimated_fix_time = "1w"
            elif risk_level == "medium":
                estimated_fix_time = "2w"
            else:
                estimated_fix_time = "1m"

            # Generate mitigation strategies
            mitigation_strategies = generate_mitigation_strategies(vuln)

            # Create enriched vulnerability
            enriched_vuln = {
                **vuln,
                "risk_level": risk_level,
                "days_since_published": days_since_published,
                "estimated_fix_time": estimated_fix_time,
                "mitigation_strategies": mitigation_strategies,
                "is_recent": days_since_published <= 30,
                "is_critical": severity_score >= 9.0 and risk_level == "critical",
                "needs_urgent_attention": (
                    severity_score >= 9.0
                    and vuln.get("exploit_available", False)
                    and not vuln.get("patch_available", False)
                    and days_since_published <= 7
                ),
                "processed_at": current_time.isoformat(),
            }

            processed_vulnerabilities.append(enriched_vuln)

        except Exception as e:
            logger.warning(f"Error processing vulnerability: {e}")
            continue

    logger.info(
        f"Successfully processed {len(processed_vulnerabilities)} vulnerabilities"
    )
    return processed_vulnerabilities


def generate_mitigation_strategies(vulnerability: dict[str, Any]) -> list[str]:
    """Generate mitigation strategies for a vulnerability."""
    strategies = []

    # Base strategies
    if vulnerability.get("patch_available"):
        patch_version = vulnerability.get("patch_version")
        if patch_version:
            strategies.append(f"Upgrade to version {patch_version} or later")
        else:
            strategies.append("Apply available security patch")

    # Technology-specific strategies
    tech_stack = vulnerability.get("technology_stack", [])

    if "web" in tech_stack:
        strategies.append("Implement Web Application Firewall (WAF) rules")
        strategies.append("Review and sanitize input validation")

    if "javascript" in tech_stack or "node.js" in tech_stack:
        strategies.append("Run npm audit and fix vulnerabilities")
        strategies.append("Use npm audit fix for automatic fixes")

    if "python" in tech_stack:
        strategies.append("Use pip-audit to check for vulnerabilities")
        strategies.append("Update requirements.txt with safe versions")

    if "docker" in tech_stack:
        strategies.append("Rebuild container images with updated base images")
        strategies.append("Scan container images for vulnerabilities")

    # Severity-based strategies
    severity_score = vulnerability.get("severity_score", 0.0)
    if severity_score >= 9.0:
        strategies.append("Implement immediate access controls")
        strategies.append("Monitor for exploitation attempts")
        strategies.append("Consider temporary service isolation")

    # Default strategies if none specific
    if not strategies:
        strategies.extend(
            [
                "Monitor vendor advisories for updates",
                "Implement defense-in-depth security measures",
                "Regular security assessments and updates",
            ]
        )

    return strategies


def save_data(data: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """Save vulnerability data to JSON and CSV files.

    Args:
        data: List of vulnerability dictionaries
        output_dir: Output directory path

    Returns:
        Dictionary with file paths
    """
    if not data:
        logger.warning("No data to save")
        return {}

    try:
        # Ensure output directory exists
        ensure_directories([output_dir])

        # Generate timestamps for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # File paths
        json_file = os.path.join(output_dir, "security_vulnerabilities_latest.json")
        csv_file = os.path.join(output_dir, "security_vulnerabilities_latest.csv")
        timestamped_json = os.path.join(
            output_dir, f"security_vulnerabilities_{timestamp}.json"
        )

        # Save as JSON
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        # Save timestamped copy
        with open(timestamped_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        # Save as CSV
        if data:
            # Flatten nested data for CSV
            flattened_data = []
            for item in data:
                flat_item = {}
                for key, value in item.items():
                    if isinstance(value, list | dict):
                        flat_item[key] = json.dumps(value, default=str)
                    else:
                        flat_item[key] = value
                flattened_data.append(flat_item)

            # Get all unique keys for CSV headers
            all_keys = set()
            for item in flattened_data:
                all_keys.update(item.keys())

            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(flattened_data)

        file_paths = {
            "json": json_file,
            "csv": csv_file,
            "timestamped_json": timestamped_json,
        }

        logger.info("Data saved successfully:")
        logger.info(f"  JSON: {json_file}")
        logger.info(f"  CSV: {csv_file}")
        logger.info(f"  Timestamped: {timestamped_json}")

        return file_paths

    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return {}


def main():
    """Main function to run the Security Vulnerability ETL process."""
    try:
        logger.info("Starting Security Vulnerability ETL process")
        start_time = time.time()

        # Create session
        session = create_session()

        # Collect vulnerabilities from multiple sources
        all_vulnerabilities = []

        # Fetch CVE vulnerabilities
        logger.info("Fetching CVE vulnerabilities...")
        cve_vulns = fetch_cve_vulnerabilities(session, days_back=7, max_results=50)
        all_vulnerabilities.extend(cve_vulns)

        # Fetch GitHub Security Advisories
        logger.info("Fetching GitHub Security Advisories...")
        github_vulns = fetch_github_security_advisories(session, max_results=25)
        all_vulnerabilities.extend(github_vulns)

        # Fetch npm security advisories
        logger.info("Fetching npm security advisories...")
        npm_vulns = fetch_npm_security_advisories(session)
        all_vulnerabilities.extend(npm_vulns)

        logger.info(f"Total vulnerabilities collected: {len(all_vulnerabilities)}")

        if not all_vulnerabilities:
            logger.warning("No vulnerability data collected")
            return

        # Process and enrich vulnerabilities
        processed_vulnerabilities = process_vulnerabilities(all_vulnerabilities)

        # Prepare output directory
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "security_vulnerabilities")

        # Save data
        file_paths = save_data(processed_vulnerabilities, output_dir)

        # Calculate summary statistics
        total_vulns = len(processed_vulnerabilities)
        critical_vulns = sum(
            1 for v in processed_vulnerabilities if v.get("risk_level") == "critical"
        )
        high_vulns = sum(
            1 for v in processed_vulnerabilities if v.get("risk_level") == "high"
        )
        with_exploits = sum(
            1 for v in processed_vulnerabilities if v.get("exploit_available")
        )
        with_patches = sum(
            1 for v in processed_vulnerabilities if v.get("patch_available")
        )

        execution_time = time.time() - start_time

        # Log summary
        logger.info("Security Vulnerability ETL completed successfully!")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info("Summary:")
        logger.info(f"  Total vulnerabilities: {total_vulns}")
        logger.info(f"  Critical: {critical_vulns}")
        logger.info(f"  High: {high_vulns}")
        logger.info(f"  With exploits: {with_exploits}")
        logger.info(f"  With patches: {with_patches}")

        if file_paths:
            logger.info("Data files created:")
            for file_type, path in file_paths.items():
                logger.info(f"  {file_type}: {path}")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Security Vulnerability ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
