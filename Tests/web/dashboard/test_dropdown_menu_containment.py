"""Guard for where dropdown menus are drawn (bug found in production on 2026-11-27).

Dash draws a `dcc.Dropdown` menu as a `position: fixed` box placed in viewport coordinates. An
ancestor with `content-visibility: auto` becomes the containing block of such a box, so the menu
lands at the trigger plus the ancestor's own offset: off-screen on every tab while the stylesheet
gave that property to the tab containers. No unit test could see it. This one reads the stylesheet
and refuses any rule that leaves a dropdown under `content-visibility: auto`.
"""

import re
from pathlib import Path

from src.utils.file_system import get_project_root

STYLESHEET = Path(get_project_root()) / "src" / "web" / "dashboard" / "assets" / "zz_visual_refresh.css"
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def selectors_that_skip_rendering(css: str) -> list[str]:
    """Every selector of a rule that sets `content-visibility: auto`."""
    selectors = []
    for selector_list, body in RULE.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if not re.search(r"content-visibility:\s*auto", body):
            continue
        # The first rule inside a media block carries the block's preamble in front of its selector.
        selector_list = re.sub(r"@media[^{]*\{", "", selector_list)
        selectors.extend(selector.strip() for selector in selector_list.split(",") if selector.strip())
    return selectors


def test_a_container_that_holds_a_dropdown_is_never_skipped():
    guarded = selectors_that_skip_rendering(STYLESHEET.read_text(encoding="utf-8"))

    assert guarded, "the rendering guard is gone: off-screen cards and tables are not laid out on purpose"
    uncovered = [selector for selector in guarded if ":not(:has(.dash-dropdown))" not in selector]
    assert not uncovered, f"a dropdown inside {uncovered} would open its menu away from its trigger"


def test_the_guard_is_read_from_the_rules_not_from_the_comments():
    css = "/* talks about content-visibility: auto */ .tab-pane { color: red; } @media (max-width: 768px) {\n  .card,\n  .table-responsive {\n    content-visibility: auto;\n  }\n}"

    assert selectors_that_skip_rendering(css) == [".card", ".table-responsive"]
    assert selectors_that_skip_rendering(".card { content-visibility: visible; }") == []
