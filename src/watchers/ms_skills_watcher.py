import re
import time
import logging
import asyncio
import os
import sys
from typing import Any, Optional, Dict
from bs4 import BeautifulSoup
import requests
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.watchers.base_watcher import BaseWatcher


class MSAppliedSkillsWatcher(BaseWatcher):
    """
    A watcher that monitors the number of Microsoft Applied Skills credentials.
    
    This watcher uses Playwright to render the page with JavaScript enabled,
    which allows it to extract data from dynamically rendered content.
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
        Override the base fetch_page method to use Playwright.
        
        Returns:
            str: HTML content of the page after JavaScript execution
        """
        try:
            self.logger.info(f"Fetching {self.url} with Playwright")
            
            # Use asyncio to run the async Playwright code
            html_content = asyncio.run(self._fetch_with_playwright())
            
            if not html_content:
                raise Exception("Failed to fetch content with Playwright")
            
            return html_content
        except Exception as e:
            self.logger.error(f"Error fetching URL {self.url} with Playwright: {str(e)}")
            raise
    
    async def _fetch_with_playwright(self) -> str:
        """
        Fetch the page content using Playwright's headless browser.
        This method now handles pagination to ensure all skills are collected.
        
        Returns:
            str: The HTML content of the page after JavaScript execution
        """
        async with async_playwright() as p:
            self.logger.debug("Launching browser")
            browser = await p.chromium.launch(headless=True)
            
            try:
                page = await browser.new_page()
                
                # Set viewport size to simulate a desktop browser
                await page.set_viewport_size({"width": 1280, "height": 800})
                
                # Set user agent to avoid bot detection
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
                })
                
                self.logger.debug(f"Navigating to {self.url}")
                response = await page.goto(self.url, wait_until="networkidle")
                
                if not response or not response.ok:
                    self.logger.error(f"Failed to load page: {response.status if response else 'No response'}")
                    return ""
                
                # Wait for content to load - looking for credential cards or result count
                try:
                    # Wait for potential elements that might indicate the page has loaded
                    self.logger.debug("Waiting for page content to load")
                    await page.wait_for_selector(".card, .card-title, .credential-card, [role='listitem'], #results-header", timeout=30000)
                except PlaywrightTimeoutError:
                    self.logger.warning("Timeout waiting for specific selectors, continuing with current content")
                
                # Wait additional time to ensure all dynamic content is loaded
                await page.wait_for_timeout(2000)
                
                # Check for pagination
                all_pages_content = await page.content()
                
                # Look for pagination controls - try common selectors for pagination
                pagination_selectors = [
                    '.pagination', 
                    '.pager', 
                    'nav[role="navigation"]',
                    '[aria-label="Pagination"]',
                    'ul.paginationjs',
                    '.page-navigation',
                    '[data-testid="pagination"]'
                ]
                
                # Try to detect pagination
                has_pagination = False
                for selector in pagination_selectors:
                    if await page.query_selector(selector):
                        has_pagination = True
                        self.logger.info(f"Detected pagination using selector: {selector}")
                        break
                
                # If we have pagination, try to navigate through all pages
                if has_pagination:
                    page_num = 1
                    max_pages = 5  # Limit to avoid infinite loops
                    
                    while page_num < max_pages:
                        self.logger.info(f"Processing page {page_num}")
                        
                        # Get current page content
                        current_page_content = await page.content()
                        all_pages_content += current_page_content
                        
                        # Look for next page button using common selectors
                        next_button_selectors = [
                            '.pagination .next', 
                            '.pagination [aria-label="Next"]',
                            '.pagination [aria-label="Siguiente"]',
                            '.pager .next',
                            '[aria-label="Next page"]',
                            '[aria-label="Página siguiente"]',
                            'button.next-page',
                            '.pagination-next',
                            '.page-item:not(.disabled) .page-link:has-text("Next")',
                            '.page-item:not(.disabled) .page-link:has-text("Siguiente")'
                        ]
                        
                        # Try to find and click the next page button
                        next_button = None
                        for selector in next_button_selectors:
                            try:
                                next_button = await page.query_selector(selector)
                                if next_button:
                                    self.logger.info(f"Found next page button with selector: {selector}")
                                    break
                            except Exception as e:
                                self.logger.debug(f"Error finding next button with selector {selector}: {str(e)}")
                        
                        # If we couldn't find the next button, try looking for page number links
                        if not next_button:
                            try:
                                next_page_num = page_num + 1
                                next_page_link = await page.query_selector(f'.pagination a:has-text("{next_page_num}")')
                                if next_page_link:
                                    next_button = next_page_link
                                    self.logger.info(f"Found link to page {next_page_num}")
                            except Exception as e:
                                self.logger.debug(f"Error finding link to page {page_num + 1}: {str(e)}")
                        
                        # If we found a next button/link and it's clickable, move to next page
                        if next_button:
                            try:
                                # Check if the button is visible and enabled
                                is_visible = await next_button.is_visible()
                                is_enabled = not (await next_button.get_attribute('disabled'))
                                
                                if is_visible and is_enabled:
                                    self.logger.info(f"Clicking to navigate to page {page_num + 1}")
                                    await next_button.click()
                                    
                                    # Wait for the page to load
                                    await page.wait_for_load_state("networkidle")
                                    await page.wait_for_timeout(2000)  # Additional wait for content
                                    
                                    page_num += 1
                                    continue
                                else:
                                    self.logger.info(f"Next button found but not clickable (visible: {is_visible}, enabled: {is_enabled})")
                                    break
                            except Exception as e:
                                self.logger.warning(f"Error clicking next page button: {str(e)}")
                                break
                        else:
                            self.logger.info(f"No next page button found, assuming we're on the last page")
                            break
                    
                    self.logger.info(f"Completed pagination, processed {page_num} pages")
                else:
                    self.logger.info("No pagination detected, using single page content")
                
                # Take a screenshot for debugging (optional)
                screenshot_path = f"data/watchers/{self.name}/debug_screenshot.png"
                await page.screenshot(path=screenshot_path)
                self.logger.debug(f"Saved screenshot to {screenshot_path}")
                
                return all_pages_content
            
            finally:
                await browser.close()
                self.logger.debug("Browser closed")
    
    def extract_value(self, html_content: str) -> Dict[str, Any]:
        """
        Extract the list of Microsoft Applied Skills from the HTML content.
        
        Args:
            html_content (str): HTML content of the page
            
        Returns:
            Dict[str, Any]: Dictionary with keys:
                - count: Number of skills found
                - skills: List of skill titles
                - extraction_method: The method used to extract skills
                - url: The URL being monitored
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        self.logger.debug("HTML content loaded for parsing")

        try:
            # Save the HTML content for debugging
            self._save_html_content(html_content)
            
            # Extract skills
            skills = self._extract_skills_from_html(soup)
            
            # If no skills found, try the fallback method (in case of extraction failure)
            if not skills:
                self.logger.warning("No skills found, using fallback extraction method")
                return self._fallback_extraction()
            
            self.logger.info(f"Successfully extracted {len(skills)} skills")
            
            return {
                "count": len(skills),
                "skills": skills,
                "extraction_method": "playwright",
                "url": self.url  # Include the URL in the state
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting value: {str(e)}")
            return self._fallback_extraction()
    
    def _extract_skills_from_html(self, soup: BeautifulSoup) -> list:
        """
        Extract skill names and their URLs from the HTML.
        
        Args:
            soup: BeautifulSoup object of the parsed HTML
            
        Returns:
            list: List of dictionaries with 'title' and 'url' keys
        """
        skills = []
        
        # Look for various selectors that might contain skill cards with titles
        selectors = [
            '.card-title', '.credential-card h3', '.credential-title', 
            '[role="listitem"] h3', '.result-title', '.skill-title',
            '.card a', 'article h3', '.card-details h3'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                self.logger.debug(f"Found {len(elements)} elements with selector '{selector}'")
                for element in elements:
                    # Skip empty or too short titles
                    if element.text and len(element.text.strip()) > 5:
                        skill_title = element.text.strip()
                        
                        # Try to find the URL for this skill
                        skill_url = None
                        
                        # If the element itself is a link, use its href
                        if element.name == 'a' and element.get('href'):
                            skill_url = element.get('href')
                        # Otherwise, look for a parent or nearby link
                        else:
                            # Check if element is inside a link
                            parent_link = element.find_parent('a')
                            if parent_link and parent_link.get('href'):
                                skill_url = parent_link.get('href')
                            # If not, look for a link in the parent card
                            else:
                                card_parent = element.find_parent('.card') or element.find_parent('article') or element.find_parent('[role="listitem"]')
                                if card_parent:
                                    link = card_parent.find('a')
                                    if link and link.get('href'):
                                        skill_url = link.get('href')
                        
                        # Make URL absolute if it's relative
                        if skill_url and skill_url.startswith('/'):
                            skill_url = f"https://learn.microsoft.com{skill_url}"
                        
                        skills.append({
                            "title": skill_title,
                            "url": skill_url if skill_url else None
                        })
        
        # If we couldn't find skills using selectors, try headings
        if not skills:
            headings = []
            for heading in soup.find_all(['h2', 'h3', 'h4']):
                if heading.text and len(heading.text.strip()) > 5:
                    skill_title = heading.text.strip()
                    
                    # Try to find the URL for this skill
                    skill_url = None
                    
                    # Check if heading is inside a link
                    parent_link = heading.find_parent('a')
                    if parent_link and parent_link.get('href'):
                        skill_url = parent_link.get('href')
                    # If not, look for a link in the parent container
                    else:
                        container = heading.find_parent('div') or heading.find_parent('article')
                        if container:
                            link = container.find('a')
                            if link and link.get('href'):
                                skill_url = link.get('href')
                    
                    # Make URL absolute if it's relative
                    if skill_url and skill_url.startswith('/'):
                        skill_url = f"https://learn.microsoft.com{skill_url}"
                    
                    headings.append({
                        "title": skill_title,
                        "url": skill_url if skill_url else None
                    })
            
            self.logger.debug(f"Found {len(headings)} potential skill headings")
            
            # Filter out common headings that are not skill names
            excluded_terms = ['microsoft', 'learn', 'explore', 'search', 'filter', 'credentials']
            skills = [h for h in headings if not any(term in h["title"].lower() for term in excluded_terms)]
        
        # Filter out navigation elements, UI controls, and common non-skill text
        ui_elements = [
            'Documentación', 'Cursos', 'Credencial', 'Ejemplos de código', 
            'Valoraciones', 'Programa', 'Aumentar las aptitudes técnicas de su equipo',
            'Documentation', 'Courses', 'Credential', 'Code samples', 
            'Ratings', 'Program', 'Contact'
        ]
        
        # Only keep items that look like actual Applied Skills
        filtered_skills = []
        for skill in skills:
            # Skip UI elements
            if skill["title"] in ui_elements:
                continue
                
            # Keep items that start with "Microsoft Applied Skills:"
            if skill["title"].startswith("Microsoft Applied Skills:"):
                filtered_skills.append(skill)
        
        # Remove duplicates while preserving order
        unique_skills = []
        seen_titles = set()
        for skill in filtered_skills:
            if skill["title"] not in seen_titles:
                seen_titles.add(skill["title"])
                unique_skills.append(skill)
        
        self.logger.debug(f"Found {len(skills)} skills, filtered to {len(filtered_skills)}, reduced to {len(unique_skills)} after removing duplicates")
        return unique_skills
    
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
        Determine if the number of skills has changed.
        
        Args:
            old_value (dict): Previous count and skills
            new_value (dict): Current count and skills
            
        Returns:
            bool: True if the number of skills has changed, False otherwise
        """
        old_count = old_value.get("count", 0)
        new_count = new_value.get("count", 0)
        
        # Log the extraction methods
        old_method = old_value.get("extraction_method", "unknown")
        new_method = new_value.get("extraction_method", "unknown")
        
        self.logger.debug(f"Comparing values - Old: {old_count} ({old_method}), New: {new_count} ({new_method})")
        
        # If both values are from fallback and unchanged, the website might be inaccessible
        if old_method == "fallback" and new_method == "fallback" and old_count == new_count:
            self.logger.warning("Both values are from fallback mechanism, website might be inaccessible")
            return False
        
        if old_count != new_count:
            self.logger.info(f"Number of Microsoft Applied Skills changed: {old_count} -> {new_count}")
            return True
        
        # If counts are the same but we want to check for changes in the skills themselves:
        old_skill_titles = set(skill["title"] for skill in old_value.get("skills", []) if isinstance(skill, dict) and "title" in skill)
        new_skill_titles = set(skill["title"] for skill in new_value.get("skills", []) if isinstance(skill, dict) and "title" in skill)
        
        # Handle legacy format where skills was a list of strings
        if not old_skill_titles and isinstance(old_value.get("skills", []), list) and old_value.get("skills", []) and isinstance(old_value["skills"][0], str):
            old_skill_titles = set(old_value.get("skills", []))
        
        added_skills = new_skill_titles - old_skill_titles
        removed_skills = old_skill_titles - new_skill_titles
        
        if added_skills or removed_skills:
            self.logger.info(f"Skills changed. Added: {added_skills}. Removed: {removed_skills}")
            return True
        
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