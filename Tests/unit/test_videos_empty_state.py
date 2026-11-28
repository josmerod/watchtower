"""The empty state of the Videos tab names the ETL that fills it and how production runs it (T-138).

It used to tell the user to run ``src.etl.youtube_shorts.youtube_shorts_etl``, which no longer exists. The script it names now
is checked against the orchestrator's ``ETL_SCRIPTS``, so a renamed or unregistered ETL breaks this test instead of the
message. Fixture-based: the manager reports no channels, so nothing under ``data/`` is read and no network is touched.
"""

import re
from pathlib import Path

import pytest

from src.web.dashboard.components import videos_tab as tab

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR = REPO_ROOT / "run_all_etl_orchestrator.py"


def _walk(node):
    """Yield every node of a Dash component tree."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        yield from _walk(child)


def _texts(layout) -> list[str]:
    return [node for node in _walk(layout) if isinstance(node, str)]


def _registered_scripts() -> list[str]:
    """The scripts the orchestrator runs in every cycle, read from its ``ETL_SCRIPTS`` list."""
    source = ORCHESTRATOR.read_text(encoding="utf-8")
    block = re.search(r"^ETL_SCRIPTS = \[\n(.*?)^\]", source, flags=re.MULTILINE | re.DOTALL)
    assert block, "ETL_SCRIPTS not found in the orchestrator"
    return re.findall(r'"([^"]+\.py)"', block.group(1))


@pytest.fixture
def no_channels(monkeypatch: pytest.MonkeyPatch):
    """The manager finds no channel directory, whatever this machine has under data/."""
    monkeypatch.setattr(tab.video_manager, "get_channels", lambda: [])
    return tab.render_videos_tab()


def test_empty_state_names_the_real_etl(no_channels):
    joined = " ".join(_texts(no_channels))

    assert "No video data found" in joined
    assert tab._YOUTUBE_ETL_SCRIPT in joined  # src/etl/goldigging/goldigging_youtube_posts.py
    assert f"uv run python {tab._YOUTUBE_ETL_SCRIPT}" in joined  # how to run it by hand
    assert tab._YOUTUBE_OUTPUT_PATH in joined
    assert "youtube_shorts" not in joined  # the ETL it used to recommend is gone


def test_empty_state_says_the_orchestrator_runs_it_every_cycle(no_channels):
    joined = " ".join(_texts(no_channels))

    assert tab._ORCHESTRATOR_SCRIPT in joined
    assert "every ETL cycle" in joined
    assert tab._YOUTUBE_ETL_LOG in joined  # where a failed run leaves its trace


def test_the_empty_state_keeps_the_marker_the_render_smoke_test_skips_on(no_channels):
    """Tests/unit/test_tab_render.py skips a tab that renders its empty state by this icon."""
    assert any("video-slash" in str(getattr(node, "className", "")) for node in _walk(no_channels))


def test_the_named_etl_exists_and_runs_every_cycle():
    script = tab._YOUTUBE_ETL_SCRIPT

    assert (REPO_ROOT / script).is_file()
    assert script in _registered_scripts()


def test_the_named_etl_is_the_one_that_writes_what_the_tab_reads():
    """The tab reads data/youtube/<theme>/youtube_videos.json: the ETL it names must write exactly that."""
    etl = (REPO_ROOT / tab._YOUTUBE_ETL_SCRIPT).read_text(encoding="utf-8")
    data_dir, base_dir, theme_slot, file_name = tab._YOUTUBE_OUTPUT_PATH.split("/")

    assert (data_dir, theme_slot) == ("data", "<theme>")
    assert f'BASE_OUTPUT_DIR = "{data_dir}/{base_dir}"' in etl
    assert "os.path.join(project_root, BASE_OUTPUT_DIR, topic)" in etl  # one directory per theme
    assert f'"{file_name}"' in etl


def test_the_named_log_follows_the_orchestrator_naming():
    """The orchestrator logs each script to logs/<script name without .py>.log."""
    assert tab._YOUTUBE_ETL_LOG == f"logs/{Path(tab._YOUTUBE_ETL_SCRIPT).stem}.log"
    assert 'log_dir = "logs"' in ORCHESTRATOR.read_text(encoding="utf-8")
