import os
import xml.etree.ElementTree as ET
from unittest.mock import (
    MagicMock,
    mock_open,  # Requires Python 3.8+ for new_callable in this specific way sometimes.
    patch,
)

import pytest

# Ensure src directory is in path to import ADHDPublicationETL and models
from src.etl.adhd.adhd_publications_etl import (
    EFETCH_URL,
    ESEARCH_URL,
    ADHDPublicationETL,
)
from src.models.adhd import ADHDPublication  # Import the Pydantic model

# Sample XML Data
SAMPLE_ESEARCH_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<eSearchResult>
    <Count>2</Count>
    <RetMax>2</RetMax>
    <RetStart>0</RetStart>
    <QueryKey>1</QueryKey>
    <WebEnv>NCID_1_123456789_130.14.22.107_9001_1604016997_1727487202_0MetA0_S_MegaStore_F_1</WebEnv>
    <IdList>
        <Id>30000001</Id>
        <Id>30000002</Id>
    </IdList>
    <TranslationSet/>
    <TranslationStack>
        <TermSet>
            <Term>"ADHD"[All Fields]</Term>
            <Field>All Fields</Field>
            <Count>1000</Count>
            <Explode>N</Explode>
        </TermSet>
    </TranslationStack>
</eSearchResult>
"""

SAMPLE_EFETCH_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<PubmedArticleSet>
<PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
                </JournalIssue>
                <Title>Journal of ADHD Research</Title>
                <ISOAbbreviation>J ADHD Res</ISOAbbreviation>
            </Journal>
            <Abstract>
                <AbstractText>This is an abstract for the first paper on ADHD interventions.</AbstractText>
            </Abstract>
            <AuthorList CompleteYN="Y">
                <Author ValidYN="Y">
                    <LastName>Doe</LastName>
                    <ForeName>John A.</ForeName>
                    <Initials>JA</Initials>
                </Author>
                <Author ValidYN="Y">
                    <LastName>Smith</LastName>
                    <ForeName>Jane B.</ForeName>
                    <Initials>JB</Initials>
                </Author>
            </AuthorList>
            <Language>eng</Language>
            <PublicationTypeList>
            </PublicationTypeList>
        </Article>
        <MedlineJournalInfo>
            <Country>United States</Country>
            <MedlineTA>J ADHD Res</MedlineTA>
            <NlmUniqueID>100000001</NlmUniqueID>
            <ISSNLinking>0000-0001</ISSNLinking>
        </MedlineJournalInfo>
        <PubmedData>
            <History>
                <PubMedPubDate PubStatus="pubmed">
                    <Year>2023</Year>
                    <Month>1</Month>
                    <Day>1</Day>
                </PubMedPubDate>
            </History>
            <PublicationStatus>ppublish</PublicationStatus>
            <ArticleIdList>
                <ArticleId IdType="pubmed">30000001</ArticleId>
            </ArticleIdList>
        </PubmedData>
    </MedlineCitation>
</PubmedArticle>
<PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
        <PMID Version="1">30000002</PMID>
        <DateCompleted>
            <Year>2023</Year>
            <Month>02</Month>
            <Day>20</Day>
        </DateCompleted>
        <Article PubModel="Print-Electronic">
            <Journal>
                <ISSN IssnType="Electronic">0000-0002</ISSN>
                <JournalIssue CitedMedium="Internet">
                    <Volume>25</Volume>
                    <Issue>2</Issue>
                    <PubDate>
                        <Year>2023</Year>
                        <Month>Feb</Month>
                    </PubDate>
                </JournalIssue>
            </Journal>
            <Abstract>
                <AbstractText>This abstract explores genetic markers for ADHD.</AbstractText>
            </Abstract>
            <AuthorList CompleteYN="Y">
                <Author ValidYN="Y">
                </Author>
            </AuthorList>
            <Language>eng</Language>
        </Article>
        <MedlineJournalInfo>
            <Country>England</Country>
            <MedlineTA>Int J Neurodev Dis</MedlineTA>
            <NlmUniqueID>100000002</NlmUniqueID>
            <ISSNLinking>0000-0002</ISSNLinking>
        </MedlineJournalInfo>
        <PubmedData>
            <History>
                <PubMedPubDate PubStatus="entrez">
                    <Year>2023</Year>
                    <Month>2</Month>
                    <Day>10</Day>
                </PubMedPubDate>
            </History>
            <PublicationStatus>epublish</PublicationStatus>
            <ArticleIdList>
                <ArticleId IdType="pubmed">30000002</ArticleId>
            </ArticleIdList>
        </PubmedData>
    </MedlineCitation>
</PubmedArticle>
</PubmedArticleSet>
"""


