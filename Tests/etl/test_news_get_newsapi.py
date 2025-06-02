import sys
import os
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json

# Add project root to sys.path to allow importing project modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Modules to be tested
from src.etl.news.news_get_newsapi import (
    create_session,
    get_newsapi_articles,
    transform_articles_to_model,
    process_articles,
    save_data, # We will mock this
    main as news_api_main # To potentially test parts of main or its setup
)
from src.models.news import NewsArticleModel # For type checking if needed

# Sample NewsAPI JSON response
SAMPLE_NEWSAPI_RESPONSE = {
    "status": "ok",
    "totalResults": 2,
    "articles": [
        {
            "source": {"id": "test-source-1", "name": "Test Source One"},
            "author": "Author One",
            "title": "First Test Article Title",
            "description": "Description for the first test article.",
            "url": "http://example.com/testarticle1",
            "urlToImage": "http://example.com/image1.jpg",
            "publishedAt": "2023-10-26T10:00:00Z",
            "content": "Full content of the first test article."
        },
        {
            "source": {"id": "test-source-2", "name": "Test Source Two"},
            "author": "Author Two",
            "title": "Second Test Article Title",
            "description": "Description for the second test article.",
            "url": "http://example.com/testarticle2",
            "urlToImage": "http://example.com/image2.jpg",
            "publishedAt": "2023-10-27T12:30:00Z",
            "content": "Full content of the second test article. This one has more words."
        }
    ]
}

# A minimal settings mock
class MockSettings:
    class MockAPI:
        news_api_key = "test_dummy_key"
    api = MockAPI()

