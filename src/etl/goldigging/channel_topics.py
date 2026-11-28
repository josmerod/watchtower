"""Channel topics of the goldigging YouTube ETL: the one definition of what a theme is.

``channels.json``, next to this module, maps a theme key to its description and
the YouTube channels that belong to it::

    {"aa-dev": {"description": "Programming and Development", "channels": ["Fireship", ...]}}

``goldigging_youtube_posts.py`` takes every key as a topic and writes one
directory per key, ``data/youtube/<key>/youtube_videos.json``. A theme is
therefore a key of this file, whatever its prefix: ``aa-``, ``z-``, ``zz-`` and
``zzz-`` only order the keys, and no code reads them. The Videos tab asks
``is_theme`` which directories under ``data/youtube/`` are themes and reads
each one's ``theme_description`` for its dropdown, so the tab and the ETL
cannot disagree about it.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHANNELS_JSON = Path(__file__).with_name("channels.json")


def load_channel_topics() -> dict[str, Any]:
    """Read ``channels.json``: theme key -> ``{"description": str, "channels": list[str]}``.

    The file holds non-ASCII handles, so it is always read as UTF-8, never in
    the locale's encoding.

    Returns:
        The parsed mapping, in file order.

    Raises:
        OSError: The file cannot be read.
        ValueError: The file is not valid JSON.
    """
    with CHANNELS_JSON.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _read_topics() -> dict[str, Any]:
    """``load_channel_topics()`` read once per process, or ``{}`` when the file cannot be read (one warning).

    A test that pins the loader clears this cache: every lookup below goes through it.
    """
    try:
        return load_channel_topics()
    except (OSError, ValueError) as exc:
        logger.warning("Channel topics could not be read from %s: %s", CHANNELS_JSON, exc)
        return {}


def theme_names() -> frozenset[str]:
    """The theme keys, which are the directory names the ETL writes under ``data/youtube/``.

    When the file cannot be read the result is empty and a warning is logged: a caller such as the dashboard then shows
    no themes instead of failing.

    Returns:
        Every key of ``channels.json``.
    """
    return frozenset(_read_topics())


def is_theme(name: str) -> bool:
    """Whether ``name`` is a theme: a key of ``channels.json``, so a directory the ETL writes."""
    return name in theme_names()


def theme_description(name: str) -> str:
    """The description ``channels.json`` gives a theme, for what the Videos tab shows next to its key.

    Args:
        name: A theme key.

    Returns:
        The description without surrounding blanks, or ``""`` when ``name`` is not a theme, the file gives it none or
        the file cannot be read.
    """
    topic = _read_topics().get(name)
    description = topic.get("description") if isinstance(topic, dict) else None
    return str(description).strip() if description else ""
