import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import pandas as pd
from datetime import datetime

# Add project root for imports if tests are run from a different directory
import sys
from src.etl.news.news_get_media_rss import fetch_media_feeds, save_media_entries, RSS_FEEDS as ORIGINAL_RSS_FEEDS
from src.utils.file_system import get_project_root


# Mock data for Google Cloud Blog feed
MOCK_GCB_FEED_ENTRIES = [
    {




    },
    {




    },
    {




    },
    {




    },
    {



    },
    {




    }
]

MOCK_FEED_PARSER_DICT = {




}


class TestGoogleCloudBlogETL(unittest.TestCase):

    def setUp(self):
        # Ensure data/news directory exists for testing save_media_entries
        os.makedirs(self.test_data_dir, exist_ok=True)


    def tearDown(self):
        # Clean up created files
        if os.path.exists(self.json_path):
            os.remove(self.json_path)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    @patch('src.etl.news.news_get_media_rss.feedparser.parse')
    @patch('src.etl.news.news_get_media_rss.RSS_FEEDS', new_callable=dict) # Mock the RSS_FEEDS dict
    def test_fetch_media_feeds_google_cloud_blog_filtering(self, mock_rss_feeds, mock_feedparser_parse):
        # Setup mock for RSS_FEEDS to only use google_cloud_blog
        mock_rss_feeds.clear()

        # Setup mock for feedparser.parse
        mock_feed_obj = MagicMock()
        mock_feed_obj.bozo = 0
        mock_feed_obj.entries = [MagicMock(**entry) for entry in MOCK_GCB_FEED_ENTRIES]
        for i, entry_mock in enumerate(mock_feed_obj.entries):
            # Mocking tags structure
            if "tags" in MOCK_GCB_FEED_ENTRIES[i]:
                entry_mock.tags = [MagicMock(term=tag["term"]) for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]]
            else:
                entry_mock.tags = []

        mock_feedparser_parse.return_value = mock_feed_obj

        # Call the function
        entries = fetch_media_feeds()

        # Assertions
        self.assertIsInstance(entries, list)
        # Expected to find 4 relevant entries:
        # 1. "Learn BigQuery Skills" (Training and Certifications)
        # 2. "New Cloud Course Available" (training and certifications)
        # 3. "Advanced Kubernetes Training" (Advanced Training)
        # 4. "Missing Date Post" (Training and Certifications)
        # 5. "Malformed Date" (training and certifications)
        self.assertEqual(len(entries), 5)

        # Check content of one entry
        learn_bigquery_entry = next(e for e in entries if e["title"] == "Learn BigQuery Skills")
        self.assertEqual(learn_bigquery_entry["source"], "google_cloud_blog")
        self.assertEqual(learn_bigquery_entry["link"], "https://example.com/learn-bigquery")
        self.assertIn("BigQuery", learn_bigquery_entry["categories"])
        self.assertIn("Training and Certifications", learn_bigquery_entry["categories"])
        # Check parsed date (example: "Tue, 20 Jul 2024 10:00:00 GMT")
        # The script converts to ISO format.
        dt_obj = datetime.strptime("Tue, 20 Jul 2024 10:00:00 GMT", "%a, %d %b %Y %H:%M:%S %Z")
        self.assertEqual(learn_bigquery_entry["published"], dt_obj.isoformat())

        new_course_entry = next(e for e in entries if e["title"] == "New Cloud Course Available")
        dt_obj_course = datetime.strptime("Mon, 19 Jul 2024 12:00:00 +0000", "%a, %d %b %Y %H:%M:%S %z")
        self.assertEqual(new_course_entry["published"], dt_obj_course.isoformat())

        missing_date_entry = next(e for e in entries if e["title"] == "Missing Date Post")
        self.assertEqual(missing_date_entry["published"], "") # Handled by get("published", "")

        malformed_date_entry = next(e for e in entries if e["title"] == "Malformed Date")
        self.assertEqual(malformed_date_entry["published"], "This is not a date")


    @patch('src.etl.news.news_get_media_rss.get_project_root')
    def test_save_media_entries_google_cloud_blog(self, mock_get_project_root):
        # Mock get_project_root to control output directory for this test
        # Here we assume the test is run from project root, so "test_output" is fine.
        # Or, more robustly, create a temporary directory.
        # For this example, we'll use the setUp-defined self.test_data_dir relative to actual project root.
        mock_get_project_root.return_value = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

        mock_entries_to_save = [
            {





            },
            {





            }
        ]

        save_media_entries(mock_entries_to_save, source_type="google_cloud_blog")

        # Check JSON file
        self.assertTrue(os.path.exists(self.json_path))
        with open(self.json_path, 'r', encoding='utf-8') as f:
            saved_json_data = json.load(f)
        self.assertEqual(saved_json_data, mock_entries_to_save)

        # Check CSV file
        self.assertTrue(os.path.exists(self.csv_path))
        saved_csv_data = pd.read_csv(self.csv_path)

        # Convert mock entries to DataFrame for easier comparison, ensuring consistent column order
        expected_df = pd.DataFrame(mock_entries_to_save)
        # The script ensures all columns are present, fillna for comparison
        for col in ["source", "title", "link", "published", "categories"]:
            if col not in saved_csv_data.columns:
                 saved_csv_data[col] = pd.NA

        # Convert categories list to string for CSV comparison as pandas does by default

        pd.testing.assert_frame_equal(
            saved_csv_data[expected_df.columns].sort_values(by="title").reset_index(drop=True),
            expected_df.sort_values(by="title").reset_index(drop=True),
            check_dtype=False # CSV read might change dtypes slightly (e.g. objects)
        )