@pytest.fixture()
def adhd_etl_instance(tmp_path):
    # Use tmp_path for output_dir to avoid creating files in the project during tests
    # The ADHDPublicationETL constructor now takes 'name' and '**kwargs'
    # We can pass 'output_dir' via kwargs if BaseETL uses it, or let BaseETL default it.
    # For testing, ensuring output_dir is set and doesn't interfere is key.
    # BaseETL likely creates self.output_dir based on self.data_dir_base and self.name.
    # Let's assume BaseETL creates data/<name>/output if no output_dir is given.
    # We just need an instance, the 'load' method isn't tested here.
    instance = ADHDPublicationETL(name="test_adhd_etl")
    # If BaseETL requires an explicit output_dir that it doesn't create from name:
    # instance = ADHDPublicationETL(name="test_adhd_etl", output_dir=str(tmp_path))
    return instance


def mock_requests_get_side_effect(*args, **kwargs):
    mock_response = MagicMock()
    if args[0] == ESEARCH_URL:
        mock_response.status_code = 200
    elif args[0] == EFETCH_URL:
        mock_response.status_code = 200
        mock_response.text = SAMPLE_EFETCH_XML
    else:
        mock_response.status_code = 404
    return mock_response


@patch("requests.get")
def test_extract_successful_fetch_and_parse(mock_get, adhd_etl_instance):
    extracted_data = adhd_etl_instance.extract()

    assert mock_get.call_count >= 2  # At least one for esearch, one for efetch

    # Verify call arguments for ESEARCH_URL
    esearch_call_args = mock_get.call_args_list[0][1]  # kwargs of the first call
    assert esearch_call_args["params"]["db"] == "pubmed"
    assert 'ADHD OR "Attention Deficit Hyperactivity Disorder"' in esearch_call_args["params"]["term"]

    # Verify call arguments for EFETCH_URL (assuming it's the second call)
    efetch_call_args = mock_get.call_args_list[1][1]  # kwargs of the second call
    assert efetch_call_args["params"]["db"] == "pubmed"
    assert efetch_call_args["params"]["WebEnv"] == "NCID_1_123456789_130.14.22.107_9001_1604016997_1727487202_0MetA0_S_MegaStore_F_1"
    assert efetch_call_args["params"]["query_key"] == "1"

    assert isinstance(extracted_data, list)
    assert len(extracted_data) == 2  # Based on SAMPLE_EFETCH_XML

    paper1 = extracted_data[0]
    assert paper1["title"] == "A Study on ADHD Interventions."
    assert paper1["authors"] == ["John A. Doe", "Jane B. Smith"]  # Adjusted based on typical ForeName LastName processing
    assert paper1["pmid"] == "30000001"
    assert paper1["doi"] == "10.1000/j.jadhdres.2023.001"
    assert paper1["url"] == "https://pubmed.ncbi.nlm.nih.gov/30000001/"
    assert paper1["abstract"] == "This is an abstract for the first paper on ADHD interventions."
    assert paper1["publication_date"] == "2023 Jan"  # Based on PubDate/Year and PubDate/Month

    paper2 = extracted_data[1]
    assert paper2["title"] == "Exploring Genetic Markers in ADHD."
    assert paper2["authors"] == ["The ADHD Genetics Consortium"]
    assert paper2["pmid"] == "30000002"
    assert paper2["doi"] == "10.1001/ijnd.2023.002"
    assert paper2["url"] == "https://pubmed.ncbi.nlm.nih.gov/30000002/"
    # Abstract with labels, ensure they are concatenated
    assert "BACKGROUND: Background: ADHD has a strong genetic component." in paper2["abstract"]
    assert "OBJECTIVE: To identify new genetic markers." in paper2["abstract"]
    assert "This abstract explores genetic markers for ADHD." in paper2["abstract"]
    assert paper2["publication_date"] == "2023 Feb"


