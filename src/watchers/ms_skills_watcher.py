import re
import time
import logging
import asyncio
import os
import sys
from typing import Any, Optional, Dict, List
from bs4 import BeautifulSoup
import requests
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.watchers.base_watcher import BaseWatcher


class MSAppliedSkillsWatcher(BaseWatcher):
    """
    A watcher that monitors Microsoft Applied Skills credentials, including their details.
    
    This watcher uses Playwright to render the page with JavaScript enabled,
    which allows it to extract data from dynamically rendered content, including navigating
    to detail pages for each skill.
    """
    
    # Known skills as of implementation - used as fallback when scraping fails
    KNOWN_SKILLS = [
        "Microsoft 365 Copilot",
        "Azure Virtual Desktop",
        "Windows Server Hybrid Administrator",
        "Azure Support Engineer for Connectivity Specialty",
        "Implementing and Managing Microsoft 365 Security Solutions",
        "Microsoft Security Operations Analyst",
        "Manage Microsoft 365 Apps in Enterprise Deployments",
        "Microsoft 365 Messaging Administrator",
        "Azure AI Engineer",
        "Azure Data Scientist",
        "Azure Data Engineer",
        "Azure Database Administrator",
        "Azure Developer",
        "Azure Administrator",
        "Microsoft 365 Developer",
        "Microsoft 365 Teams Administrator",
        "Microsoft 365 Modern Desktop Administrator",
        "Microsoft 365 Enterprise Administrator",
        "Microsoft 365 Security Administrator",
        "Windows Server Administrator",
        "Windows Client Administrator",
        "Microsoft Identity and Access Administrator",
        "Microsoft Information Protection Administrator",
        "Microsoft Azure IoT Developer",
    ]
    
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
        return "" # Placeholder, as fetching is now more complex and part of extract_value
    
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
            "evaluated_tasks": [], # List of strings
            "learning_modules_recommended": [], # List of dicts {name: str, url: str}
            "roles": [], # List of strings
            "last_updated": None, # Date string if found
            "error": None # Store potential fetching error
        }

        try:
            self.logger.info(f"Navigating to skill detail page: {skill_url}")
            await page.goto(skill_url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000) # Additional wait for dynamic content

            # Extract description (more robustly)
            try:
                # Try OpenGraph description first, then common meta description
                og_desc_element = await page.query_selector("meta[property='og:description']")
                if og_desc_element:
                    details["description"] = await og_desc_element.get_attribute("content")
                else:
                    meta_desc_element = await page.query_selector("meta[name='description']")
                    if meta_desc_element:
                        details["description"] = await meta_desc_element.get_attribute("content")
                
                # If still no description, try a common content area
                if not details["description"]:
                    # Common selectors for main content introduction or abstract
                    intro_selectors = [
                        "div[data-bi-name='description']", # MS Learn specific
                        "#introduction",                  # Common ID for intro sections
                        "section[aria-labelledby='introduction']", # Accessible intro section
                        "div.content-main > p:first-of-type", # General content paragraph
                        "article > p:first-of-type" # Article first paragraph
                    ]
                    for selector in intro_selectors:
                        content_element = await page.query_selector(selector)
                        if content_element:
                            details["description"] = (await content_element.inner_text()).strip()
                            if details["description"]: 
                                self.logger.debug(f"Extracted description for {skill_url} using '{selector}'")
                                break 
                if not details["description"]:
                    self.logger.warning(f"Could not extract detailed description for {skill_url}")

            except Exception as e_desc:
                self.logger.warning(f"Error extracting description for {skill_url}: {e_desc}")

            # Extract "Skills measured" or "Evaluated tasks"
            try:
                skills_measured_heading_selectors = [
                    "h2:has-text('Skills measured')", 
                    "h2:has-text('Habilidades evaluadas')",
                    "#skills-measured", # Common ID
                    "div[aria-labelledby*='skills-measured']"
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
                             skills_list_element = await heading_element.query_selector("+ ul, + ol") # next sibling ul or ol
                        if skills_list_element:
                            self.logger.debug(f"Found skills list for {skill_url} using heading '{heading_selector}'")
                            break
                
                if skills_list_element:
                    task_items = await skills_list_element.query_selector_all("li")
                    for item in task_items:
                        task_text = (await item.inner_text()).strip()
                        if task_text: details["evaluated_tasks"].append(task_text)
                else:
                    self.logger.warning(f"Could not find 'Skills measured' list for {skill_url}")
            except Exception as e_tasks:
                self.logger.warning(f"Error extracting evaluated tasks for {skill_url}: {e_tasks}")

            # --- Extract Learning Modules/Paths --- 
            # NOTE: Selectors below are examples and need verification!
            # Inspect the HTML of a skill page (e.g., under "Preparation" or similar sections)
            try:
                module_section_selectors = [
                    "section[aria-labelledby*='prepare']", 
                    "section[aria-labelledby*='preparation']",
                    "div[data-bi-name='prepare']",
                    "#prepare-for-the-assessment" # Example ID
                ]
                learning_modules = []
                module_section = None
                for selector in module_section_selectors:
                    module_section = await page.query_selector(selector)
                    if module_section: 
                        self.logger.debug(f"Found learning module section for {skill_url} using '{selector}'")
                        break
                
                if module_section:
                    # Find links within the preparation section (adjust selector based on actual structure)
                    module_links = await module_section.query_selector_all("a[href*='/training/modules/'], a[href*='/training/paths/']")
                    for link in module_links:
                         module_url = await link.get_attribute("href")
                         module_name = (await link.inner_text()).strip()
                         if module_url and module_name:
                            if not module_url.startswith("http"):
                                module_url = f"https://learn.microsoft.com{module_url}"
                            learning_modules.append({"name": module_name, "url": module_url})
                    details["learning_modules_recommended"] = learning_modules
                else:
                    self.logger.warning(f"Could not find learning module section for {skill_url}")
            except Exception as e_modules:
                self.logger.warning(f"Error extracting learning modules for {skill_url}: {e_modules}")

            # --- Extract Related Roles --- 
            # NOTE: Selectors below are examples and need verification!
            # Roles might be listed in a sidebar, header, or dedicated section.
            try:
                role_elements = await page.query_selector_all("a[href*='/credentials/browse/?roles='] span, div[data-bi-name='roles'] a")
                roles = []
                for role_el in role_elements:
                    role_name = (await role_el.inner_text()).strip()
                    if role_name: roles.append(role_name)
                details["roles"] = list(set(roles)) # Deduplicate
                if roles: self.logger.debug(f"Extracted roles for {skill_url}: {roles}")
            except Exception as e_roles:
                 self.logger.warning(f"Error extracting roles for {skill_url}: {e_roles}")

            # --- Extract Last Updated Date --- 
            # NOTE: Selectors below are examples and need verification!
            try:
                 last_updated_el = await page.query_selector("div[class*='last-updated'] time, meta[name='updated_at']")
                 if last_updated_el:
                     date_str = await last_updated_el.get_attribute("datetime") or (await last_updated_el.inner_text()).strip()
                     details["last_updated"] = date_str
                     if date_str: self.logger.debug(f"Extracted last updated date for {skill_url}: {date_str}")
            except Exception as e_date:
                 self.logger.warning(f"Error extracting last updated date for {skill_url}: {e_date}")

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
        """
        async with async_playwright() as p:
            self.logger.info("Launching browser for MS Skills Watcher")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            })

            all_detailed_skills = []
            try:
                self.logger.info(f"Navigating to MS Skills browse page: {self.url}")
                await page.goto(self.url, wait_until="networkidle", timeout=90000)
                await page.wait_for_timeout(5000)
                
                # --- Pagination logic (adapted from original _fetch_with_playwright) --- 
                list_page_html_accumulator = ""
                page_num = 1
                max_pages_to_scrape = 5 # Safety limit

                while page_num <= max_pages_to_scrape:
                    self.logger.info(f"Processing MS Skills list page {page_num}")
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000) # ensure scripts run
                    list_page_html_accumulator += await page.content()

                    # Try to find and click the next page button
                    next_button_selectors = [
                        'a[aria-label="Next page"], a[aria-label="Página siguiente"]', 
                        'button[aria-label="Next page"], button[aria-label="Página siguiente"]',
                        '.pagination .next a', '.pager .next a' 
                    ]
                    next_button_found_and_clicked = False
                    for selector in next_button_selectors:
                        next_button = await page.query_selector(selector)
                        if next_button and await next_button.is_visible() and await next_button.is_enabled():
                            try:
                                self.logger.info(f"Found next page button with selector: {selector}. Clicking...")
                                await next_button.click()
                                await page.wait_for_load_state("networkidle", timeout=60000)
                                await page.wait_for_timeout(3000) # Wait for new content
                                next_button_found_and_clicked = True
                                page_num += 1
                                break # Found and clicked
                            except Exception as click_err:
                                self.logger.warning(f"Error clicking next button ({selector}): {click_err}")
                        # else: self.logger.debug(f"Selector '{selector}' not found or not clickable.")
                    
                    if not next_button_found_and_clicked:
                        self.logger.info("No more next page buttons found or clickable, or max pages reached.")
                        break
                # --- End Pagination logic --- 

                soup = BeautifulSoup(list_page_html_accumulator, 'html.parser')
                initial_skills_with_urls = self._extract_skills_with_urls_from_html(soup)
                self.logger.info(f"Found {len(initial_skills_with_urls)} skills on the list page(s) after pagination attempt.")

                for skill_info in initial_skills_with_urls:
                    skill_name = skill_info.get("name")
                    skill_detail_url = skill_info.get("url")
                    self.logger.info(f"Processing skill: {skill_name} - URL: {skill_detail_url}")

                    if not skill_detail_url:
                        self.logger.warning(f"Skipping skill '{skill_name}' due to missing detail URL.")
                        all_detailed_skills.append({"name": skill_name, "url": None, "details_error": "Missing detail URL", **self._get_empty_skill_details_dict()})
                        continue
                    
                    # Ensure full URL (already handled in _extract_skills_with_urls_from_html, but good for safety)
                    if not skill_detail_url.startswith("http"):
                        base_url = "https://learn.microsoft.com"
                        skill_detail_url = f"{base_url}{skill_detail_url.lstrip('/')}"

                    skill_details_data = await self._fetch_skill_details(skill_detail_url, page)
                    
                    await asyncio.sleep(1) # Polite delay

                    all_detailed_skills.append({
                        "name": skill_name,
                        "url": skill_detail_url,
                        **skill_details_data
                    })
                
                return {"skills_count": len(all_detailed_skills), "skills": all_detailed_skills}

            except Exception as e:
                self.logger.error(f"General error in _fetch_and_extract_all_skill_data: {e}", exc_info=True)
                return {"skills_count": 0, "skills": [], "error": str(e)}
            finally:
                self.logger.info("Closing browser for MS Skills Watcher")
                await browser.close()
    
    def _get_empty_skill_details_dict(self) -> Dict[str, Any]:
        """Returns a dictionary with None values for all skill detail fields."""
        return {
            "description": None,
            "evaluated_tasks": [],
            "learning_modules_recommended": [],
            "roles": [],
            "last_updated": None,
            "error": None # Can be used if fetching this specific skill failed
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
            
            if not extracted_data or "skills" not in extracted_data or extracted_data.get("skills_count", 0) == 0:
                self.logger.warning("No skills data extracted or skills list is empty. Considering fallback.")
                # return self._fallback_extraction() # Ensure fallback is compatible or updated
                return {"skills_count": 0, "skills": [], "error": extracted_data.get("error", "No data extracted")}
            
            self.logger.info(f"Successfully extracted {extracted_data.get('skills_count')} skills with details.")
            return extracted_data

        except Exception as e:
            self.logger.error(f"Error in extract_value for MSAppliedSkills: {str(e)}", exc_info=True)
            return {"skills_count": 0, "skills": [], "error": str(e)}

    def _extract_skills_with_urls_from_html(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extracts skill names and their detail page URLs from the browse page HTML.
        """
        skills_with_urls: List[Dict[str, str]] = []
        # Primary selector based on typical structure of MS Learn credential browse pages
        # These cards usually contain an <a> tag with data-bi-cn (unique name) and the href. 
        # The text/title is often within this <a> or a child h3/div.
        skill_link_elements = soup.select('a[data-bi-cn^="applied-skill."][href*="/credentials/applied-skills/"]')

        if not skill_link_elements:
            # Fallback to more generic card selectors if the specific one fails
            self.logger.info("Primary selector for skill links failed. Trying generic card selectors...")
            # These selectors target a broader card element, then we find the link and title inside.
            generic_card_item_selectors = [
                "div.card.credential-card", # Common card structure
                "li[role='listitem'] article", # List item structure
                "div[class*='credential-card']", # Class name containing 'credential-card'
                "div[class*='card'][class*='credential']" # Contains both 'card' and 'credential'
            ]
            container_elements = []
            for selector in generic_card_item_selectors:
                container_elements = soup.select(selector)
                if container_elements:
                    self.logger.info(f"Found {len(container_elements)} skill containers using fallback selector: '{selector}'")
                    break
            
            if not container_elements:
                self.logger.warning("Could not find skill containers/links on the browse page using any known selectors.")
                return []

            # Process containers found by fallback selectors
            for container in container_elements:
                link_element = container.select_one('a[href*="/credentials/applied-skills/"]')
                if not link_element:
                    link_element = container.select_one('a[href*="/credentials/"]') # Broader link if specific AS not found
                
                if link_element and link_element.get('href'):
                    skill_url = link_element['href']
                    skill_name = None
                    # Try to find name from h3, then specific title divs, then link's text or aria-label
                    name_el = container.select_one('h3, h2, div[class*="card-title" i], div[class*="title" i]')
                    if name_el:
                        skill_name = name_el.get_text(strip=True)
                    if not skill_name:
                         skill_name = link_element.get_text(strip=True)
                    if not skill_name:
                        skill_name = link_element.get('aria-label', "Unnamed Skill")
                    
                    if not skill_url.startswith("http"):
                        skill_url = "https://learn.microsoft.com" + skill_url.lstrip('/')
                    skills_with_urls.append({"name": skill_name.strip(), "url": skill_url.strip()})
                    self.logger.debug(f"Extracted (fallback container): Name='{skill_name.strip()}', URL='{skill_url.strip()}'")
                else:
                    self.logger.debug(f"No usable link found in fallback container: {container.select_one('h3,h2').get_text(strip=True) if container.select_one('h3,h2') else 'Unknown container'}")

        else: # Process links found by primary selector
            self.logger.info(f"Found {len(skill_link_elements)} skill links using primary selector.")
            for link_element in skill_link_elements:
                skill_url = link_element['href']
                skill_name = None
                # Try to find name from a nested h3 or title-like div first
                name_el = link_element.select_one('h3, div[class*="card-title" i], div[class*="title" i]')
                if name_el:
                    skill_name = name_el.get_text(strip=True)
                if not skill_name:
                    skill_name = link_element.get_text(strip=True) # Text of the link itself
                if not skill_name:
                    skill_name = link_element.get('data-bi-cn').replace("applied-skill.", "").replace("-", " ").title() # From data-bi-cn
                if not skill_name:
                    skill_name = "Unnamed Skill (from URL)"

                if not skill_url.startswith("http"):
                     skill_url = "https://learn.microsoft.com" + skill_url.lstrip('/')
                skills_with_urls.append({"name": skill_name.strip(), "url": skill_url.strip()})
                self.logger.debug(f"Extracted (primary link): Name='{skill_name.strip()}', URL='{skill_url.strip()}'")

        if not skills_with_urls:
            self.logger.warning("No skills with URLs were extracted from the HTML content after all attempts.")
        else:
             # Deduplicate based on URL, prefering entries with more complete names if collision
            seen_urls = {}
            deduplicated_skills = []
            for skill in skills_with_urls:
                if skill["url"] not in seen_urls or len(skill["name"]) > len(seen_urls[skill["url"]]["name"]):
                    seen_urls[skill["url"]] = skill
            deduplicated_skills = list(seen_urls.values())
            if len(deduplicated_skills) < len(skills_with_urls):
                self.logger.info(f"Deduplicated skills list from {len(skills_with_urls)} to {len(deduplicated_skills)} based on URL.")
            skills_with_urls = deduplicated_skills
            
        return skills_with_urls

    def _extract_skills_from_html(self, soup: BeautifulSoup) -> list:
        """
        DEPRECATED / TO BE REMOVED or REPURPOSED.
        Original method to extract only skill names. 
        New logic uses _extract_skills_with_urls_from_html.
        """
        self.logger.warning("_extract_skills_from_html is deprecated and should be removed.")
        return [] # No longer used for primary extraction
    
    def _fallback_extraction(self) -> Dict[str, Any]:
        """Fallback method when extraction fails, using known skills list."""
        self.logger.warning("Using fallback extraction with known skills list")
        # Convert the KNOWN_SKILLS list to the new format
        skills_with_urls = [{"title": skill, "url": None} for skill in self.KNOWN_SKILLS]
        return {
            "count": len(skills_with_urls),
            "skills": skills_with_urls,
            "extraction_method": "fallback",
            "url": self.url  # Include the URL in the state
        }
    
    def has_changed(self, old_value: Dict[str, Any], new_value: Dict[str, Any]) -> bool:
        """
        Check if the list of skills or their details have changed.
        Compares the number of skills and the set of skill names and their detail URLs.
        A more robust check would involve hashing the details of each skill.
        """
        if not old_value or not new_value or "skills" not in old_value or "skills" not in new_value:
            self.logger.info("Old or new value is malformed or missing 'skills' key, considering it changed.")
            return True # Or handle as an error

        old_skills_list = old_value.get("skills", [])
        new_skills_list = new_value.get("skills", [])

        if len(old_skills_list) != len(new_skills_list):
            self.logger.info(f"Number of skills changed: {len(old_skills_list)} -> {len(new_skills_list)}")
            return True

        # Create sets of (name, url) tuples for comparison, and then compare details if name/url match
        # This is a simplified comparison. For deep comparison, one might hash content of details.
        old_skill_ids = {(s.get("name"), s.get("url")) for s in old_skills_list}
        new_skill_ids = {(s.get("name"), s.get("url")) for s in new_skills_list}

        if old_skill_ids != new_skill_ids:
            self.logger.info("Set of skill names/URLs changed.")
            # Log differences for clarity
            self.logger.debug(f"Skills only in old data: {old_skill_ids - new_skill_ids}")
            self.logger.debug(f"Skills only in new data: {new_skill_ids - old_skill_ids}")
            return True
        
        # If name/URL sets are the same, check if details within skills have changed (optional, can be intensive)
        # For now, if counts and name/URL sets are same, assume no change for simplicity.
        # To implement detailed check: iterate through new_skills_list, find corresponding in old_skills_list by name/url,
        # then compare their detail dictionaries.
        self.logger.info("No significant change detected in skill count or basic skill identifiers.")
        return False
    
    def trigger_alarm(self, old_value: Dict[str, Any], new_value: Dict[str, Any]):
        """
        Trigger an alarm when the number of skills changes.
        
        Args:
            old_value (dict): Previous count and skills
            new_value (dict): Current count and skills
        """
        old_count = old_value.get("count", 0)
        new_count = new_value.get("count", 0)
        
        # Extract skill titles, handling both new format (dict with title) and old format (strings)
        old_skill_titles = set()
        for skill in old_value.get("skills", []):
            if isinstance(skill, dict) and "title" in skill:
                old_skill_titles.add(skill["title"])
            elif isinstance(skill, str):
                old_skill_titles.add(skill)
        
        new_skill_titles = set()
        for skill in new_value.get("skills", []):
            if isinstance(skill, dict) and "title" in skill:
                new_skill_titles.add(skill["title"])
            elif isinstance(skill, str):
                new_skill_titles.add(skill)
        
        added_skills = list(new_skill_titles - old_skill_titles)
        removed_skills = list(old_skill_titles - new_skill_titles)
        
        # Include extraction methods in the details
        details = {
            "change_type": "count_changed" if old_count != new_count else "skills_changed",
            "added_skills": added_skills,
            "removed_skills": removed_skills,
            "old_extraction_method": old_value.get("extraction_method", "unknown"),
            "new_extraction_method": new_value.get("extraction_method", "unknown")
        }
        
        # Record the event with details
        event = self._record_event(
            event_type="ms_applied_skills_changed",
            old_value=old_value,
            new_value=new_value,
            details=details
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
    
    def _save_html_content(self, html_content: str):
        """
        Save the HTML content to a file for debugging purposes.
        
        Args:
            html_content (str): HTML content to save
        """
        try:
            debug_html_path = os.path.join(self.data_dir, "last_page.html")
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.logger.debug(f"Saved HTML content to {debug_html_path}")
        except Exception as e:
            self.logger.error(f"Error saving HTML content: {str(e)}") 