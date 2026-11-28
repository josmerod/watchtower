"""A callback request Dash refuses gets a 204 and one line, not a traceback (T-175).

Production logged four of these as tracebacks: a tab left open across a deploy asks for the callbacks it was
loaded with. The page gets nothing from either answer, so the server answers the way it answers a callback that
has nothing to update, and says in one line what the request asked for. Fixtures only: no data/ is read.
"""

import logging
import os
import pytest

from src.web.dashboard import app as app_module
from src.web.dashboard.app import app as dashboard_app

LOGGER = "src.web.dashboard.app"


def _quiet() -> logging.Logger:
    """A logger that drops what Flask says about a handled error."""
    return logging.getLogger("refused-callback-test")


def _post(body: dict):
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(dashboard_app.server, "logger", _quiet())
        return dashboard_app.server.test_client().post("/_dash-update-component", json=body)


def test_a_callback_this_server_no_longer_has_is_answered_quietly(caplog) -> None:
    body = {"output": "gone-with-the-deploy.children", "outputs": {"id": "gone-with-the-deploy", "property": "children"}, "inputs": [], "changedPropIds": []}

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        response = _post(body)

    assert response.status_code == 204
    assert "Dash refused a callback request" in caplog.text
    assert "reload it" in caplog.text
    assert "gone-with-the-deploy" in caplog.text  # what it asked for, which tells which tab was left open


def test_a_request_whose_outputs_came_empty_is_answered_the_same(caplog) -> None:
    callback = next(cb for cb in dashboard_app._callback_list if "digest-content.children" in cb["output"])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        response = _post({"output": callback["output"], "outputs": {}, "inputs": [], "changedPropIds": []})

    assert response.status_code == 204
    assert "digest-content" in caplog.text


def test_a_request_short_of_the_inputs_its_callback_declares_is_answered_the_same(caplog) -> None:
    """A tab left open across a deploy that added an Input sends the shorter list it was loaded with; Dash raised IndexError."""
    callback = next(cb for cb in dashboard_app._callback_list if cb["output"] == "ms-certs-table-container.children")
    assert len(callback["inputs"]) == 3  # the search box, the retired toggle and the activation store
    only_the_search = [{"id": "ms-certs-search-input", "property": "value", "value": "x"}]

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        response = _post({"output": callback["output"], "outputs": {"id": "ms-certs-table-container", "property": "children"}, "inputs": only_the_search, "changedPropIds": ["ms-certs-search-input.value"]})

    assert response.status_code == 204
    assert "ms-certs-table-container" in caplog.text and "reload it" in caplog.text


def test_an_error_one_of_our_callbacks_raised_keeps_its_traceback() -> None:
    """A KeyError in a callback of ours is a bug to see whole, not a stale tab to shrug at."""
    frame_file = os.path.join(app_module._SRC_DIR, "web", "dashboard", "components", "some_tab.py")
    try:
        exec(compile("raise KeyError('a column the code expects')", frame_file, "exec"), {})
    except KeyError as error:
        with dashboard_app.server.test_request_context("/_dash-update-component"), pytest.raises(KeyError, match="a column the code expects"):
            app_module.callback_request_refused(error)
    else:
        raise AssertionError("the snippet did not raise")


def test_an_error_on_another_route_is_left_to_flask() -> None:
    with dashboard_app.server.test_request_context("/health"), pytest.raises(KeyError, match="boom"):
        app_module.callback_request_refused(KeyError("boom"))
