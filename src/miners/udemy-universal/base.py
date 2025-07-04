"""Core components for the Udemy course enroller and scraper.

This module provides base classes and utility functions used by the
Udemy course mining and enrollment tools, including scraper logic,
Udemy API interaction, and exception handling.
"""
# TODO: Standardize the code with the other projects. Current code has been migrated from other project.

import json
import os
import re
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any
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

from colors import fr, fy
from logger import LoggerAdapter, get_logger

# Version number
VERSION = "jmmr.2.5.1"  # Updated with reliability improvements

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
    "Udemy Free Courses": "ufc",
}

LINKS = {
    "github": "https://github.com/techtanic/Discounted-Udemy-Course-Enroller",
    "support": "https://techtanic.github.io/duce/support",
    "discord": "https://discord.gg/wFsfhJh4Rh",
}

scrapper_timeout_period = 30  # seconds - increased from 10 to 20
scrapper_max_retries = 5  # retries


class LoginException(Exception):
    """Login Error.

    Args:
        Exception (str): Exception Reason
    """

    pass


class RaisingThread(threading.Thread):
    """A custom Thread class that allows exceptions to be raised in the calling thread.

    If an exception occurs within the `run` method of this thread, it is stored
    and can be re-raised when `join()` is called.
    """

    def run(self):
        """Overrides the default Thread.run() to catch exceptions."""
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
    """Scrapers: RD,TB, CV, IDC, EN, DU, UF, CJ, UF, CD."""

    def __init__(
        self,
        site_to_scrape: list | None = None,
        debug: bool = False,
    ):
        if site_to_scrape is None:
            site_to_scrape = list(scraper_dict.keys())
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
                self.logger.error(
                    f"Caught exception from thread {t.name}: {thread_exc}"
                )

        for site in self.sites:
            code_name = scraper_dict[site]
            if (
                getattr(self, f"{code_name}_done")
                and getattr(self, f"{code_name}_length") != -1
            ):
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
                    response = requests.get(
                        url, headers=default_headers, timeout=timeout
                    )
                    response.raise_for_status()
                    return response.text
                # If that fails, try with cloudscraper (handles Cloudflare protection)
                else:
                    scraper = cloudscraper.create_scraper(
                        browser={
                            "browser": "chrome",
                            "platform": "windows",
                            "desktop": True,
                        }
                    )
                    response = scraper.get(
                        url, headers=default_headers, timeout=timeout
                    )
                    return response.text
            except (
                requests.RequestException,
                cloudscraper.exceptions.CloudflareChallengeError,
            ) as e:
                retries += 1
                if retries < max_retries:
                    # Switch to cloudscraper after first regular request failure
                    if not used_cloudscraper and isinstance(
                        e, requests.RequestException
                    ):
                        if self.debug:
                            self.logger.warning(
                                f"Switching to cloudscraper for {url} after standard request failed: {e}"
                            )
                        used_cloudscraper = True
                        # No sleep before first cloudscraper attempt
                        continue

                    retry_delay = 2 * retries  # Exponential backoff
                    if self.debug:
                        self.logger.warning(
                            f"Retry {retries}/{max_retries} for {url} after {retry_delay}s: {e}"
                        )
                    time.sleep(retry_delay)
                else:
                    if self.debug:
                        self.logger.error(
                            f"Error fetching {url} after {max_retries} retries: {e}"
                        )
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
                        headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
                    )
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
                    )
                    page = context.new_page()
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=scrapper_timeout_period * 1000,
                    )

                    page_source = page.content()
                    browser.close()
                    return page_source
            except Exception as e:
                retries += 1
                if retries < max_retries:
                    retry_delay = 2 * retries  # Exponential backoff
                    if self.debug:
                        self.logger.warning(
                            f"Retry {retries}/{max_retries} for {url} with Playwright after {retry_delay}s: {e!s}"
                        )
                    time.sleep(retry_delay)
                else:
                    if self.debug:
                        self.logger.error(
                            f"Error fetching {url} with Playwright after {max_retries} retries: {e!s}"
                        )
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
            site_logger = LoggerAdapter(
                get_logger(f"scraper.{site_code}"), {"site_code": site_code}
            )
            site_logger.error(f"Error in {site_code} scraper:")
            site_logger.debug(error_trace)

    def cleanup_link(self, link: str) -> str:
        if not link:
            return ""

        try:
            parsed_url = urlparse(link)

            # Handle direct Udemy links
            if parsed_url.netloc == "www.udemy.com" or parsed_url.netloc == "udemy.com":
                query_params = parse_qs(parsed_url.query)
                valid_params = {}
                if "couponCode" in query_params:
                    valid_params["couponCode"] = query_params["couponCode"]

                cleaned_query = "&".join(
                    [f"{k}={v[0]}" for k, v in valid_params.items()]
                )
                cleaned_path = parsed_url.path.rstrip("/") + "/"

                cleaned_link = urlunparse(
                    (
                        parsed_url.scheme,
                        "www.udemy.com",  # Normalize to www subdomain
                        cleaned_path,
                        "",
                        cleaned_query,
                        "",
                    )
                )
                return cleaned_link

            # Handle known redirectors
            redirector_handlers = {
                "click.linksynergy.com": self._handle_linksynergy,
                "fast.linksly.co": self._handle_generic_redirector,
                "click.linksynergy.art": self._handle_linksynergy,
                "udemy.cc": self._handle_generic_redirector,
                "ad.admitad.com": self._handle_generic_redirector,
                "www.kqzyfj.com": self._handle_generic_redirector,
                "t.grtyi.com": self._handle_generic_redirector,
                "linkjust.com": self._handle_generic_redirector,
                "gotocourse.com": self._handle_generic_redirector,
                "anrdoezrs.net": self._handle_generic_redirector,
                "dpbolvw.net": self._handle_generic_redirector,
                "aff.reideenroll.com": self._handle_generic_redirector,
                "tracking.eljojomkt.com": self._handle_generic_redirector,
                "clk.srv.linksynergy.com": self._handle_linksynergy,
            }

            # Check if the domain is a known redirector
            handler = redirector_handlers.get(parsed_url.netloc)
            if handler:
                return handler(parsed_url, link)

            # Check if the link contains "udemy.com" anywhere
            if "udemy.com" in link:
                # Try to extract the Udemy URL
                udemy_pattern = re.search(
                    r"https?://(?:www\.)?udemy\.com/course/[^/\s]+/?(?:\?(?:couponCode=[^&\s]+)?)?",
                    link,
                )
                if udemy_pattern:
                    return self.cleanup_link(udemy_pattern.group(0))

            # If no handler found and doesn't contain udemy.com, return empty
            if self.debug:
                self.logger.debug(
                    f"Link not recognized as Udemy or known redirector: {link}"
                )
            return ""

        except Exception as e:
            if self.debug:
                self.logger.error(f"Error cleaning link {link}: {e!s}")
            return ""

    def _handle_linksynergy(self, parsed_url, link):
        """Handle LinkSynergy redirector links."""
        query_params = parse_qs(parsed_url.query)
        udemy_link = ""
        # Check for common redirect parameters
        for param in ["RD_PARM1", "murl", "u1", "url", "SREF"]:
            if param in query_params:
                udemy_link = unquote(query_params[param][0])
                break

        if udemy_link:
            return self.cleanup_link(udemy_link)
        return ""

    def _handle_generic_redirector(self, parsed_url, link):
        """Handle generic redirectors by following redirects."""
        try:
            response = requests.head(
                link, allow_redirects=True, timeout=scrapper_timeout_period
            )
            final_url = response.url

            # Check if the final URL is a Udemy link
            if "udemy.com" in final_url:
                return self.cleanup_link(final_url)
        except requests.RequestException as e:
            if self.debug:
                self.logger.error(f"Error following redirect for {link}: {e!s}")
        return ""

    def du(self):
        """Scrapes courses from Discudemy.com.

        Fetches course information from the 'all' category pages, then
        visits intermediate 'go' pages to find the actual Udemy course link.
        """
        try:
            all_items = []
            head = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            }

            for page in range(1, 6):  # Consider reducing page range initially?
                content = self.fetch_page_content(
                    f"https://www.discudemy.com/all/{page}", headers=head
                )
                if not content:
                    continue
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
                if not intermediate_url:
                    continue

                # Extract the identifier from the URL like https://www.discudemy.com/category/103/Business -> category/103/Business
                # or https://www.discudemy.com/English/2 -> English/2
                url_parts = intermediate_url.split("/")
                identifier = "/".join(
                    url_parts[-2:]
                )  # take last two parts for /go/ url

                go_url = f"https://www.discudemy.com/go/{identifier}"
                if self.debug:
                    print(f"DU Fetching intermediate: {go_url}")

                content = self.fetch_page_content(go_url, headers=head)
                if not content:
                    continue
                soup = self.parse_html(content)

                # Find the link within the 'go' page
                link_div = soup.find("div", {"class": "ui segment"})
                if not link_div or not link_div.a:
                    # Try finding link in other common tags if the primary fails
                    link_tag = soup.find(
                        "a", class_=re.compile(r"btn|button", re.I), href=True
                    )
                    if not link_tag:
                        if self.debug:
                            print(f"DU: Could not find link div/a tag on {go_url}")
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
        """Scrapes courses from UdemyFreebies.com.

        Uses Playwright if available to handle JavaScript rendering on the site.
        It navigates through course listing pages, then to intermediate course
        detail pages to find the final Udemy course link, often involving
        button clicks or redirect following.
        """
        site_code = "uf"
        processed_count = (
            0  # Initialize processed_count at the beginning to avoid UnboundLocalError
        )
        try:
            all_items = []
            head = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            }

            # Try to use Playwright for this site if available
            use_playwright = False
            try:
                from playwright.sync_api import sync_playwright

                use_playwright = True
            except ImportError:
                if self.debug:
                    print(
                        f"{site_code.upper()}: Playwright not available, using standard requests."
                    )

            # Fetch the course listing pages
            for page in range(1, 4):  # Reduced page range to 4 to speed up scraping
                url = f"https://www.udemyfreebies.com/free-udemy-courses/{page}"
                if self.debug:
                    print(f"{site_code.upper()} Fetching page {page}: {url}")

                if use_playwright:
                    # Use Playwright for the main page to handle any JS rendering
                    try:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(
                                headless=True,
                                args=["--no-sandbox", "--disable-dev-shm-usage"],
                            )
                            context = browser.new_context(user_agent=head["user-agent"])
                            page_obj = context.new_page()
                            page_obj.goto(
                                url,
                                wait_until="networkidle",
                                timeout=scrapper_timeout_period * 1000,
                            )
                            content = page_obj.content()
                            browser.close()
                    except Exception as browser_error:
                        if self.debug:
                            print(
                                f"{site_code.upper()}: Playwright browser error: {browser_error}"
                            )
                        use_playwright = False  # Fall back to requests
                        content = self.fetch_page_content(url, headers=head)
                else:
                    # Fallback to standard requests if Playwright not available
                    content = self.fetch_page_content(url, headers=head)

                if not content:
                    continue
                soup = self.parse_html(content)

                # Try multiple selectors for course items
                page_items = soup.find_all("a", {"class": "theme-img"})
                if not page_items:
                    page_items = soup.select("div.item a")  # Alternative selector
                if not page_items:
                    page_items = soup.select("article.course a")  # Another alternative

                all_items.extend(page_items)

            setattr(self, f"{site_code}_length", len(all_items))
            if self.debug:
                print(
                    f"{site_code.upper()} Length: {getattr(self, f'{site_code}_length')}"
                )
            for index, item in enumerate(all_items):
                setattr(self, f"{site_code}_progress", index + 1)

                # Extract title from multiple possible locations
                title = None
                if item.img and item.img.get("alt"):
                    title = item.img["alt"].strip()
                elif item.get("title"):
                    title = item["title"].strip()
                elif item.text:
                    title = item.text.strip()

                if not title or not item.get("href"):
                    if self.debug:
                        print(
                            f"{site_code.upper()} Skipping item {index}: Missing title or href"
                        )
                    continue

                relative_url = item["href"]

                # Use direct Udemy link if present in the initial href
                if "udemy.com/course" in relative_url:
                    link = self.cleanup_link(relative_url)
                    if link:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Found direct Udemy link: {link}"
                            )
                        self.append_to_list(
                            getattr(self, f"{site_code}_data"), title, link
                        )
                        processed_count += 1
                        continue

                # Build the intermediate URL
                if not relative_url.startswith("http"):
                    base_uf = "https://www.udemyfreebies.com"
                    intermediate_page_url = (
                        f"{base_uf}{relative_url}"
                        if relative_url.startswith("/")
                        else f"{base_uf}/{relative_url}"
                    )
                else:
                    intermediate_page_url = relative_url

                if self.debug:
                    print(
                        f"{site_code.upper()} Fetching intermediate: {intermediate_page_url}"
                    )

                # Use Playwright for intermediate pages if available
                if use_playwright:
                    try:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(
                                headless=True,
                                args=["--no-sandbox", "--disable-dev-shm-usage"],
                            )
                            context = browser.new_context(user_agent=head["user-agent"])
                            page_obj = context.new_page()
                            page_obj.goto(
                                intermediate_page_url,
                                wait_until="networkidle",
                                timeout=scrapper_timeout_period * 1000,
                            )

                            # Try clicking any "Get Deal" button that might be present
                            try:
                                # Wait for and click any button that might trigger the redirect
                                button_selector = 'a:has-text("Deal"), a:has-text("Coupon"), a:has-text("Enroll"), a.btn-success, a.coupon-btn'
                                page_obj.wait_for_selector(
                                    button_selector, timeout=10000
                                )
                                with page_obj.expect_navigation(
                                    wait_until="networkidle",
                                    timeout=scrapper_timeout_period * 1000,
                                ):
                                    page_obj.click(button_selector)

                                # Get the final URL after clicking
                                final_url = page_obj.url
                                if "udemy.com/course" in final_url:
                                    link = self.cleanup_link(final_url)
                                    if link:
                                        if self.debug:
                                            print(
                                                f"{site_code.upper()} Found (after click): {title} -> {link}"
                                            )
                                        self.append_to_list(
                                            getattr(self, f"{site_code}_data"),
                                            title,
                                            link,
                                        )
                                        processed_count += 1
                                        browser.close()
                                        continue
                            except Exception as e:
                                if self.debug:
                                    print(
                                        f"{site_code.upper()} Click attempt failed: {e!s}"
                                    )

                            # If clicking failed, try to extract from the current page
                            inter_content = page_obj.content()
                            browser.close()
                    except Exception as e:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Playwright error on {intermediate_page_url}: {e!s}"
                            )
                        inter_content = self.fetch_page_content(
                            intermediate_page_url, headers=head
                        )
                else:
                    inter_content = self.fetch_page_content(
                        intermediate_page_url, headers=head
                    )

                if not inter_content:
                    if self.debug:
                        print(
                            f"{site_code.upper()} Failed to fetch intermediate page: {intermediate_page_url}"
                        )
                    continue

                inter_soup = self.parse_html(inter_content)

                # Try multiple approaches to find the Udemy link

                # 1. Look for direct Udemy links
                udemy_links = inter_soup.find_all(
                    "a", href=re.compile(r"udemy\.com/course")
                )
                if udemy_links:
                    raw_link = udemy_links[0]["href"]
                    link = self.cleanup_link(raw_link)
                    if link:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Found direct Udemy link: {title} -> {link}"
                            )
                        self.append_to_list(
                            getattr(self, f"{site_code}_data"), title, link
                        )
                        processed_count += 1
                        continue

                # 2. Try to find redirector links
                button_selectors = [
                    # By class
                    (
                        "a",
                        {
                            "class": re.compile(
                                r"btn-success|coupon-code|redeem|affiliate|deal-button"
                            )
                        },
                    ),
                    # By text
                    (
                        "a",
                        {
                            "string": re.compile(
                                r"Get the Deal|Enroll|Redeem|Get Coupon|Get Course",
                                re.I,
                            )
                        },
                    ),
                    # By href pattern
                    ("a", {"href": re.compile(r"/out/\d+|/goto/|/redirect/|/link/")}),
                    # By container
                    ("div.coupon-wrapper a", {}),
                    ("div.text-center a", {}),
                    ("div.button-container a", {}),
                ]

                redirect_url = None
                for selector, attrs in button_selectors:
                    if "." in selector:  # CSS selector
                        elements = inter_soup.select(selector)
                    else:  # BeautifulSoup find_all
                        elements = inter_soup.find_all(selector, attrs)

                    if elements and elements[0].get("href"):
                        redirect_url = elements[0]["href"]
                        if self.debug:
                            print(
                                f"{site_code.upper()} Found redirect URL: {redirect_url}"
                            )
                        break

                if not redirect_url:
                    if self.debug:
                        print(
                            f"{site_code.upper()} No redirect URL found on {intermediate_page_url}"
                        )
                    continue

                # 3. Handle the redirect URL
                if not redirect_url.startswith("http"):
                    base_uf = "https://www.udemyfreebies.com"
                    redirect_url = (
                        f"{base_uf}{redirect_url}"
                        if redirect_url.startswith("/")
                        else f"{base_uf}/{redirect_url}"
                    )

                # 4. Follow the redirect
                try:
                    if self.debug:
                        print(f"{site_code.upper()} Following redirect: {redirect_url}")
                    response = requests.get(
                        redirect_url,
                        headers=head,
                        allow_redirects=True,
                        timeout=scrapper_timeout_period,
                    )
                    final_url = response.url

                    # 5. Process the final URL
                    link = self.cleanup_link(final_url)
                    if link:
                        if self.debug:
                            print(f"{site_code.upper()} Found: {title} -> {link}")
                        self.append_to_list(
                            getattr(self, f"{site_code}_data"), title, link
                        )
                        processed_count += 1
                    elif self.debug:
                        print(
                            f"{site_code.upper()} Skipped (not a valid Udemy link): {title} -> {final_url}"
                        )

                except requests.RequestException as e:
                    if self.debug:
                        print(
                            fr
                            + f"{site_code.upper()} Error fetching redirect {redirect_url} for {title}: {e}"
                        )
                except Exception as e:
                    if self.debug:
                        print(
                            fr
                            + f"{site_code.upper()} Error processing item {index} ({title}): {e}"
                        )

        except Exception:
            self.handle_exception(site_code)
        finally:
            setattr(self, f"{site_code}_done", True)
            if self.debug:
                print(
                    f"{site_code.upper()} Return Length: {len(getattr(self, f'{site_code}_data'))}"
                )
                print(f"{site_code.upper()} Processed Count: {processed_count}")

    def tb(self):
        """Scrapes courses from TutorialBar.com.

        Fetches course listings, then visits each course's detail page on
        TutorialBar to find the offer link, which is then processed to
        extract the final Udemy course URL.
        """
        try:
            all_items = []

            for page in range(1, 8):  # Adjust page range if needed
                content = self.fetch_page_content(
                    f"https://www.tutorialbar.com/all-courses/page/{page}"
                )
                if not content:
                    continue
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
                if self.debug:
                    print(f"TB Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content:
                    continue
                soup_intermediate = self.parse_html(content)

                # Find the specific button/link for the offer
                link_element = soup_intermediate.find(
                    "a", class_="btn_offer_block re_track_btn"
                )
                # Fallback selectors
                if not link_element:
                    link_element = soup_intermediate.find(
                        "a", class_=re.compile(r"btn.*offer|offer.*btn"), href=True
                    )
                if not link_element:
                    link_element = soup_intermediate.find(
                        "a",
                        string=re.compile(r"Get Coupon|Enroll|Offer", re.I),
                        href=True,
                    )

                if not link_element or not link_element.get("href"):
                    if self.debug:
                        print(f"TB: Could not find offer button on {intermediate_url}")
                    continue

                raw_link = link_element["href"]
                link = self.cleanup_link(raw_link)  # cleanup handles redirects

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
        """Scrapes courses from Real.Discount.

        Uses Playwright to navigate the site, potentially applying filters for
        free courses. It extracts course information from course cards, then
        visits intermediate pages to find the final Udemy course link.
        """
        site_code = "rd"
        processed_count = (
            0  # Initialize processed_count at the beginning to avoid UnboundLocalError
        )
        try:
            # Ensure Playwright is available
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                if self.debug:
                    print(
                        f"{site_code.upper()}: Playwright not installed. Run 'pip install playwright && playwright install'. Skipping scraper."
                    )
                setattr(self, f"{site_code}_error", "Playwright not installed")
                setattr(self, f"{site_code}_length", -1)
                setattr(self, f"{site_code}_done", True)
                return

            base_url = "https://real.discount/udemy-coupon-codes"  # Changed URL to a more direct one
            if self.debug:
                print(f"Starting {site_code.upper()} scraper (uses Playwright)...")

            # Use a reduced timeout for better performance
            page_timeout = (
                min(scrapper_timeout_period * 2, 60) * 1000
            )  # in ms, capped at 60 seconds

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()

                # Set default timeout for all operations
                page.set_default_timeout(page_timeout)

                if self.debug:
                    print(f"{site_code.upper()}: Navigating to {base_url}")

                try:
                    # Try to navigate with a more lenient 'domcontentloaded' wait strategy first
                    page.goto(
                        base_url, wait_until="domcontentloaded", timeout=page_timeout
                    )

                    # Wait for specific content to be available before proceeding
                    if self.debug:
                        print(
                            f"{site_code.upper()}: Waiting for course cards to load..."
                        )
                    page.wait_for_selector(
                        "div.card, article.course, div.course-card",
                        timeout=page_timeout,
                    )

                    # --- Attempt to filter for free courses ---
                    try:
                        if self.debug:
                            print(
                                f"{site_code.upper()}: Attempting to filter for free courses..."
                            )
                        # Try clicking the 'Free' filter button if it exists
                        free_filters = [
                            'label:has-text("Free")',
                            'button:has-text("Free")',
                            'a:has-text("Free Courses")',
                        ]

                        for selector in free_filters:
                            if page.is_visible(selector):
                                if self.debug:
                                    print(
                                        f"{site_code.upper()}: Found and clicking {selector}"
                                    )
                                page.click(selector)
                                # Wait for the page to update after clicking
                                page.wait_for_load_state(
                                    "networkidle", timeout=page_timeout / 2
                                )
                                break
                    except Exception as e:
                        if self.debug:
                            print(
                                f"{site_code.upper()}: Could not apply free filter: {e!s}"
                            )
                            print(
                                f"{site_code.upper()}: Proceeding with all courses..."
                            )

                    # Get content after filtering
                    content = page.content()
                except Exception as e:
                    if self.debug:
                        print(
                            f"{site_code.upper()}: Error during initial page load: {e!s}"
                        )
                        print(f"{site_code.upper()}: Trying alternate approach...")

                    # Alternative approach: try a different URL
                    alt_url = "https://real.discount/filter/free"
                    try:
                        page.goto(
                            alt_url, wait_until="domcontentloaded", timeout=page_timeout
                        )
                        if self.debug:
                            print(
                                f"{site_code.upper()}: Navigated to alternate URL: {alt_url}"
                            )
                        content = page.content()
                    except Exception as alt_error:
                        if self.debug:
                            print(
                                f"{site_code.upper()}: Alternate approach also failed: {alt_error!s}"
                            )
                        self.rd_error = f"Failed to load both primary and alternate URLs: {e!s} / {alt_error!s}"
                        self.rd_length = -1
                        self.rd_done = True
                        browser.close()
                        return

                browser.close()  # Close browser once we have the content

                if not content:
                    self.rd_error = "Failed to fetch page content with Playwright"
                    self.rd_length = -1
                    self.rd_done = True
                    if self.debug:
                        print(fr + self.rd_error)
                    return

                # Parse the HTML
                soup = self.parse_html(content)

                # Find course items - Try multiple selectors
                course_cards = []
                selectors = [
                    "div.card.product-card",
                    "div.course-item",
                    "article.course-post",
                    "div.card",  # More generic fallback
                    "div.col-md-4",  # Another fallback to try finding grid items
                ]

                for selector in selectors:
                    course_cards = soup.select(selector)
                    if course_cards:
                        if self.debug:
                            print(
                                f"{site_code.upper()}: Found {len(course_cards)} courses using selector '{selector}'"
                            )
                        break

                self.rd_length = len(course_cards)
                if self.debug:
                    print(f"{site_code.upper()} Length: {self.rd_length}")
                    if self.rd_length == 0:
                        print(
                            f"{site_code.upper()}: No courses found. Saving HTML for debugging."
                        )
                        with open("debug_rd_page.html", "w", encoding="utf-8") as f:
                            f.write(content)

                processed_count = 0
                for index, item in enumerate(course_cards):
                    self.rd_progress = index + 1

                    # Extract title and link with multiple fallback strategies
                    title = None
                    intermediate_url = None

                    # Try to find title
                    title_selectors = [
                        ("h3.card-title", lambda e: e.get_text(strip=True)),
                        ("h3", lambda e: e.get_text(strip=True)),
                        ("h2", lambda e: e.get_text(strip=True)),
                        ("div.course-title", lambda e: e.get_text(strip=True)),
                        ("img", lambda e: e.get("alt", "")),
                    ]

                    for selector, extractor in title_selectors:
                        if "." in selector:  # CSS selector
                            elements = item.select(selector)
                            if elements:
                                title = extractor(elements[0])
                                break
                        else:  # Tag name
                            element = item.find(selector)
                            if element:
                                title = extractor(element)
                                break

                    # Try to find link
                    link_selectors = [
                        ("a.stretched-link", "href"),
                        ("a.course-link", "href"),
                        ("a.btn-details", "href"),
                        ("a.card-link", "href"),
                        ("a", "href"),  # Fallback to any link
                    ]

                    for selector, attr in link_selectors:
                        if "." in selector:  # CSS selector
                            elements = item.select(selector)
                            if elements and elements[0].get(attr):
                                intermediate_url = elements[0][attr]
                                break
                        else:  # Tag name
                            elements = item.find_all(selector)
                            for el in elements:
                                if el.get(attr):
                                    intermediate_url = el[attr]
                                    break
                            if intermediate_url:
                                break

                    if not title or not intermediate_url:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Skipping item {index}: Missing title or link"
                            )
                        continue

                    # Clean title if needed
                    title = title.strip()

                    # Direct use if it's already a Udemy link
                    if "udemy.com/course" in intermediate_url:
                        link = self.cleanup_link(intermediate_url)
                        if link:
                            if self.debug:
                                print(
                                    f"{site_code.upper()} Found direct Udemy link: {title} -> {link}"
                                )
                            self.append_to_list(self.rd_data, title, link)
                            processed_count += 1
                        continue

                    # Ensure the intermediate URL is absolute
                    if not intermediate_url.startswith("http"):
                        parsed_base = urlparse(base_url)
                        intermediate_url = urlunparse(
                            (
                                parsed_base.scheme,
                                parsed_base.netloc,
                                intermediate_url,
                                "",
                                "",
                                "",
                            )
                        )

                    # Fetch the intermediate page on Real Discount to find the Udemy link
                    if self.debug:
                        print(
                            f"{site_code.upper()} Fetching intermediate: {intermediate_url}"
                        )

                    # Use a shorter timeout for intermediate pages
                    intermediate_content = self.fetch_page_content(
                        intermediate_url, timeout=min(scrapper_timeout_period, 30)
                    )
                    if not intermediate_content:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Failed to fetch intermediate page: {intermediate_url}"
                            )
                        continue

                    soup_intermediate = self.parse_html(intermediate_content)

                    # Try to find the Udemy link with multiple approaches
                    udemy_link = None

                    # 1. Look for direct Udemy links first
                    udemy_links = soup_intermediate.find_all(
                        "a", href=re.compile(r"udemy\.com/course")
                    )
                    if udemy_links:
                        udemy_link = udemy_links[0]["href"]
                    else:
                        # 2. Try finding through common button patterns
                        button_selectors = [
                            # By class
                            ("a.btn-success", "href"),
                            ("a.coupon-button", "href"),
                            ("a.go-to-deal", "href"),
                            # By text
                            ("a:contains('Get Coupon')", "href"),
                            ("a:contains('Enroll')", "href"),
                            ("a:contains('Go To Course')", "href"),
                            ("a:contains('Visit Deal')", "href"),
                        ]

                        for selector, attr in button_selectors:
                            if ":contains" in selector:  # Custom contains selector
                                text = selector.split("'")[1]
                                elements = soup_intermediate.find_all(
                                    "a", string=re.compile(text, re.I)
                                )
                            else:  # CSS selector
                                elements = soup_intermediate.select(selector)

                            if elements and elements[0].get(attr):
                                udemy_link = elements[0][attr]
                                break

                    if not udemy_link:
                        if self.debug:
                            print(
                                f"{site_code.upper()}: Could not find Udemy link on {intermediate_url}"
                            )
                        continue

                    link = self.cleanup_link(udemy_link)
                    if link:
                        if self.debug:
                            print(f"{site_code.upper()} Found: {title} -> {link}")
                        self.append_to_list(self.rd_data, title, link)
                        processed_count += 1
                    elif self.debug:
                        print(
                            f"{site_code.upper()} Skipped (non-Udemy): {title} -> {udemy_link}"
                        )

            if self.debug:
                print(f"{site_code.upper()} Processed Count: {processed_count}")

        except Exception:
            # Use handle_exception to capture the traceback and set flags
            self.handle_exception(site_code)
        finally:
            # Ensure done flag is always set
            setattr(self, f"{site_code}_done", True)
            if self.debug:
                print(
                    f"{site_code.upper()} Return Length: {len(getattr(self, f'{site_code}_data', []))}"
                )

    def cv(self):
        """Scrapes courses from Coursevania.com.

        Attempts to fetch courses using an API endpoint with a nonce if found,
        otherwise falls back to direct HTML scraping of course listings.
        It then visits intermediate course pages to find the Udemy link.
        """
        try:
            # Fetch main page to potentially get nonce or other required info
            if self.debug:
                print("CV: Fetching main page...")
            main_page_content = self.fetch_page_content(
                "https://coursevania.com/courses/"
            )
            if not main_page_content:
                self.cv_error = "Failed to fetch main page"
                self.cv_length = -1
                self.cv_done = True
                if self.debug:
                    print(fr + self.cv_error)
                return

            soup_main = self.parse_html(main_page_content)
            nonce = None
            try:
                # Look for nonce in script tags (more robustly)
                script_tags = soup_main.find_all("script")
                # Use raw strings (r prefix) for regex patterns with backslashes
                nonce_pattern = re.compile(
                    r"[\'\"]load_content[\'\"]\s*:\s*[\'\"]([a-zA-Z0-9]+)[\'\"]"
                )
                nonce_pattern_alt = re.compile(
                    r"ajax_nonce[\'\"]\s*:\s*[\'\"]([a-zA-Z0-9]+)[\'\"]"
                )  # Look for ajax_nonce too

                for script in script_tags:
                    script_content = str(script)  # Convert script tag content to string
                    match = nonce_pattern.search(script_content)
                    if match:
                        nonce = match.group(1)
                        if self.debug:
                            print(f"CV Found Nonce (load_content): {nonce}")
                        break
                    else:  # Try alternative pattern if first fails
                        match_alt = nonce_pattern_alt.search(script_content)
                        if match_alt:
                            nonce = match_alt.group(1)
                            if self.debug:
                                print(f"CV Found Nonce (ajax_nonce): {nonce}")
                            break  # Found nonce, exit loop

                # If nonce not found in script tags, try looking in input fields (sometimes stored there)
                if not nonce:
                    nonce_input = soup_main.find("input", {"name": "nonce"})
                    if nonce_input and nonce_input.get("value"):
                        nonce = nonce_input["value"]
                        if self.debug:
                            print(f"CV Found Nonce (input field): {nonce}")

                # If still no nonce, let's try looking for data attributes
                if not nonce:
                    elements_with_data = soup_main.find_all(attrs={"data-nonce": True})
                    if elements_with_data:
                        nonce = elements_with_data[0]["data-nonce"]
                        if self.debug:
                            print(f"CV Found Nonce (data attribute): {nonce}")

                if not nonce:
                    # Instead of failing, we'll try an alternative approach - directly scraping course pages
                    if self.debug:
                        print(
                            "CV: Nonce not found. Falling back to direct course page scraping..."
                        )
                    # Proceed with direct scraping

            except (ValueError, Exception) as e:
                if self.debug:
                    print(
                        f"CV Warning: Nonce finding error: {e!s}. Proceeding with alternative approach."
                    )
                # Instead of returning, continue with direct scraping approach

            # Direct scraping approach (fallback if API approach doesn't work)
            # Find course cards directly from the main page
            course_cards = soup_main.find_all(
                "div",
                class_=re.compile(r"stm_lms_courses__single|course-card|card-item"),
            )

            # If we didn't find courses directly and we have a nonce, try the API
            if len(course_cards) == 0 and nonce:
                # Make API call to load courses
                api_url = f'https://coursevania.com/wp-admin/admin-ajax.php?template=courses/grid&args={{"posts_per_page":"100"}}&action=stm_lms_load_content&nonce={nonce}&sort=date_high'
                if self.debug:
                    print(f"CV Fetching API: {api_url}")

                api_content = ""
                try:
                    response = requests.get(
                        api_url, timeout=scrapper_timeout_period * 2
                    )  # Double timeout
                    response.raise_for_status()
                    r = response.json()
                    # Check response structure - it might contain HTML in 'content' or 'html'
                    api_content = r.get("content", r.get("html", ""))
                    if not api_content and self.debug:
                        print(
                            fy
                            + f"CV: API response JSON didn't contain 'content' or 'html'. Response: {r}"
                        )

                except (requests.RequestException, json.JSONDecodeError) as e:
                    if self.debug:
                        print(
                            fy
                            + f"CV Warning: API request error: {e!s}. Proceeding with direct scraping."
                        )
                    # Continue with whatever course cards we found directly (could be empty)

                # If API returned content, parse it for course items
                if api_content:
                    soup_api = self.parse_html(api_content)
                    api_courses = soup_api.find_all(
                        "div", {"class": re.compile(r"stm_lms_courses__single")}
                    )
                    course_cards.extend(api_courses)

            # Last resort fallback - try accessing user pages which might show courses
            if len(course_cards) == 0:
                alternative_urls = [
                    "https://coursevania.com/user-account/",
                    "https://coursevania.com/courses/",
                    "https://coursevania.com/free-courses/",
                ]

                for alt_url in alternative_urls:
                    if self.debug:
                        print(f"CV Fetching alternative page: {alt_url}")
                    alt_content = self.fetch_page_content(
                        alt_url, timeout=scrapper_timeout_period * 2
                    )
                    if alt_content:
                        alt_soup = self.parse_html(alt_content)
                        alt_courses = alt_soup.find_all(
                            "div",
                            class_=re.compile(r"stm_lms_courses__single|course-item"),
                        )
                        # Also look for course links directly
                        course_links = alt_soup.find_all(
                            "a", href=re.compile(r"/courses/[^/]+/$")
                        )

                        if alt_courses:
                            course_cards.extend(alt_courses)
                            if self.debug:
                                print(
                                    f"CV Found {len(alt_courses)} courses on {alt_url}"
                                )
                            break  # Found courses, stop trying alternatives
                        elif course_links:
                            # Create synthetic course cards from links
                            for link in course_links:
                                if link.get("href") and (
                                    link.string or link.get_text(strip=True)
                                ):
                                    div = soup_main.new_tag("div")
                                    div["class"] = "synthetic-course-card"
                                    div.append(link)
                                    course_cards.append(div)
                            if self.debug:
                                print(
                                    f"CV Found {len(course_links)} course links on {alt_url}"
                                )
                            break  # Found course links, stop trying alternatives

            # Set the length based on all courses found
            self.cv_length = len(course_cards)
            if self.debug:
                print(f"CV Length (combined): {self.cv_length}")

            # Process all course cards/links found
            for index, item in enumerate(course_cards):
                self.cv_progress = index + 1

                # Find the course link - could be in several different locations depending on source
                link_tag = None

                # Try finding in title div (usual location)
                title_div = item.find(
                    "div", class_=re.compile(r"title|stm_lms_courses__single--title")
                )
                if title_div and title_div.find("a", href=True):
                    link_tag = title_div.find("a", href=True)

                # If not found, try h5/h4/h3 (common title tags)
                if not link_tag:
                    for tag_name in ["h5", "h4", "h3"]:
                        title_tag = item.find(tag_name)
                        if title_tag and title_tag.find("a", href=True):
                            link_tag = title_tag.find("a", href=True)
                            break

                # If still not found, look for any a tag with href
                if not link_tag:
                    # Check if the item itself is an a tag (from synthetic cards)
                    if item.name == "a" and item.get("href"):
                        link_tag = item
                    else:
                        link_tag = item.find("a", href=True)

                if not link_tag or not link_tag.get("href"):
                    if self.debug:
                        print(f"CV: Could not find link in item {index}")
                    continue

                # Extract title - different ways depending on link structure
                if link_tag.string and link_tag.string.strip():
                    title = link_tag.string.strip()
                else:
                    # Try getting text from the tag
                    title = link_tag.get_text(strip=True)
                    # If that fails, try looking for image alt text
                    if not title:
                        img = link_tag.find("img")
                        if img and img.get("alt"):
                            title = img["alt"].strip()
                        else:
                            # Last resort: extract from URL
                            title = (
                                link_tag["href"]
                                .split("/")[-2]
                                .replace("-", " ")
                                .title()
                            )

                intermediate_url = link_tag["href"]
                if not intermediate_url:
                    continue

                # Ensure URL is absolute
                if not intermediate_url.startswith("http"):
                    intermediate_url = (
                        f"https://coursevania.com{intermediate_url}"
                        if intermediate_url.startswith("/")
                        else f"https://coursevania.com/{intermediate_url}"
                    )

                # Fetch the intermediate course page with extended timeout
                if self.debug:
                    print(f" CV Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(
                    intermediate_url, timeout=45
                )  # Extended timeout
                if not content:
                    continue
                soup_intermediate = self.parse_html(content)

                # Try multiple potential affiliate link selectors
                affiliate_selectors = [
                    # Button class selectors (most specific first)
                    {
                        "tag": "a",
                        "attrs": {"class": "masterstudy-button-affiliate__link"},
                    },
                    {
                        "tag": "a",
                        "attrs": {"class": re.compile(r"btn-default btn.*?affiliate")},
                    },
                    {
                        "tag": "a",
                        "attrs": {"class": re.compile(r"affiliate|coupon|button")},
                    },
                    # Text-based selectors
                    {
                        "tag": "a",
                        "attrs": {
                            "string": re.compile(
                                r"Get Deal|Take This Course|Enroll Now|Redeem Coupon",
                                re.I,
                            )
                        },
                    },
                    # Container-based selectors
                    {
                        "container": "div",
                        "container_attrs": {"class": "stm-lms-buy-buttons"},
                        "tag": "a",
                    },
                    {
                        "container": "div",
                        "container_attrs": {
                            "class": re.compile(r"price|button-container|coupon-area")
                        },
                        "tag": "a",
                    },
                    # URL pattern based selectors
                    {
                        "tag": "a",
                        "attrs": {
                            "href": re.compile(r"udemy\.com/course/[^/]+/\?couponCode=")
                        },
                    },
                    # Last resort - any prominent button
                    {"tag": "a", "attrs": {"class": re.compile(r"btn|button")}},
                ]

                final_link_element = None

                # Try each selector in order until we find a match
                for selector in affiliate_selectors:
                    if "container" in selector:
                        # Two-step selection: find container first, then find link inside it
                        container = soup_intermediate.find(
                            selector["container"], selector["container_attrs"]
                        )
                        if container:
                            final_link_element = container.find(
                                selector["tag"], href=True
                            )
                    else:
                        # Direct selection
                        final_link_element = soup_intermediate.find(
                            selector["tag"], selector["attrs"], href=True
                        )

                    if final_link_element and final_link_element.get("href"):
                        break

                # If nothing found through selectors, look for udemy.com links directly in all a tags
                if not final_link_element:
                    all_links = soup_intermediate.find_all("a", href=True)
                    for link in all_links:
                        if "udemy.com/course" in link.get(
                            "href", ""
                        ) and "couponCode" in link.get("href", ""):
                            final_link_element = link
                            break

                if not final_link_element or not final_link_element.get("href"):
                    if self.debug:
                        print(
                            f"CV: Could not find affiliate link on {intermediate_url}"
                        )
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
                self.cv_length = -1  # Mark as failed if unexpected error
            if self.debug:
                print(fr + f"CV Main Exception: {main_exception}")
            # Ensure handle_exception logic is covered or called appropriately
            self.handle_exception("cv")  # Call handle_exception to set done flag etc.
        finally:
            self.cv_done = True  # Ensure done flag is always set
            if self.debug:
                print(f"CV Return Length: {len(self.cv_data)}")

    def idc(self):
        """Scrapes courses from iDownloadCoupon.com.

        Navigates through paginated course listings, extracts links to
        intermediate product pages, and then attempts to find the final
        Udemy course URL, potentially by following redirects or extracting
        it from the intermediate page content.
        """
        site_code = "idc"
        try:
            all_items = []
            processed_count = 0

            # Add more robust headers to avoid being blocked
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            # Reduce the number of pages to scan initially to improve reliability
            for page in range(1, 4):  # Reduced from 8 to 4 pages
                if self.debug:
                    print(f"{site_code.upper()} Fetching page {page}...")

                url = f"https://idownloadcoupon.com/product-category/udemy/page/{page}"
                content = self.fetch_page_content(url, headers=headers)

                if not content:
                    if self.debug:
                        print(f"{site_code.upper()} Failed to fetch page {page}")
                    continue

                soup = self.parse_html(content)

                # Try multiple selectors to find product links
                selectors = [
                    "a.woocommerce-LoopProduct-link.woocommerce-loop-product__link",
                    "li.product a.woocommerce-LoopProduct-link",
                    "li.product a",  # More generic fallback
                    ".product-inner a.product-link",  # Another possible selector
                ]

                page_items = []
                for selector in selectors:
                    page_items = soup.select(selector)
                    if page_items:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Found {len(page_items)} items with selector: {selector}"
                            )
                        break

                if not page_items and self.debug:
                    print(
                        f"{site_code.upper()}: No items found on page {page}. Site structure may have changed."
                    )

                all_items.extend(page_items)

            self.idc_length = len(all_items)
            if self.debug:
                print(f"{site_code.upper()} Total items found: {self.idc_length}")

            for index, item in enumerate(all_items):
                self.idc_progress = index + 1

                # Extract title from multiple possible sources
                title = None

                # Try to get title from h2 tag
                title_tag = item.find("h2", class_="woocommerce-loop-product__title")
                if title_tag and title_tag.text:
                    title = title_tag.text.strip()
                else:
                    # Try to get from img alt attribute
                    img_tag = item.find("img")
                    if img_tag and img_tag.get("alt"):
                        title = img_tag["alt"].strip()
                    # Try to get from title attribute
                    elif item.get("title"):
                        title = item["title"].strip()

                # Get the product URL
                intermediate_url = item.get("href")

                if not title or not intermediate_url:
                    if self.debug:
                        print(
                            f"{site_code.upper()} Skipping item {index}: Missing title or URL"
                        )
                    continue

                if self.debug:
                    print(
                        f"{site_code.upper()} Processing: {title} - {intermediate_url}"
                    )

                # If the URL already has udemy.com in it, use it directly
                if "udemy.com/course" in intermediate_url:
                    link = self.cleanup_link(intermediate_url)
                    if link:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Found direct Udemy link: {title} -> {link}"
                            )
                        self.append_to_list(
                            getattr(self, f"{site_code}_data"), title, link
                        )
                        processed_count += 1
                    continue

                # Multiple approaches to extract ID from URL
                link_num = None

                # Approach 1: Try different regex patterns to match ID in URL
                regex_patterns = [
                    r"(?:go|udemy)/(\d+)/?$",  # /go/12345/ or /udemy/12345/
                    r"/product/[^/]+/(\d+)/?$",  # /product/title-here/12345/
                    r"p=(\d+)",  # p=12345 in query string
                    r"id=(\d+)",  # id=12345 in query string
                    r"(?:course|coupon)[/=](\d+)",  # course/12345 or coupon=12345
                    r"/(\d+)/?$",  # Any number at the end of URL
                ]

                for pattern in regex_patterns:
                    match = re.search(pattern, intermediate_url)
                    if match:
                        link_num = match.group(1)
                        if self.debug:
                            print(
                                f"{site_code.upper()} Found ID {link_num} using pattern {pattern}"
                            )
                        break

                # Approach 2: If no ID found, try fetching the intermediate page
                if not link_num:
                    if self.debug:
                        print(
                            f"{site_code.upper()} No ID found in URL. Fetching intermediate page: {intermediate_url}"
                        )
                    try:
                        inter_content = self.fetch_page_content(
                            intermediate_url, headers=headers
                        )
                        if inter_content:
                            inter_soup = self.parse_html(inter_content)

                            # Look for direct Udemy links on the page
                            udemy_links = inter_soup.find_all(
                                "a", href=re.compile(r"udemy\.com/course")
                            )
                            if udemy_links:
                                raw_link = udemy_links[0]["href"]
                                link = self.cleanup_link(raw_link)
                                if link:
                                    if self.debug:
                                        print(
                                            f"{site_code.upper()} Found direct Udemy link on intermediate page: {link}"
                                        )
                                    self.append_to_list(
                                        getattr(self, f"{site_code}_data"), title, link
                                    )
                                    processed_count += 1
                                continue

                            # Look for redirect buttons
                            redirect_buttons = [
                                inter_soup.find(
                                    "a",
                                    class_=re.compile(r"button|btn|coupon|deal", re.I),
                                ),
                                inter_soup.find(
                                    "a",
                                    string=re.compile(r"Get Deal|Coupon|Enroll", re.I),
                                ),
                                inter_soup.select_one("div.product-button a"),
                            ]

                            for button in redirect_buttons:
                                if button and button.get("href"):
                                    redirect_url = button["href"]
                                    # Check if it's a udemy link
                                    if "udemy.com/course" in redirect_url:
                                        link = self.cleanup_link(redirect_url)
                                        if link:
                                            if self.debug:
                                                print(
                                                    f"{site_code.upper()} Found Udemy link from button: {link}"
                                                )
                                            self.append_to_list(
                                                getattr(self, f"{site_code}_data"),
                                                title,
                                                link,
                                            )
                                            processed_count += 1
                                        continue

                                    # Check if it contains a numeric ID
                                    for pattern in regex_patterns:
                                        match = re.search(pattern, redirect_url)
                                        if match:
                                            link_num = match.group(1)
                                            if self.debug:
                                                print(
                                                    f"{site_code.upper()} Found ID {link_num} from button href"
                                                )
                                            break

                                    if link_num:
                                        break
                    except Exception as e:
                        if self.debug:
                            print(
                                fr
                                + f"{site_code.upper()} Error fetching intermediate page: {e!s}"
                            )

                # If we still don't have an ID, skip this item
                if not link_num:
                    if self.debug:
                        print(
                            f"{site_code.upper()} Could not extract ID from {intermediate_url}"
                        )
                    continue

                # Construct possible redirect URLs with the ID we found
                possible_redirects = [
                    f"https://idownloadcoupon.com/udemy/{link_num}/",
                    f"https://idownloadcoupon.com/go/{link_num}/",
                    f"https://idownloadcoupon.com/product/udemy-{link_num}/",
                ]

                udemy_link = None
                for redirect_url in possible_redirects:
                    if self.debug:
                        print(f"{site_code.upper()} Trying redirect: {redirect_url}")
                    try:
                        # Try HEAD request first for efficiency
                        response = requests.head(
                            redirect_url,
                            headers=headers,
                            allow_redirects=True,
                            timeout=scrapper_timeout_period,
                        )

                        if "udemy.com/course" in response.url:
                            udemy_link = response.url
                            if self.debug:
                                print(
                                    f"{site_code.upper()} HEAD redirect successful: {udemy_link}"
                                )
                            break

                        # If HEAD doesn't lead to Udemy, try GET
                        response_get = requests.get(
                            redirect_url,
                            headers=headers,
                            allow_redirects=True,
                            timeout=scrapper_timeout_period,
                        )

                        if "udemy.com/course" in response_get.url:
                            udemy_link = response_get.url
                            if self.debug:
                                print(
                                    f"{site_code.upper()} GET redirect successful: {udemy_link}"
                                )
                            break

                        # If direct redirect didn't work, check for Udemy links in the response
                        if not udemy_link:
                            redirect_content = response_get.text
                            redirect_soup = self.parse_html(redirect_content)
                            udemy_links = redirect_soup.find_all(
                                "a", href=re.compile(r"udemy\.com/course")
                            )
                            if udemy_links:
                                udemy_link = udemy_links[0]["href"]
                                if self.debug:
                                    print(
                                        f"{site_code.upper()} Found Udemy link in redirect page: {udemy_link}"
                                    )
                                break

                    except requests.RequestException as e:
                        if self.debug:
                            print(
                                f"{site_code.upper()} Error with redirect {redirect_url}: {e!s}"
                            )
                        continue

                # Process the Udemy link if found
                if udemy_link:
                    link = self.cleanup_link(udemy_link)
                    if link:
                        if self.debug:
                            print(f"{site_code.upper()} Found: {title} -> {link}")
                        self.append_to_list(
                            getattr(self, f"{site_code}_data"), title, link
                        )
                        processed_count += 1
                    elif self.debug:
                        print(
                            f"{site_code.upper()} Skipped (invalid Udemy link): {title} -> {udemy_link}"
                        )
                else:
                    if self.debug:
                        print(
                            f"{site_code.upper()} Could not find Udemy link for {title}"
                        )

        except Exception:
            self.handle_exception(site_code)
        finally:
            setattr(self, f"{site_code}_done", True)
            if self.debug:
                print(
                    f"{site_code.upper()} Return Length: {len(getattr(self, f'{site_code}_data', []))}"
                )
                print(f"{site_code.upper()} Processed Count: {processed_count}")

    def en(self):
        """Scrapes courses from E-Next.in.

        Fetches course listings from paginated results, then visits each
        course's detail page on E-Next to extract the title and the
        final Udemy course link.
        """
        try:
            all_items_intermediate = []
            # Scrape the listing pages to get links to individual course pages on e-next
            for page in range(1, 10):  # Adjust page range if needed
                if self.debug:
                    print(f"EN Fetching page {page}...")
                content = self.fetch_page_content(
                    f"https://jobs.e-next.in/course/udemy/{page}"
                )
                if not content:
                    continue
                soup = self.parse_html(content)
                # Find links that likely lead to the e-next course details page - Verify selector
                page_items = soup.find_all(
                    "a", {"class": "btn btn-secondary btn-sm btn-block"}
                )
                if not page_items and self.debug:  # Try fallback
                    print(
                        f"EN: Primary selector failed on page {page}. Trying article links..."
                    )
                    articles = soup.find_all("article", class_="job-item")
                    for article in articles:
                        link = article.find("a", href=True)
                        if link:
                            page_items.append(link)

                all_items_intermediate.extend(page_items)

            self.en_length = len(all_items_intermediate)
            if self.debug:
                print(f"EN Intermediate Length: {self.en_length}")

            processed_count = 0
            for index, item in enumerate(all_items_intermediate):
                self.en_progress = index + 1
                intermediate_url = item.get("href")
                if not intermediate_url:
                    continue

                # Fetch the e-next course details page
                if self.debug:
                    print(f" EN Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content:
                    continue
                soup_intermediate = self.parse_html(content)

                # Find the title and the Udemy link on the details page - Verify selectors
                title_element = soup_intermediate.find("h3")  # Assuming title is in h3
                link_element = soup_intermediate.find(
                    "a", {"class": "btn btn-primary"}
                )  # Assuming Udemy link is in this button
                # Fallbacks
                if not title_element:
                    title_element = soup_intermediate.find("h1")
                if not link_element:
                    link_element = soup_intermediate.find(
                        "a", string=re.compile("Enroll|Link|Coupon", re.I), href=True
                    )
                if not link_element:
                    link_element = soup_intermediate.select_one(
                        "div.course-buttons a"
                    )  # Example selector

                if (
                    not title_element
                    or not link_element
                    or not link_element.get("href")
                ):
                    if self.debug:
                        print(
                            f"EN: Could not find title/link element on {intermediate_url}"
                        )
                    continue

                title = title_element.string.strip() if title_element.string else "N/A"
                raw_link = link_element["href"]
                link = self.cleanup_link(raw_link)  # Handles potential redirects

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
        """Scrapes courses from CourseJoiner.com.

        Navigates through paginated course listings, extracting links to
        individual course posts on CourseJoiner. It then fetches these
        post pages and follows a redirect link to find the final Udemy
        course URL.
        """
        try:
            all_items_intermediate = []
            # Fetch course listing pages
            for page in range(1, 4):  # Adjust page range
                if self.debug:
                    print(f"CJ Fetching page {page}...")
                content = self.fetch_page_content(
                    f"https://www.coursejoiner.com/category/free-udemy/page/{page}/"
                )
                if not content:
                    continue
                soup = self.parse_html(content)
                # Find links to individual course posts - Verify selector
                page_items = soup.find_all(
                    "h2", class_="card-title entry-title"
                )  # Assuming links are in h2/a
                if not page_items and self.debug:  # Fallback
                    print(
                        f"CJ: Primary selector failed page {page}. Trying article titles..."
                    )
                    page_items = soup.select("article h2.entry-title")

                all_items_intermediate.extend(page_items)

            self.cj_length = len(all_items_intermediate)
            if self.debug:
                print(f"CJ Intermediate Length: {self.cj_length}")

            for index, item in enumerate(all_items_intermediate):
                self.cj_progress = index + 1
                link_tag = item.find("a", href=True)  # Link is usually inside the h2
                if not link_tag or not link_tag.string or not link_tag.get("href"):
                    continue

                title = link_tag.string.strip()
                intermediate_url = link_tag["href"]

                # Fetch the CourseJoiner post page
                if self.debug:
                    print(f" CJ Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content:
                    continue
                soup_intermediate = self.parse_html(content)

                # Find the specific button that links to the deal - Verify Selector (VERY LIKELY TO CHANGE)
                link_element = soup_intermediate.find(
                    "a",
                    class_="wp-block-button__link has-black-color has-luminous-vivid-amber-to-luminous-vivid-orange-gradient-background has-text-color has-background wp-element-button",
                )
                # Fallback selectors if the main one fails
                if not link_element:
                    link_element = soup_intermediate.find(
                        "a",
                        string=re.compile(
                            r"Get Coupon|Enroll Now|Get Deal", re.IGNORECASE
                        ),
                        href=True,
                    )  # Find by text
                if not link_element:
                    # Look for links within common button container classes
                    button_container = soup_intermediate.find(
                        "div", class_=re.compile(r"wp-block-button")
                    )
                    if button_container:
                        link_element = button_container.find("a", href=True)
                if not link_element:  # Try finding based on URL patterns
                    link_element = soup_intermediate.find(
                        "a", href=re.compile(r"/go/|/visit/|/out/", re.I)
                    )

                if not link_element or not link_element.get("href"):
                    if self.debug:
                        print(f"CJ: Could not find link button on {intermediate_url}")
                    continue

                raw_link = link_element["href"]

                # CourseJoiner often uses multiple redirects (internal, then maybe affiliate)
                try:
                    # Use requests session to handle redirects automatically
                    session = requests.Session()
                    session.headers.update(
                        {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        }
                    )
                    # Set max redirects to avoid infinite loops
                    session.max_redirects = 7
                    if self.debug:
                        print(f" CJ Following redirects for: {raw_link}")
                    response = session.get(
                        raw_link, timeout=scrapper_timeout_period * 2
                    )  # Longer timeout for redirects
                    response.raise_for_status()
                    final_url = response.url  # URL after all redirects

                    link = self.cleanup_link(final_url)

                    if link:
                        if self.debug:
                            print(f"CJ Found: {title} -> {link}")
                        self.append_to_list(self.cj_data, title, link)
                    elif self.debug:
                        print(
                            f"CJ Skipped (non-Udemy after redirects?): {title} -> {final_url}"
                        )

                except requests.exceptions.TooManyRedirects:
                    if self.debug:
                        print(
                            fr
                            + f"CJ Error: Too many redirects for {title} from {raw_link}"
                        )
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
        """Scrapes courses from CursosDev.com.

        Fetches course listings from paginated results, then visits each
        course's detail page on CursosDev. It follows a redirect link
        from the detail page to obtain the final Udemy course URL.
        """
        try:
            all_items_intermediate = []
            # Fetch listing pages
            for page in range(1, 4):  # Adjust page range
                if self.debug:
                    print(f"CD Fetching page {page}...")
                content = self.fetch_page_content(
                    f"https://www.cursosdev.com/?page={page}"  # Check URL structure
                )
                if not content:
                    continue
                soup = self.parse_html(content)
                # Find course cards/links - Verify selector
                page_items = soup.find_all(
                    "a",
                    class_="c-card block bg-white shadow-md hover:shadow-xl rounded-lg overflow-hidden",  # Verify class
                )
                if not page_items and self.debug:  # Fallback
                    print(
                        f"CD: Primary selector failed page {page}. Trying article links..."
                    )
                    page_items = soup.select("div.card a")

                all_items_intermediate.extend(page_items)

            self.cd_length = len(all_items_intermediate)
            if self.debug:
                print(f"CD Intermediate Length: {self.cd_length}")

            for index, item in enumerate(all_items_intermediate):
                self.cd_progress = index + 1
                intermediate_url = item.get("href")

                if (
                    not intermediate_url or "cursosdev.com" not in intermediate_url
                ):  # Ensure it's a link to their site
                    # Check if intermediate_url is relative and prepend base if needed
                    if intermediate_url and intermediate_url.startswith("/"):
                        intermediate_url = (
                            f"https://www.cursosdev.com{intermediate_url}"
                        )
                    else:
                        continue

                # Fetch the CursosDev course details page
                if self.debug:
                    print(f" CD Fetching intermediate: {intermediate_url}")
                content = self.fetch_page_content(intermediate_url)
                if not content:
                    continue
                soup_intermediate = self.parse_html(content)

                # Find title and the link to Udemy (often requires following a redirect)
                title_element = soup_intermediate.find(
                    "h1", class_=re.compile(r"text-3xl|text-4xl")
                )  # Verify title tag/class
                link_element = soup_intermediate.find(
                    "a",
                    class_=re.compile(
                        r"bg-indigo-900|bg-purple-800|btn-primary"
                    ),  # Find button by class pattern
                    href=True,
                )
                # Fallback: Find by text
                if not link_element:
                    link_element = soup_intermediate.find(
                        "a",
                        string=re.compile(
                            r"Ir al curso|Acessar|Get Coupon", re.IGNORECASE
                        ),
                        href=True,
                    )

                if not title_element or not link_element:
                    if self.debug:
                        print(
                            f"CD: Could not find title/link element on {intermediate_url}"
                        )
                    continue

                title = title_element.string.strip() if title_element.string else "N/A"
                raw_link = link_element[
                    "href"
                ]  # This is likely an internal redirect URL

                try:
                    # Follow the redirect(s)
                    # Prepend base URL if raw_link is relative
                    if raw_link.startswith("/"):
                        raw_link = f"https://www.cursosdev.com{raw_link}"

                    if self.debug:
                        print(f" CD Following redirect: {raw_link}")
                    session = requests.Session()
                    session.max_redirects = 5
                    response = session.get(
                        raw_link, allow_redirects=True, timeout=scrapper_timeout_period
                    )
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

    def ufc(self):  # UdemyFreeCourses.org - Uses Playwright
        """Scrapes courses from UdemyFreeCourses.org.

        Uses Playwright to handle JavaScript rendering and navigate through
        paginated course listings across different categories (free, 100% off).
        It extracts links to intermediate course pages and then attempts to find
        the final Udemy course URL from those pages.
        """
        site_code = "ufc"
        try:
            # Ensure Playwright is available
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                if self.debug:
                    print(
                        f"{site_code.upper()}: Playwright not installed. Run 'pip install playwright && playwright install'. Skipping scraper."
                    )
                setattr(self, f"{site_code}_error", "Playwright not installed")
                setattr(self, f"{site_code}_length", -1)
                setattr(self, f"{site_code}_done", True)
                return

            if self.debug:
                print(
                    f"Starting {site_code.upper()} scraper (uses Playwright, may be slow)..."
                )

            # We'll store found courses here before deduplication
            all_found_courses = []
            deduplicated_courses = []

            # URLs to scrape, with the pattern type (either category style or direct list)
            # We'll try both free courses and 100% off coupon courses
            url_patterns = [
                {
                    "base": "https://udemyfreecourses.org/category/free-course/page/",
                    "pages": 3,
                },
                {
                    "base": "https://udemyfreecourses.org/category/100-off-coupon/page/",
                    "pages": 3,
                },
                {
                    "base": "https://udemyfreecourses.org/page/",
                    "pages": 2,
                },  # Also try the main blog listing
            ]

            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(
                        headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
                    )
                except Exception as browser_error:
                    if self.debug:
                        print(
                            f"{site_code.upper()}: Playwright browsers not installed. Run 'playwright install'. Error: {browser_error}"
                        )
                    setattr(
                        self,
                        f"{site_code}_error",
                        f"Playwright browsers not installed: {browser_error}",
                    )
                    setattr(self, f"{site_code}_length", -1)
                    setattr(self, f"{site_code}_done", True)
                    return

                # Create a persistent context that we'll reuse
                page_context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
                )

                for url_pattern in url_patterns:
                    base_url = url_pattern["base"]
                    max_pages = url_pattern["pages"]
                    pattern_items = []

                    for page_num in range(1, max_pages + 1):
                        page_url = f"{base_url}{page_num}/"
                        if self.debug:
                            print(f"Fetching {site_code.upper()}: {page_url}")

                        try:
                            page = page_context.new_page()

                            # --- Set up routing to block resources BEFORE navigation ---
                            def block_resources(route):
                                if route.request.resource_type in {
                                    "image",
                                    "stylesheet",
                                    "font",
                                }:
                                    route.abort()
                                else:
                                    route.continue_()

                            page.route("**/*", block_resources)
                            # -----------------------------------------------------------

                            # Increase timeout significantly for Playwright
                            page.goto(
                                page_url,
                                wait_until="domcontentloaded",
                                timeout=scrapper_timeout_period * 6 * 1000,
                            )  # 180 seconds
                            content = page.content()
                            page.close()  # Close page after use

                            if not content:
                                if self.debug:
                                    print(
                                        fr + f"Failed to fetch content for {page_url}"
                                    )
                                continue

                            soup = self.parse_html(content)

                            # Find course items - Try multiple selector approaches
                            page_items = []

                            # Method 1: Look for article tags
                            article_items = soup.find_all(
                                "article", class_=re.compile(r"post-\d+|tdb_module")
                            )
                            if article_items:
                                page_items.extend(article_items)

                            # Method 2: Look for div modules (common in WordPress themes)
                            div_modules = soup.select(
                                "div.td-module-container, div.td_module_wrap"
                            )
                            if div_modules:
                                page_items.extend(div_modules)

                            # Method 3: Look for any entry/item classes (generic fallback)
                            entry_items = soup.select(
                                'div[class*="item-inner"], div[class*="entry-"], article.item'
                            )
                            if entry_items:
                                page_items.extend(entry_items)

                            # Method 4: As a last resort, look for h2/h3 tags that might indicate posts
                            if not page_items:
                                heading_items = []
                                for heading in soup.find_all(
                                    ["h2", "h3"],
                                    class_=re.compile(r"entry-title|post-title"),
                                ):
                                    if heading.find("a", href=True):
                                        heading_items.append(
                                            heading.parent
                                        )  # Get the parent container of the heading
                                page_items.extend(heading_items)

                            if not page_items:
                                if self.debug:
                                    print(
                                        f" {site_code.upper()}: No items found with selectors on {page_url}"
                                    )
                                if page_num > 1:
                                    if self.debug:
                                        print(
                                            f"  No new items found on page {page_num}, stopping for {base_url}"
                                        )
                                    break  # If no items found on page > 1, assume we've reached the end

                            if self.debug:
                                print(
                                    f"  Added {len(page_items)} items from {page_url}"
                                )
                            pattern_items.extend(page_items)

                        except Exception as page_error:
                            if self.debug:
                                print(fr + f"Error processing {page_url}: {page_error}")
                            # Continue to next page despite error

                    # Process items found for this pattern
                    for item in pattern_items:
                        try:
                            # Extract title and link with multiple approaches
                            title_tag = None
                            link_tag = None

                            # Approach 1: Look for heading with link
                            for heading_tag in ["h2", "h3", "h4"]:
                                title_tag = item.find(
                                    heading_tag,
                                    class_=re.compile(r"entry-title|post-title"),
                                )
                                if title_tag and title_tag.find("a", href=True):
                                    link_tag = title_tag.find("a", href=True)
                                    break

                            # Approach 2: Look for title/link in other common structures
                            if not title_tag or not link_tag:
                                link_tag = item.find(
                                    "a",
                                    class_=re.compile(r"entry-title|post-link"),
                                    href=True,
                                )
                                if link_tag:
                                    title_tag = link_tag

                            # Approach 3: Just find any link and use its text
                            if not title_tag or not link_tag:
                                link_tag = item.find("a", href=True)
                                if link_tag:
                                    title_tag = link_tag

                            if title_tag and link_tag and link_tag.get("href"):
                                title = title_tag.get_text(strip=True)
                                intermediate_url = link_tag["href"]
                                if not intermediate_url.startswith(
                                    "http"
                                ):  # Handle relative URLs
                                    intermediate_url = (
                                        f"https://udemyfreecourses.org{intermediate_url}"
                                        if intermediate_url.startswith("/")
                                        else f"https://udemyfreecourses.org/{intermediate_url}"
                                    )

                                # Fetch intermediate page (using requests is usually faster here)
                                try:
                                    if self.debug:
                                        print(
                                            f"  {site_code.upper()} Fetching intermediate: {intermediate_url}"
                                        )
                                    intermediate_content = self.fetch_page_content(
                                        intermediate_url,
                                        timeout=scrapper_timeout_period * 2,
                                    )
                                    if not intermediate_content:
                                        continue
                                    intermediate_soup = self.parse_html(
                                        intermediate_content
                                    )

                                    # Try multiple approaches to find the Udemy link/coupon
                                    udemy_link = None

                                    # Approach 1: Look for buttons with specific classes
                                    final_link_tag = intermediate_soup.find(
                                        "a",
                                        class_=re.compile(
                                            r"fasc-button|btn-success|coupon-button|rh-deal-link"
                                        ),
                                        href=True,
                                    )

                                    # Approach 2: Look for links with specific text
                                    if not final_link_tag:
                                        final_link_tag = intermediate_soup.find(
                                            "a",
                                            string=re.compile(
                                                r"Enroll|Coupon|Get|Link|Take This Course",
                                                re.I,
                                            ),
                                            href=True,
                                        )

                                    # Approach 3: Look in common container divs
                                    if not final_link_tag:
                                        for container_class in [
                                            "rh-post-wrapper",
                                            "entry-content",
                                            "post-content",
                                            "deal-box",
                                        ]:
                                            container = intermediate_soup.find(
                                                "div", class_=container_class
                                            )
                                            if container:
                                                final_link_tag = container.find(
                                                    "a", href=True
                                                )
                                                if final_link_tag:
                                                    break

                                    # Approach 4: Look for direct Udemy links
                                    if not final_link_tag:
                                        direct_udemy_link = intermediate_soup.find(
                                            "a",
                                            href=re.compile(
                                                r"udemy\.com/course/[^/]+/\?couponCode="
                                            ),
                                        )
                                        if direct_udemy_link:
                                            final_link_tag = direct_udemy_link

                                    # Process the found link
                                    if final_link_tag and final_link_tag.get("href"):
                                        raw_link = final_link_tag["href"]
                                        # Sometimes the link needs to be cleaned or followed to get the actual Udemy URL
                                        udemy_link = self.cleanup_link(raw_link)

                                        # If cleanup_link didn't give us a valid Udemy link but the raw link seems
                                        # to be a redirect, try following it
                                        if not udemy_link and (
                                            "go.udemy" in raw_link
                                            or "/go/" in raw_link
                                            or "/redirect/" in raw_link
                                        ):
                                            try:
                                                response = requests.get(
                                                    raw_link,
                                                    allow_redirects=True,
                                                    timeout=scrapper_timeout_period * 2,
                                                )
                                                if response.ok:
                                                    udemy_link = self.cleanup_link(
                                                        response.url
                                                    )
                                            except Exception as redirect_err:
                                                if self.debug:
                                                    print(
                                                        f"  {site_code.upper()} Error following redirect: {redirect_err}"
                                                    )

                                    # Add to our found courses if we have a valid link
                                    if udemy_link:
                                        all_found_courses.append((title, udemy_link))
                                        if self.debug:
                                            print(
                                                f"  {site_code.upper()} Found: {title} -> {udemy_link}"
                                            )
                                    else:
                                        if self.debug:
                                            print(
                                                f"  {site_code.upper()} No valid Udemy link found for: {title}"
                                            )

                                except Exception as intermediate_err:
                                    if self.debug:
                                        print(
                                            f"  {site_code.upper()} Error processing intermediate page: {intermediate_err}"
                                        )

                        except Exception as item_err:
                            if self.debug:
                                print(
                                    f"  {site_code.upper()} Error processing item: {item_err}"
                                )
                            # Continue to next item despite error

                # Close the browser
                browser.close()

            # Deduplicate courses (can have duplicate entries across pages/categories)
            seen_links = set()
            for title, link in all_found_courses:
                if link not in seen_links:
                    deduplicated_courses.append((title, link))
                    seen_links.add(link)

            # Set the final data and length
            self.ufc_data = deduplicated_courses
            self.ufc_length = len(deduplicated_courses)

            if self.debug:
                print(
                    f"{site_code.upper()} Final Length (deduplicated): {self.ufc_length}"
                )

        except Exception as e:
            self.handle_exception(site_code)
            if self.debug:
                print(fr + f"{site_code.upper()} Main exception: {e}")
        finally:
            self.ufc_done = True
            if self.debug:
                print(f"{site_code.upper()} Return Length: {len(self.ufc_data)}")


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
        self.logger = LoggerAdapter(
            get_logger("udemy"), {"user": None, "interface": interface}
        )

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
        """Load settings from file."""
        try:
            settings_file = (
                "duce-cli-settings.json" if self.interface == "cli" else "settings.json"
            )
            with open(settings_file, encoding="utf-8") as f:
                settings = json.load(f)
            self.settings = settings
            if self.debug:
                self.logger.debug("Settings loaded from file")
            return settings
        except FileNotFoundError:
            self.logger.warning(
                f"Settings file not found: {settings_file}, creating default settings"
            )
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
                "sites": dict.fromkeys(scraper_dict.keys(), True),
                "discounted_only": False,
                "course_update_threshold_months": 24,
            }
            self.settings = default_settings
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=2)
            return default_settings
        except Exception as e:
            self.logger.error(f"Error loading settings: {e!s}")
            self.settings = {}
            return {}

    def save_settings(self):
        settings_file = (
            "duce-cli-settings.json" if self.interface == "cli" else "settings.json"
        )
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)
        self.logger.debug("Settings saved to file")

    def make_cookies(self, client_id: str, access_token: str, csrf_token: str):
        self.cookie_dict = {
            "client_id": client_id,
            "access_token": access_token,
            "csrftoken": csrf_token,
        }

    def fetch_cookies(self):
        """Fetch browser cookies for login."""
        self.logger.info("Fetching cookies from browser")
        try:
            cookies = rookiepy.get_cookies("udemy.com")
            if not cookies:
                raise Exception("No cookies found for udemy.com")
            self.make_cookies(
                cookies["client_id"], cookies["access_token"], cookies["csrftoken"]
            )
            return cookies
        except Exception as e:
            self.logger.error(f"Error fetching cookies: {e!s}")
            raise

    def get_enrolled_courses(self):
        """Get list of already enrolled courses."""
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
        """Check if there's a newer version available."""
        self.logger.info("Checking for updates")
        try:
            r = requests.get(
                "https://techtanic.github.io/duce/update",
                headers={"User-Agent": "DUCE"},
                timeout=5,
            )
            latest_version = r.json()["version"]
            # Parse current and latest version as semver
            current_major, current_minor = map(int, VERSION.split(".")[0:2])
            latest_major, latest_minor = map(int, latest_version.split(".")[0:2])

            if latest_major > current_major or (
                latest_major == current_major and latest_minor > current_minor
            ):
                login_title = f"Update v{latest_version}"
                main_title = f"Update v{latest_version}"
                self.logger.warning(f"Update available: v{latest_version}")
            else:
                login_title = "Login"
                main_title = "DUCE"
                self.logger.info("You are using the latest version")

            return login_title, main_title
        except Exception as e:
            self.logger.warning(f"Error checking for updates: {e!s}")
            return "Login", "DUCE"

    def manual_login(self, email: str, password: str):
        """Manually login using email and password."""
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
        """Get session info to verify login status."""
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
        self.logger.extra["user"] = self.display_name

        r = s.get(
            "https://www.udemy.com/api-2.0/shopping-carts/me/",
            headers=headers,
            cookies=self.cookie_dict,
        )
        r = r.json()
        self.currency: str = r["user"]["credit"]["currency_code"]
        self.logger.info(
            f"Login verified for {self.display_name}, currency: {self.currency}"
        )

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
        """Check course price with a given coupon code.

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
            r.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = r.json()
            price_info = data.get("price_text", {}).get("data", {})
            amount_str = price_info.get("list_price", {}).get("price_string")
            if not amount_str:  # Fallback if list_price is not directly available
                amount_str = price_info.get(
                    "amount"
                )  # Check if 'amount' is directly available

            if amount_str:
                # Extract numeric value, handling currency symbols etc.
                import re

                match = re.search(r"[0-9]+([,.][0-9]+)?", amount_str)
                if match:
                    amount = float(
                        match.group(0).replace(",", ".")
                    )  # Handle both , and . as decimal separators
                    # Check if the price indicates it's free
                    is_free = (
                        price_info.get("purchase_price", {}).get("amount", 1) == 0
                        or amount == 0
                    )
                    # Coupon is considered valid if the course is free OR if a coupon code was provided and used
                    # (assuming the API returns price info means coupon is somewhat valid)
                    coupon_valid = is_free or bool(coupon_code)
                    return amount, coupon_valid
                else:
                    self.print(
                        f"Could not extract numeric price from '{amount_str}' for course {course_id}",
                        color="yellow",
                    )
                    return -1.0, False  # Indicate price extraction failure
            else:
                self.print(
                    f"Could not find price string in API response for course {course_id}",
                    color="yellow",
                )
                return -1.0, False  # Indicate price info not found

        except requests.exceptions.HTTPError as http_err:
            # Specifically handle HTTP errors (like 404 Not Found, 403 Forbidden)
            self.print(
                f"HTTP error checking course {course_id} ({coupon_code}): {http_err}",
                color="red",
            )
            # Check if it's a 404 error, potentially indicating the course or coupon is invalid/expired
            if http_err.response.status_code == 404:
                self.print(
                    f"Course {course_id} with coupon {coupon_code} likely expired or invalid (404).",
                    color="yellow",
                )
                return -1.0, False  # Treat as invalid coupon/course
            # Treat other HTTP errors as general check failures
            return -1.0, False
        except requests.exceptions.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            self.print(
                f"Failed to decode JSON response for course {course_id} ({coupon_code}). Skipping check.",
                color="yellow",
            )
            # You might want to log r.text here for debugging if the issue persists
            # self.print(f"Raw Response: {r.text}", color="grey")
            return -1.0, False  # Treat as invalid or unable to check

    def start_enrolling(self):
        self.remove_duplicate_courses()
        self.initialize_counters()
        self.setup_txt_file()

        total_courses = sum(len(courses) for courses in self.scraped_data.values())
        previous_courses_count = 0
        for _site_index, (site, courses) in enumerate(self.scraped_data.items()):
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
            return  # Added return
        elif course["retry"]:
            self.print("Retrying...", color="red")
            time.sleep(1)
            self.handle_course_enrollment()
            return  # Added return

        course_id = course["course_id"]

        # --- Fetch and Log Course Details ---
        try:
            course_details = self.get_course_details(course_id)
            if course_details and not course_details.get("error"):
                self.logger.info(
                    f"Details for course {course_id} ({course_details.get('title', 'N/A')})"
                )
                # Log some key details
                self.logger.debug(
                    f"  Rating: {course_details.get('rating')}, Students: {course_details.get('num_students')}, Lang: {course_details.get('language')}"
                )
                self.logger.debug(
                    f"  Instructor(s): {', '.join([i.get('name', '') for i in course_details.get('instructors', [])])}"
                )
                self.logger.debug(
                    f"  Last Updated: {course_details.get('last_update_date')}"
                )
            elif course_details and course_details.get("error"):
                self.logger.warning(
                    f"Could not fetch full details for course {course_id}: {course_details.get('error')}"
                )
            else:
                self.logger.warning(
                    f"Could not fetch any details for course {course_id}"
                )
        except Exception as detail_err:
            self.logger.error(
                f"Error fetching details for course {course_id}: {detail_err}",
                exc_info=True,
            )
        # --- End Fetch and Log Course Details ---

        if course["is_excluded"]:
            # Exclude check was already done in get_course_id based on dma,
            # but we might want to re-evaluate based on fetched details here later.
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
                "This course would have cost you "
                + str(round(amount, 2))
                + " EUR. Enjoy!",
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

    def get_course_details(
        self, course_id: str, max_retries: int = 3, base_delay: int = 2
    ) -> dict[str, Any]:
        """Fetches detailed information for a given Udemy course ID.

        Tries to fetch data from the Udemy API first. If that fails or provides
        incomplete data, it falls back to scraping the course landing page.
        Includes retry logic for network requests.

        Args:
            course_id: The ID of the Udemy course.
            max_retries: Maximum number of retries for network requests.
            base_delay: Base delay in seconds for exponential backoff.

        Returns:
            A dictionary containing course details, or an error message if fetching fails.
            Keys can include: 'title', 'headline', 'rating', 'num_students',
            'instructors', 'language', 'last_update_date', 'description',
            'curriculum_sections', 'url', 'error'.
        """
        details: dict[str, Any] = {"course_id": course_id, "error": None}
        api_url = f"https://{self.domain}/api-2.0/courses/{course_id}/?fields[course]=title,headline,rating,num_subscribers,visible_instructors,locale,last_update_date,description,curriculum_context,url,is_paid,price_detail,primary_category,primary_subcategory"

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"Attempt {attempt + 1} to fetch course details for {course_id} from API: {api_url}"
                )
                response = self.client.get(api_url, timeout=20)  # Increased timeout
                response.raise_for_status()
                data = response.json()

                details["title"] = data.get("title")
                details["headline"] = data.get("headline")
                details["rating"] = data.get("rating")
                details["num_students"] = data.get("num_subscribers")
                details["url"] = (
                    f"https://{self.domain}{data.get('url')}"
                    if data.get("url")
                    else None
                )

                instructors_data = data.get("visible_instructors", [])
                details["instructors"] = [
                    {
                        "name": ins.get("display_name"),
                        "title": ins.get("job_title"),
                        "image": ins.get("image_100x100"),
                        "url": f"https://{self.domain}{ins.get('url')}"
                        if ins.get("url")
                        else None,
                    }
                    for ins in instructors_data
                ]

                locale_data = data.get("locale")
                details["language"] = (
                    locale_data.get("simple_english_title") if locale_data else None
                )
                details["last_update_date"] = data.get(
                    "last_update_date"
                )  # Format: YYYY-MM-DD

                # Description might be HTML, keep as is for now
                details["description"] = data.get("description")

                # Curriculum (high-level sections and lecture counts)
                curriculum = data.get("curriculum_context", {}).get("data", {})
                sections = curriculum.get("sections", [])
                details["curriculum_sections"] = []
                for sec in sections:
                    lectures = sec.get("items", [])
                    details["curriculum_sections"].append(
                        {
                            "title": sec.get("title"),
                            "lecture_count": sec.get("lecture_count"),
                            "content_length_text": sec.get("content_length_text"),
                            "lectures": [
                                {
                                    "title": lect.get("title"),
                                    "content_summary": lect.get("content_summary"),
                                }
                                for lect in lectures
                                if lect.get("_class") == "lecture"
                            ],
                        }
                    )

                details["is_paid"] = data.get("is_paid", True)
                price_detail = data.get("price_detail")
                if price_detail:
                    details["price"] = price_detail.get("amount")
                    details["currency"] = price_detail.get("currency")

                primary_category = data.get("primary_category")
                if primary_category:
                    details["primary_category"] = primary_category.get("title")
                primary_subcategory = data.get("primary_subcategory")
                if primary_subcategory:
                    details["primary_subcategory"] = primary_subcategory.get("title")

                self.logger.info(
                    f"Successfully fetched details for course {course_id} via API."
                )
                details["error"] = None  # Clear error if successful
                return details

            except requests.exceptions.HTTPError as http_err:
                self.logger.warning(
                    f"API HTTP error for course {course_id} (attempt {attempt + 1}): {http_err}"
                )
                if http_err.response.status_code == 404:
                    details["error"] = "Course not found via API (404)."
                    # Don't retry on 404, but allow fallback to scrape
                    break
                if http_err.response.status_code == 403:
                    details["error"] = "Access forbidden to course API (403)."
                    # Don't retry on 403, but allow fallback to scrape
                    break
                # For other HTTP errors, retry
            except (requests.RequestException, json.JSONDecodeError) as e:
                self.logger.warning(
                    f"API request/JSON error for course {course_id} (attempt {attempt + 1}): {e}"
                )

            if attempt < max_retries - 1:
                time.sleep(base_delay * (2**attempt))  # Exponential backoff
            else:
                self.logger.error(
                    f"API failed after {max_retries} attempts for course {course_id}."
                )
                if not details[
                    "error"
                ]:  # Set a generic error if a specific one (like 404) wasn't set
                    details["error"] = (
                        "Failed to fetch details from API after multiple retries."
                    )

        # Placeholder for scraping logic and final return
        self.logger.info(
            f"API part finished for {course_id}, proceeding to potential scrape. Current error: {details.get('error')}"
        )
        return details  # Temporary return, will be replaced

        # Fallback to scraping if API failed or if crucial info is missing (e.g. description, curriculum)
        # We can define "crucial info missing" more strictly if needed
        should_scrape = bool(details["error"]) or not all(
            details.get(k) for k in ["title", "description"]
        )

        if should_scrape:
            self.logger.info(
                f"Falling back to scraping for course {course_id}. Previous API error: {details.get('error', 'N/A')}"
            )
            # Construct a plausible course URL. The slug doesn't strictly matter for course ID based fetching.
            scrape_url = f"https://{self.domain}/course/placeholder-slug/{course_id}/"

            for attempt in range(max_retries):
                try:
                    self.logger.debug(
                        f"Scrape attempt {attempt + 1} for course {course_id} from {scrape_url}"
                    )
                    # Use the existing client which should handle cloudscraper session
                    response = self.client.get(
                        scrape_url, timeout=30
                    )  # Longer timeout for page load
                    response.raise_for_status()
                    soup = bs(response.content, "html5lib")

                    # Extract data-module-args for structured data if available
                    body_tag = soup.find("body")
                    dma_str = body_tag.get("data-module-args") if body_tag else None

                    if dma_str:
                        try:
                            dma = json.loads(dma_str)
                            # Look in multiple places for course data within DMA
                            course_data_options = [
                                dma.get("course"),
                                dma.get("serverSideProps", {}).get("course"),
                                dma.get("componentProps", {}).get(
                                    "course"
                                ),  # Another common location
                                dma.get("prerenderedData", {}).get(
                                    "course"
                                ),  # Yet another location
                            ]
                            course_data = next(
                                (cd for cd in course_data_options if cd is not None), {}
                            )

                            if not details.get("title") and course_data.get("title"):
                                details["title"] = course_data["title"]
                            if not details.get("headline") and course_data.get(
                                "headline"
                            ):
                                details["headline"] = course_data["headline"]
                            if not details.get("rating") and course_data.get("rating"):
                                details["rating"] = course_data["rating"]

                            num_students_options = [
                                course_data.get("num_students"),
                                course_data.get("num_subscribers"),
                            ]
                            current_num_students = next(
                                (ns for ns in num_students_options if ns is not None),
                                None,
                            )
                            if (
                                not details.get("num_students")
                                and current_num_students is not None
                            ):
                                details["num_students"] = current_num_students

                            if not details.get("url"):
                                details["url"] = (
                                    f"https://{self.domain}{course_data.get('url')}"
                                    if course_data.get("url")
                                    else scrape_url
                                )

                            if not details.get("instructors"):
                                instructors_dma_options = [
                                    course_data.get("visible_instructors"),
                                    course_data.get("instructors", {}).get(
                                        "instructors_info"
                                    ),
                                ]
                                instructors_dma = next(
                                    (
                                        ido
                                        for ido in instructors_dma_options
                                        if ido is not None
                                    ),
                                    [],
                                )
                                details["instructors"] = [
                                    {
                                        "name": ins.get("display_name"),
                                        "title": ins.get("job_title"),
                                        "image": ins.get("image_100x100"),
                                        "url": f"https://{self.domain}{ins.get('url')}"
                                        if ins.get("url")
                                        else f"https://{self.domain}{ins.get('absolute_url')}"
                                        if ins.get("absolute_url")
                                        else None,
                                    }
                                    for ins in instructors_dma
                                ]

                            if not details.get("language") and course_data.get(
                                "locale", {}
                            ).get("simple_english_title"):
                                details["language"] = course_data["locale"][
                                    "simple_english_title"
                                ]
                            if not details.get("last_update_date") and course_data.get(
                                "last_update_date"
                            ):
                                details["last_update_date"] = course_data[
                                    "last_update_date"
                                ]

                            description_options = [
                                course_data.get("description"),
                                course_data.get("details_html"),
                            ]
                            current_description = next(
                                (
                                    desc
                                    for desc in description_options
                                    if desc is not None
                                ),
                                None,
                            )
                            if not details.get("description") and current_description:
                                details["description"] = current_description

                            if not details.get("curriculum_sections"):
                                curriculum_dma_options = [
                                    course_data.get(
                                        "curriculum_lectures"
                                    ),  # This might be flat list
                                    course_data.get(
                                        "curriculum_sections"
                                    ),  # This is usually structured
                                    dma.get("curriculum_context", {})
                                    .get("data", {})
                                    .get("sections"),  # API-like path in DMA
                                ]
                                sections_dma_source = next(
                                    (
                                        cdo
                                        for cdo in curriculum_dma_options
                                        if cdo is not None
                                    ),
                                    [],
                                )

                                temp_curriculum = []
                                # Heuristic: if sections_dma_source looks like a list of lectures (flat), group them under a generic section
                                if sections_dma_source and all(
                                    "object_type" in item
                                    and item["object_type"] == "lecture"
                                    for item in sections_dma_source
                                    if isinstance(item, dict)
                                ):
                                    temp_curriculum.append(
                                        {
                                            "title": "Course Content",
                                            "lecture_count": len(sections_dma_source),
                                            "content_length_text": course_data.get(
                                                "content_info"
                                            ),  # Or some aggregate
                                            "lectures": [
                                                {
                                                    "title": lect.get("title"),
                                                    "content_summary": lect.get(
                                                        "content_summary"
                                                    ),
                                                }
                                                for lect in sections_dma_source
                                            ],
                                        }
                                    )
                                else:  # Assume it's a list of sections
                                    for sec_dma in sections_dma_source:
                                        if not isinstance(sec_dma, dict):
                                            continue  # Skip if not a dict
                                        lectures_dma = sec_dma.get("items", [])
                                        temp_curriculum.append(
                                            {
                                                "title": sec_dma.get("title"),
                                                "lecture_count": sec_dma.get(
                                                    "lecture_count"
                                                ),
                                                "content_length_text": sec_dma.get(
                                                    "content_length_text"
                                                ),
                                                "lectures": [
                                                    {
                                                        "title": lect.get("title"),
                                                        "content_summary": lect.get(
                                                            "content_summary"
                                                        ),
                                                    }
                                                    for lect in lectures_dma
                                                    if isinstance(lect, dict)
                                                    and (
                                                        lect.get("object_type")
                                                        == "lecture"
                                                        or lect.get("_class")
                                                        == "lecture"
                                                    )
                                                ],
                                            }
                                        )
                                if temp_curriculum:
                                    details["curriculum_sections"] = temp_curriculum

                            self.logger.info(
                                f"Successfully extracted details for course {course_id} via DMA scrape."
                            )
                            details["error"] = None
                            return details
                        except json.JSONDecodeError:
                            self.logger.warning(
                                f"Failed to parse data-module-args for course {course_id}."
                            )
                        except Exception as dma_exc:
                            self.logger.warning(
                                f"Error processing DMA for course {course_id}: {dma_exc}",
                                exc_info=self.debug,
                            )

                    # If DMA fails or is not present, try more direct scraping (less reliable)
                    self.logger.info(
                        f"DMA not available or failed for {course_id}. Attempting direct scrape selectors."
                    )

                    if not details.get("title"):
                        title_tag = soup.select_one(
                            'h1[data-purpose="lead-title"], .clp-lead__title, .course-header__title h1'
                        )
                        if title_tag:
                            details["title"] = title_tag.get_text(strip=True)

                    if not details.get("headline"):
                        headline_tag = soup.select_one(
                            'div[data-purpose="lead-headline"], .clp-lead__headline'
                        )
                        if headline_tag:
                            details["headline"] = headline_tag.get_text(strip=True)

                    if not details.get("rating"):
                        rating_tag = soup.select_one(
                            'span[data-purpose="rating-number"], span.tooltip-container span.sr-only'
                        )
                        if rating_tag:
                            rating_text = rating_tag.get_text(strip=True)
                            match = re.search(r"([0-9\\\\.]+)", rating_text)
                            if match:
                                details["rating"] = float(match.group(1))

                    if not details.get("num_students"):
                        students_tag = soup.select_one(
                            'div[data-purpose="enrollment"], .course-header__details-text:-soup-contains("students"), .clp-lead__element-item:-soup-contains("students") span'
                        )
                        if students_tag:
                            students_text = students_tag.get_text(strip=True).replace(
                                ",", ""
                            )
                            match = re.search(r"(\\\\d+)", students_text)
                            if match:
                                details["num_students"] = int(match.group(1))

                    if not details.get("description"):
                        desc_tag = soup.select_one(
                            'div[data-purpose="description"], div.ud-component--course-landing-page-udlite--description, .course-description'
                        )
                        if desc_tag:
                            details["description"] = str(desc_tag)

                    if not details.get("instructors"):
                        instructor_elements = soup.select(
                            'div[data-purpose="instructor-name-top"] a, .instructor--instructor__title--32R_P a'
                        )
                        temp_instructors = []
                        for el in instructor_elements:
                            name = el.get_text(strip=True)
                            url_path = el.get("href")
                            if name and url_path:
                                temp_instructors.append(
                                    {
                                        "name": name,
                                        "url": f"https://{self.domain}{url_path}"
                                        if url_path.startswith("/")
                                        else url_path,
                                        "title": None,
                                        "image": None,
                                    }
                                )
                        if temp_instructors:
                            details["instructors"] = temp_instructors

                    if not details.get("last_update_date"):
                        last_update_tag = soup.select_one(
                            'div[data-purpose="last-update-date"] span, .course-header__details-text:-soup-contains("Last updated")'
                        )
                        if last_update_tag:
                            date_text = (
                                last_update_tag.get_text(strip=True)
                                .replace("Last updated", "")
                                .strip()
                            )
                            try:
                                parsed_date = None
                                if re.match(r"\\\\d{1,2}/\\\\d{4}", date_text):
                                    dt_obj = datetime.strptime(date_text, "%m/%Y")
                                    parsed_date = dt_obj.strftime("%Y-%m-01")
                                elif re.match(r"[A-Za-z]+ \\\\d{4}", date_text):
                                    dt_obj = datetime.strptime(date_text, "%B %Y")
                                    parsed_date = dt_obj.strftime("%Y-%m-01")
                                if parsed_date:
                                    details["last_update_date"] = parsed_date
                            except ValueError:
                                self.logger.warning(
                                    f"Could not parse last update date string: {date_text} for course {course_id}"
                                )

                    if not details.get("curriculum_sections"):
                        curriculum_sections_scrape = []
                        section_elements = soup.select(
                            'div[data-purpose^="course-curriculum-section-"], .curriculum--section--1J_z1'
                        )
                        for sec_el in section_elements:
                            title_el = sec_el.select_one(
                                'div[data-purpose="section-title"] span, .section--section-title--1v4gJ'
                            )
                            meta_el = sec_el.select_one(
                                'div[data-purpose="section-meta"] span, .section--section-meta--2Q0N0 span'
                            )
                            lectures_el = sec_el.select(
                                'div[data-purpose="lecture-title"], .lecture--lecture-title--3VZz-'
                            )

                            lecture_count = len(lectures_el)
                            content_length_text = None
                            if meta_el:  # Try to get lectures count and time from meta
                                meta_text = meta_el.get_text(strip=True)
                                count_match = re.search(
                                    r"(\d+)\s*lectures", meta_text, re.IGNORECASE
                                )
                                if count_match:
                                    lecture_count = int(count_match.group(1))
                                time_match = re.search(
                                    r"([\d\w\s]+total length)", meta_text, re.IGNORECASE
                                )  # e.g. "12 lectures • 1h 30m total length"
                                if time_match:
                                    content_length_text = (
                                        time_match.group(1)
                                        .replace(" total length", "")
                                        .strip()
                                    )

                            if title_el:
                                curriculum_sections_scrape.append(
                                    {
                                        "title": title_el.get_text(strip=True),
                                        "lecture_count": lecture_count,
                                        "content_length_text": content_length_text,
                                        "lectures": [
                                            {
                                                "title": lec.get_text(strip=True),
                                                "content_summary": None,
                                            }
                                            for lec in lectures_el
                                        ],
                                    }
                                )
                        if curriculum_sections_scrape:
                            details["curriculum_sections"] = curriculum_sections_scrape

                    self.logger.info(
                        f"Successfully scraped details for course {course_id} from HTML."
                    )
                    details["error"] = None
                    return details

                except requests.exceptions.HTTPError as http_err:
                    self.logger.warning(
                        f"Scrape HTTP error for course {course_id} (attempt {attempt + 1}): {http_err}"
                    )
                    if http_err.response.status_code == 404:
                        details["error"] = "Course landing page not found (404)."
                        break
                    if http_err.response.status_code == 403:
                        details["error"] = "Access forbidden to course page (403)."
                        break
                except requests.RequestException as e:
                    self.logger.warning(
                        f"Scrape request error for course {course_id} (attempt {attempt + 1}): {e}"
                    )
                except Exception as e_scrape:
                    self.logger.error(
                        f"General error during scraping course {course_id} (attempt {attempt + 1}): {e_scrape}",
                        exc_info=self.debug,
                    )

                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2**attempt))
                else:
                    self.logger.error(
                        f"Scraping failed after {max_retries} attempts for course {course_id}."
                    )
                    if not details["error"]:
                        details["error"] = (
                            "Failed to fetch details by scraping after multiple retries."
                        )

        # Final check and return
        if not details.get("title") and not details.get("error"):
            details["error"] = "Failed to retrieve any course details despite attempts."
        elif details.get("title") and details.get("error"):
            self.logger.warning(
                f"Returning partial details for {course_id} despite error: {details['error']}"
            )
            # Keep the error message to indicate partial data, but we have a title.
        elif not details.get("title") and details.get("error"):
            self.logger.error(
                f"Failed to get title for {course_id}. Error: {details['error']}"
            )

        return details

    def is_course_excluded(self, dma: dict[str, Any]) -> bool:
        """Checks if a course should be excluded based on settings and course data.

        This method evaluates various attributes of a course, extracted from
        the 'data-module-args' (dma) of a Udemy course page, against the user's
        filter settings (last update, instructor, keywords, category, language, rating).

        Args:
            dma: A dictionary containing course data, typically parsed from
                 the 'data-module-args' attribute of a Udemy course page.

        Returns:
            True if the course should be excluded, False otherwise.
        """
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
