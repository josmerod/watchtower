"""The ``/docs`` page is documentation that ships inside the dashboard.

These tests keep it from rotting: the page must render, and every route, query
parameter and ``source`` key it advertises must exist in the FastAPI app.
Fixtures only (no network, no ``data/`` files).
"""

import re
from urllib.parse import parse_qs, urlsplit

import pytest

from src.api.main import app as api_app
from src.services.data_loader import BENCHMARKS_SOURCES_CONFIG, GAMES_SOURCES_CONFIG, KNOWLEDGE_SOURCES_CONFIG, NEWS_SOURCES_CONFIG
from src.web.dashboard.app import WATCHTOWER_DOCS_HTML
from src.web.dashboard.app import app as dashboard_app

API_BASE = "https://watchtower-api.josmerod.es"

# Categories whose feed the docs filter with ``?source=``, mapped to the config the API reads.
CATEGORY_SOURCES = {
    "news": NEWS_SOURCES_CONFIG,
    "knowledge-garden": KNOWLEDGE_SOURCES_CONFIG,
    "games": GAMES_SOURCES_CONFIG,
    "benchmarks": BENCHMARKS_SOURCES_CONFIG,
}


def _api_routes():
    """Return ``{path: {query parameter name}}`` for every operation in the OpenAPI schema."""
    return {path: {param["name"] for param in operation["get"].get("parameters", []) if param["in"] == "query"} for path, operation in api_app.openapi()["paths"].items()}


def _documented_routes():
    """Return ``{route: [parameter names]}`` as listed in the "Core API routes" table."""
    table = {}
    for row in re.findall(r"<tr>(.*?)</tr>", WATCHTOWER_DOCS_HTML, flags=re.S):
        cells = re.findall(r"<td>(.*?)</td>", row, flags=re.S)
        if len(cells) == 3 and cells[0].startswith("<code>/api/v1/"):
            route = re.search(r"<code>(.*?)</code>", cells[0]).group(1)
            table[route] = re.findall(r"<code>(.*?)</code>", cells[2])
    return table


def _curl_urls():
    """Return the split URLs of the curl examples in the page."""
    blocks = re.findall(r"<pre><code>(.*?)</code></pre>", WATCHTOWER_DOCS_HTML, flags=re.S)
    return [urlsplit(url.replace("&amp;", "&")) for block in blocks if "curl " in block for url in re.findall(rf"{API_BASE}([^\"\s<]+)", block)]


def test_docs_page_renders():
    response = dashboard_app.server.test_client().get("/docs")

    assert response.status_code == 200
    assert "Core API routes" in response.get_data(as_text=True)


def test_table_lists_routes():
    assert _documented_routes()
    assert _curl_urls()


def test_documented_routes_exist():
    api_routes = _api_routes()
    missing = sorted(set(_documented_routes()) - api_routes.keys())

    assert not missing, f"the docs page advertises routes the API does not serve: {missing}"


@pytest.mark.parametrize("route", sorted(_documented_routes()))
def test_documented_parameters_exist(route):
    assert set(_documented_routes()[route]) <= _api_routes().get(route, set())


@pytest.mark.parametrize("url", _curl_urls(), ids=lambda url: url.path + url.query)
def test_curl_examples_are_valid(url):
    if url.path == "/health":
        assert url.path in {route.path for route in api_app.routes}
        return

    parameters = _api_routes().get(url.path)
    assert parameters is not None, f"{url.path} is not an API route"

    query = parse_qs(url.query)
    assert query.keys() <= parameters, f"{url.path} does not accept {sorted(query.keys() - parameters)}"
    if "source" in query:
        assert query["source"][0] in CATEGORY_SOURCES[url.path.removeprefix("/api/v1/")]
