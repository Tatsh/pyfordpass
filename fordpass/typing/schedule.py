"""SRSM (recurring remote-start) schedule shapes."""
from __future__ import annotations

from typing import TypedDict

__all__ = ('ScheduleEntry', 'SchedulesEnvelope', 'SchedulesResponse')


class ScheduleEntry(TypedDict, total=False):
    """One recurring remote-start schedule entry."""

    fri: str
    """``'1'`` if the schedule fires on Friday."""
    mon: str
    """``'1'`` if the schedule fires on Monday."""
    name: str
    """User-supplied schedule name."""
    requestDateTime: str
    """Originally-requested start datetime."""
    sat: str
    """``'1'`` if the schedule fires on Saturday."""
    startScheduleId: str
    """Server-assigned schedule identifier."""
    startTime: str
    """Local time-of-day (``'HH:MM'``) when the engine should fire."""
    status: str
    """``'1'`` for active, ``'0'`` for disabled (strings from upstream)."""
    sun: str
    """``'1'`` if the schedule fires on Sunday."""
    thu: str
    """``'1'`` if the schedule fires on Thursday."""
    timeZone: int
    """Internal time-zone code."""
    tue: str
    """``'1'`` if the schedule fires on Tuesday."""
    wed: str
    """``'1'`` if the schedule fires on Wednesday."""


class SchedulesEnvelope(TypedDict, total=False):
    """
    Inner ``startSchedule`` envelope wrapping the schedule list.

    ``$values`` (the actual list) is not a valid Python identifier; consumers access it via
    ``envelope['$values']`` at runtime.
    """

    schemaName: str
    """Newtonsoft.Json schema sentinel."""
    schemaVersion: str
    """Newtonsoft.Json schema-version sentinel."""


class SchedulesResponse(TypedDict, total=False):
    """Top-level shape of the ``getschedules`` SRSM response."""

    startSchedule: SchedulesEnvelope
    """Schedule list, wrapped in a Newtonsoft.Json ``$values`` envelope."""
    status: int
    """HTTP-style status code echoed in the body."""
