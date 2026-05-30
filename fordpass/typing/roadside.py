"""Roadside-assistance response shapes."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ('IDNameEntry', 'IDNameListResponse', 'RoadsideActiveResponse')


class IDNameEntry(TypedDict):
    """An ``{id, name}`` pair used by several catalogue endpoints."""

    id: str
    """Upstream identifier."""
    name: str
    """Display label."""


class IDNameListResponse(TypedDict, total=False):
    """Envelope around an ID/name list (roadside symptoms / location types)."""

    locationTypes: Sequence[IDNameEntry]
    """Populated by the roadside-location-types endpoint."""
    symptoms: Sequence[IDNameEntry]
    """Populated by the roadside-symptoms endpoint."""


class RoadsideActiveResponse(TypedDict, total=False):
    """Top-level shape of the active-roadside-event response."""

    eventId: str
    """Identifier of the active roadside event, if any."""