@patch("requests.get")
def test_extract_handles_esearch_api_error(mock_get, adhd_etl_instance):
    mock_response_esearch_error = MagicMock()
    mock_response_esearch_error.status_code = 500
    mock_response_esearch_error.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")

    # Make requests.get return the error response only for the esearch call
    def esearch_error_side_effect(*args, **kwargs):
        if args[0] == ESEARCH_URL:
            return mock_response_esearch_error
        # For other calls (like efetch, though it shouldn't be reached), behave normally or raise error
        mock_response_other = MagicMock()
        mock_response_other.status_code = 404
        return mock_response_other

    mock_get.side_effect = esearch_error_side_effect

    # Patch the logger to check if errors are logged
    with patch.object(adhd_etl_instance.logger, "error") as mock_logger_error:
        extracted_data = adhd_etl_instance.extract()
        assert extracted_data == []
        mock_logger_error.assert_called_once()  # Check that an error was logged
        assert "Error during eSearch request" in mock_logger_error.call_args[0][0]


@patch("requests.get")
def test_extract_handles_efetch_api_error(mock_get, adhd_etl_instance):
    mock_response_efetch_error = MagicMock()
    mock_response_efetch_error.status_code = 500
    mock_response_efetch_error.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")

    def efetch_error_side_effect(*args, **kwargs):
        if args[0] == ESEARCH_URL:  # Successful esearch
            mock_esearch_ok = MagicMock()
            mock_esearch_ok.status_code = 200
            mock_esearch_ok.text = SAMPLE_ESEARCH_XML
            return mock_esearch_ok
        elif args[0] == EFETCH_URL:  # Failed efetch
            return mock_response_efetch_error
        mock_response_other = MagicMock()
        mock_response_other.status_code = 404
        return mock_response_other

    mock_get.side_effect = efetch_error_side_effect

    with patch.object(adhd_etl_instance.logger, "error") as mock_logger_error:
        extracted_data = adhd_etl_instance.extract()
        assert extracted_data == []
        mock_logger_error.assert_called_once()
        assert "Error during eFetch request" in mock_logger_error.call_args[0][0]


@patch("requests.get")
def test_extract_handles_empty_pmids_from_esearch(mock_get, adhd_etl_instance):
    SAMPLE_ESEARCH_XML_NO_PMIDS = """<?xml version="1.0" encoding="UTF-8" ?>
    <eSearchResult>
        <Count>0</Count>
        <RetMax>0</RetMax>
        <RetStart>0</RetStart>
        <QueryKey>1</QueryKey>
        <WebEnv>WEBENV_NO_PMIDS</WebEnv>
        <IdList/>
    </eSearchResult>
    """

    def no_pmids_side_effect(*args, **kwargs):
        if args[0] == ESEARCH_URL:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_ESEARCH_XML_NO_PMIDS
            return mock_response
        # Should not reach efetch
        mock_response_other = MagicMock()
        mock_response_other.status_code = 404
        return mock_response_other

    mock_get.side_effect = no_pmids_side_effect

    with patch.object(adhd_etl_instance.logger, "warning") as mock_logger_warning:
        extracted_data = adhd_etl_instance.extract()
        assert extracted_data == []
        mock_logger_warning.assert_called_once()
        assert "No PMIDs found or WebEnv/QueryKey missing" in mock_logger_warning.call_args[0][0]
        # Ensure efetch was not called
        efetch_calls = [call for call in mock_get.call_args_list if call[0][0] == EFETCH_URL]
        assert len(efetch_calls) == 0


# Import requests for the HTTPError exception
import requests


# Test for parsing errors during eSearch
@patch("requests.get")
@patch("xml.etree.ElementTree.fromstring")
def test_extract_handles_esearch_xml_parse_error(mock_fromstring, mock_get, adhd_etl_instance):
    mock_esearch_response = MagicMock()
    mock_esearch_response.status_code = 200
    mock_esearch_response.content = b"<malformed_xml>"
    mock_get.return_value = mock_esearch_response

    with patch.object(adhd_etl_instance.logger, "error") as mock_logger_error:
        extracted_data = adhd_etl_instance.extract()
        assert extracted_data == []
        mock_logger_error.assert_called_once()
        assert "Error parsing eSearch XML response" in mock_logger_error.call_args[0][0]


