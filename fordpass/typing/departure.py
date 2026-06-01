"""Departure-time schedule write shapes (EV/PHEV only)."""
from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict

__all__ = ('DepartureDayOfWeek', 'DepartureScheduleDay', 'DepartureScheduleSlot',
           'PreconditionTemperature', 'ScheduleStatus', 'TimeOfDay')

DepartureDayOfWeek: TypeAlias = Literal['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY',
                                        'SATURDAY', 'SUNDAY']
"""Upper-case English day name accepted by ``updateDepartureTimes``.

:meta hide-value:
"""

PreconditionTemperature: TypeAlias = Literal['OFF', 'LOW', 'MEDIUM', 'HIGH']
"""Cabin-preconditioning intensity for one departure slot.

:meta hide-value:
"""

ScheduleStatus: TypeAlias = Literal['ON', 'OFF']
"""Whether a single departure slot is active.

:meta hide-value:
"""


class TimeOfDay(TypedDict):
    """Wall-clock time a departure slot fires, in the vehicle's local zone."""

    hours: int
    """Hour of day (``0``-``24``; ``24`` is the upstream sentinel for "midnight / disabled")."""
    minutes: int
    """Minute of hour (``0``-``59``)."""


class DepartureScheduleSlot(TypedDict):
    """One departure slot within a day group."""

    locationId: str
    """Opaque charge-location identifier (UUID or numeric string); passed through unchanged."""
    preconditionTemperature: PreconditionTemperature
    """Cabin-preconditioning intensity for this slot."""
    scheduleId: int
    """Server-assigned slot identifier, unique across the whole schedule list."""
    scheduleStatus: ScheduleStatus
    """Whether this slot is active."""
    timeOfDay: TimeOfDay
    """Departure time for this slot."""


class DepartureScheduleDay(TypedDict):
    """All departure slots configured for one day of the week."""

    dayOfWeek: DepartureDayOfWeek
    """The day these slots apply to."""
    schedules: list[DepartureScheduleSlot]
    """The slots configured for ``dayOfWeek``."""