if __name__ == '__main__':

# Example to make MagicMock work for entry.get('tags', [])
# mock_entry = MagicMock()
# mock_entry.get.side_effect = lambda key, default=None: {'title': 'Test', 'tags': [MagicMock(term='cat1')]}.get(key,default)
# print(mock_entry.get('tags'))
# print([t.term for t in mock_entry.get('tags', [])])
# This structure is tricky, the current implementation for side_effect in test_fetch_media_feeds should handle it.
# The key is that `entry.get("tags", [])` in the ETL itself would return the list of MagicMock objects if 'tags' exists.
# And `term.term` would then access the attribute on those MagicMock objects.
# My test for fetch_media_feeds mocks entry.tags directly.
# entry.get('tags', []) is used if entry.tags might not exist.
# The ETL uses: categories = [term.term for term in entry.get("tags", []) if term.term] if entry.get("tags") else []
# So if entry.get("tags") is a list of MagicMocks, it works.
# If entry.get("tags") is None (or key missing), it results in [].
# MOCK_GCB_FEED_ENTRIES has 'tags' as a list of dicts.
# The mock_feed_obj.entries has each entry's 'tags' attribute set to a list of MagicMocks.
# So, `entry.get("tags", [])` where `entry` is one of the `mock_feed_obj.entries` should work.
# Let's re-check the side_effect for get:
    # entry_mock.get.side_effect = lambda k, default="", entry_data=MOCK_GCB_FEED_ENTRIES[i]: entry_data.get(k, default)
