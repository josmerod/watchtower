"""Source health indicators (spec 01 F4 / 03 F4).

Renders a row of colored dots — one per data file — based on the age of the
file's last modification: green < 24 h, amber < 7 d, red otherwise or missing.
"""

import time
from pathlib import Path

from dash import html

DAY_SECONDS = 86_400
WEEK_SECONDS = 7 * DAY_SECONDS

_COLORS = {"success": "#198754", "warning": "#ffc107", "danger": "#dc3545"}


def _health_state(path: Path, now: float) -> tuple[str, str]:
    """Return (color, tooltip) for a data file path."""
    if not path.exists():
        return "danger", "sin datos"
    age = now - path.stat().st_mtime
    if age < DAY_SECONDS:
        hours = max(1, int(age / 3600))
        return "success", f"hace {hours} h"
    if age < WEEK_SECONDS:
        return "warning", f"hace {int(age / DAY_SECONDS)} d"
    return "danger", f"hace {int(age / DAY_SECONDS)} d (stale)"


def source_health_dots(sources: dict[str, str], title: str = "Source health") -> html.Div:
    """Render a row of per-source health dots with age tooltips.

    Args:
        sources: Mapping of display name -> data file path.
        title: Accessible label for the row.
    """
    now = time.time()
    dots = []
    for name, path_str in sources.items():
        color, tip = _health_state(Path(path_str), now)
        dots.append(
            html.Span(
                [
                    html.Span("●", style={"color": _COLORS.get(color, "#6c757d")}, className="me-1"),
                    html.Small(name, className="text-muted"),
                ],
                title=f"{name}: {tip}",
                className="me-3 d-inline-flex align-items-center",
            )
        )
    return html.Div(
        [
            html.Small(title, className="text-muted me-2"),
            *dots,
        ],
        className="d-flex flex-wrap align-items-center mb-2",
    )