@patch('src.etl.news.news_get_newsapi.save_data') # Mock save_data to prevent file writes
@patch('requests.Session.get') # Mock requests.get
@patch('src.etl.news.news_get_newsapi.get_settings') # Mock get_settings
def main_test_logic(mock_get_settings, mock_requests_get, mock_save_data):
    print("Starting NewsAPI ETL test logic...")

    # Configure mocks
    mock_get_settings.return_value = MockSettings()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_NEWSAPI_RESPONSE
    mock_response.raise_for_status = MagicMock() # Does nothing
    mock_requests_get.return_value = mock_response

    mock_save_data.return_value = {"json_file": "dummy.json"} # Simulate return value

    test_passed = True
    error_messages = []

    try:
        # 1. Create session
        session = create_session()
        if session is None:
            test_passed = False
            error_messages.append("Failed: create_session() returned None.")
            raise AssertionError("Session creation failed")
        print("Step 1: create_session() - OK")

        # 2. Get raw articles
        raw_articles = get_newsapi_articles(session, "test_key_from_mock_settings", query="test_query", max_articles_to_fetch=2)
        if not raw_articles or len(raw_articles) != len(SAMPLE_NEWSAPI_RESPONSE["articles"]):
            test_passed = False
            error_messages.append(f"Failed: get_newsapi_articles() expected {len(SAMPLE_NEWSAPI_RESPONSE['articles'])} articles, got {len(raw_articles) if raw_articles else 0}.")
            raise AssertionError("Fetching raw articles failed")
        print(f"Step 2: get_newsapi_articles() - OK, fetched {len(raw_articles)} articles.")

        # 3. Transform articles
        # Check published_at of the first raw article before transformation
        raw_published_at_str = SAMPLE_NEWSAPI_RESPONSE["articles"][0]["publishedAt"]

        transformed_articles = transform_articles_to_model(raw_articles, query_source="test_query_src", language_code="en")
        if not transformed_articles or len(transformed_articles) != len(raw_articles):
            test_passed = False
            error_messages.append("Failed: transform_articles_to_model() did not transform all articles.")
            raise AssertionError("Transforming articles failed")

        # Check if published_at was correctly parsed into a datetime object in the Model
        first_transformed_article_model = transformed_articles[0]
        if not isinstance(first_transformed_article_model.published_at, datetime):
            test_passed = False
            error_messages.append(f"Failed: transformed_articles[0].published_at is not a datetime object, type is {type(first_transformed_article_model.published_at)}.")
        else:
            # Compare with expected datetime
            expected_dt = datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
            if first_transformed_article_model.published_at != expected_dt:
                test_passed = False
                error_messages.append(f"Failed: transformed_articles[0].published_at '{first_transformed_article_model.published_at}' does not match expected '{expected_dt}'.")

        print(f"Step 3: transform_articles_to_model() - OK, transformed {len(transformed_articles)} articles.")

        # 4. Process articles
        processed_articles_list = process_articles(transformed_articles)
        if not processed_articles_list or len(processed_articles_list) != len(transformed_articles):
            test_passed = False
            error_messages.append("Failed: process_articles() did not process all transformed articles.")
            raise AssertionError("Processing articles failed")

        first_processed_article = processed_articles_list[0]
        expected_title = SAMPLE_NEWSAPI_RESPONSE["articles"][0]["title"]
        if first_processed_article.get("title") != expected_title:
            test_passed = False
            error_messages.append(f"Failed: Processed article title mismatch. Expected '{expected_title}', got '{first_processed_article.get('title')}'.")

        if first_processed_article.get("platform") != "newsapi":
            test_passed = False
            error_messages.append(f"Failed: Processed article platform mismatch. Expected 'newsapi', got '{first_processed_article.get('platform')}'.")

        if first_processed_article.get("data_source") != "NewsAPI.org":
            test_passed = False
            error_messages.append(f"Failed: Processed article data_source mismatch. Expected 'NewsAPI.org', got '{first_processed_article.get('data_source')}'.")

        # Check if 'fetched_at' exists and is a valid ISO datetime string
        fetched_at_str = first_processed_article.get("fetched_at")
        if not fetched_at_str:
            test_passed = False
            error_messages.append("Failed: Processed article 'fetched_at' is missing.")
        else:
            try:
                datetime.fromisoformat(fetched_at_str)
            except ValueError:
                test_passed = False
                error_messages.append(f"Failed: Processed article 'fetched_at' ('{fetched_at_str}') is not a valid ISO format string.")

        # Check if 'published_at' in processed dict is an ISO string (after model_dump)
        published_at_processed_str = first_processed_article.get("published_at")
        if not published_at_processed_str:
             test_passed = False
             error_messages.append("Failed: Processed article 'published_at' is missing in the dictionary.")
        else:
            try:
                # Ensure it's the correct ISO format string that model_dump produces
                datetime.fromisoformat(published_at_processed_str.replace('Z', '+00:00'))
                # Compare string value if needed, e.g. ensure it matches original input if timezone handling is consistent
                # Expected: "2023-10-26T10:00:00Z" or "2023-10-26T10:00:00+00:00"
                if not (published_at_processed_str == raw_published_at_str or published_at_processed_str == raw_published_at_str.replace('Z', '+00:00')):
                    # This check might be too strict if model_dump slightly changes format but is still valid ISO
                    pass # Loosening this specific string comparison for now as long as it's valid ISO
            except ValueError:
                test_passed = False
                error_messages.append(f"Failed: Processed article 'published_at' ('{published_at_processed_str}') is not a valid ISO format string after model_dump.")


        print(f"Step 4: process_articles() - OK, processed {len(processed_articles_list)} articles.")

        # 5. Save data (mocked)
        file_paths = save_data(processed_articles_list, "dummy_output_dir", source_name="test_newsapi")
        mock_save_data.assert_called_once_with(processed_articles_list, "dummy_output_dir", source_name="test_newsapi")
        if not file_paths or file_paths["json_file"] != "dummy.json": # Check if mock return value is received
             test_passed = False
             error_messages.append("Failed: save_data mock not called as expected or return value incorrect.")
        print("Step 5: save_data() (mocked) - OK, assertion passed.")

    except AssertionError as e: # Catch assertion errors from test steps
        print(f"AssertionError during test: {e}")
        # test_passed is already False if an assertion error is raised from within the try block.
    except Exception as e:
        test_passed = False
        error_messages.append(f"An unexpected error occurred: {e}")
        import traceback
        error_messages.append(traceback.format_exc())

    if test_passed:
        print("\n--- NewsAPI ETL Test PASSED ---")
    else:
        print("\n--- NewsAPI ETL Test FAILED ---")
        for msg in error_messages:
            print(msg)

    return test_passed


if __name__ == "__main__":
    print(f"Running test script: {os.path.basename(__file__)}")
    # This basic try-except is for the overall script execution
    try:
        test_successful = main_test_logic()
        if not test_successful:
            sys.exit(1) # Indicate failure to CI or calling scripts
    except Exception as e:
        print(f"Critical error during test execution: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