# Test for parsing errors during eFetch
@patch("requests.get")
@patch("xml.etree.ElementTree.fromstring")
def test_extract_handles_efetch_xml_parse_error(mock_fromstring, mock_get, adhd_etl_instance):
    # This needs two different behaviors for fromstring: success for esearch, failure for efetch
    # And two different behaviors for requests.get: success for esearch, success for efetch (content-wise)

    # First call to fromstring (esearch) should succeed
    esearch_root_mock = ET.Element("eSearchResult")
    id_list_mock = ET.SubElement(esearch_root_mock, "IdList")
    ET.SubElement(id_list_mock, "Id").text = "12345"

    # Set up side effects
    # mock_fromstring will be called twice. First for esearch, then for efetch.
    mock_fromstring.side_effect = [
        esearch_root_mock,  # Successful parse for esearch
        ET.ParseError("Malformed eFetch XML"),  # Failed parse for efetch
    ]

    # requests.get will also be called twice.
    mock_esearch_response = MagicMock()
    mock_esearch_response.status_code = 200

    mock_efetch_response = MagicMock()
    mock_efetch_response.status_code = 200
    mock_efetch_response.content = b"<malformed_efetch_xml>"  # Content for efetch

    with patch.object(adhd_etl_instance.logger, "error") as mock_logger_error:
        extracted_data = adhd_etl_instance.extract()
        assert extracted_data == []
        mock_logger_error.assert_called_once()
        assert "Error parsing eFetch XML response" in mock_logger_error.call_args[0][0]


# --- Tests for transform method ---


@pytest.fixture()
def sample_raw_papers_data():
    return [
        {
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345/"
            # 'source' is added by transform, not expected in raw data from extract
        },
        {"url": "https://pubmed.ncbi.nlm.nih.gov/67890/"},
        {  # Paper with minimal required data by Pydantic model (title, authors, source)
            # 'source' will be added by transform
            # 'abstract', 'doi', 'journal_title' are optional in Pydantic model or not directly used
        },
    ]


def test_transform_maps_data_correctly(adhd_etl_instance, sample_raw_papers_data):
    transformed_papers = adhd_etl_instance.transform(sample_raw_papers_data)

    assert isinstance(transformed_papers, list)
    assert len(transformed_papers) == len(sample_raw_papers_data)

    for i, transformed_paper in enumerate(transformed_papers):
        assert isinstance(transformed_paper, ADHDPublication)
        raw_item = sample_raw_papers_data[i]

        assert transformed_paper.title == raw_item["title"]
        assert transformed_paper.authors == raw_item["authors"]
        assert transformed_paper.publication_date == raw_item.get("publication_date")
        assert transformed_paper.abstract == raw_item.get("abstract")
        assert transformed_paper.doi == raw_item.get("doi")
        assert transformed_paper.url == raw_item["url"]
        assert transformed_paper.source == "PubMed"  # This is set by transform


def test_transform_handles_empty_input(adhd_etl_instance):
    transformed_papers = adhd_etl_instance.transform([])
    assert transformed_papers == []


