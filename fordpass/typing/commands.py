"""Generic command-response envelope shapes."""
from __future__ import annotations

from typing import TypedDict

__all__ = ('AckResponse',)


class AckResponse(TypedDict, total=False):
    """Generic acknowledgement envelope from a TMC command POST."""

    commandId: str
    """Server-assigned command identifier."""
    status: str
    """Initial command status (``'QUEUED'``, ``'PENDING'``, …)."""