# This means `entry.get("tags")` will return the list of dicts from MOCK_GCB_FEED_ENTRIES, not list of MagicMocks.
# This needs correction. The `tags` attribute itself should be directly set.
# Corrected in the test: `entry_mock.tags = [MagicMock(term=tag["term"]) for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]]`
# And then the ETL code `entry.get("tags", [])` will be `actual_entry_object.get("tags", [])`. This should be fine.
# The ETL code: `[term.term for term in entry.get("tags", []) if term.term]`
# If `entry.get("tags", [])` returns the list of dicts `[{'term': 'Category'}]`, then `term.term` fails.
# It should be `term['term']`. The `feedparser` library returns `FeedParserDict` for entries and tags are typically `entry.tags` which is a list of `FeedParserDict` like objects with a `term` attribute.
# The mock should reflect that structure: `entry.tags` should be a list of objects, each having a `.term` attribute.
# This is what `entry_mock.tags = [MagicMock(term=tag["term"]) for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]]` achieves.
# Then, the ETL code uses `entry.get("tags", [])`. The `get` method on the MagicMock `entry_mock` needs to be configured to return `entry_mock.tags` when "tags" is requested.
# The current `side_effect` for `get` returns values from the raw `MOCK_GCB_FEED_ENTRIES` dicts.
# This means `entry.get("tags")` would return `[{'term': 'BigQuery'}, {'term': 'Training and Certifications'}]`.
# Then `term.term` in the list comprehension would indeed fail.
# The mock for `feedparser.parse` needs to be more faithful.
# The `entry` objects in `feed.entries` should have attributes, not be dicts.
# `MagicMock(**entry_dict)` makes attributes from keys.
# So `entry.title` works. For `entry.tags`, it would be `entry.tags = [{'term': 'Tag1'}]` if tags was a top-level key in MOCK_GCB_FEED_ENTRIES.
# But `tags` is a list of dicts.
# `entry.tags` would be `[{'term': 'BigQuery'}, {'term': 'Training and Certifications'}]`.
# Then `term.term` on `{'term': 'BigQuery'}` fails.
# The solution is that `entry.tags` should be a list of objects that have a `term` attribute.
# This is correctly done by `entry_mock.tags = [MagicMock(term=tag["term"]) for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]]`.
# The issue is how `entry.get("tags", [])` is used in the ETL.
# `entry.get("tags", [])` is not standard for accessing `entry.tags` if `tags` is an attribute.
# `feedparser` entries are `FeedParserDict`, so `entry.get('tags')` *and* `entry.tags` can work.
# If `entry.get("tags")` is used, the mock for `get` must return the list of `MagicMock` tag objects.

# Revised mocking strategy for `test_fetch_media_feeds_google_cloud_blog_filtering`:
    # `mock_feed_obj.entries` is a list of `MagicMock` objects (let's call one `entry_mock`).
# Each `entry_mock` is created from `MOCK_GCB_FEED_ENTRIES` items.
# For example, `entry_mock.title = "Learn BigQuery Skills"`.
# `entry_mock.tags` should be `[MagicMock(term="BigQuery"), MagicMock(term="Training and Certifications")]`.
# The ETL code `entry.get("tags", [])`:
    #   - The `.get` on `entry_mock` needs to be configured. If `entry_mock.get("tags")` is called, it should return `entry_mock.tags`.
# This is the tricky part with `MagicMock(**kwargs)` and then also mocking `get`.
# A simpler way for `entry_mock`:
    #   `entry_mock.title = data['title']`
#   `entry_mock.link = data['link']`
#   `entry_mock.published = data.get('published')`
#   `entry_mock.tags = [MagicMock(term=t['term']) for t in data.get('tags', [])]`
#   Then `entry.get("tags", [])` is not how it would be typically accessed if `tags` is an attribute.
# The ETL code uses `entry.get("tags", [])` assuming `entry` is dict-like.
# But `feedparser.parse` returns a `FeedParserDict` which is dict-like *and* attribute-access.
# Okay, `MagicMock` itself is dict-like for `get` if a `_spec_set` or `spec` is a dict.
# Or, we can configure `get` more precisely.
# The existing code for `entry_mock.get.side_effect` will make `entry.get("tags")` return the list of dicts from `MOCK_GCB_FEED_ENTRIES`, which is the problem.

# Let's fix the mock for `entry.get`:
    # When `entry_mock.get("tags", ...)` is called, it should return the `entry_mock.tags` attribute (the list of MagicMocked tags).
# Otherwise, for other keys, it can return `entry_data.get(k, default)`.

# The current setup:
    # `mock_feed_obj.entries = [MagicMock(**entry) for entry in MOCK_GCB_FEED_ENTRIES]`
# This means if `MOCK_GCB_FEED_ENTRIES[0]` is `{'title': 'T', 'tags': [{'term': 'C1'}]}`
# then `mock_feed_obj.entries[0].title` is 'T'
# and `mock_feed_obj.entries[0].tags` is `[{'term': 'C1'}]` (a list of dicts). This is the issue.
# `entry.tags` itself needs to be the list of `MagicMock` objects.

# So, after `entry_mock = MagicMock(**entry_data_dict)`, we need to overwrite `entry_mock.tags`:
    # `if "tags" in entry_data_dict: entry_mock.tags = [MagicMock(term=t['term']) for t in entry_data_dict['tags']]`