def test_transform_handles_missing_critical_fields(adhd_etl_instance, caplog):
    # 'title' is a required field in ADHDPublication Pydantic model

    # To capture logs from adhd_etl_instance.logger specifically:
    # Method 1: Patch the logger on the instance if it's already configured
    # with patch.object(adhd_etl_instance.logger, 'error') as mock_logger_error:
    #     transformed_papers = adhd_etl_instance.transform(malformed_data)
    #     assert mock_logger_error.call_count >= 1 # At least one error for the missing title

    # Method 2: Use pytest's caplog fixture (simpler if logger is standard logging)
    # This requires the logger used in the ETL to propagate to root or be captured by pytest.
    # BaseETL's logger is named after the class, so it should be captured by caplog.

    import logging  # Required for caplog to work with named loggers

    caplog.set_level(logging.ERROR, logger="ADHDPublicationETL")  # Ensure we capture errors from this logger

    transformed_papers = adhd_etl_instance.transform(malformed_data)

    # Assertions
    # One valid paper should pass through
    assert len(transformed_papers) == 1
    assert transformed_papers[0].title == "Valid Title"

    # Check that errors were logged for the malformed items
    assert len(caplog.records) >= 2  # Two items should have caused errors

    # Check details of logged messages (optional, but good for specific error types)
    # Pydantic's ValidationError will be caught by the generic Exception in transform
    error_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]

    missing_title_error_found = any("Error transforming article titled 'None'" in msg or "Error transforming article titled 'Title with no authors'" in msg for msg in error_messages)
    assert missing_title_error_found, "Expected error for missing title or authors not logged"

    # More specific check if Pydantic's error details are in the log message
    # Example: if Pydantic's error message like "title_field\n  field required" is logged:
    # assert any("title" in record.message.lower() and "required" in record.message.lower() for record in caplog.records if record.levelname == "ERROR")
    # assert any("authors" in record.message.lower() and "required" in record.message.lower() for record in caplog.records if record.levelname == "ERROR")
    # The current generic exception logging in `transform` might not include Pydantic's detailed field info directly in the logged message.
    # It logs f"Error transforming article titled '{paper_data.get('title')}': {e}"
    # So, for the missing title, paper_data.get('title') would be None.
    # For missing authors, the title exists.

    # Check for the missing title error specifically
    assert any("Error transforming article titled 'None'" in msg for msg in error_messages)
    # Check for the missing authors error
    assert any("Error transforming article titled 'Title with no authors'" in msg for msg in error_messages)


# --- Tests for load method ---


@pytest.fixture()
def sample_transformed_papers_data():
    return [
        ADHDPublication(
            title="Test Title 1 Loaded",
            authors=["Author X", "Author Y"],
            publication_date="2023 Mar 10",
            abstract="Abstract for loaded paper 1.",
            doi="10.load/test.1",
            url="https://pubmed.ncbi.nlm.nih.gov/load1",
            source="PubMed",
        ),
        ADHDPublication(
            title="Test Title 2 Loaded: Minimal",
            authors=["Author Z"],
            publication_date="2022",
            abstract=None,  # Optional
            doi=None,  # Optional
            url="https://pubmed.ncbi.nlm.nih.gov/load2",
            source="PubMed",
        ),
    ]


@patch("os.makedirs")  # Mock makedirs as it's called inside load
@patch("builtins.open", new_callable=mock_open)
@patch("pandas.DataFrame.to_csv")
def test_load_saves_json_and_csv_correctly(mock_df_to_csv, mock_file_open, mock_os_makedirs, adhd_etl_instance, sample_transformed_papers_data, tmp_path, caplog):
    adhd_etl_instance.output_dir = str(tmp_path)  # Redirect output for this test

    caplog.set_level(logging.INFO)  # Capture info logs for success messages

    adhd_etl_instance.load(sample_transformed_papers_data)

    # Verify directory creation calls
    json_dir = tmp_path / "json"
    csv_dir = tmp_path / "csv"
    mock_os_makedirs.assert_any_call(json_dir, exist_ok=True)
    mock_os_makedirs.assert_any_call(csv_dir, exist_ok=True)

    # Expected data for json.dump
    expected_papers_dict_list = [paper.model_dump() for paper in sample_transformed_papers_data]

    # JSON Assertions
    # mock_open().write calls are what json.dump eventually calls.
    # We need to check call_args for the paths.
    # Two calls for JSON: timestamped and latest
    json_open_calls = [call for call in mock_file_open.call_args_list if call[0][0].endswith(".json")]
    assert len(json_open_calls) == 2

    # Check that one call is for 'latest_papers.json' and another for a timestamped file
    # The exact timestamp is hard to predict, so check for structure.
    assert any(str(json_dir / "latest_papers.json") in call[0][0] for call in json_open_calls)
    assert any(str(json_dir / "papers_") in call[0][0] and ".json" in call[0][0] and "latest" not in call[0][0] for call in json_open_calls)

    # Verify content written to JSON (mock_open().write() is called by json.dump)
    # This gets a bit tricky with mock_open. We can check the *first* write call's content.
    # Assuming the first JSON file written is the timestamped one or latest.
    # json.dump(data, file_handle, ...)
    # The file_handle is m_open(), so m_open().write was called with json string.
    # This requires inspecting what was passed to `json.dump` rather than `write`.
    # A simpler way is to check the content written, if mock_open allows reading it back,
    # or by checking the arguments to `json.dump` if we patch `json.dump` itself.

    # For simplicity with mock_open, let's focus on the calls and paths.
    # To check content, we would typically patch json.dump:
    # @patch('json.dump')
    # def test_load_saves_json_and_csv_correctly(mock_json_dump, ...):
    #    ...
    #    mock_json_dump.assert_any_call(expected_papers_dict_list, mock_file_open.return_value, ...)
    # For now, checking paths and call counts for open is sufficient given the toolset.

    # CSV Assertions
    assert mock_df_to_csv.call_count == 2

    # Check paths for CSV
    csv_paths_called = [call[0][0] for call in mock_df_to_csv.call_args_list]
    assert any(str(csv_dir / "latest_papers.csv") in path for path in csv_paths_called)
    assert any(str(csv_dir / "papers_") in path and ".csv" in path and "latest" not in path for path in csv_paths_called)

    # Check kwargs for to_csv
    for call_args in mock_df_to_csv.call_args_list:
        assert call_args[1]["index"] is False  # index=False

    # Check DataFrame content (first argument to to_csv is the DataFrame instance)
    # df_arg = mock_df_to_csv.call_args_list[0][0][0] # This is the DataFrame instance
    # pd.testing.assert_frame_equal(df_arg, pd.DataFrame(expected_papers_dict_list))
    # This comparison can be tricky if 'authors' list is not handled identically by direct DataFrame creation.
    # The load method converts authors list to string: df['authors'].apply(lambda x: ', '.join(x)...)
    # So, we'd need to replicate that for expected_df.

    # Log assertions
    assert "Successfully saved" in caplog.text  # General check for success logs
    assert "papers to" in caplog.text
    assert "latest_papers.json" in caplog.text
    assert "latest_papers.csv" in caplog.text
    assert "Load process completed for 2 papers" in caplog.text


