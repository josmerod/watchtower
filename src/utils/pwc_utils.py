"""Utilities for interacting with the PapersWithCode API.

This module provides functions to fetch paper details, including associated
repositories, datasets, tasks, and methods, from PapersWithCode (PwC)
using either an ArXiv ID or paper title. It handles API request retries
and polite request delays.
"""
import asyncio  # Added for sleep
import time
from typing import Any

try:
    from paperswithcode import PapersWithCodeClient
    from paperswithcode.models import Paper
    HAS_PWC = True
except ImportError:
    HAS_PWC = False
    PapersWithCodeClient = None
    Paper = None
# Import exceptions if the client library defines specific ones for retries
# from paperswithcode.exceptions import RateLimitError, ServerError # Example

from utils.logging import get_logger

logger = get_logger(__name__)

# Rate limit settings for PwC API
REQUEST_DELAY_SECONDS = 1 # Be polite between different API calls
RETRY_DELAY_SECONDS = 5   # Delay before retrying a failed call
MAX_RETRIES = 3

def _extract_arxiv_id_from_url(arxiv_url: str) -> str | None:
    """Extracts the ArXiv ID from an ArXiv URL (e.g., http://arxiv.org/abs/1234.5678v1 -> 1234.5678).

    Args:
        arxiv_url (str): The ArXiv URL.

    Returns:
        Optional[str]: The extracted ArXiv ID (without version) or None.
    """
    if not arxiv_url or 'arxiv.org/abs/' not in arxiv_url:
        return None
    try:
        # Get the part after /abs/
        id_with_version = arxiv_url.split('/abs/')[1]
        # Remove version if present (e.g., v1, v2)
        if 'v' in id_with_version:
            return id_with_version.split('v')[0]
        return id_with_version
    except IndexError:
        logger.warning(f"Could not parse ArXiv ID from URL: {arxiv_url}")
        return None

