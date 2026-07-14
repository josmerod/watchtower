import csv
import json
import os
import time
from datetime import datetime
from typing import Any  # Added typing imports

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.settings import get_settings
from src.models.news import NewsArticleModel
from src.utils.file_system import ensure_directories, get_project_root

# Add project root to Python path
from src.utils.logging import get_logger

logger = get_logger("NewsApiETL")


def create_session():
    """Creates a requests session with retry logic."""
    logger.debug("Creating requests session with retry logic.")
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    logger.info("Requests session created successfully.")
    return session


def get_newsapi_articles(
    session: requests.Session,
    api_key: str,
    query: str = "technology",
    language: str = "en",
    page_size: int = 100,
    max_articles_to_fetch: int = 200,
) -> list[dict[str, Any]]:  # Return type updated for raw articles
    """Fetches articles from NewsAPI."""
    logger.info(f"Fetching articles from NewsAPI for query: '{query}', language: '{language}'")
    base_url = "https://newsapi.org/v2/everything"
    headers = {"X-Api-Key": api_key}

    all_articles = []
    page = 1
    fetched_count = 0

    while fetched_count < max_articles_to_fetch:
        params = {
            "q": query,
            "language": language,
            "pageSize": min(page_size, max_articles_to_fetch - fetched_count),  # Adjust page size if near max
            "page": page,
            "sortBy": "publishedAt",
        }

        try:
            logger.debug(f"Requesting page {page} with params: {params}")
            response = session.get(base_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            data = response.json()

            articles_on_page = data.get("articles", [])
            total_results = data.get("totalResults", 0)

            if not articles_on_page:
                logger.info("No more articles found for the current query.")
                break

            all_articles.extend(articles_on_page)
            fetched_count += len(articles_on_page)
            logger.info(f"Fetched {len(articles_on_page)} articles from page {page}. Total fetched so far: {fetched_count}/{max_articles_to_fetch} (Total available for query: {total_results})")

            if fetched_count >= total_results or fetched_count >= max_articles_to_fetch:
                logger.info("Reached max articles to fetch or no more results available.")
                break

            page += 1
            time.sleep(1)  # Respect API rate limits if any (NewsAPI developer plan has no strict per-second limit but good practice)

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e} - Response: {e.response.text}")
            if e.response.status_code == 401:  # Unauthorized
                logger.error("NewsAPI key is invalid or unauthorized. Please check your API key.")
                return []  # Stop trying if API key is bad
            elif e.response.status_code == 429:  # Rate limited
                logger.warning("Rate limited by NewsAPI. Consider increasing delay between requests or reducing page_size/max_articles.")
            break
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            break
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e} - Response text: {response.text}")
            break

    logger.info(f"Finished fetching. Total articles retrieved: {len(all_articles)}")
    return all_articles[:max_articles_to_fetch]


def transform_articles_to_model(raw_articles: list[dict[str, Any]], query_source: str, language_code: str = "en") -> list[NewsArticleModel]:
    """Transforms raw article data from NewsAPI into a list of NewsArticleModel objects."""
    transformed_articles = []
    if not raw_articles:
        return transformed_articles

    logger.info(f"Transforming {len(raw_articles)} raw articles. Query source: '{query_source}', Language code: '{language_code}'")

    for raw_article in raw_articles:
        try:
            title = raw_article.get("title")
            url = raw_article.get("url")

            if not title or not url:
                logger.warning(f"Skipping article due to missing title or URL: {raw_article.get('source', {}).get('name')} - {title[:50] if title else 'N/A'}")
                continue

            content = raw_article.get("content")
            description = raw_article.get("description")

            # Use description if content is missing or too short (NewsAPI content can be truncated)
            if not content or len(content) < 50:  # Arbitrary length check
                content = description
            if not content:  # If still no content, log and skip or use a placeholder
                logger.debug(f"Article '{title}' has no content or description.")
                # For now, we allow it, but it might be filtered later depending on use case

            published_at_str = raw_article.get("publishedAt")
            published_at_dt = None
            if published_at_str:
                try:
                    # Handle Z for UTC explicitly for wider Python version compatibility
                    if published_at_str.endswith("Z"):
                        published_at_str = published_at_str[:-1] + "+00:00"
                    published_at_dt = datetime.fromisoformat(published_at_str)
                except ValueError as e:
                    logger.warning(f"Could not parse publishedAt date '{published_at_str}' for article '{title}': {e}")
                    # Fallback or skip: For now, allow None, but it might be an issue for DB constraints

            author = raw_article.get("author")
            source_name = raw_article.get("source", {}).get("name")
            source_id = raw_article.get("source", {}).get("id")

            # Basic tag generation
            tags = [query_source.lower()] if query_source else []
            if source_name and source_name.lower() not in tags:
                tags.append(source_name.lower().replace(" ", "-"))

            # Language mapping (simplified for now)
            # NewsAPI uses ISO 639-1 codes. ContentLanguage enum needs to align or have mapping.
            # For now, we'll just store the provided language_code.
            # A more robust solution would map NewsAPI codes to ContentLanguage enum members.
            article_language = language_code
            # try:
            #    article_language_enum = ContentLanguage(language_code)
            # except ValueError:
            #    logger.warning(f"Language code '{language_code}' not in ContentLanguage enum. Storing as string.")
            #    article_language_enum = language_code # Store as string if not in enum

            article_model = NewsArticleModel(
                title=title,
                url=url,
                content=content,
                excerpt=description,
                published_at=published_at_dt,
                author=author,
                source_name=source_name,
                source_id=source_id,
                category=query_source,  # Main query term as category
                tags=tags,
                language=article_language,  # Store the input language code
                original_id=url,  # URL is usually a good unique ID for news articles
                scraped_at=datetime.utcnow(),
                metadata=raw_article,  # Store the whole raw article for now
            )
            transformed_articles.append(article_model)
        except Exception as e:
            logger.error(
                f"Error transforming article: {raw_article.get('title', 'N/A')}. Error: {e}",
                exc_info=True,
            )

    logger.info(f"Successfully transformed {len(transformed_articles)} articles out of {len(raw_articles)} raw articles.")
    return transformed_articles