@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
@patch("pandas.DataFrame.to_csv")
def test_load_handles_empty_input(mock_df_to_csv, mock_file_open, mock_os_makedirs, adhd_etl_instance, tmp_path, caplog):
    adhd_etl_instance.output_dir = str(tmp_path)
    caplog.set_level(logging.WARNING)

    adhd_etl_instance.load([])

    mock_os_makedirs.assert_not_called()  # Should not attempt to create dirs if no data
    mock_file_open.assert_not_called()
    mock_df_to_csv.assert_not_called()

    assert "No data provided to load method." in caplog.text


# This test does not mock os.makedirs to verify its actual behavior
@patch("builtins.open", new_callable=mock_open)  # Mock file operations to prevent actual writes
@patch("pandas.DataFrame.to_csv")  # Mock csv writing
def test_load_creates_output_directories(mock_df_to_csv, mock_file_open, adhd_etl_instance, sample_transformed_papers_data, tmp_path):
    adhd_etl_instance.output_dir = str(tmp_path)

    json_dir = tmp_path / "json"
    csv_dir = tmp_path / "csv"

    assert os.path.exists(json_dir), "JSON directory was not created"
    assert os.path.isdir(json_dir), "JSON path is not a directory"
    assert os.path.exists(csv_dir), "CSV directory was not created"
    assert os.path.isdir(csv_dir), "CSV path is not a directory"


# --- Tests for run method ---


@patch.object(ADHDPublicationETL, "load")
@patch.object(ADHDPublicationETL, "transform")
@patch.object(ADHDPublicationETL, "extract")
def test_run_calls_extract_transform_load_in_order(m_extract, m_transform, m_load, adhd_etl_instance, caplog):
    caplog.set_level(logging.INFO)

    mock_extracted_data = [{"pmid": "1", "title": "Raw Paper", "authors": ["Auth"], "url": "url1", "source": "PubMed"}]
    # ADHDPublication needs title, authors, source, url at minimum if other fields are None by default
    mock_transformed_data = [ADHDPublication(title="Transformed Paper", authors=["Author"], source="PubMed", url="http://example.com/1", pmid="1")]

    m_extract.return_value = mock_extracted_data
    m_transform.return_value = mock_transformed_data

    adhd_etl_instance.run()

    m_extract.assert_called_once()
    m_transform.assert_called_once_with(mock_extracted_data)
    m_load.assert_called_once_with(mock_transformed_data)

    assert f"ETL pipeline: {adhd_etl_instance.name} completed successfully." in caplog.text
    assert f"Starting ETL pipeline: {adhd_etl_instance.name}" in caplog.text


