# TODO: Standardize the code with the other projects. Current code has been migrated from other project.

import json
import os
import re
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import parse_qs, unquote, urlparse, urlsplit, urlunparse

import cloudscraper
import requests
# import rookiepy
from bs4 import BeautifulSoup as bs
from playwright.sync_api import sync_playwright

# Make rookiepy optional
try:
    import rookiepy
    ROOKIEPY_AVAILABLE = True
except ImportError:
    ROOKIEPY_AVAILABLE = False
    print("rookiepy package not available - some functionality may be limited")

from colors import fb, fc, fg, flb, flg, fm, fr, fy
from logger import get_logger, LoggerAdapter

VERSION = "jmmr.2.5"

scraper_dict: dict = {
    "Udemy Freebies": "uf",
    "Tutorial Bar": "tb",
    "Real Discount": "rd",
    "Course Vania": "cv",
    "IDownloadCoupons": "idc",
    "E-next": "en",
    "Discudemy": "du",
    "Course Joiner": "cj",
    "Cursos Dev": "cd",
    "Udemy Free Courses": "ufc"
}

LINKS = {
    "github": "https://github.com/techtanic/Discounted-Udemy-Course-Enroller",
    "support": "https://techtanic.github.io/duce/support",
    "discord": "https://discord.gg/wFsfhJh4Rh",
}

scrapper_timeout_period = 20  # seconds - increased from 10 to 20
scrapper_max_retries = 5  # retries


class LoginException(Exception):
    """Login Error

    Args:
        Exception (str): Exception Reason
    """

    pass


