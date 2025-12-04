import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

# Add project root to sys.path
try:
    from src.web.fullstreamlit.components import museums_tab
except ImportError:
    # Placeholder if direct import fails (e.g., in a restricted environment)
    class MuseumsTabModuleMock:
        def render(self, logger, museum_data):
            logger.info("Mocked museums_tab.render called")
            if museum_data.empty:
                # Simulate st.info call for empty data
                # In a real test with mocks, we'd check if st.info was called
                pass

    museums_tab = MuseumsTabModuleMock()

# Sample DataFrame for testing
SAMPLE_MUSEUM_DF = pd.DataFrame(
    [
        {
            "name": "Museum 1",
            "description": "Desc 1",
            "country_label": "Artland",
            "main_subject_label": "Art",
            "image_url": "http://example.com/1.jpg",
            "website_url": "http://example.com/1",
            "virtual_tour_url": "http://example.com/tour1",
        },
        {"name": "Museum 2", "description": "Desc 2", "country_label": "Histland", "main_subject_label": "History", "image_url": None, "website_url": "http://example.com/2", "virtual_tour_url": None},
        {
            "name": "Museum 3",
            "description": "Desc 3",
            "country_label": "Artland",
            "main_subject_label": "Science",
            "image_url": "http://example.com/3.jpg",
            "website_url": "http://example.com/3",
            "virtual_tour_url": "http://example.com/tour3",
        },
    ]
)

STREAMLIT_PATCH_MODULES = [
    "streamlit.title",
    "streamlit.header",
    "streamlit.subheader",
    "streamlit.text_input",
    "streamlit.selectbox",
    "streamlit.image",
    "streamlit.metric",
    "streamlit.warning",
    "streamlit.info",
    "streamlit.container",
    "streamlit.markdown",
    "streamlit.caption",
]


class TestMuseumsTab(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        # Apply patches for all common Streamlit functions
        self.patchers = []
        self.mock_objects = {}
        for module_path in STREAMLIT_PATCH_MODULES:
            patcher = patch(module_path, MagicMock())
            self.patchers.append(patcher)

        # Specific mock for st.columns to return a list of MagicMock objects (columns)
        self.mock_objects["columns"].return_value = [MagicMock(), MagicMock(), MagicMock()]
        # Specific mock for st.expander to allow 'with' statement
        expander_mock = MagicMock()
        expander_mock.__enter__ = MagicMock(return_value=None)
        expander_mock.__exit__ = MagicMock(return_value=None)
        self.mock_objects["expander"].return_value = expander_mock
        # Specific mock for st.container
        container_mock = MagicMock()
        container_mock.__enter__ = MagicMock(return_value=None)
        container_mock.__exit__ = MagicMock(return_value=None)
        self.mock_objects["container"].return_value = container_mock

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()

    def test_render_empty_data(self):
        """Test rendering when no museum data is provided."""
        empty_df = pd.DataFrame(columns=SAMPLE_MUSEUM_DF.columns)
        museums_tab.render(self.mock_logger, empty_df)

        self.mock_objects["title"].assert_called_once_with("🏛️ Directorio de Museos Virtuales")
        self.mock_objects["info"].assert_called_once_with("No hay datos de museos virtuales disponibles en este momento.")
        self.mock_logger.info.assert_any_call("Render de museos: No hay datos disponibles.")

    def test_render_with_data(self):
        """Test rendering with sample museum data."""
        # Simulate user inputs for filters - default "Todos" and empty search
        self.mock_objects["text_input"].return_value = ""  # Empty search query
        # The selectbox mock needs to handle being called multiple times and return different values if needed
        # For default behavior (index 0 -> "Todos"), this is okay.
        self.mock_objects["selectbox"].return_value = "Todos"

        self.mock_objects["title"].assert_called_once_with("🏛️ Directorio de Museos Virtuales")
        self.mock_logger.info.assert_any_call(f"Renderizando datos de {len(SAMPLE_MUSEUM_DF)} museos virtuales.")

        self.mock_objects["header"].assert_called_once_with("Filtros para Museos")
        self.mock_objects["text_input"].assert_called_once_with("Buscar por nombre o descripción", key="museum_search")

        # Check selectbox calls (country and subject)
        self.assertEqual(self.mock_objects["selectbox"].call_count, 2)
        # Example: Check one of the selectbox calls more specifically if needed
        # self.mock_objects['selectbox'].assert_any_call("Filtrar por País", ["Todos", "Artland", "Histland"], index=0, key="museum_country_filter")

        self.mock_objects["metric"].assert_called_once_with("Total de Museos Encontrados", len(SAMPLE_MUSEUM_DF))

        # Check if subheader was called for each museum name
        self.assertEqual(self.mock_objects["subheader"].call_count, len(SAMPLE_MUSEUM_DF))
        for name in SAMPLE_MUSEUM_DF["name"]:
            self.mock_objects["subheader"].assert_any_call(name)

        # Check if image was called for museums with image_url
        num_images = SAMPLE_MUSEUM_DF["image_url"].notna().sum()
        self.assertEqual(self.mock_objects["image"].call_count, num_images)
        if num_images > 0:
            self.mock_objects["image"].assert_any_call(SAMPLE_MUSEUM_DF["image_url"].dropna().iloc[0], use_column_width="always")

        # Check that expander was called for each item
        self.assertEqual(self.mock_objects["expander"].call_count, len(SAMPLE_MUSEUM_DF))

    def test_render_with_search_filter_no_results(self):
        """Test rendering when filters result in no matches."""
        self.mock_objects["text_input"].return_value = "NonExistentQuery123"  # Search query that won't match
        self.mock_objects["selectbox"].return_value = "Todos"  # Default for dropdowns

        self.mock_objects["title"].assert_called_once_with("🏛️ Directorio de Museos Virtuales")
        self.mock_objects["metric"].assert_called_once_with("Total de Museos Encontrados", 0)
        self.mock_objects["warning"].assert_called_once_with("No se encontraron museos que coincidan con los filtros aplicados.")

        # Ensure subheader (for displaying items) was not called
        self.mock_objects["subheader"].assert_not_called()

    def test_render_with_country_filter(self):
        """Test filtering by country."""
        self.mock_objects["text_input"].return_value = ""

        # Simulate selecting 'Artland' for country, 'Todos' for subject
        def selectbox_side_effect(*args, **kwargs):
            if kwargs.get("key") == "museum_country_filter":
                return "Artland"
            if kwargs.get("key") == "museum_subject_filter":
                return "Todos"
            return "Todos"  # Default

        expected_count = len(SAMPLE_MUSEUM_DF[SAMPLE_MUSEUM_DF["country_label"] == "Artland"])
        self.mock_objects["metric"].assert_called_once_with("Total de Museos Encontrados", expected_count)
        self.assertEqual(self.mock_objects["subheader"].call_count, expected_count)


if __name__ == "__main__":
    # Ensure streamlit is globally available for the patched tests
    unittest.main()
