"""Data model for the cinema listings: one record per screening."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.base import TimestampedModel

ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def session_key(*, cinema: str, title: str, date: str, time: str, version: str = "", format: str = "") -> tuple[str, ...]:
    """Name the fields that tell two screenings apart.

    Two records with the same cinema, film, day, time, version and format are
    the same screening listed twice. The format is in the key because a 2D and
    an IMAX screening of one film can start at the same minute: they are two
    sessions, in two rooms.

    Args:
        cinema: Cinema name.
        title: Film title.
        date: Screening day as YYYY-MM-DD.
        time: Start time as HH:MM.
        version: VOSE, VOS, VO, DOB or "" when the listing prints none.
        format: IMAX, 3D... or "" for a plain screening.

    Returns:
        A hashable, case-insensitive key.
    """
    return (cinema.casefold(), title.casefold(), date, time, version.casefold(), format.casefold())


def session_id(key: tuple[str, ...]) -> str:
    """Derive the record id from a session key, so a session keeps its id across runs.

    Args:
        key: A key from ``session_key``.

    Returns:
        Hex digest of the key.
    """
    return hashlib.sha1("|".join(key).encode("utf-8")).hexdigest()


class CinemaSession(TimestampedModel):
    """One screening: a film at a cinema, on a day, at a time.

    Every field is what the listing that published the session says. ``price``
    stays ``None`` and ``original_title`` stays empty until a source prints
    them: neither is guessed.
    """

    title: str = Field(description="Film title as the listing prints it, without the version or format suffixes")
    cinema: str = Field(description="Cinema name")
    city: str = Field(description="City or town of the cinema")
    date: str = Field(description="Screening day as YYYY-MM-DD")
    time: str = Field(description="Start time as HH:MM")
    source: str = Field(description="Site the session was read from")
    original_title: str = Field(default="", description="Original title when the listing gives one")
    address: str = Field(default="", description="Street or venue when the listing gives one")
    version: str = Field(default="", description="VOSE, VOS, VO, DOB, or empty when the listing prints none")
    format: str = Field(default="", description="IMAX, 3D, 35 mm..., or empty for a plain screening")
    price: float | None = Field(default=None, description="Price when the listing publishes one, otherwise None")
    ticket_url: str = Field(default="", description="Where the listing sends the user to buy the ticket")
    film_url: str = Field(default="", description="Page of the film on the source site")
    room: str = Field(default="", description="Screen number when the listing prints one")
    duration_min: int | None = Field(default=None, description="Running time in minutes when the listing prints one")
    year: int | None = Field(default=None, description="Release year when the listing prints one")
    director: str = Field(default="", description="Director when the listing prints one")
    language: str = Field(default="", description="Audio and subtitle text as the listing prints it")
    first_detected_at: datetime | None = Field(default=None, description="When Watchtower first saw the session; kept from run to run")
    # The base model means to stamp this field but pydantic does not run validators on a default, so it stays
    # None there. Every run writes its sessions anew: stamp them with the run that last listed the session.
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When the last run that lists this session wrote it")

    @field_validator("title", "cinema", "city", "date", "time", "source", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        """Drop the whitespace around the identifiers."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("title", "cinema", "city", "source")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        """A record nobody can tell apart is not stored: the names are required."""
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("date")
    @classmethod
    def _real_day(cls, value: str) -> str:
        """Accept only a real calendar day in ISO form, the format the freshness watcher reads."""
        if not ISO_DAY.fullmatch(value):
            raise ValueError("must be YYYY-MM-DD")
        date.fromisoformat(value)
        return value

    @field_validator("time")
    @classmethod
    def _clock_time(cls, value: str) -> str:
        """Accept only a 24-hour HH:MM start time."""
        if not ISO_TIME.fullmatch(value):
            raise ValueError("must be HH:MM on a 24-hour clock")
        return value

    @field_validator("price")
    @classmethod
    def _price_not_negative(cls, value: float | None) -> float | None:
        """A price is a positive amount; anything else is a parsing error."""
        if value is not None and value < 0:
            raise ValueError("must not be negative")
        return value

    @model_validator(mode="before")
    @classmethod
    def _derive_id(cls, data: Any) -> Any:
        """Give the session an id derived from what makes it unique, unless one is passed.

        The base id is a random uuid: a session would get a new one on every
        run. Deriving it from the key keeps it stable for as long as the
        session is published.
        """
        if isinstance(data, dict) and not data.get("id"):
            data = dict(data)
            data["id"] = session_id(
                session_key(
                    cinema=str(data.get("cinema", "")),
                    title=str(data.get("title", "")),
                    date=str(data.get("date", "")),
                    time=str(data.get("time", "")),
                    version=str(data.get("version", "")),
                    format=str(data.get("format", "")),
                )
            )
        return data


def sessions_key_of(record: BaseModel | dict[str, Any]) -> tuple[str, ...]:
    """Read the session key off a stored record, model or dictionary."""
    get = record.get if isinstance(record, dict) else lambda name, default=None: getattr(record, name, default)
    return session_key(
        cinema=str(get("cinema", "")),
        title=str(get("title", "")),
        date=str(get("date", "")),
        time=str(get("time", "")),
        version=str(get("version", "") or ""),
        format=str(get("format", "") or ""),
    )