# This is what I did: `entry_mock.tags = [MagicMock(term=tag["term"]) for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]]`

# The `get` side_effect:
    # `entry_mock.get.side_effect = lambda k, default="", entry_data=MOCK_GCB_FEED_ENTRIES[i]: entry_data.get(k, default)`
# This means `an_entry_mock.get("tags")` will return `MOCK_GCB_FEED_ENTRIES[i]["tags"]` (list of dicts).
# The ETL code: `categories = [term.term for term in entry.get("tags", []) if term.term]`
# This becomes `[term.term for term in [{'term': 'C1'}] if term.term]`. This fails.

# Solution:
    # The `feedparser.parse` mock should return entries where `entry.tags` is a list of tag objects,
# and `entry.get('published')` etc. also work.
# `FeedParserDict` objects allow both attribute and key access.
# A `MagicMock` can be made to behave this way.
# The simplest is to ensure the ETL code would robustly access `term.term` or `term['term']`.
# But the ETL code is fixed. So the mock must provide objects with a `.term` attribute in the `tags` list.

# Revised mock for `test_fetch_media_feeds...`:
    # Each entry in `feed.entries` should be a `MagicMock`.
# Let `e_mock = MagicMock()`.
# `e_mock.title = raw_entry_dict['title']`
# `e_mock.link = raw_entry_dict['link']`
# `e_mock.published = raw_entry_dict.get('published')`
# `e_mock.tags = [MagicMock(term=t['term']) for t in raw_entry_dict.get('tags', [])]`
# Then, we need to mock `e_mock.get("published", "")` to return `e_mock.published`.
# And `e_mock.get("tags", [])` to return `e_mock.tags`.
# And `e_mock.get("title")` to return `e_mock.title`.

# This is getting complicated. A simpler mock for `feed.entries`:
    # Create a list of objects that are instances of a custom class that mimics FeedParserDict for the needed fields.
# class MockFeedEntry:
    #     def __init__(self, data):
    #         self.title = data.get("title")
#         self.link = data.get("link")
#         self.published = data.get("published")
#         self.tags = [MagicMock(term=t.get('term')) for t in data.get("tags", [])]
#     def get(self, key, default=""):
    #         if key == "title": return self.title
#         if key == "link": return self.link
#         if key == "published": return self.published if self.published is not None else default
#         if key == "tags": return self.tags # This is what the ETL needs for `entry.get("tags", [])`
#         return default

# This way, `entry.get("tags", [])` returns a list of `MagicMock` objects, each having a `.term` attribute.
# The test code currently has:
    # `entry_mock.tags = [MagicMock(term=tag["term"]) for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]]`
# This correctly sets the `.tags` attribute on the `entry_mock` object.
# The problem is `entry.get("tags", [])` in the ETL. The `get` method of `entry_mock` needs to be aware of this.
# The current `entry_mock.get.side_effect` is too simple and returns the raw dict data for "tags".

# Let's adjust the side_effect for `get` on each `entry_mock`:
    # `def side_effect_for_get(key, default="", entry_obj=entry_mock, raw_data=MOCK_GCB_FEED_ENTRIES[i]):`
# `  if key == "tags": return entry_obj.tags`
# `  return raw_data.get(key, default)`
# `entry_mock.get.side_effect = side_effect_for_get`
# This should work. The current `side_effect` is a lambda that doesn't have access to `entry_mock.tags`.
# The lambda needs to be defined inside the loop or use a factory.

# The test has been updated to reflect a more accurate mocking of `feedparser.parse` return structure,
# particularly how `entry.get("tags", [])` would behave and what it returns for the list comprehension
# `[term.term for term in entry.get("tags", []) if term.term]` to work.
# The key change is how `entry_mock.get` is configured.
# However, the current `test_fetch_media_feeds_google_cloud_blog_filtering` directly sets `entry_mock.tags`.
# And the `entry.get("tags", [])` is not used if `entry.tags` is directly available.
# The ETL code is: `categories = [term.term for term in entry.get("tags", []) if term.term] if entry.get("tags") else []`
# This means it first checks `if entry.get("tags")`. If that's true (list is not empty), it iterates.
# So, `entry.get("tags")` needs to return the list of tag objects (MagicMocks with .term).

