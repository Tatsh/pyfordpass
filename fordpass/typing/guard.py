"""Ford MPS Guard Mode response shapes."""
from __future__ import annotations

from typing import TypedDict

__all__ = ('GuardModeResponse',)


class GuardModeResponse(TypedDict, total=False):
    """
    Ford MPS Guard Mode session response.

    The get / enable / disable calls all return this envelope. ``returnCode`` is ``200`` on
    success; other codes accompany an explanatory ``returnMessage`` (for example ``300`` with
    ``'Enrollment is still in progress.'``). Additional keys may appear depending on the model.
    """

    returnCode: int
    """Numeric result code (``200`` on success)."""
    returnMessage: str
    """Human-readable result message."""
