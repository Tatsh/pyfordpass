"""OTA release-notes response shape."""
from __future__ import annotations

from typing import TypedDict

__all__ = ('ReleaseNotesResponse',)


class ReleaseNotesResponse(TypedDict, total=False):
    """Top-level shape of the OTA release-notes response."""

    response: str
    """Release-notes text."""