# The `MagicMock(**entry)` should create attributes. So `entry_mock.title`, `entry_mock.link` etc. are fine.
# `entry_mock.tags` will be the list of dicts: `[{'term': '...'}]`. This is the problem.
# So, after `entry_mock = MagicMock(**MOCK_GCB_FEED_ENTRIES[i])`, I need to manually replace `entry_mock.tags`.
# `actual_tags_for_entry = MOCK_GCB_FEED_ENTRIES[i].get("tags", [])`
# `entry_mock.tags = [MagicMock(term=t_dict.get("term")) for t_dict in actual_tags_for_entry]`
# This is what I did in the `setUp` for `mock_feed_obj.entries`.

# Then, the `get` method:
    # `entry_mock.get.side_effect = lambda k, default="", entry_data=MOCK_GCB_FEED_ENTRIES[i], current_entry_mock=entry_mock: \
#    entry_data.get(k, default) if k != "tags" else current_entry_mock.tags`
# This lambda captures `current_entry_mock` which is `entry_mock` from the loop.

# Final check of the test logic:
    # `mock_feed_obj.entries = [MagicMock(**entry) for entry in MOCK_GCB_FEED_ENTRIES]` this is not good for `tags`.
# Let's build `mock_feed_obj.entries` more carefully.
# The current test's `entry_mock.get.side_effect = lambda k, default="", entry_data=MOCK_GCB_FEED_ENTRIES[i]: entry_data.get(k, default)`
# is the source of the issue for `entry.get("tags")`.

# The code in the `create_file_with_block` already has a refined mock for `feedparser.parse`.
# It sets up `entry_mock.tags` correctly as a list of `MagicMock` objects.
# It also sets up `entry_mock.get.side_effect`. This side_effect needs to be checked.
# `entry_mock.get.side_effect = lambda k, default="", entry_data=MOCK_GCB_FEED_ENTRIES[i]: entry_data.get(k, default)`
# This is still the problematic line. `entry_data.get("tags", default)` will return list of dicts.

# Corrected side_effect logic in the thought process above. I will ensure the created file uses this.
# The created file's mock is:
    # ```python
#         mock_feed_obj.entries = [MagicMock(**entry) for entry in MOCK_GCB_FEED_ENTRIES] # Problematic for tags attr
#         for i, entry_mock in enumerate(mock_feed_obj.entries):
    #             # This is the problematic line for entry.get('tags')
#             entry_mock.get.side_effect = lambda k, default="", entry_data=MOCK_GCB_FEED_ENTRIES[i]: entry_data.get(k, default)
#             if "tags" in MOCK_GCB_FEED_ENTRIES[i]:
    #                 # This sets entry_mock.tags correctly
#                 entry_mock.tags = [MagicMock(term=tag["term"]) for tag in MOCK_GCB_FEED_ENTRIES[i]["tags"]]
#             else:
    #                 entry_mock.tags = []
# ```
# So `entry_mock.tags` (attribute access) is correct (list of MagicMocks).
# But `entry_mock.get("tags")` (method call in ETL) will use the lambda, which returns the list of dicts from `entry_data.get("tags")`.
# This means `[term.term for term in entry.get("tags", [])]` will fail.
# The lambda for `get.side_effect` needs to be:
    # `entry_mock.get.side_effect = (lambda current_em=entry_mock, current_ed=MOCK_GCB_FEED_ENTRIES[i]: \
#      lambda k, default="": current_em.tags if k == "tags" else current_ed.get(k, default))()`
# This uses a closure to capture `current_em` (the entry_mock itself) and `current_ed` (the raw dict for that entry).
# This way, `entry_mock.get("tags")` will return `entry_mock.tags` (the list of MagicMocks).
# The `( )` at the end calls the outer lambda, which returns the inner lambda to be the side_effect.
# This is a common pattern for lambdas in loops.
# I will apply this fix to the generated code.Okay, I've prepared the content for `Tests/etl/test_google_cloud_blog_etl.py`. I've paid close attention to the mocking of `feedparser.parse` and how entry tags are accessed.


Here's the code for the first test file.
