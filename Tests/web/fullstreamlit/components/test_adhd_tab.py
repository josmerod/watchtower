import json
from unittest.mock import mock_open, patch

import pytest

# Add project root to allow imports from src
from web.fullstreamlit.components.adhd_tab import ADHDPapersComponent

# Mock streamlit before it's used by the component, if necessary for other tests.
# However, for _load_data, we only need to patch st.error.

@pytest.fixture
def adhd_component_instance(tmp_path):
    """Provides an ADHDPapersComponent instance with data_file_path redirected to tmp_path."""
    component = ADHDPapersComponent()
    # Override the data_file_path to use a temporary directory
    # The original component sets this path based on project_root and etl_output_dir
    # For testing _load_data in isolation, we directly set data_file_path.
    return component

def test_load_data_successful(adhd_component_instance, tmp_path):
    """Tests successful loading of data from a JSON file."""
    sample_data = [{'title': 'Paper 1', 'author': 'Author A'}, {'title': 'Paper 2', 'author': 'Author B'}]

    # Create the dummy JSON file in the temporary path
    data_file = tmp_path / "test_latest_papers.json" # Same path as in fixture
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f)

    # Ensure the component's data_file_path is correctly pointing to this file
    # This should already be handled by the fixture, but double-check if issues arise.
    # adhd_component_instance.data_file_path = str(data_file)

    loaded_data = adhd_component_instance._load_data()
    assert loaded_data == sample_data

@patch('streamlit.error') # Patch streamlit.error where it's called
def test_load_data_file_not_found(mock_st_error, adhd_component_instance, caplog): # caplog can capture internal logs if any
    """Tests behavior when the data file does not exist."""
    # Ensure the file does NOT exist (tmp_path is fresh, so it shouldn't unless created)
    # data_file_path is already set by the fixture to a non-existent file in tmp_path initially

    loaded_data = adhd_component_instance._load_data()

    assert loaded_data == []
    mock_st_error.assert_called_once()
    # Check that the error message contains relevant info
    args, _ = mock_st_error.call_args
    assert "Data file not found" in args[0]
    assert adhd_component_instance.data_file_path in args[0]


@patch('streamlit.error') # Patch streamlit.error
def test_load_data_json_decode_error(mock_st_error, adhd_component_instance, tmp_path):
    """Tests behavior when the data file contains invalid JSON."""
    invalid_json_content = "{'title': 'Paper 1', 'author': 'Author A',,}" # Invalid JSON (extra comma, single quotes)

    data_file = tmp_path / "test_latest_papers.json" # Same path as in fixture
    with open(data_file, 'w', encoding='utf-8') as f:
        f.write(invalid_json_content)

    # adhd_component_instance.data_file_path = str(data_file) # Ensure path is set

    loaded_data = adhd_component_instance._load_data()

    assert loaded_data == []
    mock_st_error.assert_called_once()
    args, _ = mock_st_error.call_args
    assert "Error loading ADHD data" in args[0]
    # The actual exception message from json.JSONDecodeError might also be in args[0]


@patch('streamlit.error')
def test_load_data_generic_exception(mock_st_error, adhd_component_instance, tmp_path):
    """Tests behavior with a generic (non-JSONDecode, non-FileNotFound) exception during file reading."""
    # This can be simulated by making `open` raise an unexpected error.

    # Create a dummy file so os.path.exists passes
    data_file = tmp_path / "test_latest_papers.json"
    data_file.touch() # Create an empty file

    # adhd_component_instance.data_file_path = str(data_file)

    with patch('builtins.open', mock_open()) as m_open: # Ensure this mock_open is from unittest.mock

        loaded_data = adhd_component_instance._load_data()

    assert loaded_data == []
    mock_st_error.assert_called_once()
    args, _ = mock_st_error.call_args
    assert "Error loading ADHD data: Unexpected I/O error" in args[0]


# --- Tests for render and render_paper_card methods ---

@patch('streamlit.title')
@patch('streamlit.warning')
@patch.object(ADHDPapersComponent, '_load_data', return_value=[]) # Mock _load_data directly on the class/instance
def test_render_no_data_shows_warning(mock_load_data, mock_st_warning, mock_st_title, adhd_component_instance):
    """Tests that a warning is shown when no data is loaded."""
    adhd_component_instance.render()

    mock_st_title.assert_called_once_with("ADHD Papers and Resources")
    mock_load_data.assert_called_once() # This now correctly checks the mock on the instance/class
    mock_st_warning.assert_called_once_with("No ADHD papers found. Please run the ADHDPublicationETL first.")


