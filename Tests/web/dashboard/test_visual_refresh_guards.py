"""Guards on `zz_visual_refresh.css`, the sheet that loads last.

It carries the fixes for the blanket `!important` rules of the legacy sheets
(`style.css`, `css/mobile_responsive.css`). Each test pins one of them: when
the fix is dropped or loses the specificity it needs, the page breaks again
with nothing failing elsewhere.
"""

import re
from pathlib import Path

from src.utils.file_system import get_project_root

ASSETS = Path(get_project_root()) / "src" / "web" / "dashboard" / "assets"
FINAL_SHEET = ASSETS / "zz_visual_refresh.css"
LEGACY_MOBILE_SHEET = ASSETS / "css" / "mobile_responsive.css"

RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
# The chain that gives a selector the specificity of the blanket background rule.
BLANKET_CHAIN = ":not(.table):not(.alert):not(.card):not(.nav-tabs)"


def rules_of(stylesheet: Path) -> list[tuple[list[str], dict[str, str]]]:
    """Every rule of a sheet as (selectors, declarations), comments stripped."""
    css = re.sub(r"/\*.*?\*/", "", stylesheet.read_text(encoding="utf-8"), flags=re.S)
    rules = []
    for selector_list, body in RULE.findall(css):
        # The first rule inside a media block carries the block's preamble in front of its selector.
        selectors = [selector.strip() for selector in re.sub(r"@media[^{]*\{", "", selector_list).split(",") if selector.strip()]
        declarations = dict(part.strip().split(":", 1) for part in body.split(";") if ":" in part)
        rules.append((selectors, {name: value.strip() for name, value in declarations.items()}))
    return rules


def rules_matching(stylesheet: Path, selector_part: str) -> list[tuple[str, dict[str, str]]]:
    """(selector, declarations) of every rule with `selector_part` among its selectors."""
    return [(selector, declarations) for selectors, declarations in rules_of(stylesheet) for selector in selectors if selector_part in selector]


def test_tab_links_lose_the_offsets_of_the_legacy_mobile_sheet():
    """Under 768px the legacy sheet moves every .nav-tabs .nav-link to -9999px.

    A subtab link keeps `position: relative` (its underline), so without the
    reset its bar renders empty on a phone.
    """
    legacy = rules_matching(LEGACY_MOBILE_SHEET, ".nav-tabs .nav-link")
    assert any(d.get("left", "").startswith("-9999px") for _, d in legacy), "the legacy sheet changed: re-check that tab links still need the reset"

    reset = [(s, d) for s, d in rules_matching(FINAL_SHEET, ".nav-tabs .nav-link") if d.get("left") == "auto !important" and d.get("top") == "auto !important"]
    assert reset, "no rule of the final sheet brings .nav-tabs .nav-link back to left/top: auto"
    assert any(":hover" not in s and ":focus" not in s for s, _ in reset), "the reset only applies on hover or focus"