def process_articles(articles: list[NewsArticleModel]) -> list[dict[str, Any]]:
    logger.info(f"Processing {len(articles)} articles.")
    processed_data = []
    current_time_iso = datetime.utcnow().isoformat()
    for article_model in articles:
        article_dict = article_model.model_dump(mode="json")  # Ensures datetime is ISO string
        article_dict["platform"] = "newsapi"
        article_dict["data_source"] = "NewsAPI.org"
        article_dict["fetched_at"] = current_time_iso
        # Ensure tags are simple list of strings for easier CSV/JSON handling if they exist
        if "tags" in article_dict and isinstance(article_dict["tags"], list):
            article_dict["tags"] = [str(tag) for tag in article_dict["tags"]]
        processed_data.append(article_dict)
    logger.info(f"Finished processing {len(processed_data)} articles.")
    return processed_data


def save_data(data: list[dict[str, Any]], output_dir: str, source_name: str = "newsapi"):
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file_path = os.path.join(output_dir, f"{source_name}_{timestamp}.json")
    csv_file_path = os.path.join(output_dir, f"{source_name}_{timestamp}.csv")
    latest_json_path = os.path.join(output_dir, f"{source_name}_latest.json")
    latest_csv_path = os.path.join(output_dir, f"{source_name}_latest.csv")

    logger.info(f"Saving data to {output_dir} with source name {source_name}")

    try:
        # Save main JSON file
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved JSON data to {json_file_path}")

        # Save latest JSON file
        with open(latest_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved latest JSON data to {latest_json_path}")

        # Save CSV files
        if data:
            # Prepare data for CSV (e.g. flatten lists)
            csv_data = []
            for item in data:
                csv_item = item.copy()
                for key, value in csv_item.items():
                    if isinstance(value, list):
                        csv_item[key] = ", ".join(map(str, value))  # Simple list to string
                    elif isinstance(value, dict):
                        # For simplicity, convert dicts to JSON strings for CSV
                        csv_item[key] = json.dumps(value)
                csv_data.append(csv_item)

            if csv_data:  # Ensure there's data to write
                fieldnames = csv_data[0].keys()
                # Save main CSV file
                with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
                logger.info(f"Successfully saved CSV data to {csv_file_path}")

                # Save latest CSV file
                with open(latest_csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
                logger.info(f"Successfully saved latest CSV data to {latest_csv_path}")
            else:
                logger.info("No data to write to CSV after processing for CSV.")
        else:
            logger.info("No data provided to save_data function.")

    except OSError as e:
        logger.error(f"IOError saving data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving data: {e}", exc_info=True)  # Added exc_info for better debugging
        # Consider re-raising critical errors if needed, or handle more gracefully
        # For now, we log and continue, but for critical save operations, re-raising might be better.

    return {
        "json_file": (json_file_path if "json_file_path" in locals() else None),  # Ensure paths are defined
        "csv_file": csv_file_path if "csv_file_path" in locals() else None,
        "latest_json": latest_json_path if "latest_json_path" in locals() else None,
        "latest_csv": latest_csv_path if "latest_csv_path" in locals() else None,
    }


def main():
    logger.info("Starting NewsAPI ETL process")

    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "raw", "newsapi")  # Adjusted path to include "raw"
    ensure_directories([output_dir])  # Ensure base output directory exists

    settings = get_settings()
    api_key = settings.api.news_api_key
    if not api_key:
        logger.warning(
            "NewsAPI key not found in settings (checked API_NEWS_API_KEY). NewsAPI data collection will be skipped. To enable NewsAPI: set API_NEWS_API_KEY in your .env file or environment variables."
        )
        # Create empty output files to maintain consistency in data structure
        empty_data = []
        file_paths = save_data(empty_data, output_dir, source_name="newsapi_no_key")
        logger.info(f"Created empty NewsAPI output files (no API key): {file_paths}")
        logger.info("NewsAPI ETL completed (skipped due to missing API key)")
        return

    session = create_session()

    query = 'AI OR "Artificial Intelligence" OR LLM OR GenAI OR Generative AI'
    language = "en"
    max_articles = 100  # For testing

    logger.info(f"Attempting to fetch up to {max_articles} articles for query: '{query}' in language '{language}'.")

    raw_articles = get_newsapi_articles(
        session,
        api_key,
        query=query,
        language=language,
        page_size=50,
        max_articles_to_fetch=max_articles,
    )

    if raw_articles:
        logger.info(f"Fetched {len(raw_articles)} raw articles from NewsAPI.")
        transformed_articles = transform_articles_to_model(raw_articles, query_source="AI", language_code=language)

        if transformed_articles:
            logger.info(f"Successfully transformed {len(transformed_articles)} articles into NewsArticleModel.")
            processed_articles_list = process_articles(transformed_articles)
            if processed_articles_list:
                file_paths = save_data(processed_articles_list, output_dir, source_name="newsapi")
                logger.info(f"NewsAPI ETL completed. Data saved to: {file_paths}")
            else:
                logger.info("No articles were processed after transformation.")
        else:
            logger.warning("No articles were successfully transformed, though raw articles were fetched.")
    else:
        logger.info("No articles fetched from NewsAPI. This could be due to the query, API limits, or an error during fetching.")

    logger.info("NewsAPI ETL process finished.")  # Adjusted final log message


if __name__ == "__main__":
    main()
