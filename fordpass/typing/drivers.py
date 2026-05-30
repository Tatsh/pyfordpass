"""Secondary-driver response shapes."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ('DriverEntry', 'DriversCountResponse', 'DriversListResponse', 'InviteResponse')


class DriverEntry(TypedDict, total=False):
    """One entry in the authorised + pending drivers list."""

    GUID: str
    """User's GUID."""
    displayName: str
    """Display name."""
    inviteId: str | None
    """Pending-invite id; ``None`` when the driver is already authorised."""
    userAuthStatus: str
    """``'Authorized'`` / ``'Pending'``."""


class DriversCountResponse(TypedDict, total=False):
    """Top-level shape of the authorised-user count response."""

    count: int
    """Number of currently authorised secondary drivers."""


class DriversListResponse(TypedDict, total=False):
    """Top-level shape of the drivers-list response."""

    authAndPendingUsers: Sequence[DriverEntry]
    """Combined authorised + pending list."""
    code: object
    """Upstream status code (``None`` on success)."""
    message: object
    """Upstream message (``None`` on success)."""
    status: Mapping[str, object]
    """Status envelope."""


class InviteResponse(TypedDict, total=False):
    """Response envelope for the secondary-driver invite endpoint."""

    errorCode: str | None
    """Upstream error code; ``None`` (or absent) on success."""
    errorMessage: str | None
    """Upstream error message; ``None`` (or absent) on success."""
    inviteId: str
    """Server-assigned invite identifier (present on success)."""
