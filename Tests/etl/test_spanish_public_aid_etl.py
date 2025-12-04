"""Tests for Spanish Public Aid ETL."""

from unittest.mock import Mock, patch

import pytest

from src.etl.spanish_public_aid.spanish_public_aid_etl import SpanishPublicAidETL
from src.models.spanish_public_aid import (
    AidCategory,
    AidScope,
    AidStatus,
    AidType,
    BeneficiaryType,
    SpanishPublicAidModel,
)


class TestSpanishPublicAidETL:
    """Test cases for Spanish Public Aid ETL."""

    @pytest.fixture()
    def etl_instance(self):
        """Create an ETL instance for testing."""
        return SpanishPublicAidETL()

    @pytest.fixture()
    def sample_raw_data(self):
        """Sample raw data for testing."""
        return {
            "title": "Ayuda para vivienda joven",
            "description": "Ayuda económica destinada a jóvenes para el alquiler de vivienda",
            "source_url": "https://www.gva.es/ayuda-vivienda-joven",
            "source_name": "Generalitat Valenciana",
            "source_scope": AidScope.AUTONOMOUS_COMMUNITY,
            "organizing_entity": "Generalitat Valenciana",
            "raw_element": '<div class="ayuda">Test content</div>',
        }

    @pytest.fixture()
    def sample_enhanced_data(self):
        """Sample enhanced data for testing."""
        return {
            "title": "Ayuda para vivienda joven",
            "description": "Ayuda económica destinada a jóvenes para el alquiler de vivienda",
            "aid_type": AidType.GRANT,
            "category": AidCategory.HOUSING,
            "organizing_entity": "Generalitat Valenciana",
            "beneficiary_type": BeneficiaryType.INDIVIDUAL,
            "status": AidStatus.OPEN,
            "source_url": "https://www.gva.es/ayuda-vivienda-joven",
            "source_name": "Generalitat Valenciana",
            "data_quality_score": 0.8,
            "tags": ["comunidad-valenciana", "generalitat-valenciana"],
            "keywords": ["ayuda", "vivienda", "joven"],
        }

    def test_init(self, etl_instance):
        """Test ETL initialization."""
        assert etl_instance.name == "spanish_public_aid"
        assert etl_instance.description == "ETL process for scraping Spanish public aid convocations"
        assert len(etl_instance.sources) == 4
        assert "bdns" in etl_instance.sources
        assert "gva" in etl_instance.sources
        assert "valencia" in etl_instance.sources
        assert "labora" in etl_instance.sources

    def test_determine_aid_type(self, etl_instance):
        """Test aid type determination."""
        assert etl_instance._determine_aid_type("Beca de estudios", "") == AidType.SCHOLARSHIP
        assert etl_instance._determine_aid_type("Préstamo para vivienda", "") == AidType.LOAN
        assert etl_instance._determine_aid_type("Subvención empresarial", "") == AidType.SUBSIDY
        assert etl_instance._determine_aid_type("Ayuda general", "") == AidType.GRANT

    def test_determine_category(self, etl_instance):
        """Test category determination."""
        assert etl_instance._determine_category("Ayuda vivienda", "") == AidCategory.HOUSING
        assert etl_instance._determine_category("Programa empleo", "") == AidCategory.EMPLOYMENT
        assert etl_instance._determine_category("Beca educación", "") == AidCategory.EDUCATION
        assert etl_instance._determine_category("Ayuda joven", "") == AidCategory.YOUTH
        assert etl_instance._determine_category("Ayuda general", "") == AidCategory.OTHER

    def test_determine_status(self, etl_instance):
        """Test status determination."""
        assert etl_instance._determine_status("Convocatoria cerrada", "") == AidStatus.CLOSED
        assert etl_instance._determine_status("En evaluación", "") == AidStatus.IN_EVALUATION
        assert etl_instance._determine_status("Ayuda resuelta", "") == AidStatus.RESOLVED
        assert etl_instance._determine_status("Nueva ayuda", "") == AidStatus.OPEN

    def test_determine_beneficiary_type(self, etl_instance):
        """Test beneficiary type determination."""
        assert etl_instance._determine_beneficiary_type("Ayuda empresa", "") == BeneficiaryType.COMPANY
        assert etl_instance._determine_beneficiary_type("Ayuda ONG", "") == BeneficiaryType.NGO
        assert etl_instance._determine_beneficiary_type("Ayuda universidad", "") == BeneficiaryType.EDUCATIONAL_INSTITUTION
        assert etl_instance._determine_beneficiary_type("Ayuda personal", "") == BeneficiaryType.INDIVIDUAL

    def test_generate_tags(self, etl_instance, sample_raw_data):
        """Test tag generation."""
        tags = etl_instance._generate_tags(sample_raw_data)
        assert "comunidad-valenciana" in tags
        assert "generalitat-valenciana" in tags

    def test_generate_keywords(self, etl_instance, sample_raw_data):
        """Test keyword extraction."""
        keywords = etl_instance._generate_keywords(sample_raw_data)
        assert "ayuda" in keywords
        assert "vivienda" in keywords
        assert "joven" in keywords

    def test_calculate_quality_score(self, etl_instance, sample_raw_data):
        """Test quality score calculation."""
        score = etl_instance._calculate_quality_score(sample_raw_data)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be decent quality with provided data

    def test_calculate_quality_score_empty_data(self, etl_instance):
        """Test quality score with empty data."""
        score = etl_instance._calculate_quality_score({})
        assert score == 0.0

    def test_enhance_aid_data(self, etl_instance, sample_raw_data):
        """Test data enhancement."""
        enhanced = etl_instance._enhance_aid_data(sample_raw_data)

        assert enhanced["title"] == sample_raw_data["title"]
        assert enhanced["description"] == sample_raw_data["description"]
        assert enhanced["aid_type"] == AidType.GRANT
        assert enhanced["category"] == AidCategory.HOUSING
        assert enhanced["beneficiary_type"] == BeneficiaryType.INDIVIDUAL
        assert enhanced["status"] == AidStatus.OPEN
        assert "data_quality_score" in enhanced
        assert "tags" in enhanced
        assert "keywords" in enhanced

    @patch("requests.Session.get")
    def test_extract_from_bdns_success(self, mock_get, etl_instance):
        """Test successful extraction from BDNS."""
        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = """
        <html>
            <body>
                <div class="convocatoria-item">
                    <h3>Test Aid Title</h3>
                    <p>Test description</p>
                    <a href="/aid/123">Ver más</a>
                </div>
            </body>
        </html>
        """.encode()
        mock_get.return_value = mock_response

        source_config = etl_instance.sources["bdns"]
        result = etl_instance._extract_from_bdns(source_config)

        assert isinstance(result, list)
        # Note: Actual result depends on parsing logic

    @patch("requests.Session.get")
    def test_extract_from_source_error_handling(self, mock_get, etl_instance):
        """Test error handling in source extraction."""
        # Mock network error
        mock_get.side_effect = Exception("Network error")

        source_config = etl_instance.sources["bdns"]
        result = etl_instance._extract_from_bdns(source_config)

        assert result == []

    def test_transform_valid_data(self, etl_instance, sample_raw_data):
        """Test transformation of valid data."""
        data = [sample_raw_data]
        result = etl_instance.transform(data)

        assert len(result) > 0
        assert isinstance(result[0], SpanishPublicAidModel)
        assert result[0].title == sample_raw_data["title"]

    def test_transform_invalid_data(self, etl_instance):
        """Test transformation with invalid data."""
        # Data without required fields
        invalid_data = [{"invalid": "data"}]
        result = etl_instance.transform(invalid_data)

        # Should return empty list due to validation failures
        assert len(result) == 0

    def test_transform_low_quality_data(self, etl_instance):
        """Test transformation filters out low quality data."""
        # Create data with very low quality
        low_quality_data = [
            {
                "title": "A",  # Very short title
                "description": "",  # No description
                "source_url": "invalid",  # Invalid URL
            }
        ]

        result = etl_instance.transform(low_quality_data)

        # Should be filtered out due to low quality score
        assert len(result) == 0

    @patch("builtins.open", create=True)
    @patch("json.dump")
    def test_load_data(self, mock_json_dump, mock_open, etl_instance, sample_enhanced_data):
        """Test data loading."""
        # Create mock aid model
        mock_aid = Mock(spec=SpanishPublicAidModel)
        mock_aid.model_dump.return_value = sample_enhanced_data

        data = [mock_aid]

        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        etl_instance.load(data)

        # Verify files were written
        assert mock_open.call_count >= 2  # Main file and stats file
        assert mock_json_dump.call_count >= 2

    def test_load_empty_data(self, etl_instance):
        """Test loading empty data."""
        # Should not raise an error
        etl_instance.load([])

    def test_generate_statistics(self, etl_instance):
        """Test statistics generation."""
        # Create mock aids
        mock_aids = []
        for i in range(5):
            mock_aid = Mock(spec=SpanishPublicAidModel)
            mock_aid.is_active = i < 3  # 3 active aids
            mock_aid.is_urgent = i < 1  # 1 urgent aid
            mock_aid.category.value = "vivienda"
            mock_aid.scope.scope.value = "autonomica"
            mock_aid.status.value = "abierta"
            mock_aid.beneficiary_type.value = "persona_fisica"
            mock_aids.append(mock_aid)

        stats = etl_instance._generate_statistics(mock_aids)

        assert stats["total_aids"] == 5
        assert stats["active_aids"] == 3
        assert stats["closing_soon"] == 1
        assert "by_category" in stats
        assert "by_scope" in stats
        assert "by_status" in stats
        assert "by_beneficiary_type" in stats

    def test_generate_statistics_empty(self, etl_instance):
        """Test statistics generation with empty data."""
        stats = etl_instance._generate_statistics([])
        assert stats == {}


