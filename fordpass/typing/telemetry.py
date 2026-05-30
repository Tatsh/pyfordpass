"""Telemetry response shapes - metric envelopes and the ``:query`` snapshot."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ('MetricEntry', 'MetricValue', 'TelemetryResponse', 'TirePressureEntry')


class TirePressureEntry(TypedDict, total=False):
    """One entry in the per-wheel tire-pressure list."""

    oemCorrelationId: str
    """Upstream correlation id."""
    updateTime: str
    """ISO-8601 timestamp of the reading."""
    value: float
    """Current pressure in kilopascals."""
    vehicleWheel: str
    """Wheel identifier (``'FRONT_LEFT'``, ``'REAR_RIGHT'``, …)."""
    wheelPlacardFront: float
    """Manufacturer-recommended front pressure (kPa)."""
    wheelPlacardRear: float
    """Manufacturer-recommended rear pressure (kPa)."""


MetricValue: TypeAlias = (
    'str | int | float | bool | Mapping[str, "MetricValue"] | Sequence["MetricValue"] | None')
"""
Recursive type for one telemetry metric's ``value`` field.

The TMC service emits primitives, nested objects (position, heading,
acceleration, configurations, indicators), and lists (per-wheel tire data,
per-door / per-seat status). This union exhaustively models the shape without
falling back to :py:class:`Any`.

:meta hide-value:
"""


class MetricEntry(TypedDict, total=False):
    """Shared envelope around a single telemetry metric's value + provenance."""

    oemCorrelationId: str
    """Upstream correlation id."""
    tags: Sequence[str]
    """Optional tags attached to the reading."""
    updateTime: str
    """ISO-8601 timestamp of the reading."""
    value: MetricValue
    """The metric's value (scalar, nested object, or list - see :data:`MetricValue`)."""


class TelemetryResponse(TypedDict, total=False):
    """
    Top-level shape of the telemetry-query response.

    Only the always-present envelope keys are listed; ``metrics`` is keyed by metric name and the
    value side follows :py:class:`MetricEntry` (most metrics) or :py:class:`Sequence[MetricEntry]`
    (per-instance metrics like tires, doors, seats).
    """

    events: Mapping[str, MetricEntry]
    """Per-event values (e.g. ``automaticSoftwareUpdateUserSettingsEvent``)."""
    metrics: Mapping[str, MetricEntry | Sequence[MetricEntry]]
    """Per-metric values (e.g. ``odometer``, ``fuelLevel``, ``tirePressure``)."""
    states: Mapping[str, MetricEntry]
    """Per-state values (e.g. ``vehicleLifeCycleMode``)."""
    updateTime: str
    """ISO-8601 timestamp of the snapshot."""
    vehicleId: str
    """TMC-internal vehicle identifier."""
    vin: str
    """The queried VIN."""