async def get_pwc_details_for_paper(
    arxiv_id_url: str | None = None,
    title: str | None = None,
    pwc_client: PapersWithCodeClient | None = None
) -> dict[str, Any] | None:
    """Fetches paper details from PapersWithCode using ArXiv ID or title with retries.

    Args:
        arxiv_id_url (Optional[str]): The ArXiv ID (e.g., '1706.03762') or full ArXiv URL.
        title (Optional[str]): The title of the paper to search if ArXiv ID is not available.
        pwc_client (Optional[PapersWithCodeClient]): An existing PapersWithCodeClient instance.
                                                    If None, a new one will be created.

    Returns:
        Optional[Dict[str, Any]]: A dictionary with PapersWithCode details or None if not found or error.
    """
    if not HAS_PWC:
        logger.warning("PapersWithCode client not available. Install with: pip install paperswithcode-client")
        return None

    client = pwc_client if pwc_client else PapersWithCodeClient()

    pwc_paper_obj: Paper | None = None
    pwc_id: str | None = None
    # TODO: Add unit tests for input parsing (_extract_arxiv_id_from_url)
    cleaned_arxiv_id = None
    if arxiv_id_url:
        cleaned_arxiv_id = _extract_arxiv_id_from_url(arxiv_id_url) if 'arxiv.org' in arxiv_id_url else arxiv_id_url

    # --- Find PwC Paper ID (with retries) ---
    for attempt in range(MAX_RETRIES):
        try:
            if cleaned_arxiv_id:
                logger.debug(f"Searching PwC for ArXiv ID: {cleaned_arxiv_id} (Attempt {attempt + 1})")
                papers_list = client.paper_list(arxiv_id=cleaned_arxiv_id, items_per_page=1)
                if papers_list.results:
                    pwc_paper_obj = papers_list.results[0]
                    pwc_id = pwc_paper_obj.id
                    logger.info(f"Found PwC paper {pwc_id} for ArXiv ID {cleaned_arxiv_id}")
                    break # Found paper, exit retry loop
                else:
                    # Not found is not necessarily an error to retry, but log it.
                    logger.info(f"No PwC paper found for ArXiv ID {cleaned_arxiv_id} on attempt {attempt + 1}")
                    # We might still try searching by title below if ID search fails

            # If no paper found by ID, or no ID provided, try title (only if title available)
            if not pwc_paper_obj and title:
                logger.debug(f"Searching PwC for title: {title} (Attempt {attempt + 1})")
                await asyncio.sleep(REQUEST_DELAY_SECONDS) # Add delay if trying title after ID failed
                papers_list_title = client.paper_list(q=title, items_per_page=1)
                if papers_list_title.results:
                    pwc_paper_obj = papers_list_title.results[0] # Take the first match
                    pwc_id = pwc_paper_obj.id
                    logger.info(f"Found PwC paper {pwc_id} for title '{title}'")
                    break # Found paper, exit retry loop
                else:
                    logger.info(f"No PwC paper found for title '{title}' on attempt {attempt + 1}")

            # If we found the paper by ID or title, break the loop
            if pwc_paper_obj:
                 break
            # If not found by either and it was the last attempt, log and exit loop
            elif attempt == MAX_RETRIES - 1:
                 logger.warning(f"Could not find PwC paper for arXiv '{cleaned_arxiv_id}' or title '{title}' after {MAX_RETRIES} attempts.")
                 return None

        except Exception as e: # Catch generic exceptions which might indicate API issues
            # Consider catching more specific client exceptions if available e.g., RateLimitError, ServerError
            logger.warning(f"Error finding PwC paper (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying after {RETRY_DELAY_SECONDS} seconds...")
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            else:
                logger.error(f"Failed to find PwC paper after {MAX_RETRIES} attempts due to error: {e}")
                return None # Failed after retries

    # If paper wasn't found even without errors (e.g., search returned empty)
    if not pwc_paper_obj or not pwc_id:
        logger.info(f"PwC paper not found for arXiv '{cleaned_arxiv_id}' or title '{title}'.")
        return None

    # --- Fetch Details for the found Paper ID (with retries for each part) ---
    # TODO: Add unit tests for PwC data extraction logic below
    details: dict[str, Any] = {
        "pwc_id": pwc_id,
        "pwc_url": pwc_paper_obj.url_abs,
        "pwc_title": pwc_paper_obj.title,
        "pwc_proceeding": pwc_paper_obj.proceeding,
        "pwc_repositories": [],
        "pwc_datasets": [],
        "pwc_tasks_and_metrics": [],
        "pwc_methods": [],
        "error": None
    }

    async def fetch_with_retry(api_call, *args, **kwargs):
        """Helper to wrap API calls with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                result = api_call(*args, **kwargs)
                return result
            except Exception as e:
                 logger.warning(f"Error in API call {api_call.__name__} (Attempt {attempt + 1}): {e}")
                 if attempt < MAX_RETRIES - 1:
                     logger.info(f"Retrying after {RETRY_DELAY_SECONDS} seconds...")
                     await asyncio.sleep(RETRY_DELAY_SECONDS)
                 else:
                     logger.error(f"Failed API call {api_call.__name__} after {MAX_RETRIES} attempts: {e}")
                     return None # Indicate failure
        return None # Should not be reached if MAX_RETRIES > 0

    try:
        # Get repositories
        await asyncio.sleep(REQUEST_DELAY_SECONDS) # Polite delay
        repositories_list = await fetch_with_retry(client.paper_repository_list, paper_id=pwc_id)
        if repositories_list and repositories_list.results:
            details["pwc_repositories"] = [
                {
                    "url": repo.url,
                    "name": repo.name,
                    "owner": repo.owner,
                    "stars": repo.stars,
                    "framework": repo.framework,
                    "is_official": repo.is_official
                }
                for repo in repositories_list.results
            ]
        elif not repositories_list:
             details["error"] = details.get("error", "") + "Failed to fetch repositories; "

        # Get datasets
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        datasets_list = await fetch_with_retry(client.paper_dataset_list, paper_id=pwc_id)
        if datasets_list and datasets_list.results:
            details["pwc_datasets"] = [
                {
                    "id": dataset.id,
                    "name": dataset.name,
                    "url": dataset.url,
                    "is_featured": dataset.is_featured
                }
                for dataset in datasets_list.results
            ]
        elif not datasets_list:
             details["error"] = details.get("error", "") + "Failed to fetch datasets; "

        # Get methods used in the paper
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        methods_list = await fetch_with_retry(client.paper_method_list, paper_id=pwc_id)
        if methods_list and methods_list.results:
            details["pwc_methods"] = [method.name for method in methods_list.results]
        elif not methods_list:
             details["error"] = details.get("error", "") + "Failed to fetch methods; "

        # Get tasks
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
        tasks_list = await fetch_with_retry(client.paper_task_list, paper_id=pwc_id)
        if tasks_list and tasks_list.results:
            details["pwc_tasks_and_metrics"] = [
                {"task_id": task_obj.id, "task_name": task_obj.name, "task_description": task_obj.description, "leaderboards": []}
                for task_obj in tasks_list.results
            ]
        elif not tasks_list:
              details["error"] = details.get("error", "") + "Failed to fetch tasks; "

        # Clean up error message if it was just placeholder text
        if details["error"] and details["error"].strip().endswith(";"):
            details["error"] = details["error"].strip()[:-1].strip()
        if not details["error"]: details["error"] = None

        return details

    except Exception as e:
        logger.error(f"Unexpected error fetching PapersWithCode details for PwC ID {pwc_id}: {e}", exc_info=True)
        details["error"] = f"General fetch error: {e}"
        return details

if __name__ == '__main__':
    logger.info("Starting PapersWithCode Utils example")

    # Example: Attention Is All You Need
    # Direct ArXiv ID
    # arxiv_id_to_test = "1706.03762" # Transformer paper
    # pwc_data = get_pwc_details_for_paper(arxiv_id_url=arxiv_id_to_test)

    # ArXiv URL
    arxiv_url_to_test = "http://arxiv.org/abs/1706.03762v5"
    pwc_data_from_url = get_pwc_details_for_paper(arxiv_id_url=arxiv_url_to_test)

    if pwc_data_from_url:
        logger.info(f"PwC Details for {arxiv_url_to_test} (from URL):")
        for key, value in pwc_data_from_url.items():
            if isinstance(value, list):
                logger.info(f"  {key}: ({len(value)} items)")
                for item_idx, item in enumerate(value[:2]): # Log first 2 items for brevity
                    logger.info(f"    Item {item_idx+1}: {item}")
            else:
                logger.info(f"  {key}: {value}")
    else:
        logger.warning(f"Could not fetch PwC details for {arxiv_url_to_test} (from URL)")

    # Example: Search by title (might be less reliable)
    time.sleep(REQUEST_DELAY_SECONDS) # Wait before next API call if any
    # title_to_test = "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
    # pwc_data_title = get_pwc_details_for_paper(title=title_to_test)
    # if pwc_data_title:
    #     logger.info(f"PwC Details for title '{title_to_test}':")
    #     logger.info(json.dumps(pwc_data_title, indent=2))
    # else:
    #     logger.warning(f"Could not fetch PwC details for title '{title_to_test}'")

    logger.info("PapersWithCode Utils example finished")
