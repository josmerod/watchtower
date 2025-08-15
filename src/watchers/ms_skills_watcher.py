"""Microsoft Applied Skills Watcher.

This module provides the `MSAppliedSkillsWatcher` class, which monitors the
Microsoft Learn website for new or updated "Applied Skills" credentials.
It uses Playwright for dynamic content rendering and detailed information extraction.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from playwright.async_api import (
    Page,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)

# Add the project root to the path to ensure imports work correctly
from src.watchers.base_watcher import BaseWatcher


class MSAppliedSkillsWatcher(BaseWatcher):
    """
    A watcher that monitors Microsoft Applied Skills credentials, including their details.

    This watcher uses Playwright to render the page with JavaScript enabled,
    which allows it to extract data from dynamically rendered content, including navigating
    to detail pages for each skill.
    """

    def __init__(self, name: str = "ms_applied_skills", check_interval: int = 3600):
        """
        Initialize the Microsoft Applied Skills watcher.

        Args:
            name (str): Name for this watcher (default: ms_applied_skills)
            check_interval (int): Time in seconds between checks (default: 1 hour)
        """
        url = "https://learn.microsoft.com/es-es/credentials/browse/?credential_types=applied%20skills"
        super().__init__(name, url, check_interval)

        # Set a more verbose logger for this specific watcher
        self.logger.setLevel(logging.DEBUG)

    def fetch_page(self) -> str:
        """
        This method is a bit of a misnomer now, as the core fetching and processing
        happens within extract_value using Playwright directly.
        It can return an empty string or be reworked if BaseWatcher expects HTML.
        For now, let extract_value handle the async playwright logic directly.
        """
        return (
            ""  # Placeholder, as fetching is now more complex and part of extract_value
        )

    async def _fetch_skill_details(self, skill_url: str, page: Page) -> Dict[str, Any]:
        """
        Fetches and extracts details for a single skill from its dedicated page.

        Args:
            skill_url (str): The URL of the skill's detail page.
            page (Page): An active Playwright Page object to use for navigation.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted details of the skill.
                          Returns an empty dict if details cannot be fetched or parsed.
        """
        details: Dict[str, Any] = {
            "description": None,
            "evaluated_tasks": [],  # List of strings
            "learning_modules_recommended": [],  # List of dicts {name: str, url: str}
            "roles": [],  # List of strings
            "last_updated": None,  # Date string if found
            "error": None,  # Store potential fetching error
        }

        try:
            self.logger.info(f"Navigating to skill detail page: {skill_url}")
            await page.goto(skill_url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)  # Additional wait for dynamic content

            # Extract description (more robustly)
            try:
                # Try OpenGraph description first, then common meta description
                og_desc_element = await page.query_selector(
                    "meta[property='og:description']"
                )
                if og_desc_element:
                    details["description"] = await og_desc_element.get_attribute(
                        "content"
                    )
                else:
                    meta_desc_element = await page.query_selector(
                        "meta[name='description']"
                    )
                    if meta_desc_element:
                        details["description"] = await meta_desc_element.get_attribute(
                            "content"
                        )

                # If still no description, try a common content area
                if not details["description"]:
                    # Common selectors for main content introduction or abstract
                    intro_selectors = [
                        "div[data-bi-name='description']",  # MS Learn specific
                        "#introduction",  # Common ID for intro sections
                        "section[aria-labelledby='introduction']",  # Accessible intro section
                        "div.content-main > p:first-of-type",  # General content paragraph
                        "article > p:first-of-type",  # Article first paragraph
                    ]
                    for selector in intro_selectors:
                        content_element = await page.query_selector(selector)
                        if content_element:
                            details["description"] = (
                                await content_element.inner_text()
                            ).strip()
                            if details["description"]:
                                self.logger.debug(
                                    f"Extracted description for {skill_url} using '{selector}'"
                                )
                                break
                if not details["description"]:
                    self.logger.warning(
                        f"Could not extract detailed description for {skill_url}"
                    )

            except Exception as e_desc:
                self.logger.warning(
                    f"Error extracting description for {skill_url}: {e_desc}"
                )

            # Extract "Skills measured" or "Evaluated tasks"
            try:
                skills_measured_heading_selectors = [
                    "h2:has-text('Skills measured')",
                    "h2:has-text('Habilidades evaluadas')",
                    "#skills-measured",  # Common ID
                    "div[aria-labelledby*='skills-measured']",
                ]
                skills_list_element = None
                for heading_selector in skills_measured_heading_selectors:
                    heading_element = await page.query_selector(heading_selector)
                    if heading_element:
                        # Try to find a ul or ol sibling or child of the heading's parent
                        parent = await heading_element.query_selector("xpath=..")
                        if parent:
                            skills_list_element = await parent.query_selector("ul, ol")
                        if not skills_list_element:
                            skills_list_element = await heading_element.query_selector(
                                "+ ul, + ol"
                            )  # next sibling ul or ol
                        if skills_list_element:
                            self.logger.debug(
                                f"Found skills list for {skill_url} using heading '{heading_selector}'"
                            )
                            break

                if skills_list_element:
                    task_items = await skills_list_element.query_selector_all("li")
                    for item in task_items:
                        task_text = (await item.inner_text()).strip()
                        if task_text:
                            details["evaluated_tasks"].append(task_text)
                else:
                    self.logger.warning(
                        f"Could not find 'Skills measured' list for {skill_url}"
                    )
            except Exception as e_tasks:
                self.logger.warning(
                    f"Error extracting evaluated tasks for {skill_url}: {e_tasks}"
                )

            # --- Extract Learning Modules/Paths ---
            # NOTE: Selectors below are examples and need verification!
            # Inspect the HTML of a skill page (e.g., under "Preparation" or similar sections)
            try:
                module_section_selectors = [
                    "section[aria-labelledby*='prepare']",
                    "section[aria-labelledby*='preparation']",
                    "div[data-bi-name='prepare']",
                    "#prepare-for-the-assessment",  # Example ID
                ]
                learning_modules = []
                module_section = None
                for selector in module_section_selectors:
                    module_section = await page.query_selector(selector)
                    if module_section:
                        self.logger.debug(
                            f"Found learning module section for {skill_url} using '{selector}'"
                        )
                        break

                if module_section:
                    # Find links within the preparation section (adjust selector based on actual structure)
                    module_links = await module_section.query_selector_all(
                        "a[href*='/training/modules/'], a[href*='/training/paths/']"
                    )
                    for link in module_links:
                        module_url = await link.get_attribute("href")
                        module_name = (await link.inner_text()).strip()
                        if module_url and module_name:
                            if not module_url.startswith("http"):
                                module_url = f"https://learn.microsoft.com{module_url}"
                            learning_modules.append(
                                {"name": module_name, "url": module_url}
                            )
                    details["learning_modules_recommended"] = learning_modules
                else:
                    self.logger.warning(
                        f"Could not find learning module section for {skill_url}"
                    )
            except Exception as e_modules:
                self.logger.warning(
                    f"Error extracting learning modules for {skill_url}: {e_modules}"
                )

            # --- Extract Related Roles ---
            # NOTE: Selectors below are examples and need verification!
            # Roles might be listed in a sidebar, header, or dedicated section.
            try:
                role_elements = await page.query_selector_all(
                    "a[href*='/credentials/browse/?roles='] span, div[data-bi-name='roles'] a"
                )
                roles = []
                for role_el in role_elements:
                    role_name = (await role_el.inner_text()).strip()
                    if role_name:
                        roles.append(role_name)
                details["roles"] = list(set(roles))  # Deduplicate
                if roles:
                    self.logger.debug(f"Extracted roles for {skill_url}: {roles}")
            except Exception as e_roles:
                self.logger.warning(
                    f"Error extracting roles for {skill_url}: {e_roles}"
                )

            # --- Extract Last Updated Date ---
            # NOTE: Selectors below are examples and need verification!
            try:
                last_updated_el = await page.query_selector(
                    "div[class*='last-updated'] time, meta[name='updated_at']"
                )
                if last_updated_el:
                    date_str = (
                        await last_updated_el.get_attribute("datetime")
                        or (await last_updated_el.inner_text()).strip()
                    )
                    details["last_updated"] = date_str
                    if date_str:
                        self.logger.debug(
                            f"Extracted last updated date for {skill_url}: {date_str}"
                        )
            except Exception as e_date:
                self.logger.warning(
                    f"Error extracting last updated date for {skill_url}: {e_date}"
                )

            self.logger.info(f"Successfully fetched details for: {skill_url}")
            return details
        except PlaywrightTimeoutError:
            self.logger.error(f"Timeout error fetching skill details for {skill_url}")
            return {"error": "Timeout fetching details"}
        except Exception as e:
            self.logger.error(f"Error fetching skill details for {skill_url}: {str(e)}")
            return {"error": str(e)}

    async def _fetch_and_extract_all_skill_data(self) -> Dict[str, Any]:
        """
        Orchestrates fetching the list of skills and then their individual details.
        Updated to handle dynamic content loading with better waiting strategies and pagination.
        """
        async with async_playwright() as p:
            self.logger.info("Launching browser for MS Skills Watcher")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.set_extra_http_headers(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )

            all_detailed_skills = []
            try:
                self.logger.info(f"Navigating to MS Skills browse page: {self.url}")
                await page.goto(self.url, wait_until="networkidle", timeout=90000)

                # Wait for the dynamic content to load
                self.logger.info("Waiting for dynamic content to load...")

                # Wait for the content browser container to be present
                await page.wait_for_selector(
                    "#content-browser-container", timeout=30000
                )
                self.logger.info("Content browser container found")

                # Wait additional time for JavaScript to render the content
                await page.wait_for_timeout(10000)  # 10 seconds for content to load

                # Try to wait for actual credential cards to appear
                card_selectors = [
                    'div[data-bi-name="card"]',
                    ".card",
                    "article",
                    'div[class*="credential"]',
                ]

                cards_loaded = False
                for selector in card_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=15000)
                        card_count = await page.evaluate(
                            f'document.querySelectorAll("{selector}").length'
                        )
                        if card_count > 0:
                            self.logger.info(
                                f"Found {card_count} cards with selector '{selector}'"
                            )
                            cards_loaded = True
                            break
                    except Exception as e:
                        self.logger.debug(f"Selector '{selector}' not found: {e}")
                        continue

                if not cards_loaded:
                    self.logger.warning(
                        "No credential cards found with standard selectors, proceeding with available content"
                    )

                # Additional wait to ensure all content is fully rendered
                await page.wait_for_timeout(5000)

                # Collect skills from all pages
                page_number = 1
                all_skills_with_urls = []

                while True:
                    self.logger.info(f"Processing page {page_number}")

                    # Get the HTML content for current page
                    html_content = await page.content()
                    self.logger.info(
                        f"Retrieved HTML content for page {page_number} ({len(html_content)} characters)"
                    )

                    # Save HTML for debugging if needed (only first page to avoid clutter)
                    if page_number == 1:
                        self._save_html_content(html_content)

                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(html_content, "html.parser")
                    page_skills = self._extract_skills_with_urls_from_html(soup)

                    if not page_skills:
                        self.logger.warning(
                            f"No Applied Skills found on page {page_number}"
                        )
                        break

                    all_skills_with_urls.extend(page_skills)
                    self.logger.info(
                        f"Found {len(page_skills)} Applied Skills on page {page_number}"
                    )

                    # Check if there's a next page
                    try:
                        # Look for pagination next button
                        next_button_selectors = [
                            "button.pagination-next:not([hidden]):not([disabled])",
                            ".pagination-next:not([hidden]):not([disabled])",
                            'button[aria-label*="Siguientes"]:not([hidden]):not([disabled])',
                            'button[aria-label*="Next"]:not([hidden]):not([disabled])',
                            'a[aria-label*="Siguientes"]:not([hidden]):not([disabled])',
                            'a[aria-label*="Next"]:not([hidden]):not([disabled])',
                        ]

                        next_button = None
                        for selector in next_button_selectors:
                            try:
                                next_button = await page.query_selector(selector)
                                if next_button:
                                    # Check if button is actually visible and clickable
                                    is_visible = await next_button.is_visible()
                                    is_enabled = await next_button.is_enabled()
                                    if is_visible and is_enabled:
                                        self.logger.info(
                                            f"Found next button with selector: {selector}"
                                        )
                                        break
                                    else:
                                        next_button = None
                            except Exception as e:
                                self.logger.debug(
                                    f"Next button selector '{selector}' failed: {e}"
                                )
                                continue

                        if not next_button:
                            # Alternative: look for page 2, 3, etc. buttons
                            page_button_selector = f'button[data-page="{page_number + 1}"]:not([hidden]):not([disabled])'
                            next_button = await page.query_selector(
                                page_button_selector
                            )
                            if next_button:
                                is_visible = await next_button.is_visible()
                                is_enabled = await next_button.is_enabled()
                                if is_visible and is_enabled:
                                    self.logger.info(
                                        f"Found page {page_number + 1} button"
                                    )
                                else:
                                    next_button = None

                        if next_button:
                            self.logger.info(f"Navigating to page {page_number + 1}")
                            await next_button.click()

                            # Wait for the page to load
                            await page.wait_for_timeout(5000)

                            # Wait for content to be updated
                            try:
                                await page.wait_for_function(
                                    f"document.querySelector('.pagination-link.is-current')?.getAttribute('data-page') === '{page_number + 1}' || document.querySelector('.pagination-link.is-current')?.textContent === '{page_number + 1}'",
                                    timeout=10000,
                                )
                            except Exception as e:
                                self.logger.warning(
                                    f"Could not confirm page navigation: {e}"
                                )
                                # Continue anyway as the click might have worked

                            await page.wait_for_timeout(
                                3000
                            )  # Additional wait for content to load
                            page_number += 1
                        else:
                            self.logger.info(
                                f"No more pages found after page {page_number}"
                            )
                            break

                    except Exception as e:
                        self.logger.warning(f"Error checking for next page: {e}")
                        break

                # Remove duplicates based on URL (in case of overlap between pages)
                if all_skills_with_urls:
                    seen_urls = {}
                    for skill in all_skills_with_urls:
                        url = skill["url"]
                        if url not in seen_urls or len(skill["name"]) > len(
                            seen_urls[url]["name"]
                        ):
                            seen_urls[url] = skill
                    all_skills_with_urls = list(seen_urls.values())

                self.logger.info(
                    f"Total unique Applied Skills found across all pages: {len(all_skills_with_urls)}"
                )

                if not all_skills_with_urls:
                    self.logger.error(
                        "No Applied Skills found on any page. This indicates:"
                    )
                    self.logger.error("1. Content is still loading dynamically")
                    self.logger.error("2. Page structure has changed significantly")
                    self.logger.error("3. Applied Skills are not currently available")

                    return {
                        "skills_count": 0,
                        "skills": [],
                        "error": "No Applied Skills found on any page",
                        "extraction_method": "failed",
                        "page_url": self.url,
                    }

                # Process each skill to get detailed information
                for skill_info in all_skills_with_urls:
                    skill_name = skill_info.get("name")
                    skill_detail_url = skill_info.get("url")
                    self.logger.info(
                        f"Processing skill: {skill_name} - URL: {skill_detail_url}"
                    )

                    if not skill_detail_url:
                        self.logger.warning(
                            f"Skipping skill '{skill_name}' due to missing detail URL."
                        )
                        all_detailed_skills.append(
                            {
                                "name": skill_name,
                                "url": None,
                                "details_error": "Missing detail URL",
                                **self._get_empty_skill_details_dict(),
                            }
                        )
                        continue

                    # Ensure full URL
                    if not skill_detail_url.startswith("http"):
                        base_url = "https://learn.microsoft.com"
                        skill_detail_url = f"{base_url}/{skill_detail_url.lstrip('/')}"

                    # Get detailed information for this skill
                    try:
                        skill_details_data = await self._fetch_skill_details(
                            skill_detail_url, page
                        )
                        await asyncio.sleep(2)  # Polite delay between requests
                    except Exception as e:
                        self.logger.error(
                            f"Error fetching details for {skill_name}: {e}"
                        )
                        skill_details_data = {
                            "error": str(e),
                            **self._get_empty_skill_details_dict(),
                        }

                    all_detailed_skills.append(
                        {
                            "name": skill_name,
                            "url": skill_detail_url,
                            **skill_details_data,
                        }
                    )

                return {
                    "skills_count": len(all_detailed_skills),
                    "skills": all_detailed_skills,
                    "extraction_method": "playwright_dynamic_paginated",
                    "page_url": self.url,
                    "pages_processed": page_number,
                }

            except Exception as e:
                self.logger.error(
                    f"General error in _fetch_and_extract_all_skill_data: {e}",
                    exc_info=True,
                )
                return {
                    "skills_count": 0,
                    "skills": [],
                    "error": str(e),
                    "extraction_method": "failed",
                    "page_url": self.url,
                }
            finally:
                self.logger.info("Closing browser for MS Skills Watcher")
                await browser.close()

    def _save_html_content(self, html_content: str) -> None:
        """Save HTML content to file for debugging purposes."""
        try:
            debug_dir = Path(self.events_dir) / "debug"
            debug_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = debug_dir / f"ms_skills_page_{timestamp}.html"

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            self.logger.info(f"Saved HTML content to {debug_file} for debugging")

            # Keep only the last 5 debug files
            debug_files = sorted(debug_dir.glob("ms_skills_page_*.html"))
            if len(debug_files) > 5:
                for old_file in debug_files[:-5]:
                    old_file.unlink()
                    self.logger.debug(f"Removed old debug file: {old_file}")

        except Exception as e:
            self.logger.warning(f"Could not save HTML content for debugging: {e}")

    def _get_empty_skill_details_dict(self) -> Dict[str, Any]:
        """Return empty skill details dictionary with default values."""
        return {
            "description": None,
            "skills_learned": [],
            "prerequisites": [],
            "level": None,
            "products": [],
            "roles": [],
            "duration": None,
            "type": "Applied Skills",
            "last_updated": None,
        }

    def extract_value(self, html_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts the list of Microsoft Applied Skills and their details.
        This method now orchestrates the entire Playwright-based fetching and extraction.
        The html_content argument from BaseWatcher is largely ignored here.
        """
        self.logger.info("Starting extraction for MS Applied Skills details.")
        try:
            extracted_data = asyncio.run(self._fetch_and_extract_all_skill_data())

            if (
                not extracted_data
                or "skills" not in extracted_data
                or extracted_data.get("skills_count", 0) == 0
            ):
                self.logger.error("No skills data extracted or skills list is empty.")
                return {
                    "skills_count": 0,
                    "skills": [],
                    "error": extracted_data.get("error", "No data extracted"),
                }

            self.logger.info(
                f"Successfully extracted {extracted_data.get('skills_count')} skills with details."
            )
            return extracted_data

        except Exception as e:
            self.logger.error(
                f"Error in extract_value for MSAppliedSkills: {str(e)}", exc_info=True
            )
            return {"skills_count": 0, "skills": [], "error": str(e)}

    def _extract_skills_with_urls_from_html(
        self, soup: BeautifulSoup
    ) -> List[Dict[str, str]]:
        """
        Extracts skill names and their detail page URLs from the browse page HTML.
        Updated for dynamic content loading (JavaScript-rendered page).
        """
        skills_with_urls: List[Dict[str, str]] = []

        # The page loads content dynamically, so we need to search for the actual rendered content
        # Based on the structure seen in the browser, certificates appear as individual cards

        # Updated selectors for the actual rendered content structure
        skill_card_selectors = [
            # Generic card selectors that should catch the rendered content
            'div[data-bi-name="card"]',  # Main card container
            ".card",  # Generic card class
            "article",  # Article elements that might contain the cards
            '[role="article"]',  # ARIA role for articles
            'div[class*="card"]',  # Any div with card in the class name
            'div[data-testid*="card"]',  # Test ID patterns
            'div[class*="credential"]',  # Credential-specific containers
            'li[data-bi-name*="card"]',  # List items that might be cards
            'div[data-bi-name*="credential"]',  # BI name patterns
        ]

        found_cards = []

        # First, try to find the container and any cards within it
        content_container = soup.select_one(
            '#content-browser-container, [data-bi-name="content-browser"]'
        )
        if content_container:
            self.logger.info("Found content browser container")

            # Look for cards within the container
            for selector in skill_card_selectors:
                cards = content_container.select(selector)
                if cards:
                    self.logger.info(
                        f"Found {len(cards)} cards using selector: '{selector}' within container"
                    )
                    found_cards.extend(cards)
                    break
        else:
            self.logger.warning(
                "Content browser container not found, searching entire page"
            )

            # Search entire page
            for selector in skill_card_selectors:
                cards = soup.select(selector)
                if cards:
                    self.logger.info(
                        f"Found {len(cards)} cards using selector: '{selector}' on entire page"
                    )
                    found_cards.extend(cards)
                    break

        if not found_cards:
            self.logger.warning(
                "No cards found with any selector. Content might not be loaded yet."
            )
            return []

        # Remove duplicates while preserving order
        seen_cards = set()
        unique_cards = []
        for card in found_cards:
            card_html = str(card)
            if card_html not in seen_cards:
                seen_cards.add(card_html)
                unique_cards.append(card)

        found_cards = unique_cards
        self.logger.info(f"Processing {len(found_cards)} unique cards")

        # Process each card to extract skill information
        for card in found_cards:
            try:
                skill_url = None
                skill_name = None

                # Look for links within the card that point to applied skills
                link_selectors = [
                    'a[href*="/credentials/applied-skills/"]',  # Direct applied skills links
                    'a[href*="applied-skills"]',  # Any applied skills links
                    'a[href*="/credentials/"]',  # General credentials links
                    'a[data-bi-name*="title"]',  # Title links with BI names
                    'a[role="button"]',  # Links styled as buttons
                    "h3 a, h2 a, h4 a",  # Heading links
                    "a",  # Any link as last resort
                ]

                link_element = None
                for link_selector in link_selectors:
                    link_element = card.select_one(link_selector)
                    if link_element and link_element.get("href"):
                        href = link_element.get("href", "")
                        # Prefer applied-skills links
                        if "applied-skills" in href.lower():
                            skill_url = href
                            break
                        elif "/credentials/" in href and not skill_url:
                            skill_url = href

                if not skill_url and link_element:
                    skill_url = link_element.get("href", "")

                # Look for skill name in various elements
                name_selectors = [
                    "h1, h2, h3, h4, h5, h6",  # Any heading
                    '[data-bi-name*="title"]',  # BI name title elements
                    ".title, .card-title",  # Title classes
                    'a[href*="applied-skills"]',  # Link text for applied skills
                    '[role="heading"]',  # ARIA heading role
                    "strong",  # Strong emphasis
                    "b",  # Bold text
                ]

                for name_selector in name_selectors:
                    title_element = card.select_one(name_selector)
                    if title_element:
                        candidate_name = title_element.get_text(strip=True)
                        # Look for actual skill names (longer than just "Applied Skills")
                        if (
                            candidate_name
                            and len(candidate_name) > 15
                            and "applied skills" in candidate_name.lower()
                        ):
                            skill_name = candidate_name
                            break
                        elif (
                            candidate_name
                            and len(candidate_name) > 10
                            and not skill_name
                        ):
                            skill_name = candidate_name

                # If no good name found, try getting it from the link
                if not skill_name and link_element:
                    skill_name = link_element.get_text(strip=True)

                # Clean up the skill name
                if skill_name:
                    # Remove common prefixes/suffixes
                    prefixes_to_remove = [
                        "Microsoft Applied Skills: ",
                        "Applied Skills: ",
                        "Microsoft: ",
                        "APPLIED SKILLS",
                    ]

                    for prefix in prefixes_to_remove:
                        if skill_name.startswith(prefix):
                            skill_name = skill_name[len(prefix) :].strip()

                    # Remove trailing text that's not part of the title
                    skill_name = skill_name.split("\n")[
                        0
                    ].strip()  # Take first line only

                # Validate we found both name and URL
                if not skill_name or not skill_url:
                    self.logger.debug(
                        f"Skipping card - Name: '{skill_name}', URL: '{skill_url}'"
                    )
                    continue

                # Ensure full URL
                if skill_url.startswith("/"):
                    skill_url = "https://learn.microsoft.com" + skill_url
                elif not skill_url.startswith("http"):
                    skill_url = "https://learn.microsoft.com/" + skill_url.lstrip("/")

                # Only include Applied Skills (filter out other credentials)
                if "applied-skills" not in skill_url.lower():
                    self.logger.debug(
                        f"Skipping non-Applied Skills credential: {skill_name}"
                    )
                    continue

                skills_with_urls.append(
                    {"name": skill_name.strip(), "url": skill_url.strip()}
                )

                self.logger.debug(
                    f"Extracted Applied Skill: '{skill_name}' -> {skill_url}"
                )

            except Exception as e:
                self.logger.warning(f"Error processing card: {e}")
                continue

        # Deduplicate based on URL
        if skills_with_urls:
            seen_urls = {}
            for skill in skills_with_urls:
                url = skill["url"]
                if url not in seen_urls or len(skill["name"]) > len(
                    seen_urls[url]["name"]
                ):
                    seen_urls[url] = skill

            skills_with_urls = list(seen_urls.values())

        self.logger.info(
            f"Successfully extracted {len(skills_with_urls)} unique Applied Skills"
        )

        # If we didn't find any Applied Skills, log some debug info
        if not skills_with_urls:
            self.logger.warning("No Applied Skills found. Debug info:")
            all_links = soup.select("a[href]")
            applied_skills_links = [
                link
                for link in all_links
                if "applied-skills" in link.get("href", "").lower()
            ]
            self.logger.warning(f"Total links found: {len(all_links)}")
            self.logger.warning(
                f"Applied Skills links found: {len(applied_skills_links)}"
            )

            if applied_skills_links:
                for i, link in enumerate(applied_skills_links[:3]):  # Show first 3
                    self.logger.warning(
                        f"Sample Applied Skills link {i + 1}: {link.get('href')} - Text: '{link.get_text(strip=True)[:50]}'"
                    )

        return skills_with_urls

    def has_changed(self, old_value: Dict[str, Any], new_value: Dict[str, Any]) -> bool:
        """
        Check if the list of skills or their details have changed.
        Compares the number of skills and the set of skill names and their detail URLs.
        A more robust check would involve hashing the details of each skill.
        """
        if (
            not old_value
            or not new_value
            or "skills" not in old_value
            or "skills" not in new_value
        ):
            self.logger.info(
                "Old or new value is malformed or missing 'skills' key, considering it changed."
            )
            return True  # Or handle as an error

        old_skills_list = old_value.get("skills", [])
        new_skills_list = new_value.get("skills", [])

        if len(old_skills_list) != len(new_skills_list):
            self.logger.info(
                f"Number of skills changed: {len(old_skills_list)} -> {len(new_skills_list)}"
            )
            return True

        # Create sets of (name, url) tuples for comparison, handling both old and new formats
        old_skill_ids = set()
        for skill in old_skills_list:
            if isinstance(skill, dict):
                # Handle both new format (name) and old format (title)
                name = skill.get("name", skill.get("title", ""))
                url = skill.get("url", "")
                old_skill_ids.add((name, url))
            elif isinstance(skill, str):
                old_skill_ids.add((skill, ""))

        new_skill_ids = set()
        for skill in new_skills_list:
            if isinstance(skill, dict):
                # Handle both new format (name) and old format (title)
                name = skill.get("name", skill.get("title", ""))
                url = skill.get("url", "")
                new_skill_ids.add((name, url))
            elif isinstance(skill, str):
                new_skill_ids.add((skill, ""))

        if old_skill_ids != new_skill_ids:
            self.logger.info("Set of skill names/URLs changed.")
            # Log differences for clarity
            self.logger.debug(
                f"Skills only in old data: {old_skill_ids - new_skill_ids}"
            )
            self.logger.debug(
                f"Skills only in new data: {new_skill_ids - old_skill_ids}"
            )
            return True

        # If name/URL sets are the same, check if details within skills have changed (optional, can be intensive)
        # For now, if counts and name/URL sets are same, assume no change for simplicity.
        # To implement detailed check: iterate through new_skills_list, find corresponding in old_skills_list by name/url,
        # then compare their detail dictionaries.
        self.logger.info(
            "No significant change detected in skill count or basic skill identifiers."
        )
        return False

    def trigger_alarm(self, old_value: Dict[str, Any], new_value: Dict[str, Any]):
        """
        Trigger an alarm when the number of skills changes.

        Args:
            old_value (dict): Previous count and skills
            new_value (dict): Current count and skills
        """
        # Handle both old format (count) and new format (skills_count)
        old_count = old_value.get("skills_count", old_value.get("count", 0))
        new_count = new_value.get("skills_count", new_value.get("count", 0))

        # Extract skill titles, handling both new format (dict with name) and old format (strings or title)
        old_skill_titles = set()
        for skill in old_value.get("skills", []):
            if isinstance(skill, dict):
                # Handle both new format (name) and old format (title)
                skill_name = skill.get("name", skill.get("title", ""))
                if skill_name:
                    old_skill_titles.add(skill_name)
            elif isinstance(skill, str):
                old_skill_titles.add(skill)

        new_skill_titles = set()
        for skill in new_value.get("skills", []):
            if isinstance(skill, dict):
                # Handle both new format (name) and old format (title)
                skill_name = skill.get("name", skill.get("title", ""))
                if skill_name:
                    new_skill_titles.add(skill_name)
            elif isinstance(skill, str):
                new_skill_titles.add(skill)

        added_skills = list(new_skill_titles - old_skill_titles)
        removed_skills = list(old_skill_titles - new_skill_titles)

        # Include extraction methods in the details
        details = {
            "change_type": (
                "count_changed" if old_count != new_count else "skills_changed"
            ),
            "added_skills": added_skills,
            "removed_skills": removed_skills,
            "old_extraction_method": old_value.get("extraction_method", "unknown"),
            "new_extraction_method": new_value.get("extraction_method", "unknown"),
        }

        # Record the event with details
        event = self._record_event(
            event_type="ms_applied_skills_changed",
            old_value=old_value,
            new_value=new_value,
            details=details,
        )

        # Log appropriate message
        if old_count < new_count:
            message = f"Microsoft Applied Skills INCREASED: {old_count} -> {new_count}"
            if added_skills:
                message += f"\nNew skills: {', '.join(added_skills)}"
        elif old_count > new_count:
            message = f"Microsoft Applied Skills DECREASED: {old_count} -> {new_count}"
            if removed_skills:
                message += f"\nRemoved skills: {', '.join(removed_skills)}"
        else:
            message = f"Microsoft Applied Skills changed but count remained the same: {old_count}"
            if added_skills:
                message += f"\nNew skills: {', '.join(added_skills)}"
            if removed_skills:
                message += f"\nRemoved skills: {', '.join(removed_skills)}"

        self.logger.warning(message)

        # TODO: Implement notification mechanisms here
        # For now, just log the event

    def _get_browse_page_html(self, browse_url: str) -> Optional[str]:
        """
        Fetch the HTML content of the browse page with improved error handling and modern headers.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        try:
            self.logger.info(f"Fetching browse page: {browse_url}")

            # Add session for better connection handling
            session = requests.Session()
            session.headers.update(headers)

            # Try the request with timeout and retries
            for attempt in range(3):
                try:
                    response = session.get(browse_url, timeout=30, allow_redirects=True)

                    if response.status_code == 200:
                        self.logger.info(
                            f"Successfully fetched browse page (attempt {attempt + 1})"
                        )
                        content = response.text

                        # Basic validation of content
                        if (
                            "microsoft.com" in content
                            or "Applied Skills" in content
                            or "credentials" in content
                        ):
                            self.logger.debug(
                                f"Page content looks valid (length: {len(content)} chars)"
                            )
                            return content
                        else:
                            self.logger.warning(
                                f"Page content doesn't look like Microsoft Learn page (attempt {attempt + 1})"
                            )
                            if attempt == 2:  # Last attempt
                                self.logger.debug(
                                    f"Content preview: {content[:500]}..."
                                )
                            continue

                    elif response.status_code == 429:
                        self.logger.warning(
                            f"Rate limited (429) - waiting before retry (attempt {attempt + 1})"
                        )
                        time.sleep(5 * (attempt + 1))  # Exponential backoff
                        continue

                    elif response.status_code in [503, 502, 504]:
                        self.logger.warning(
                            f"Server error {response.status_code} - retrying (attempt {attempt + 1})"
                        )
                        time.sleep(2 * (attempt + 1))
                        continue

                    else:
                        self.logger.error(
                            f"HTTP {response.status_code} error fetching browse page (attempt {attempt + 1})"
                        )
                        if attempt == 2:  # Last attempt
                            self.logger.error(
                                f"Response content preview: {response.text[:500]}..."
                            )
                        continue

                except requests.exceptions.Timeout:
                    self.logger.warning(
                        f"Timeout fetching browse page (attempt {attempt + 1})"
                    )
                    if attempt < 2:
                        time.sleep(5)
                        continue

                except requests.exceptions.ConnectionError:
                    self.logger.warning(
                        f"Connection error fetching browse page (attempt {attempt + 1})"
                    )
                    if attempt < 2:
                        time.sleep(10)
                        continue

                except Exception as e:
                    self.logger.error(
                        f"Unexpected error fetching browse page (attempt {attempt + 1}): {e}"
                    )
                    if attempt < 2:
                        time.sleep(5)
                        continue

            self.logger.error("Failed to fetch browse page after all attempts")
            return None

        except Exception as e:
            self.logger.error(f"Critical error in _get_browse_page_html: {e}")
            return None
        finally:
            try:
                session.close()
            except:
                pass


if __name__ == "__main__":
    import asyncio

    # Set up logging level
    import logging
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    # Create and run the watcher
    watcher = MSAppliedSkillsWatcher()

    print("🔍 Running MS Skills Watcher once...")
    try:
        # Run the extraction once
        result = watcher.extract_value()

        # Publish the result as JSON to stdout
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Optionally, print a summary to stderr
        print(f"\n✅ Extraction completed!", file=sys.stderr)
        print(
            f"📊 Found {result.get('skills_count', 0)} Applied Skills", file=sys.stderr
        )

        if result.get("error"):
            print(f"⚠️  Error occurred: {result['error']}", file=sys.stderr)

        # Check if debug files were created
        debug_dir = Path("data/watchers/ms_applied_skills/events/debug")
        if debug_dir.exists():
            debug_files = list(debug_dir.glob("*.html"))
            if debug_files:
                latest_debug = max(debug_files, key=lambda p: p.stat().st_mtime)
                print(f"🔧 Debug HTML saved to: {latest_debug}", file=sys.stderr)

    except Exception as e:
        print(f"❌ Error running watcher: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