@patch.object(ADHDPublicationETL, "load")
@patch.object(ADHDPublicationETL, "transform")
@patch.object(ADHDPublicationETL, "extract", return_value=[])  # Mock extract to return empty list
def test_run_handles_empty_extract_output(m_extract, m_transform, m_load, adhd_etl_instance, caplog):
    caplog.set_level(logging.WARNING)

    adhd_etl_instance.run()

    m_extract.assert_called_once()
    m_transform.assert_not_called()
    m_load.assert_not_called()

    assert "Extraction yielded no data. Skipping transform and load." in caplog.text


@patch.object(ADHDPublicationETL, "load")
@patch.object(ADHDPublicationETL, "transform", return_value=[])  # Mock transform to return empty list
@patch.object(ADHDPublicationETL, "extract")
def test_run_handles_empty_transform_output(m_extract, m_transform, m_load, adhd_etl_instance, caplog):
    caplog.set_level(logging.WARNING)

    # Need extract to return non-empty, so transform is called
    mock_extracted_data = [{"pmid": "1", "title": "Raw Paper", "authors": ["Auth"], "url": "url1", "source": "PubMed"}]
    m_extract.return_value = mock_extracted_data

    adhd_etl_instance.run()

    m_extract.assert_called_once()
    m_transform.assert_called_once_with(mock_extracted_data)
    m_load.assert_not_called()

    assert "Transformation yielded no data. Skipping load." in caplog.text


@patch.object(ADHDPublicationETL, "load")
@patch.object(ADHDPublicationETL, "transform")
@patch.object(ADHDPublicationETL, "extract", side_effect=Exception("Big Extractor Boom"))  # Mock extract to raise exception
def test_run_handles_general_exception_during_extract(m_extract, m_transform, m_load, adhd_etl_instance, caplog):
    caplog.set_level(logging.ERROR)

    adhd_etl_instance.run()

    m_extract.assert_called_once()
    m_transform.assert_not_called()
    m_load.assert_not_called()

    assert f"Error during ETL pipeline: {adhd_etl_instance.name}: Big Extractor Boom" in caplog.text


@patch.object(ADHDPublicationETL, "load")
@patch.object(ADHDPublicationETL, "transform", side_effect=Exception("Transform Failure"))  # Mock transform to raise exception
@patch.object(ADHDPublicationETL, "extract")
def test_run_handles_general_exception_during_transform(m_extract, m_transform, m_load, adhd_etl_instance, caplog):
    caplog.set_level(logging.ERROR)

    mock_extracted_data = [{"pmid": "1", "title": "Raw Paper", "authors": ["Auth"], "url": "url1", "source": "PubMed"}]
    m_extract.return_value = mock_extracted_data  # Extract succeeds

    adhd_etl_instance.run()

    m_extract.assert_called_once()
    m_transform.assert_called_once_with(mock_extracted_data)
    m_load.assert_not_called()

    assert f"Error during ETL pipeline: {adhd_etl_instance.name}: Transform Failure" in caplog.text


@patch.object(ADHDPublicationETL, "load", side_effect=Exception("Load Exploded"))  # Mock load to raise exception
@patch.object(ADHDPublicationETL, "transform")
@patch.object(ADHDPublicationETL, "extract")
def test_run_handles_general_exception_during_load(m_extract, m_transform, m_load, adhd_etl_instance, caplog):
    caplog.set_level(logging.ERROR)

    mock_extracted_data = [{"pmid": "1", "title": "Raw Paper", "authors": ["Auth"], "url": "url1", "source": "PubMed"}]
    mock_transformed_data = [ADHDPublication(title="Transformed Paper", authors=["Author"], source="PubMed", url="http://example.com/1", pmid="1")]

    m_extract.return_value = mock_extracted_data
    m_transform.return_value = mock_transformed_data  # Transform succeeds

    adhd_etl_instance.run()

    m_extract.assert_called_once()
    m_transform.assert_called_once_with(mock_extracted_data)
    m_load.assert_called_once_with(mock_transformed_data)

    assert f"Error during ETL pipeline: {adhd_etl_instance.name}: Load Exploded" in caplog.text
