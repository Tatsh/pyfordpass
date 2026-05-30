"""Active-alerts and alert-history response shapes."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ('AlertCategory', 'AlertColorCode', 'AlertEntry', 'AlertHistoryEntry',
           'AlertHistoryResponse', 'AlertPrognostics', 'AlertUrgency', 'AlertsResponse')

AlertUrgency: TypeAlias = Literal['H', 'M', 'N']
"""
Alert urgency code: ``N`` (normal), ``M`` (medium), or ``H`` (high).

:meta hide-value:
"""

AlertColorCode: TypeAlias = Literal['A', 'R', 'Y']
"""
Display colour code for an alert tile: amber, yellow, or red.

:meta hide-value:
"""

AlertCategory: TypeAlias = Literal['Diagnostics', 'Prognostics']
"""
Top-level alert category.

:meta hide-value:
"""


class AlertPrognostics(TypedDict, total=False):
    """Detail block for prognostics-type alert entries (11 known fields)."""

    dtsMessage: str | None
    """Diagnostic-trouble-symptom message body."""
    estDistanceKM: float | None
    """Estimated distance to service in kilometres."""
    estDistanceMiles: float | None
    """Estimated distance to service in miles."""
    estServiceDate: str | None
    """ISO-8601 estimated service date."""
    featureData: str | None
    """Feature-specific freeform data."""
    featureType: str | None
    """Prognostics feature category (``'SM'`` = scheduled maintenance, ``'OL'`` = oil life, …)."""
    nextIntervalKMs: float | None
    """Next service interval in kilometres."""
    nextIntervalMiles: float | None
    """Next service interval in miles."""
    oilRemaining: float | None
    """Oil-life percentage remaining."""
    shouldShow: bool
    """Whether the HMI should surface this row."""
    tireWithSlowLeak: str | None
    """Wheel identifier (``'FRONT_LEFT'``, …) when a slow-leak alert fired."""


class AlertEntry(TypedDict, total=False):
    """
    One entry in the active-alerts list.

    Most string-typed fields are nullable; the upstream returns ``null`` rather than omitting the
    key when no value is set.
    """

    alertDescription: str | None
    """Human-readable description; ``None`` when the alert has no description."""
    alertIdentifier: str | None
    """Stable identifier (e.g. ``'E19-374-43'``); ``None`` for some prognostics."""
    alertTraceId: str | None
    """Upstream trace identifier; commonly ``None``."""
    alertType: AlertCategory
    """Category (``'Prognostics'`` / ``'Diagnostics'``)."""
    colorCode: AlertColorCode
    """Display colour code: ``'A'`` (amber), ``'Y'`` (yellow), or ``'R'`` (red)."""
    eventTimeStamp: str
    """Timestamp when the alert was raised."""
    iconName: str
    """Icon asset name."""
    prognostics: AlertPrognostics | None
    """Detail block for prognostics-type alerts; ``None`` for other alert types."""
    sortOrder: int | None
    """Display-ordering hint; ``None`` when upstream did not score the row."""
    urgency: AlertUrgency
    """``'N'`` (normal), ``'M'`` (medium), or ``'H'`` (high)."""
    vha: Mapping[str, object] | None
    """Detail block for vehicle-health-alert-type alerts; ``None`` otherwise."""
    wilCode: str
    """Warning-indicator-lamp code (``'None'`` when there is no WIL)."""


class AlertsResponse(TypedDict, total=False):
    """Top-level shape of the current-alerts response."""

    VIN: str
    """Echoed VIN."""
    alerts: Sequence[AlertEntry]
    """Currently-active alerts."""


class AlertHistoryEntry(TypedDict, total=False):
    """One entry in the alert-history list."""

    alertType: str
    """Category (``'prognostics'``, ``'diagnostics'``)."""
    eventTime: str
    """Local-time timestamp when the alert was raised."""
    messageBody: str
    """Full message text."""
    messageSubject: str
    """Short subject line."""
    messageTypeId: int
    """Upstream message-type identifier."""


class AlertHistoryResponse(TypedDict, total=False):
    """Top-level shape of the alert-history response."""

    error: object
    """``None`` on success; otherwise the upstream error envelope."""
    messages: Sequence[AlertHistoryEntry]
    """Historical alert entries."""