class RaisingThread(threading.Thread):
    def run(self):
        self._exc = None
        try:
            super().run()
        except Exception as e:
            self._exc = e

    def join(self, timeout=None):
        super().join(timeout=timeout)
        if self._exc:
            raise self._exc


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class Scraper:
    """
    Scrapers: RD,TB, CV, IDC, EN, DU, UF, CJ, UF, CD
    """

    def __init__(
        self,
        site_to_scrape: list = list(scraper_dict.keys()),
        debug: bool = False,
    ):
        self.sites = site_to_scrape
        self.debug = debug
        self.logger = get_logger(__name__, debug=debug)
        self.logger.info(f"Initializing scraper for sites: {', '.join(site_to_scrape)}")
        
        for site in self.sites:
            code_name = scraper_dict[site]
            setattr(self, f"{code_name}_length", 0)
            setattr(self, f"{code_name}_data", [])
            setattr(self, f"{code_name}_done", False)
            setattr(self, f"{code_name}_progress", 0)
            setattr(self, f"{code_name}_error", "")

    def get_scraped_courses(self, target: object) -> list:
        threads = []
        scraped_data = {}
        for site in self.sites:
            t = RaisingThread(
                target=target,
                args=(site,),
                daemon=True,
            )
            t.start()
            threads.append(t)
            time.sleep(0.5)

        for t in threads:
            try:
                t.join()
            except Exception as thread_exc:
                self.logger.error(f"Caught exception from thread {t.name}: {thread_exc}")

        for site in self.sites:
            code_name = scraper_dict[site]
            if getattr(self, f"{code_name}_done") and getattr(self, f"{code_name}_length") != -1:
                scraped_data[site] = getattr(self, f"{code_name}_data")
            elif not getattr(self, f"{code_name}_done"):
                self.logger.warning(f"Scraper for {site} did not complete.")
                scraped_data[site] = []
            else:
                self.logger.warning(f"Scraper for {site} failed, data not included.")
                scraped_data[site] = []

        return scraped_data

    def append_to_list(self, target: list, title: str, link: str):
        target.append((title, link))

    def fetch_page_content(self, url, headers=None, timeout=scrapper_timeout_period):
        """Fetches page content using requests library with specified timeout and retries."""
        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            )
        }
        if headers:
            default_headers.update(headers)
        
        retries = 0
        max_retries = scrapper_max_retries
        used_cloudscraper = False
        
        while retries < max_retries:
            try:
                # First try with regular requests
                if not used_cloudscraper:
                    response = requests.get(url, headers=default_headers, timeout=timeout)
                    response.raise_for_status()
                    return response.text
                # If that fails, try with cloudscraper (handles Cloudflare protection)
                else:
                    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
                    response = scraper.get(url, headers=default_headers, timeout=timeout)
                    return response.text
                    
            except (requests.RequestException, Exception) as e:
                retries += 1
                # If we haven't tried cloudscraper yet and this is not the last retry, try it
                if not used_cloudscraper and retries < max_retries - 1:
                    used_cloudscraper = True
                    if self.debug:
                        self.logger.warning(f"Switching to cloudscraper for {url} after standard request failed: {str(e)}")
                    continue  # Skip the delay and retry immediately with cloudscraper
                
                if retries < max_retries:
                    retry_delay = 2 * retries  # Exponential backoff
                    if self.debug:
                        self.logger.warning(f"Retry {retries}/{max_retries} for {url} after {retry_delay}s: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    if self.debug:
                        self.logger.error(f"Error fetching {url} after {max_retries} retries: {str(e)}")
                    return ""
        return ""

    def fetch_page_content_uf_with_js(self, url):
        """Fetches page content using Playwright for sites requiring JavaScript execution."""
        retries = 0
        max_retries = scrapper_max_retries
        while retries < max_retries:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage"]
                    )
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
                    )
                    page = context.new_page()
                    page.goto(url, wait_until='domcontentloaded', timeout=scrapper_timeout_period * 1000)

                    page_source = page.content()
                    browser.close()
                    return page_source
            except Exception as e:
                retries += 1
                if retries < max_retries:
                    retry_delay = 2 * retries  # Exponential backoff
                    if self.debug:
                        self.logger.warning(f"Retry {retries}/{max_retries} for {url} with Playwright after {retry_delay}s: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    if self.debug:
                        self.logger.error(f"Error fetching {url} with Playwright after {max_retries} retries: {str(e)}")
                    return ""
        return ""

    def parse_html(self, content: str):
        if not content:
            return bs("", "html5lib")
        return bs(content, "html5lib")

    def handle_exception(self, site_code: str):
        error_trace = traceback.format_exc()
        setattr(self, f"{site_code}_error", error_trace)
        setattr(self, f"{site_code}_length", -1)
        setattr(self, f"{site_code}_done", True)
        if self.debug:
            site_logger = LoggerAdapter(get_logger(f"scraper.{site_code}"), {'site_code': site_code})
            site_logger.error(f"Error in {site_code} scraper:")
            site_logger.debug(error_trace)

    def cleanup_link(self, link: str) -> str:
        if not link:
            return ""
            
        try:
            parsed_url = urlparse(link)

            if parsed_url.netloc == "www.udemy.com":
                query_params = parse_qs(parsed_url.query)
                valid_params = {}
                if 'couponCode' in query_params:
                    valid_params['couponCode'] = query_params['couponCode']

                cleaned_query = "&amp;".join([f"{k}={v[0]}" for k, v in valid_params.items()])
                cleaned_path = parsed_url.path.rstrip('/') + '/'

                cleaned_link = urlunparse((
                    parsed_url.scheme,
                    parsed_url.netloc,
                    cleaned_path,
                    '',
                    cleaned_query,
                    ''
                ))
                return cleaned_link

            if parsed_url.netloc == "click.linksynergy.com":
                query_params = parse_qs(parsed_url.query)
                udemy_link = ""
                if "RD_PARM1" in query_params:
                    udemy_link = unquote(query_params["RD_PARM1"][0])
                elif "murl" in query_params:
                    udemy_link = unquote(query_params["murl"][0])

                if udemy_link:
                    return self.cleanup_link(udemy_link)
                else:
                    return ""

            if self.debug:
                self.logger.debug(f"Link not recognized as Udemy or known redirector: {link}")
            return ""

        except Exception as e:
            if self.debug:
                self.logger.error(f"Error cleaning link {link}: {str(e)}")
            return ""

    def du(self):
        try:
            all_items = []
            head = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            }

            for page in range(1, 6): # Consider reducing page range initially?
                content = self.fetch_page_content(
                    f"https://www.discudemy.com/all/{page}", headers=head
                )
                if not content: continue
                soup = self.parse_html(content)
                page_items = soup.find_all("a", {"class": "card-header"})
                all_items.extend(page_items)

            self.du_length = len(all_items)
            if self.debug:
                print(f"DU Length: {self.du_length}")

            for index, item in enumerate(all_items):
                self.du_progress = index + 1
                title = item.string.strip() if item.string else "N/A"
                # Discudemy requires fetching the intermediate 'go' page
                intermediate_url = item.get("href")
                if not intermediate_url: continue

                # Extract the identifier from the URL like https://www.discudemy.com/category/103/Business -> category/103/Business
                # or https://www.discudemy.com/English/2 -> English/2
                url_parts = intermediate_url.split('/')
                identifier = "/".join(url_parts[-2:]) # take last two parts for /go/ url

                go_url = f"https://www.discudemy.com/go/{identifier}"
                if self.debug: print(f"DU Fetching intermediate: {go_url}")

                content = self.fetch_page_content(go_url, headers=head)
                if not content: continue
                soup = self.parse_html(content)

                # Find the link within the 'go' page
                link_div = soup.find("div", {"class": "ui segment"})
                if not link_div or not link_div.a:
                    # Try finding link in other common tags if the primary fails
                     link_tag = soup.find("a", class_=re.compile(r"btn|button", re.I), href=True)
                     if not link_tag:
                         if self.debug: print(f"DU: Could not find link div/a tag on {go_url}")
                         continue
                     raw_link = link_tag.get("href")
                else:
                     raw_link = link_div.a.get("href")


                link = self.cleanup_link(raw_link)

                if link:
                    if self.debug:
                        print(f"DU Found: {title} -> {link}")
                    self.append_to_list(self.du_data, title, link)
                elif self.debug:
                     print(f"DU Skipped (non-Udemy?): {title} -> {raw_link}")

        except Exception:
            self.handle_exception("du")
        finally:
            self.du_done = True
            if self.debug:
                print(f"DU Return Length: {len(self.du_data)}")

    def uf(self):
        site_code = "uf"
        try:
            all_items = []
            head = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            }
            for page in range(1, 6): # Adjust page range as needed
                content = self.fetch_page_content(
                    f"https://www.udemyfreebies.com/free-udemy-courses/{page}", headers=head
                )
                if not content: continue
                soup = self.parse_html(content)
                page_items = soup.find_all("a", {"class": "theme-img"})
                all_items.extend(page_items)

            setattr(self, f"{site_code}_length", len(all_items))
            if self.debug:
                print(f"{site_code.upper()} Length: {getattr(self, f'{site_code}_length')}")

            processed_count = 0
            for index, item in enumerate(all_items):
                setattr(self, f"{site_code}_progress", index + 1)
                if not item.img or not item.img.get("alt") or not item.get("href"):
                    continue

                title = item.img["alt"].strip()
                relative_url = item['href']
                course_id_or_identifier = None # Initialize ID

                # 1. Try extracting ID directly from the initial link
                match_direct_id = re.search(r'(?:out|goto)/.*?(\d+)/?$', relative_url)
                if match_direct_id:
                    course_id_or_identifier = match_direct_id.group(1)
                    if self.debug: print(f"{site_code.upper()} Found direct ID: {course_id_or_identifier}")
                else:
                    # 2. If no direct ID, assume it's an intermediate page URL
                    # Construct full intermediate URL (handle relative paths)
                    if not relative_url.startswith('http'):
                        base_uf = "https://www.udemyfreebies.com"
                        intermediate_page_url = f"{base_uf}{relative_url}" if relative_url.startswith('/') else f"{base_uf}/{relative_url}"
                    else:
                        intermediate_page_url = relative_url

                    if self.debug: print(f"{site_code.upper()} No direct ID. Fetching intermediate page: {intermediate_page_url}")
                    inter_content = self.fetch_page_content(intermediate_page_url, headers=head)
                    if inter_content:
                        inter_soup = self.parse_html(inter_content)
                        # 3. Find the '/out/ID' link on the intermediate page
                        out_link_tag = inter_soup.find("a", href=re.compile(r'/out/\d+'))
                        if out_link_tag:
                            match_indirect_id = re.search(r'/out/(\d+)', out_link_tag['href'])
                            if match_indirect_id:
                                course_id_or_identifier = match_indirect_id.group(1)
                                if self.debug: print(f"{site_code.upper()} Found ID on intermediate page: {course_id_or_identifier}")
                        else:
                             if self.debug: print(f"{site_code.upper()} Could not find /out/ID link on intermediate page: {intermediate_page_url}")
                    else:
                         if self.debug: print(f"{site_code.upper()} Failed to fetch intermediate page content: {intermediate_page_url}")

                # 4. If no ID found either way, skip this item
                if not course_id_or_identifier:
                    if self.debug: print(f"{site_code.upper()}: Failed to extract ID for {title} from {relative_url}")
                    continue

                # 5. Construct redirect URL and proceed
                redirect_fetch_url = f"https://www.udemyfreebies.com/out/{course_id_or_identifier}"
                if self.debug: print(f"{site_code.upper()} Fetching redirect: {redirect_fetch_url}")

                try:
                    response = requests.get(redirect_fetch_url, headers=head, allow_redirects=True, timeout=scrapper_timeout_period)
                    response.raise_for_status()
                    final_url = response.url

                    link = self.cleanup_link(final_url)

                    if link:
                        if self.debug:
                            print(f"{site_code.upper()} Found: {title} -> {link}")
                        self.append_to_list(getattr(self, f"{site_code}_data"), title, link)
                        processed_count += 1
                    elif self.debug:
                         print(f"{site_code.upper()} Skipped (non-Udemy link after redirect?): {title} -> {final_url}")

                except requests.RequestException as e:
                    if self.debug:
                        print(fr + f"Error fetching redirect {redirect_fetch_url} for {title}: {e}")
                except Exception as e:
                     if self.debug:
                         print(fr + f"Error processing item {index} ({title}): {e}")

        except Exception:
            self.handle_exception(site_code)
        finally:
            setattr(self, f"{site_code}_done", True)
            if self.debug:
                print(f"{site_code.upper()} Return Length: {len(getattr(self, f'{site_code}_data'))}")

    def tb(self):
        try:
            all_items = []

            for page in range(1, 8): # Adjust page range if needed
                content = self.fetch_page_content(
                    f"https://www.tutorialbar.com/all-courses/page/{page}"
                )
                if not content: continue
                soup = self.parse_html(content)
                # Find h2 tags containing the course links
                page_items = soup.find_all(
                    "h2", class_="mb15 mt0 font110 mobfont100 fontnormal lineheight20"
                )
                all_items.extend(page_items)

            self.tb_length = len(all_items)
            if self.debug:
                print(f"TB Length: {self.tb_length}")

            for index, item in enumerate(all_items):
                self.tb_progress = index + 1
                if not item.a or not item.a.string or not item.a.get("href"):
                    continue

                title = item.a.string.strip()
                intermediate_url = item["href"]

                # Fetch the course page on TutorialBar to find the Udemy link
                if self.debug: print(f"TB Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content: continue
                soup_intermediate = self.parse_html(content)

                # Find the specific button/link for the offer
                link_element = soup_intermediate.find("a", class_="btn_offer_block re_track_btn")
                 # Fallback selectors
                if not link_element:
                    link_element = soup_intermediate.find("a", class_=re.compile(r"btn.*offer|offer.*btn"), href=True)
                if not link_element:
                    link_element = soup_intermediate.find("a", string=re.compile(r"Get Coupon|Enroll|Offer", re.I), href=True)

                if not link_element or not link_element.get("href"):
                    if self.debug: print(f"TB: Could not find offer button on {intermediate_url}")
                    continue

                raw_link = link_element["href"]
                link = self.cleanup_link(raw_link) # cleanup handles redirects

                if link:
                    if self.debug:
                        print(f"TB Found: {title} -> {link}")
                    self.append_to_list(self.tb_data, title, link)
                elif self.debug:
                    print(f"TB Skipped (non-Udemy?): {title} -> {raw_link}")

        except Exception:
            self.handle_exception("tb")
        finally:
            self.tb_done = True
            if self.debug:
                print(f"TB Return Length: {len(self.tb_data)}")

    def rd(self):
        site_code = "rd"
        try:
            # Ensure Playwright is available
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                print(fr + f"Playwright not installed. Run 'pip install playwright && playwright install'. Skipping {site_code.upper()} scraper.")
                self.handle_exception(site_code) # Mark as failed due to missing dependency
                return

            all_items_details = []
            base_url = "https://real.discount/courses/"
            if self.debug: print(f"Starting {site_code.upper()} scraper (uses Playwright)...")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
                )
                page = context.new_page()

                if self.debug: print(f"{site_code.upper()}: Navigating to {base_url}")
                # Increase timeout for initial load
                page.goto(base_url, wait_until='domcontentloaded', timeout=scrapper_timeout_period * 3 * 1000) # 30 seconds

                # --- Attempt to click the 'Free' filter ---
                try:
                    if self.debug: print(f"{site_code.upper()}: Attempting to click 'Free' filter...")
                    # Common selectors for a 'Free' filter/checkbox/label. May need adjustment.
                    free_filter_selector = 'label:has-text("Free")' # Check if this label exists
                    # Alternative selectors:
                    # free_filter_selector = 'input[value="free"]'
                    # free_filter_selector = 'a:has-text("Free")'
                    # free_filter_selector = '.filter-option:has-text("Free")'

                    # Wait for the filter element to be visible before clicking
                    page.wait_for_selector(free_filter_selector, state="visible", timeout=15000) # 15 seconds wait
                    page.click(free_filter_selector)
                    if self.debug: print(f"{site_code.upper()}: Clicked 'Free' filter.")

                    # Wait for content to potentially reload after filtering.
                    # 'networkidle' is often good, but might time out if there's persistent background activity.
                    # Waiting for a specific change might be more reliable if identifiable.
                    page.wait_for_load_state('networkidle', timeout=20000) # 20 seconds wait
                    if self.debug: print(f"{site_code.upper()}: Waited for network idle after filter.")

                except Exception as filter_err:
                    if self.debug:
                        print(fr + f"{site_code.upper()}: Could not find or click the 'Free' filter (selector: '{free_filter_selector}'). Proceeding without filter. Error: {filter_err}")
                    # Continue without filtering if the click fails

                # Get page content after attempting filter
                content = page.content()
                browser.close() # Close browser once content is fetched

                if not content:
                    self.rd_error = "Failed to fetch page content with Playwright"
                    self.rd_length = -1
                    self.rd_done = True
                    if self.debug: print(fr + self.rd_error)
                    return

                # Parse the HTML
                soup = self.parse_html(content)

                # Find course items - SELECTOR NEEDS VERIFICATION based on actual page structure
                course_cards = soup.find_all("div", class_=re.compile(r"card product-card|course-item")) # Example common card classes
                if not course_cards: course_cards = soup.select("article.course-post") # Another fallback

                if not course_cards and self.debug:
                    print(fy + f"{site_code.upper()}: No course cards found with current selectors.")
                    # Save HTML for inspection if debugging
                    # with open("debug_rd_page.html", "w", encoding="utf-8") as f:
                    #     f.write(content)

                self.rd_length = len(course_cards)
                if self.debug:
                    print(f"{site_code.upper()} Length (from Playwright page): {self.rd_length}")

                for index, item in enumerate(course_cards):
                    self.rd_progress = index + 1

                    # Extract title and intermediate link - SELECTORS NEED VERIFICATION
                    title_tag = item.find("h3", class_=re.compile(r"card-title|course-title"))
                    link_tag = item.find("a", class_=re.compile(r"stretched-link|course-link|btn-details"), href=True)
                    if not link_tag: link_tag = item.find("a", href=True) # Fallback to any link within the card

                    if not title_tag or not link_tag or not link_tag.get("href"):
                        if self.debug: print(f" {site_code.upper()} Skipping item {index}: Missing title or link tag.")
                        continue

                    title = title_tag.get_text(strip=True)
                    intermediate_url = link_tag["href"]

                    # Ensure the intermediate URL is absolute
                    if not intermediate_url.startswith('http'):
                         parsed_base = urlparse(base_url)
                         intermediate_url = urlunparse((parsed_base.scheme, parsed_base.netloc, intermediate_url, '', '', ''))

                    # Fetch the intermediate page on Real Discount to find the Udemy link
                    if self.debug: print(f" {site_code.upper()} Fetching intermediate: {intermediate_url}")
                    intermediate_content = self.fetch_page_content(intermediate_url)
                    if not intermediate_content: continue
                    soup_intermediate = self.parse_html(intermediate_content)

                    # Find the final Udemy link button/element - SELECTOR NEEDS VERIFICATION
                    # Look for buttons/links with text like "Get Coupon", "Go To Course", etc.
                    final_link_element = soup_intermediate.find("a", class_=re.compile(r"btn-success|coupon-button|go-to-deal"), href=True)
                    if not final_link_element:
                        final_link_element = soup_intermediate.find("a", string=re.compile(r"Get Coupon|Enroll|Go To Course|Visit Deal", re.I), href=True)

                    if not final_link_element or not final_link_element.get("href"):
                        if self.debug: print(f" {site_code.upper()}: Could not find final link button on {intermediate_url}")
                        continue

                    raw_link = final_link_element["href"]
                    link = self.cleanup_link(raw_link) # cleanup_link handles redirects (like linksynergy)

                    if link:
                        if self.debug:
                            print(f" {site_code.upper()} Found: {title} -> {link}")
                        self.append_to_list(self.rd_data, title, link)
                    elif self.debug:
                        print(f" {site_code.upper()} Skipped (non-Udemy?): {title} -> {raw_link}")

        except Exception:
            # Use handle_exception to capture the traceback and set flags
            self.handle_exception(site_code)
        finally:
            # Ensure done flag is always set
            setattr(self, f"{site_code}_done", True)
            if self.debug:
                print(f"{site_code.upper()} Return Length: {len(getattr(self, f'{site_code}_data', []))}")

    def cv(self):
        try:
            # Fetch main page to potentially get nonce or other required info
            if self.debug: print("CV: Fetching main page...")
            main_page_content = self.fetch_page_content("https://coursevania.com/courses/")
            if not main_page_content:
                 self.cv_error = "Failed to fetch main page"
                 self.cv_length = -1
                 self.cv_done = True
                 if self.debug: print(fr + self.cv_error)
                 return

            soup_main = self.parse_html(main_page_content)
            nonce = None
            try:
                # Look for nonce in script tags (more robustly)
                script_tags = soup_main.find_all("script")
                # Use raw strings (r prefix) for regex patterns with backslashes
                nonce_pattern = re.compile(r'[\'\"]load_content[\'\"]\s*:\s*[\'\"]([a-zA-Z0-9]+)[\'\"]')
                nonce_pattern_alt = re.compile(r'ajax_nonce[\'\"]\s*:\s*[\'\"]([a-zA-Z0-9]+)[\'\"]') # Look for ajax_nonce too

                for script in script_tags:
                    script_content = str(script) # Convert script tag content to string
                    match = nonce_pattern.search(script_content)
                    if match:
                        nonce = match.group(1)
                        if self.debug: print(f"CV Found Nonce (load_content): {nonce}")
                        break
                    else: # Try alternative pattern if first fails
                        match_alt = nonce_pattern_alt.search(script_content)
                        if match_alt:
                             nonce = match_alt.group(1)
                             if self.debug: print(f"CV Found Nonce (ajax_nonce): {nonce}")
                             break # Found nonce, exit loop

                if not nonce:
                     raise ValueError("Nonce not found in script tags")

            except (ValueError, Exception) as e:
                self.cv_error = f"Nonce finding error: {str(e)}"
                self.cv_length = -1
                self.cv_done = True
                if self.debug: print(fr + self.cv_error)
                return

            # Make API call to load courses
            # Try different API endpoints or parameters if the first fails
            api_url = f"https://coursevania.com/wp-admin/admin-ajax.php?template=courses/grid&args={{\"posts_per_page\":\"100\"}}&action=stm_lms_load_content&nonce={nonce}&sort=date_high"
            if self.debug: print(f"CV Fetching API: {api_url}")

            api_content = ""
            try:
                response = requests.get(api_url, timeout=scrapper_timeout_period)
                response.raise_for_status()
                r = response.json()
                # Check response structure - it might contain HTML in 'content' or 'html'
                api_content = r.get("content", r.get("html", ""))
                if not api_content and self.debug:
                     print(fy + f"CV: API response JSON didn't contain 'content' or 'html'. Response: {r}")

            except (requests.RequestException, json.JSONDecodeError) as e:
                self.cv_error = f"API request error: {str(e)}"
                self.cv_length = -1
                self.cv_done = True
                if self.debug: print(fr + self.cv_error)
                return

            # Parse the HTML content returned by the API
            if not api_content:
                 if self.debug: print(fy + "CV: API returned no content to parse.")
                 self.cv_length = 0
                 # Don't set done=True here, let the main loop finish
                 # self.cv_done = True
                 # return # Continue to finally block even if no content
            else:
                 soup_api = self.parse_html(api_content)
                 # Find course items within the API response HTML - Verify selector
                 page_items = soup_api.find_all("div", {"class": re.compile(r"stm_lms_courses__single")})
                 self.cv_length = len(page_items)
                 if self.debug:
                     print(f"CV Length (from API): {self.cv_length}")

                 for index, item in enumerate(page_items):
                    self.cv_progress = index + 1
                    # Find title link inside the item
                    title_link_tag = item.find("div", class_="stm_lms_courses__single--title")
                    link_tag = None
                    if title_link_tag:
                        link_tag = title_link_tag.find("a", href=True)

                    if not link_tag or not link_tag.string:
                         # Try alternative title/link finding if primary fails
                         title_tag_alt = item.find("h5")
                         if title_tag_alt and title_tag_alt.a:
                             link_tag = title_tag_alt.a
                         else: # Last resort: find any link within the item
                             link_tag = item.find("a", href=True)
                             if not link_tag: continue # Skip if no link found

                    title = link_tag.string.strip() if link_tag.string else "N/A"
                    intermediate_url = link_tag.get("href", "")
                    if not intermediate_url: continue

                    # Fetch the intermediate course page on CourseVania with increased timeout
                    if self.debug: print(f" CV Fetching intermediate: {intermediate_url}")
                    content = self.fetch_page_content(intermediate_url, timeout=30) # Increased timeout to 30s
                    if not content: continue
                    soup_intermediate = self.parse_html(content)

                    # Find the affiliate link button - Verify selector
                    final_link_element = soup_intermediate.find("a", class_="masterstudy-button-affiliate__link")
                    # Fallback selectors
                    if not final_link_element:
                        final_link_element = soup_intermediate.find("a", class_=re.compile(r"btn-default btn.*?affiliate"), href=True)
                    if not final_link_element:
                        # Check common button area - ensure find returns a tag before finding again
                        buy_buttons_div = soup_intermediate.find("div", class_="stm-lms-buy-buttons")
                        if buy_buttons_div:
                            final_link_element = buy_buttons_div.find("a", href=True)

                    if not final_link_element or not final_link_element.get("href"):
                        if self.debug: print(f"CV: Could not find affiliate link on {intermediate_url}")
                        continue

                    raw_link = final_link_element["href"]
                    link = self.cleanup_link(raw_link)

                    if link:
                        if self.debug:
                            print(f"CV Found: {title} -> {link}")
                        self.append_to_list(self.cv_data, title, link)
                    elif self.debug:
                        print(f"CV Skipped (non-Udemy?): {title} -> {raw_link}")

        except Exception as main_exception:
            # Avoid calling handle_exception if error already handled in nested try/except
            if not getattr(self, "cv_error", ""):
                 self.cv_error = traceback.format_exc()
                 self.cv_length = -1 # Mark as failed if unexpected error
            if self.debug: print(fr + f"CV Main Exception: {main_exception}")
            # Ensure handle_exception logic is covered or called appropriately
            self.handle_exception("cv") # Call handle_exception to set done flag etc.
        finally:
            self.cv_done = True # Ensure done flag is always set
            if self.debug:
                print(f"CV Return Length: {len(self.cv_data)}")

    def idc(self):
        try:
            all_items = []
            for page in range(1, 8): # Adjust page range if needed
                if self.debug: print(f"IDC Fetching page {page}...")
                content = self.fetch_page_content(
                    f"https://idownloadcoupon.com/product-category/udemy/page/{page}"
                )
                if not content: continue
                soup = self.parse_html(content)
                # Find product links - Verify selector
                page_items = soup.find_all(
                    "a",
                    attrs={
                        "class": "woocommerce-LoopProduct-link woocommerce-loop-product__link"
                    },
                )
                if not page_items and self.debug: # Try fallback selector if needed
                     print(f"IDC: No items with primary selector on page {page}. Trying fallback...")
                     page_items = soup.select("li.product a.woocommerce-LoopProduct-link") # Example fallback

                all_items.extend(page_items)

            self.idc_length = len(all_items)
            if self.debug:
                print(f"IDC Length: {self.idc_length}")

            for index, item in enumerate(all_items):
                self.idc_progress = index + 1
                title_tag = item.find("h2", class_="woocommerce-loop-product__title")
                intermediate_url = item.get("href")

                if not title_tag or not title_tag.string or not intermediate_url:
                     # Try finding title from img alt if h2 fails
                     img_tag = item.find("img")
                     if img_tag and img_tag.get("alt") and intermediate_url:
                         title = img_tag["alt"].strip()
                     else:
                         if self.debug: print(f"IDC Skipping item {index}: Missing title or URL")
                         continue
                else:
                     title = title_tag.string.strip()

                # IDC often uses a redirect structure like /go/12345/ or /udemy/12345/
                match = re.search(r'(?:go|udemy)/(\d+)/?$', intermediate_url) # Combine patterns
                if not match:
                     # Extract number from URL like /product/title-here/12345/
                     match_alt = re.search(r'/product/.*?/(\d+)/?$', intermediate_url)
                     if not match_alt:
                         if self.debug: print(f"IDC: Could not extract ID from {intermediate_url}")
                         continue
                     link_num = match_alt.group(1)
                else:
                     link_num = match.group(1)

                # Construct the likely redirect URL - Verify this structure is correct
                redirect_url = f"https://idownloadcoupon.com/udemy/{link_num}/"
                if self.debug: print(f" IDC Fetching redirect: {redirect_url}")

                try:
                    # Make a HEAD request first to get redirect location efficiently
                    response = requests.head(
                        redirect_url,
                        allow_redirects=False, # We want the 'Location' header
                        timeout=scrapper_timeout_period
                    )
                    raw_link = None
                    if 300 <= response.status_code < 400 and "Location" in response.headers:
                        raw_link = response.headers["Location"]
                        if self.debug: print(f"  IDC Redirect Location (HEAD): {raw_link}")
                    else: # Fallback to GET if HEAD doesn't redirect or fails
                         if self.debug: print(f"  IDC HEAD failed or no redirect (Status: {response.status_code}). Trying GET...")
                         response_get = requests.get(redirect_url, allow_redirects=True, timeout=scrapper_timeout_period)
                         raw_link = response_get.url # Get final URL after GET redirects
                         if self.debug: print(f"  IDC Final URL (GET): {raw_link}")

                    if raw_link:
                        link = self.cleanup_link(unquote(raw_link)) # cleanup_link handles further redirects (like linksynergy)

                        if link:
                            if self.debug:
                                print(f"IDC Found: {title} -> {link}")
                            self.append_to_list(self.idc_data, title, link)
                        elif self.debug:
                            print(f"IDC Skipped (non-Udemy?): {title} -> {raw_link}")
                    else:
                         if self.debug: print(f"IDC: Failed to get redirect link from {redirect_url}")

                except requests.RequestException as e:
                    if self.debug:
                        print(fr + f"IDC Error fetching redirect {redirect_url} for {title}: {e}")
                except Exception as e:
                    if self.debug:
                        print(fr + f"IDC Error processing item {index} ({title}): {e}")

        except Exception:
            self.handle_exception("idc")
        finally:
            self.idc_done = True
            if self.debug:
                print(f"IDC Return Length: {len(self.idc_data)}")

    def en(self):
        try:
            all_items_intermediate = []
            # Scrape the listing pages to get links to individual course pages on e-next
            for page in range(1, 10): # Adjust page range if needed
                if self.debug: print(f"EN Fetching page {page}...")
                content = self.fetch_page_content(
                    f"https://jobs.e-next.in/course/udemy/{page}"
                )
                if not content: continue
                soup = self.parse_html(content)
                # Find links that likely lead to the e-next course details page - Verify selector
                page_items = soup.find_all(
                    "a", {"class": "btn btn-secondary btn-sm btn-block"}
                )
                if not page_items and self.debug: # Try fallback
                    print(f"EN: Primary selector failed on page {page}. Trying article links...")
                    articles = soup.find_all("article", class_="job-item")
                    for article in articles:
                        link = article.find("a", href=True)
                        if link: page_items.append(link)

                all_items_intermediate.extend(page_items)

            self.en_length = len(all_items_intermediate)
            if self.debug:
                print(f"EN Intermediate Length: {self.en_length}")

            processed_count = 0
            for index, item in enumerate(all_items_intermediate):
                self.en_progress = index + 1
                intermediate_url = item.get("href")
                if not intermediate_url: continue

                # Fetch the e-next course details page
                if self.debug: print(f" EN Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content: continue
                soup_intermediate = self.parse_html(content)

                # Find the title and the Udemy link on the details page - Verify selectors
                title_element = soup_intermediate.find("h3") # Assuming title is in h3
                link_element = soup_intermediate.find("a", {"class": "btn btn-primary"}) # Assuming Udemy link is in this button
                # Fallbacks
                if not title_element: title_element = soup_intermediate.find("h1")
                if not link_element: link_element = soup_intermediate.find("a", string=re.compile("Enroll|Link|Coupon", re.I), href=True)
                if not link_element: link_element = soup_intermediate.select_one("div.course-buttons a") # Example selector


                if not title_element or not link_element or not link_element.get("href"):
                    if self.debug: print(f"EN: Could not find title/link element on {intermediate_url}")
                    continue

                title = title_element.string.strip() if title_element.string else "N/A"
                raw_link = link_element["href"]
                link = self.cleanup_link(raw_link) # Handles potential redirects

                if link:
                    if self.debug:
                        print(f"EN Found: {title} -> {link}")
                    self.append_to_list(self.en_data, title, link)
                    processed_count += 1
                elif self.debug:
                     print(f"EN Skipped (non-Udemy?): {title} -> {raw_link}")

            # Update length to reflect successfully processed items if needed, or keep intermediate length
            # self.en_length = processed_count # Optional: change length to actual found courses

        except Exception:
            self.handle_exception("en")
        finally:
            self.en_done = True
            if self.debug:
                # print(f"EN Processed Count: {processed_count}") # Use if length is updated
                print(f"EN Return Length: {len(self.en_data)}")

    def cj(self):
        try:
            all_items_intermediate = []
            # Fetch course listing pages
            for page in range(1, 4): # Adjust page range
                if self.debug: print(f"CJ Fetching page {page}...")
                content = self.fetch_page_content(
                    f"https://www.coursejoiner.com/category/free-udemy/page/{page}/"
                )
                if not content: continue
                soup = self.parse_html(content)
                # Find links to individual course posts - Verify selector
                page_items = soup.find_all("h2", class_="card-title entry-title") # Assuming links are in h2/a
                if not page_items and self.debug: # Fallback
                     print(f"CJ: Primary selector failed page {page}. Trying article titles...")
                     page_items = soup.select("article h2.entry-title")

                all_items_intermediate.extend(page_items)

            self.cj_length = len(all_items_intermediate)
            if self.debug:
                print(f"CJ Intermediate Length: {self.cj_length}")

            for index, item in enumerate(all_items_intermediate):
                self.cj_progress = index + 1
                link_tag = item.find("a", href=True) # Link is usually inside the h2
                if not link_tag or not link_tag.string or not link_tag.get("href"):
                    continue

                title = link_tag.string.strip()
                intermediate_url = link_tag["href"]

                # Fetch the CourseJoiner post page
                if self.debug: print(f" CJ Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content: continue
                soup_intermediate = self.parse_html(content)

                # Find the specific button that links to the deal - Verify Selector (VERY LIKELY TO CHANGE)
                link_element = soup_intermediate.find(
                    "a",
                    class_="wp-block-button__link has-black-color has-luminous-vivid-amber-to-luminous-vivid-orange-gradient-background has-text-color has-background wp-element-button",
                )
                # Fallback selectors if the main one fails
                if not link_element:
                     link_element = soup_intermediate.find("a", string=re.compile(r"Get Coupon|Enroll Now|Get Deal", re.IGNORECASE), href=True) # Find by text
                if not link_element:
                     # Look for links within common button container classes
                     button_container = soup_intermediate.find("div", class_=re.compile(r"wp-block-button"))
                     if button_container:
                         link_element = button_container.find("a", href=True)
                if not link_element: # Try finding based on URL patterns
                     link_element = soup_intermediate.find("a", href=re.compile(r"/go/|/visit/|/out/", re.I))


                if not link_element or not link_element.get("href"):
                    if self.debug: print(f"CJ: Could not find link button on {intermediate_url}")
                    continue

                raw_link = link_element["href"]

                # CourseJoiner often uses multiple redirects (internal, then maybe affiliate)
                try:
                    # Use requests session to handle redirects automatically
                    session = requests.Session()
                    session.headers.update({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    })
                    # Set max redirects to avoid infinite loops
                    session.max_redirects = 7
                    if self.debug: print(f" CJ Following redirects for: {raw_link}")
                    response = session.get(raw_link, timeout=scrapper_timeout_period * 2) # Longer timeout for redirects
                    response.raise_for_status()
                    final_url = response.url # URL after all redirects

                    link = self.cleanup_link(final_url)

                    if link:
                        if self.debug:
                            print(f"CJ Found: {title} -> {link}")
                        self.append_to_list(self.cj_data, title, link)
                    elif self.debug:
                        print(f"CJ Skipped (non-Udemy after redirects?): {title} -> {final_url}")

                except requests.exceptions.TooManyRedirects:
                     if self.debug: print(fr + f"CJ Error: Too many redirects for {title} from {raw_link}")
                except requests.RequestException as e:
                    if self.debug:
                        print(fr + f"CJ Error following redirects for {title}: {e}")
                except Exception as e:
                    if self.debug:
                        print(fr + f"CJ Error processing item {index} ({title}): {e}")

        except Exception:
            self.handle_exception("cj")
        finally:
            self.cj_done = True
            if self.debug:
                print(f"CJ Return Length: {len(self.cj_data)}")

    def cd(self):
        try:
            all_items_intermediate = []
            # Fetch listing pages
            for page in range(1, 4): # Adjust page range
                if self.debug: print(f"CD Fetching page {page}...")
                content = self.fetch_page_content(
                    f"https://www.cursosdev.com/?page={page}" # Check URL structure
                )
                if not content: continue
                soup = self.parse_html(content)
                # Find course cards/links - Verify selector
                page_items = soup.find_all(
                    "a",
                    class_="c-card block bg-white shadow-md hover:shadow-xl rounded-lg overflow-hidden" # Verify class
                )
                if not page_items and self.debug: # Fallback
                     print(f"CD: Primary selector failed page {page}. Trying article links...")
                     page_items = soup.select("div.card a")

                all_items_intermediate.extend(page_items)

            self.cd_length = len(all_items_intermediate)
            if self.debug:
                print(f"CD Intermediate Length: {self.cd_length}")

            for index, item in enumerate(all_items_intermediate):
                self.cd_progress = index + 1
                intermediate_url = item.get("href")

                if not intermediate_url or "cursosdev.com" not in intermediate_url: # Ensure it's a link to their site
                    # Check if intermediate_url is relative and prepend base if needed
                    if intermediate_url and intermediate_url.startswith('/'):
                        intermediate_url = f"https://www.cursosdev.com{intermediate_url}"
                    else:
                        continue


                # Fetch the CursosDev course details page
                if self.debug: print(f" CD Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content: continue
                soup_intermediate = self.parse_html(content)

                # Find title and the link to Udemy (often requires following a redirect)
                title_element = soup_intermediate.find("h1", class_=re.compile(r"text-3xl|text-4xl")) # Verify title tag/class
                link_element = soup_intermediate.find(
                    "a",
                    class_=re.compile(r"bg-indigo-900|bg-purple-800|btn-primary"), # Find button by class pattern
                    href=True
                )
                # Fallback: Find by text
                if not link_element:
                     link_element = soup_intermediate.find("a", string=re.compile(r"Ir al curso|Acessar|Get Coupon", re.IGNORECASE), href=True)

                if not title_element or not link_element:
                     if self.debug: print(f"CD: Could not find title/link element on {intermediate_url}")
                     continue

                title = title_element.string.strip() if title_element.string else "N/A"
                raw_link = link_element["href"] # This is likely an internal redirect URL

                try:
                    # Follow the redirect(s)
                    # Prepend base URL if raw_link is relative
                    if raw_link.startswith('/'):
                        raw_link = f"https://www.cursosdev.com{raw_link}"

                    if self.debug: print(f" CD Following redirect: {raw_link}")
                    session = requests.Session()
                    session.max_redirects = 5
                    response = session.get(raw_link, allow_redirects=True, timeout=scrapper_timeout_period)
                    response.raise_for_status()
                    final_url = response.url

                    link = self.cleanup_link(final_url)

                    if link:
                        if self.debug:
                            print(f"CD Found: {title} -> {link}")
                        self.append_to_list(self.cd_data, title, link)
                    elif self.debug:
                        print(f"CD Skipped (non-Udemy?): {title} -> {final_url}")

                except requests.RequestException as e:
                    if self.debug:
                        print(fr + f"CD Error following redirect for {title}: {e}")
                except Exception as e:
                    if self.debug:
                        print(fr + f"CD Error processing item {index} ({title}): {e}")

        except Exception:
            self.handle_exception("cd")
        finally:
            self.cd_done = True
            if self.debug:
                print(f"CD Return Length: {len(self.cd_data)}")

    def ufc(self): # UdemyFreeCourses.org - Uses Playwright
        site_code = "ufc"
        try:
            # Ensure Playwright is available
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                print(fr + f"Playwright not installed. Run 'pip install playwright && playwright install'. Skipping {site_code.upper()} scraper.")
                self.handle_exception(site_code) # Mark as failed due to missing dependency
                return

            all_items_tuples = []
            # More specific categories might yield better results if the main one is too broad/noisy
            bases = [
                "https://udemyfreecourses.org/category/free-course", # Main free category
                "https://udemyfreecourses.org/category/100-off-coupon", # Another potential category
            ]
            print(fy + f"Starting {site_code.upper()} scraper (uses Playwright, may be slow)...")

            with sync_playwright() as p_context:
                 browser = p_context.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                 # Create context without the old routing arguments
                 page_context = browser.new_context(
                      user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
                 )

                 for base in bases:
                     # Limit pages for testing/efficiency
                     for page_num in range(1, 3): # Scrape first 2 pages per category
                         page_url = f"{base}/page/{page_num}/"
                         if self.debug: print(f"Fetching {site_code.upper()}: {page_url}")

                         try:
                             page = page_context.new_page()

                             # --- Set up routing to block resources BEFORE navigation ---
                             def block_resources(route):
                                 if route.request.resource_type in {'image', 'stylesheet', 'font'}:
                                     route.abort()
                                 else:
                                     route.continue_()
                             page.route("**/*", block_resources)
                             # -----------------------------------------------------------

                             # Increase timeout significantly for Playwright
                             page.goto(page_url, wait_until='domcontentloaded', timeout=scrapper_timeout_period * 5 * 1000) # 50 seconds
                             content = page.content()
                             page.close() # Close page after use

                             if not content:
                                 if self.debug: print(fr + f"Failed to fetch content for {page_url}")
                                 continue

                             soup = self.parse_html(content)

                             # Find course items - Adjust selector based on current site structure
                             # Initial selectors
                             page_items = soup.find_all("article", class_=re.compile(r"post-\\d+|tdb_module"))
                             if not page_items: # Fallback 1
                                 page_items = soup.select("div.td-module-container")
                             if not page_items: # Fallback 2: Look for common wrapper classes
                                 page_items = soup.select('div[class*="item-inner"], div.td_module_wrap, article.item')
                             # Add more fallbacks here if needed based on site inspection

                             if not page_items and self.debug:
                                 print(fy + f" UFC: No items found with selectors on {page_url}")

                             added_items_count = 0
                             for item in page_items:
                                 # Find title and link within the item container - Verify selectors
                                 title_tag = item.find("h3", class_=re.compile(r"entry-title|td-module-title"))
                                 link_tag = None
                                 if title_tag:
                                     link_tag = title_tag.find("a", href=True) # Link is often inside title

                                 if not link_tag: # Fallback if link not in title
                                     link_tag = item.find("a", class_=re.compile(r"td-image-wrap|entry-title"), href=True) # Check image link or title link again
                                 if not link_tag: # Last resort
                                     link_tag = item.find("a", href=True) # Find first link in item

                                 if title_tag and link_tag and link_tag.get("href"):
                                     title = title_tag.get_text(strip=True)
                                     intermediate_url = link_tag["href"]
                                     if not intermediate_url.startswith('http'): # Handle relative URLs
                                         intermediate_url = f"https://udemyfreecourses.org{intermediate_url}" if intermediate_url.startswith('/') else f"https://udemyfreecourses.org/{intermediate_url}"

                                     # Fetch intermediate page (using requests is usually faster here)
                                     try:
                                         if self.debug: print(f"  UFC Fetching intermediate: {intermediate_url}")
                                         intermediate_content = self.fetch_page_content(intermediate_url)
                                         if not intermediate_content: continue
                                         intermediate_soup = self.parse_html(intermediate_content)

                                         # Find the final redirect link on the intermediate page - VERIFY SELECTORS
                                         final_link_tag = intermediate_soup.find("a", class_=re.compile(r"fasc-button|btn-success|coupon-button"), href=True) # Common button classes
                                         if not final_link_tag:
                                              final_link_tag = intermediate_soup.find("a", string=re.compile("Enroll|Coupon|Get|Link", re.I), href=True)
                                         if not final_link_tag: # Check specific divs
                                             btn_div = intermediate_soup.find("div", class_="rh-post-wrapper")
                                             if btn_div: final_link_tag = btn_div.find("a", href=True)

                                         if final_link_tag and final_link_tag.get("href"):
                                             raw_link = final_link_tag["href"]
                                             # Follow redirects from the intermediate page link
                                             session = requests.Session()
                                             session.max_redirects = 5
                                             response = session.get(raw_link, allow_redirects=True, timeout=scrapper_timeout_period)
                                             final_redirected_url = response.url

                                             link = self.cleanup_link(final_redirected_url) # Cleanup the final URL

                                             if link:
                                                 all_items_tuples.append((title, link))
                                                 added_items_count += 1
                                                 if self.debug: print(f"    -> Added: {title} ({link})")
                                             elif self.debug:
                                                 print(f"    -> Skipped (non-Udemy?): {title} -> {final_redirected_url}")
                                         elif self.debug:
                                              print(f"    -> UFC: Could not find final link tag on {intermediate_url}")

                                     except requests.RequestException as req_err:
                                         if self.debug: print(fr + f"    -> Error fetching/redirecting intermediate {intermediate_url}: {req_err}")
                                     except Exception as gen_err:
                                         if self.debug: print(fr + f"    -> Error processing intermediate {intermediate_url}: {gen_err}")
                                 else:
                                      if self.debug and item.get_text(strip=True): # Avoid printing for empty divs
                                        print(fy + f"  -> UFC Skipping item, title or link tag not found correctly.")


                             if self.debug: print(f"  Added {added_items_count} items from {page_url}")
                             # Stop pagination if no items were added
                             if added_items_count == 0 and page_num > 1:
                                 if self.debug: print(f"  No new items found on page {page_num}, stopping for {base}")
                                 break # Stop scraping this category

                         except Exception as page_err:
                              if self.debug: print(fr + f"Error processing page {page_url} with Playwright: {page_err}")
                              # traceback.print_exc() # Uncomment for full trace
                              continue # Try next page/base

                 browser.close() # Close browser when done with all categories

            # Remove duplicates (based on link) before setting final data
            final_data = []
            seen_links = set()
            for title, link in all_items_tuples:
                 if link not in seen_links:
                      final_data.append((title, link))
                      seen_links.add(link)

            setattr(self, f"{site_code}_length", len(final_data))
            setattr(self, f"{site_code}_data", final_data)
            # Set progress manually to full length
            setattr(self, f"{site_code}_progress", len(final_data))

            if self.debug:
                print(f"{site_code.upper()} Final Length (deduplicated): {len(final_data)}")

        except Exception:
            self.handle_exception(site_code) # Catch any top-level errors
        finally:
            setattr(self, f"{site_code}_done", True)
            if self.debug:
                print(f"{site_code.upper()} Return Length: {len(getattr(self, f'{site_code}_data', []))}")


class Udemy:
    def __init__(self, interface: str, debug: bool = False):
        self.interface = interface
        self.debug = debug
        self.domain = "www.udemy.com"  # Add the missing domain attribute
        self.client = cloudscraper.session()
        headers = {
            "User-Agent": "okhttp/4.9.2 UdemyAndroid 8.9.2(499) (phone)",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en;q=0.5",
            "Referer": "https://www.udemy.com/",
            "X-Requested-With": "XMLHttpRequest",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

        self.client.headers.update(headers)
        self.settings = {}
        self.enrolled_courses = {}
        self.logger = LoggerAdapter(get_logger("udemy"), {'user': None, 'interface': interface})

    def print(self, content: str, color: str, **kargs):
        # Map color names to log levels
        level_map = {
            "red": "error",
            "yellow": "warning",
            "green": "info",
            "light green": "info",
            "blue": "info",
            "light blue": "info",
            "cyan": "info",
            "magenta": "info",
        }
        
        # Use the appropriate log level based on color
        log_level = level_map.get(color, "info")
        log_method = getattr(self.logger, log_level)
        
        # For GUI interface, still use the window output
        if self.interface == "gui":
            colours_dict = {
                "yellow": fy,
                "red": fr,
                "blue": fb,
                "light blue": flb,
                "green": fg,
                "light green": flg,
                "cyan": fc,
                "magenta": fm,
            }
            self.window["out"].print(content, text_color=color, **kargs)
        
        # Always log to the central logging system regardless of interface
        log_method(content)

    def get_date_from_utc(self, d: str):
        utc_dt = datetime.strptime(d, "%Y-%m-%dT%H:%M:%SZ")
        dt = utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
        return dt.strftime("%B %d, %Y")

    def get_now_to_utc(self):
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    def load_settings(self):
        """Load settings from file"""
        try:
            settings_file = (
                "duce-cli-settings.json" if self.interface == "cli" else "settings.json"
            )
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            self.settings = settings
            if self.debug:
                self.logger.debug("Settings loaded from file")
            return settings
        except FileNotFoundError:
            self.logger.warning(f"Settings file not found: {settings_file}, creating default settings")
            # Create a default settings file if it doesn't exist
            default_settings = {
                "email": "",
                "password": "",
                "use_browser_cookies": False,
                "stay_logged_in": {"auto": False, "manual": False},
                "categories": {},
                "languages": {"en": True},
                "min_rating": 0,
                "max_price": 0,
                "min_reviews": 0,
                "instructor_exclude": [],
                "title_exclude": [],
                "save_txt": True,
                "sites": {
                    site: True for site in scraper_dict.keys()
                },
                "discounted_only": False,
                "course_update_threshold_months": 24,
            }
            self.settings = default_settings
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=2)
            return default_settings
        except Exception as e:
            self.logger.error(f"Error loading settings: {str(e)}")
            self.settings = {}
            return {}

    def save_settings(self):
        settings_file = "duce-cli-settings.json" if self.interface == "cli" else "settings.json"
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)
        self.logger.debug("Settings saved to file")

    def make_cookies(self, client_id: str, access_token: str, csrf_token: str):
        self.cookie_dict = {"client_id": client_id, "access_token": access_token, "csrftoken": csrf_token}

    def fetch_cookies(self):
        """Fetch browser cookies for login"""
        self.logger.info("Fetching cookies from browser")
        try:
            cookies = rookiepy.get_cookies("udemy.com")
            if not cookies:
                raise Exception("No cookies found for udemy.com")
            self.make_cookies(cookies["client_id"], cookies["access_token"], cookies["csrftoken"])
            return cookies
        except Exception as e:
            self.logger.error(f"Error fetching cookies: {str(e)}")
            raise

    def get_enrolled_courses(self):
        """Get list of already enrolled courses"""
        self.logger.info("Fetching enrolled courses list")
        page = 1
        next_page = True
        enrolled_courses = {}
        while next_page:
            url = f"https://www.udemy.com/api-2.0/users/me/subscribed-courses?page={page}&page_size=100&fields[course]=title"
            r = self.client.get(url)
            courses = r.json()
            for course in courses["results"]:
                enrolled_courses[course["id"]] = course["title"]
            if courses["next"]:
                page += 1
            else:
                next_page = False
        self.enrolled_courses = enrolled_courses
        self.logger.info(f"Found {len(enrolled_courses)} enrolled courses")

    def check_for_update(self) -> tuple[str, str]:
        """Check if there's a newer version available"""
        self.logger.info("Checking for updates")
        try:
            r = requests.get(
                "https://techtanic.github.io/duce/update", 
                headers={"User-Agent": "DUCE"}, 
                timeout=5
            )
            latest_version = r.json()["version"]
            # Parse current and latest version as semver
            current_major, current_minor = map(int, VERSION.split(".")[0:2])
            latest_major, latest_minor = map(int, latest_version.split(".")[0:2])
            
            if latest_major > current_major or (latest_major == current_major and latest_minor > current_minor):
                login_title = f"Update v{latest_version}"
                main_title = f"Update v{latest_version}"
                self.logger.warning(f"Update available: v{latest_version}")
            else:
                login_title = "Login"
                main_title = "DUCE"
                self.logger.info("You are using the latest version")
            
            return login_title, main_title
        except Exception as e:
            self.logger.warning(f"Error checking for updates: {str(e)}")
            return "Login", "DUCE"

    def manual_login(self, email: str, password: str):
        """Manually login using email and password"""
        self.logger.info("Attempting manual login with email and password")
        s = requests.session()
        r = s.get(
            "https://www.udemy.com/join/signup-popup/?locale=en_US&response_type=html&next=https%3A%2F%2Fwww.udemy.com%2Flogout%2F",
            headers={"User-Agent": "okhttp/4.9.2 UdemyAndroid 8.9.2(499) (phone)"},
        )
        try:
            csrf_token = r.cookies["csrftoken"]
        except:
            if self.debug:
                self.logger.error("Failed to get CSRF token from login page")
                self.logger.debug(r.text)
            raise LoginException("Could not get CSRF token")
            
        data = {
            "csrfmiddlewaretoken": csrf_token,
            "locale": "en_US",
            "email": email,
            "password": password,
        }

        s.cookies.update(r.cookies)
        s.headers.update(
            {
                "User-Agent": "okhttp/4.9.2 UdemyAndroid 8.9.2(499) (phone)",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-GB,en;q=0.5",
                "Referer": "https://www.udemy.com/join/login-popup/?passwordredirect=True&response_type=json",
                "Origin": "https://www.udemy.com",
                "DNT": "1",
                "Host": "www.udemy.com",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }
        )
        s = cloudscraper.create_scraper(sess=s)
        r = s.post(
            "https://www.udemy.com/join/login-popup/?passwordredirect=True&response_type=json",
            data=data,
            allow_redirects=False,
        )
        if r.text.__contains__("returnUrl"):
            self.make_cookies(
                r.cookies["client_id"], r.cookies["access_token"], csrf_token
            )
            self.logger.info("Manual login successful")
        else:
            login_error = r.json()["error"]["data"]["formErrors"][0]
            if login_error[0] == "Y":
                self.logger.error("Too many login attempts")
                raise LoginException("Too many logins per hour try later")
            elif login_error[0] == "T":
                self.logger.error("Email or password incorrect")
                raise LoginException("Email or password incorrect")
            else:
                self.logger.error(f"Login error: {login_error}")
                raise LoginException(login_error)

    def get_session_info(self):
        """Get session info to verify login status"""
        self.logger.info("Verifying login status")
        s = cloudscraper.CloudScraper()
        headers = {
            "User-Agent": "okhttp/4.9.2 UdemyAndroid 8.9.2(499) (phone)",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en;q=0.5",
            "Referer": "https://www.udemy.com/",
            "X-Requested-With": "XMLHttpRequest",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

        r = s.get(
            "https://www.udemy.com/api-2.0/contexts/me/?header=True",
            cookies=self.cookie_dict,
            headers=headers,
        )
        r = r.json()
        if self.debug:
            self.logger.debug(f"Session info: {r}")
            
        if not r["header"]["isLoggedIn"]:
            self.logger.error("Login verification failed")
            raise LoginException("Login Failed")

        self.display_name: str = r["header"]["user"]["display_name"]
        # Update logger with username
        self.logger.extra['user'] = self.display_name
        
        r = s.get(
            "https://www.udemy.com/api-2.0/shopping-carts/me/",
            headers=headers,
            cookies=self.cookie_dict,
        )
        r = r.json()
        self.currency: str = r["user"]["credit"]["currency_code"]
        self.logger.info(f"Login verified for {self.display_name}, currency: {self.currency}")

        s = cloudscraper.CloudScraper()
        s.cookies.update(self.cookie_dict)
        s.headers.update(headers)
        s.keep_alive = False
        self.client = s
        self.get_enrolled_courses()

    def is_keyword_excluded(self, title: str) -> bool:
        title_words = title.casefold().split()
        for word in title_words:
            word = word.casefold()
            if word in self.title_exclude:
                return True
        return False

    def is_instructor_excluded(self, instructors: list) -> bool:
        for instructor in instructors:
            if instructor in self.settings["instructor_exclude"]:
                return True
        return False

    def is_course_updated(self, last_update: str | None) -> bool:
        if not last_update:
            return True
        current_date = datetime.now()
        last_update_date = datetime.strptime(last_update, "%Y-%m-%d")
        years = current_date.year - last_update_date.year
        months = current_date.month - last_update_date.month
        days = current_date.day - last_update_date.day

        if days < 0:
            months -= 1

        if months < 0:
            years -= 1
            months += 12

        month_diff = years * 12 + months
        return month_diff < self.settings["course_update_threshold_months"]

    def is_user_dumb(self) -> bool:
        self.sites = [key for key, value in self.settings["sites"].items() if value]
        self.categories = [
            key for key, value in self.settings["categories"].items() if value
        ]
        self.languages = [
            key for key, value in self.settings["languages"].items() if value
        ]
        self.instructor_exclude = self.settings["instructor_exclude"]
        self.title_exclude = self.settings["title_exclude"]
        self.min_rating = self.settings["min_rating"]
        return not all([bool(self.sites), bool(self.categories), bool(self.languages)])

    def save_course(self):
        if self.settings["save_txt"]:
            self.txt_file.write(f"{self.title} - {self.link}\n")
            self.txt_file.flush()
            os.fsync(self.txt_file.fileno())

    def remove_duplicate_courses(self):
        existing_links = set()
        new_data = {}
        for key, courses in self.scraped_data.items():
            new_data[key] = []
            for title, link in courses:
                link = self.normalize_link(link)
                if link not in existing_links:
                    new_data[key].append((title, link))
                    existing_links.add(link)
        self.scraped_data = {k: v for k, v in new_data.items() if v}

    def normalize_link(self, link):
        parsed_url = urlparse(link)
        path = (
            parsed_url.path if parsed_url.path.endswith("/") else parsed_url.path + "/"
        )
        return urlunparse(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment,
            )
        )

    def get_course_id(self, url):
        course = {
            "course_id": None,
            "url": url,
            "is_invalid": False,
            "is_free": None,
            "is_excluded": None,
            "retry": None,
            "msg": "Report to developer",
        }
        url = re.sub(r"\W+$", "", unquote(url))
        try:
            r = self.client.get(url)
        except requests.exceptions.ConnectionError:
            if self.debug:
                print(r.text)
            course["retry"] = True
            return course
        course["url"] = r.url
        soup = bs(r.content, "html5lib")

        course_id = soup.find("body").get("data-clp-course-id", "invalid")

        if course_id == "invalid":
            course["is_invalid"] = True
            course["msg"] = "Course ID not found: Report to developer"
            return course
        course["course_id"] = course_id
        dma = json.loads(soup.find("body")["data-module-args"])
        if self.debug:
            with open("debug/dma.json", "w") as f:
                json.dump(dma, f, indent=4)

        if dma.get("view_restriction"):
            course["is_invalid"] = True
            course["msg"] = dma["serverSideProps"]["limitedAccess"]["errorMessage"][
                "title"
            ]
            return course

        course["is_free"] = not dma["serverSideProps"]["course"].get("isPaid", True)
        if not self.debug and self.is_course_excluded(dma):
            course["is_excluded"] = True
            return course

        return course

    def is_course_excluded(self, dma):
        instructors = [
            i["absolute_url"].split("/")[-2]
            for i in dma["serverSideProps"]["course"]["instructors"]["instructors_info"]
            if i["absolute_url"]
        ]
        lang = dma["serverSideProps"]["course"]["localeSimpleEnglishTitle"]
        cat = dma["serverSideProps"]["topicMenu"]["breadcrumbs"][0]["title"]
        rating = dma["serverSideProps"]["course"]["rating"]
        last_update = dma["serverSideProps"]["course"]["lastUpdateDate"]

        if not self.is_course_updated(last_update):
            self.print(
                f"Course excluded: Last updated {last_update}", color="light blue"
            )
        elif self.is_instructor_excluded(instructors):
            self.print(f"Instructor excluded: {instructors[0]}", color="light blue")
        elif self.is_keyword_excluded(self.title):
            self.print("Keyword Excluded", color="light blue")
        elif cat not in self.categories:
            self.print(f"Category excluded: {cat}", color="light blue")
        elif lang not in self.languages:
            self.print(f"Language excluded: {lang}", color="light blue")
        elif rating < self.min_rating:
            self.print(f"Low rating: {rating}", color="light blue")
        else:
            return False
        return True

    def extract_course_coupon(self, url):
        params = parse_qs(urlsplit(url).query)
        return params.get("couponCode", [False])[0]

    def check_course(self, course_id: str, coupon_code: str) -> tuple[float, bool]:
        """
        Check course price with a given coupon code.

        Args:
            course_id: The ID of the course.
            coupon_code: The coupon code to check.

        Returns:
            A tuple containing the course price (float) and coupon validity (bool).
                 Returns -1.0 for price if an error occurs.
        """
        url = f"https://{self.domain}/api-2.0/course-landing-components/{course_id}/me/?components=price_text"
        if coupon_code:
            url += f"&couponCode={coupon_code}"

        try:
            r = self.client.get(url)
            r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = r.json()
            price_info = data.get("price_text", {}).get("data", {})
            amount_str = price_info.get("list_price", {}).get("price_string")
            if not amount_str: # Fallback if list_price is not directly available
                 amount_str = price_info.get("amount") # Check if 'amount' is directly available

            if amount_str:
                # Extract numeric value, handling currency symbols etc.
                import re
                match = re.search(r'[0-9]+([,.][0-9]+)?', amount_str)
                if match:
                    amount = float(match.group(0).replace(',', '.')) # Handle both , and . as decimal separators
                    # Check if the price indicates it's free
                    is_free = price_info.get("purchase_price", {}).get("amount", 1) == 0 or amount == 0
                    # Coupon is considered valid if the course is free OR if a coupon code was provided and used
                    # (assuming the API returns price info means coupon is somewhat valid)
                    coupon_valid = is_free or bool(coupon_code)
                    return amount, coupon_valid
                else:
                     self.print(f"Could not extract numeric price from '{amount_str}' for course {course_id}", color="yellow")
                     return -1.0, False # Indicate price extraction failure
            else:
                self.print(f"Could not find price string in API response for course {course_id}", color="yellow")
                return -1.0, False # Indicate price info not found

        except requests.exceptions.HTTPError as http_err:
             # Specifically handle HTTP errors (like 404 Not Found, 403 Forbidden)
             self.print(f"HTTP error checking course {course_id} ({coupon_code}): {http_err}", color="red")
             # Check if it's a 404 error, potentially indicating the course or coupon is invalid/expired
             if http_err.response.status_code == 404:
                 self.print(f"Course {course_id} with coupon {coupon_code} likely expired or invalid (404).", color="yellow")
                 return -1.0, False # Treat as invalid coupon/course
             # Treat other HTTP errors as general check failures
             return -1.0, False
        except requests.exceptions.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            self.print(f"Failed to decode JSON response for course {course_id} ({coupon_code}). Skipping check.", color="yellow")
            # You might want to log r.text here for debugging if the issue persists
            # self.print(f"Raw Response: {r.text}", color="grey")
            return -1.0, False # Treat as invalid or unable to check

    def start_enrolling(self):
        self.remove_duplicate_courses()
        self.initialize_counters()
        self.setup_txt_file()

        total_courses = sum(len(courses) for courses in self.scraped_data.values())
        previous_courses_count = 0
        for site_index, (site, courses) in enumerate(self.scraped_data.items()):
            self.print(f"\nSite: {site} [{len(courses)}]", color="cyan")

            for index, (title, link) in enumerate(courses):
                self.title = title
                self.link = link
                self.print_course_info(previous_courses_count + index, total_courses)
                self.handle_course_enrollment()
            previous_courses_count += len(courses)

    def initialize_counters(self):
        self.successfully_enrolled_c = 0
        self.already_enrolled_c = 0
        self.expired_c = 0
        self.excluded_c = 0
        self.amount_saved_c = 0

    def setup_txt_file(self):
        if self.settings["save_txt"]:
            os.makedirs("Courses/", exist_ok=True)
            self.txt_file = open(
                f"Courses/{time.strftime('%Y-%m-%d--%H-%M')}.txt", "w", encoding="utf-8"
            )

    def print_course_info(self, index, total_courses):
        self.print(f"[{index + 1} / {total_courses}] ", color="magenta", end=" ")
        self.print(self.title, color="yellow", end=" ")
        self.print(self.link, color="blue")

    def handle_course_enrollment(self):
        course = self.get_course_id(self.link)
        if course["is_invalid"]:
            self.print(course["msg"], color="red")
            self.excluded_c += 1
        elif course["retry"]:
            self.print("Retrying...", color="red")
            time.sleep(1)
            self.handle_course_enrollment()
        elif course["is_excluded"]:
            self.excluded_c += 1
        elif course["course_id"] in self.enrolled_courses:
            self.print(
                f"You purchased this course on {self.get_date_from_utc(self.enrolled_courses[course['course_id']])}",
                color="light blue",
            )
            self.already_enrolled_c += 1
        elif course["is_free"]:
            self.handle_free_course(course["course_id"])
        elif not course["is_free"]:
            self.handle_discounted_course(course["course_id"])
        else:
            self.print("Unknown Error: Report this link to the developer", color="red")
            self.excluded_c += 1

    def handle_free_course(self, course_id):
        if self.settings["discounted_only"]:
            self.print("Free course excluded", color="light blue")
            self.excluded_c += 1
        else:
            success = self.free_checkout(course_id)
            if success:
                self.print("Successfully Subscribed", color="green")
                self.successfully_enrolled_c += 1
                self.save_course()
            else:
                self.print(
                    "Unknown Error: Report this link to the developer", color="red"
                )
                self.expired_c += 1

    def discounted_checkout(self, coupon, course_id) -> dict:
        payload = {
            "checkout_environment": "Marketplace",
            "checkout_event": "Submit",
            "payment_info": {
                "method_id": "0",
                "payment_method": "free-method",
                "payment_vendor": "Free",
            },
            "shopping_info": {
                "items": [
                    {
                        "buyable": {"id": course_id, "type": "course"},
                        "discountInfo": {"code": coupon},
                        "price": {"amount": 0, "currency": self.currency.upper()},
                    }
                ],
                "is_cart": True,
            },
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US",
            "Referer": f"https://www.udemy.com/payment/checkout/express/course/{course_id}/?discountCode={coupon}",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "x-checkout-is-mobile-app": "false",
            "Origin": "https://www.udemy.com",
            "DNT": "1",
            "Sec-GPC": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        csrftoken = None
        for cookie in self.client.cookies:
            if cookie.name == "csrftoken":
                csrftoken = cookie.value
                break

        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
        else:
            raise ValueError("CSRF token not found")

        r = self.client.post(
            "https://www.udemy.com/payment/checkout-submit/",
            json=payload,
            headers=headers,
        )
        try:
            r = r.json()
        except:
            self.print(r.text, color="red")
            self.print("Unknown Error: Report this to the developer", color="red")
            return {"status": "failed", "message": "Unknown Error"}        
        return r

    def free_checkout(self, course_id):
        self.client.get(f"https://www.udemy.com/course/subscribe/?courseId={course_id}")
        r = self.client.get(
            f"https://www.udemy.com/api-2.0/users/me/subscribed-courses/{course_id}/?fields%5Bcourse%5D=%40default%2Cbuyable_object_type%2Cprimary_subcategory%2Cis_private"
        ).json()
        return r.get("_class") == "course"

    def handle_discounted_course(self, course_id):
        coupon_code = self.extract_course_coupon(self.link)
        amount, coupon_valid = self.check_course(course_id, coupon_code)
        if amount == "retry":
            self.print("Retrying...", color="red")
            time.sleep(1)
            self.handle_discounted_course(course_id)
        elif coupon_valid:
            self.process_coupon(course_id, coupon_code, amount)
        else:
            self.print("Coupon Expired", color="red")
            self.expired_c += 1

    def process_coupon(self, course_id, coupon_code, amount):
        checkout_response = self.discounted_checkout(coupon_code, course_id)
        if msg := checkout_response.get("detail"):
            self.print(msg, color="red")
            try:
                wait_time = int(re.search(r"\d+", checkout_response["detail"]).group(0))
            except:
                self.print(
                    "Unknown Error: Report this link to the developer", color="red"
                )
                self.print(checkout_response, color="red")
                wait_time = 60
            time.sleep(wait_time + 1.5)
            self.process_coupon(course_id, coupon_code, amount)
        elif checkout_response["status"] == "succeeded":
            self.print("Successfully Enrolled To Course :)", color="green")
            self.print(
                "This course would have cost you " + str(round(amount, 2)) + " EUR. Enjoy!",
                color="green",
            )
            self.successfully_enrolled_c += 1
            self.enrolled_courses[course_id] = self.get_now_to_utc()
            self.amount_saved_c += amount
            self.save_course()
            time.sleep(3.8)
        elif checkout_response["status"] == "failed":
            message = checkout_response["message"]
            if "item_already_subscribed" in message:
                self.print("Already Enrolled", color="light blue")
                self.already_enrolled_c += 1
            else:
                self.print("Unknown Error: Report this to the developer", color="red")
                self.print(checkout_response, color="red")  # Add color parameter here
        else:
            self.print("Unknown Error: Report this to the developer", color="red")
            self.print(checkout_response, color="red")  # Add color parameter here