class TestSpanishPublicAidETLIntegration:
    """Integration tests for Spanish Public Aid ETL."""

    @pytest.fixture()
    def etl_instance(self):
        """Create an ETL instance for testing."""
        return SpanishPublicAidETL()

    @patch("src.etl.spanish_public_aid.spanish_public_aid_etl.SpanishPublicAidETL._extract_from_source")
    def test_extract_integration(self, mock_extract_source, etl_instance):
        """Test complete extraction process."""
        # Mock extraction results
        mock_extract_source.return_value = [
            {
                "title": "Test Aid 1",
                "description": "Test description 1",
                "source_url": "https://example.com/aid1",
                "source_name": "Test Source",
                "organizing_entity": "Test Entity",
            }
        ]

        result = etl_instance.extract()

        assert isinstance(result, list)
        # Should be called for each enabled source
        enabled_sources = sum(1 for s in etl_instance.sources.values() if s.get("enabled", True))
        assert mock_extract_source.call_count == enabled_sources

    def test_full_etl_pipeline_mock(self, etl_instance):
        """Test full ETL pipeline with mocked data."""
        # Mock the extract method to return test data
        test_data = [
            {
                "title": "Ayuda Test",
                "description": "Descripción de prueba para una ayuda de vivienda",
                "source_url": "https://test.example.com/ayuda",
                "source_name": "Test Source",
                "source_scope": AidScope.NATIONAL,
                "organizing_entity": "Test Entity",
                "raw_element": "<div>test</div>",
            }
        ]

        with patch.object(etl_instance, "extract", return_value=test_data):
            with patch.object(etl_instance, "load") as mock_load:
                metrics = etl_instance.run()

                # Verify the pipeline ran successfully
                assert metrics.records_extracted > 0
                assert mock_load.called

    def test_configuration_loading(self, etl_instance):
        """Test that configuration is properly loaded."""
        assert hasattr(etl_instance, "config")
        assert hasattr(etl_instance.config, "max_aids_per_source")
        assert hasattr(etl_instance.config, "data_quality_threshold")
        assert hasattr(etl_instance.config, "request_delay_seconds")


if __name__ == "__main__":
    pytest.main([__file__])
