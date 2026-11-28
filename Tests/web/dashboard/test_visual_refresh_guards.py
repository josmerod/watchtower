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
LEGACY_SHEET = ASSETS / "style.css"
LEGACY_MOBILE_SHEET = ASSETS / "css" / "mobile_responsive.css"

RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
# The chain that gives a selector the specificity of the blanket background rule.
BLANKET_CHAIN = ":not(.table):not(.alert):not(.card):not(.nav-tabs)"
# What counts one class towards specificity: a class, or a pseudo-class with or without its argument.
CLASS_LEVEL = re.compile(r"\.[\w-]+|:[\w-]+(?:\([^)]*\))?")


def _split_selectors(text: str) -> list[str]:
    """The selectors of a list, split on the commas outside its parentheses.

    `:is(div, span)` holds commas of its own: a plain split turns it into two selectors.
    """
    selectors, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            selectors.append(text[start:index])
            start = index + 1
    selectors.append(text[start:])
    return [selector.strip() for selector in selectors if selector.strip()]


def rules_of(stylesheet: Path) -> list[tuple[list[str], dict[str, str]]]:
    """Every rule of a sheet as (selectors, declarations), comments stripped."""
    css = re.sub(r"/\*.*?\*/", "", stylesheet.read_text(encoding="utf-8"), flags=re.S)
    rules = []
    for selector_list, body in RULE.findall(css):
        # The first rule inside a media block carries the block's preamble in front of its selector.
        selectors = _split_selectors(re.sub(r"@media[^{]*\{", "", selector_list))
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


def test_primary_buttons_outrank_the_blanket_background():
    """The blanket rule paints every background dark with the chain's specificity.

    A rule that gives .btn-primary its light accent has to carry the same
    chain, or the dark text of the button is left on a dark background.
    """
    blanket = [(s, d) for s, d in rules_matching(FINAL_SHEET, "html body") if "background-color" in d and BLANKET_CHAIN in s]
    assert blanket, "the blanket background rule moved: re-check what the buttons have to outrank"

    keepers = [
        (s, d) for s, d in rules_matching(FINAL_SHEET, ".btn-primary") if BLANKET_CHAIN in s and "color" in d and ("background" in d or "background-color" in d) and ":hover" not in s and ":focus" not in s
    ]
    assert keepers, "no rule gives .btn-primary a background and a text color with the blanket chain on its selector"

    html, body = len(re.findall(r"(?<![\w-])html(?![\w-])", keepers[0][0])), len(re.findall(r"(?<![\w-])body(?![\w-])", keepers[0][0]))
    assert html and body, "the rule does not start with `html body`: it is less specific than the blanket rule"


def test_main_bar_wraps_instead_of_scrolling():
    """The tablist rule forces one non-wrapping, scrollable line.

    The main bar holds 18 tabs: on one line it scrolled and hid eight of them at 1280 px (T-169). The override has to carry both the id and the class: with one of them it is less specific than `#dashboard-tabs` in the tablist rule.
    """
    wrapping = [(s, d) for s, d in rules_matching(FINAL_SHEET, "#dashboard-tabs.desktop-nav-tabs") if d.get("flex-wrap") == "wrap !important" and d.get("overflow-x") == "hidden !important"]

    assert wrapping, "no rule makes the main bar wrap instead of scrolling"
    assert all(":hover" not in s and ":focus" not in s for s, _ in wrapping)
    one_line = [(s, d) for s, d in rules_matching(FINAL_SHEET, "#dashboard-tabs.desktop-nav-tabs") if d.get("flex-wrap") == "nowrap !important"]
    assert one_line, "the rule for a phone (one scrollable row) is gone"  # it comes later in the sheet, so it wins there