@patch('streamlit.title')
@patch('streamlit.markdown')
@patch('streamlit.text_input', return_value="") # Default search is empty
@patch.object(ADHDPapersComponent, 'render_paper_card') # Mock the card rendering method
def test_render_with_data_displays_papers(mock_render_card, mock_st_text_input, mock_st_markdown, mock_st_title, adhd_component_instance):
    """Tests that papers are displayed when data is available."""
    sample_papers = [
    ]
    # Patch _load_data on the specific instance to control its return value
    with patch.object(adhd_component_instance, '_load_data', return_value=sample_papers) as mock_load_data:
        adhd_component_instance.render()

        mock_st_title.assert_called_once_with("ADHD Papers and Resources")
        mock_load_data.assert_called_once()
        mock_st_markdown.assert_any_call(f"Displaying {len(sample_papers)} papers.")
        mock_st_text_input.assert_called_once_with("Search by title or abstract:")

        assert mock_render_card.call_count == len(sample_papers)
        mock_render_card.assert_any_call(sample_papers[0], 0)
        mock_render_card.assert_any_call(sample_papers[1], 1)


@patch('streamlit.title')
@patch('streamlit.markdown')
@patch('streamlit.text_input') # We'll control its return value
@patch('streamlit.info')
@patch.object(ADHDPapersComponent, 'render_paper_card')
def test_render_search_filters_papers(mock_render_card, mock_st_info, mock_st_text_input, mock_st_markdown, mock_st_title, adhd_component_instance):
    """Tests search functionality filters papers correctly."""
    sample_papers = [
    ]
    with patch.object(adhd_component_instance, '_load_data', return_value=sample_papers) as mock_load_data:
        # Test 1: Search term "ADHD" - should match the first paper
        mock_st_text_input.return_value = "ADHD"
        adhd_component_instance.render()

        mock_load_data.assert_called_with() # Called once for this render pass
        mock_st_markdown.assert_any_call("Found 1 papers matching your search.")
        mock_render_card.assert_called_once_with(sample_papers[0], 0)

        # Test 2: Search term "nonexistent" - should match no papers
        mock_render_card.reset_mock() # Reset call count from previous assertion
        mock_st_markdown.reset_mock()
        mock_st_text_input.return_value = "nonexistent"

        mock_st_markdown.assert_any_call("Found 0 papers matching your search.")
        mock_render_card.assert_not_called()
        mock_st_info.assert_called_with("No papers match your current search criteria.")


@patch('streamlit.expander')
@patch('streamlit.markdown')
@patch('streamlit.write')
def test_render_paper_card_displays_details(mock_st_write, mock_st_markdown, mock_st_expander, adhd_component_instance):
    """Tests that render_paper_card displays all details of a paper."""
    paper = {






        'abstract': 'This is a very detailed test abstract for the paper card.'
    }

    # Mock the context manager behavior of st.expander
    # mock_expander_context = mock_st_expander.return_value.__enter__.return_value
    # No, st.expander itself is the context manager. If it's called, it's "entered".


    mock_st_expander.assert_called_once_with(f"{paper['title']}")

    # Check that markdown was called with the correct details
    # The order of these calls might vary, so use assert_any_call
    mock_st_markdown.assert_any_call(f"**Authors:** {', '.join(paper['authors'])}")
    mock_st_markdown.assert_any_call(f"**Date:** {paper['publication_date']}")
    mock_st_markdown.assert_any_call(f"**Source:** {paper['source']}")
    mock_st_markdown.assert_any_call(f"**DOI:** [{paper['doi']}](https://doi.org/{paper['doi']})")
    mock_st_markdown.assert_any_call(f"**Link:** [View Paper]({paper['url']})")

    mock_st_write.assert_called_once_with(f"**Abstract:** {paper['abstract']}")


@patch('streamlit.expander')
@patch('streamlit.markdown')
@patch('streamlit.write')
def test_render_paper_card_handles_missing_optional_fields(mock_st_write, mock_st_markdown, mock_st_expander, adhd_component_instance):
    """Tests that render_paper_card gracefully handles missing optional fields like DOI or abstract."""
    paper_minimal = {







    }

    mock_st_expander.assert_called_once_with(f"{paper_minimal['title']}")
    mock_st_markdown.assert_any_call(f"**Authors:** {', '.join(paper_minimal['authors'])}")
    mock_st_markdown.assert_any_call(f"**Date:** {paper_minimal['publication_date']}")
    mock_st_markdown.assert_any_call(f"**Source:** {paper_minimal['source']}")
    mock_st_markdown.assert_any_call(f"**Link:** [View Paper]({paper_minimal['url']})")

    # Check that DOI markdown was NOT called if DOI is None
    # And abstract is displayed as "No abstract available."
    doi_markdown_call = f"**DOI:** [{paper_minimal['doi']}]" # This would be problematic if doi is None

    called_markdowns = [call[0][0] for call in mock_st_markdown.call_args_list]
    assert not any(f"**DOI:** [{None}]" in called_md for called_md in called_markdowns) # Ensure DOI for None isn't made
    assert not any("**DOI:** [" in called_md and paper_minimal['doi'] is None for called_md in called_markdowns)


    mock_st_write.assert_called_once_with("**Abstract:** No abstract available.")

    # Test with empty string abstract
    mock_st_write.reset_mock()
    paper_empty_abstract = {**paper_minimal, 'abstract': ''}
    mock_st_write.assert_called_once_with("**Abstract:** No abstract available.")