def test_checkboxes_and_radios_keep_their_mark():
    """The input rule paints every input one flat colour with one corner radius.

    A checkbox and a radio are not text fields: Bootstrap draws their mark as a background image and rounds a radio, and
    the bare `input` selector erased both, so "Mostrar retiradas" looked unchecked while it listed the retired credentials.
    """
    bare_input = re.compile(r"input(?::focus)?")  # the whole selector: `.Select-input > input` is a text field and stays painted
    painting = [(s, d) for s, d in rules_matching(FINAL_SHEET, "input") if bare_input.fullmatch(s) and {"background", "background-color", "border-radius", "border-color"} & set(d)]

    assert not painting, painting


def test_plotly_layers_do_not_cover_the_plot():
    """The legacy sheet paints every Plotly layer svg with a background.

    A graph stacks three of them (the plot, the labels and the legend, the hover layer), so the two upper ones covered the plot and every graph of the dashboard was an empty rectangle.
    The reset has to outrank the legacy rule and the blanket rule of this sheet, the more specific of the two.
    """
    legacy = [(s, d) for s, d in rules_matching(LEGACY_SHEET, ".main-svg") if {"background", "background-color"} & set(d)]
    assert legacy, "the legacy rule is gone: drop the reset and this test"

    reset = [(s, d) for s, d in rules_matching(FINAL_SHEET, ".main-svg") if d.get("background-color") == "transparent !important"]
    assert reset, "no rule of the final sheet makes the Plotly layer svgs transparent"
    for selector, _ in reset:
        assert len(CLASS_LEVEL.findall(selector)) > len(CLASS_LEVEL.findall(BLANKET_CHAIN)), selector


def test_cell_content_does_not_paint_over_its_row():
    """The blanket rule of style.css paints every element the page colour, the content of a cell included.

    The `.table td` rule above is made transparent, but it is four classes short of the blanket one. So in a striped
    table the wrappers that title_cell and text_cell put in a cell, and the links, covered the stripe and the hover of
    their row: a dark block inside a lighter frame, read as a box behind the title.
    """
    legacy = [(s, d) for s, d in rules_matching(LEGACY_SHEET, BLANKET_CHAIN) if "background-color" in d]
    assert legacy, "the blanket rule of the legacy sheet is gone: drop the reset and this test"

    reset = [(s, d) for s, d in rules_matching(FINAL_SHEET, ".table td") if d.get("background-color") == "transparent !important" and ":hover" not in s and ":focus" not in s]
    assert reset, "no rule of the final sheet makes the content of a cell transparent"
    for selector, _ in reset:
        assert len(CLASS_LEVEL.findall(selector)) > len(CLASS_LEVEL.findall(BLANKET_CHAIN)), selector
        assert all(re.search(rf"(?<![\w-]){part}(?![\w-])", selector) for part in ("div", "span", "a")), "the wrappers of title_cell and text_cell, and the links, are not all covered"
        assert '[class*="bg-"]' in selector and ".btn" in selector, "an element with a background of its own has to keep it"


def test_a_link_in_a_cell_stays_readable_under_the_pointer():
    """`.table td a:hover` of style.css turns the text of a link dark, for a purple pill.

    The blanket rule paints that pill over, so a link of any table vanished on hover: dark text on the dark page
    colour. The hover rule of the final sheet has to outrank the legacy one.
    """
    legacy = [(s, d) for s, d in rules_matching(LEGACY_SHEET, ".table td a") if ":hover" in s and "color" in d]
    assert legacy, "the hover rule of the legacy sheet is gone: drop the reset and this test"

    links = rules_matching(FINAL_SHEET, ".table td a")
    hover = [(s, d) for s, d in links if ":hover" in s]
    assert hover, "no hover rule of the final sheet covers a link in a cell"
    assert any(":focus" in s for s, _ in links), "the keyboard focus gets no rule of its own"
    for selector, declarations in hover:
        assert declarations.get("color") == "#ddd6fe !important" and declarations.get("text-decoration") == "underline !important", (selector, declarations)
        assert len(CLASS_LEVEL.findall(selector)) > max(len(CLASS_LEVEL.findall(s)) for s, _ in legacy), selector
