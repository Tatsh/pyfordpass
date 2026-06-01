"""
Pure helpers that operate on already-fetched FordPass response payloads.

These functions hold no state, perform no I/O, and have no dependency on the client class. They
live here so callers can import the specific helper they need without instantiating
:py:class:`fordpass.sansio.FordPassClient`.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias, TypeGuard, cast

if TYPE_CHECKING:
    from .typing.alerts import AlertsResponse
    from .typing.common import CompassDirection, GPSPosition
    from .typing.departure import DepartureScheduleDay
    from .typing.telemetry import DepartureSchedule, MetricEntry
    from .typing.vehicle import GarageVehicle

MetricsBlock: TypeAlias = 'Mapping[str, MetricEntry | Sequence[MetricEntry]]'
"""
The ``metrics`` sub-object of a telemetry response (the shape on
:py:class:`fordpass.typing.telemetry.TelemetryResponse`).

:meta hide-value:
"""

__all__ = ('MetricsBlock', 'extract_departure_schedule_days', 'extract_fuel', 'extract_odometer',
           'extract_oil_life', 'extract_position', 'find_next_departure',
           'find_preferred_dealer_code', 'is_list_like', 'is_washer_fluid_low',
           'scalar_metric_value', 'walk_mapping')


def scalar_metric_value(entry: MetricEntry | Sequence[MetricEntry] | None) -> Any:
    """
    Pluck ``entry['value']`` from a scalar :py:class:`MetricEntry`.

    Parameters
    ----------
    entry : MetricEntry | Sequence[MetricEntry] | None
        A single metric entry, a list-shaped metric, or ``None``.

    Returns
    -------
    Any
        The metric's ``value`` field when ``entry`` is a single :py:class:`MetricEntry`; ``None``
        when ``entry`` is missing or a list-shaped metric (no scalar value to extract).
    """
    if isinstance(entry, Mapping):
        return entry.get('value')  # ty: ignore[invalid-argument-type]
    return None


def is_list_like(value: object) -> TypeGuard[Sequence[Any]]:
    """
    Return ``True`` if ``value`` is a list-like sequence (excluding ``str`` and ``bytes``).

    Parameters
    ----------
    value : object
        Any object.

    Returns
    -------
    TypeGuard[Sequence[Any]]
        ``True`` for lists, tuples, and other :py:class:`~collections.abc.Sequence` types, but
        ``False`` for strings and bytes (which are themselves Sequences in Python's type hierarchy
        but are virtually never what callers mean when they check for list-shaped JSON data).
    """
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def walk_mapping(obj: Any, *keys: str) -> Any:
    """
    Walk ``keys`` through nested mappings, returning ``None`` on the first miss.

    Parameters
    ----------
    obj : Any
        The root object to start the walk from.
    keys : str
        Variadic sequence of keys to look up, one level deeper per key.

    Returns
    -------
    Any
        The deeply-nested value, or ``None`` if any hop is missing or not a Mapping.
    """
    for k in keys:
        if not isinstance(obj, Mapping):
            return None
        obj = obj.get(k)
    return obj


def extract_fuel(metrics: MetricsBlock) -> tuple[float | None, float | None]:
    """
    Extract ``(fuel_percent, fuel_range)`` from a telemetry metrics block.

    Units of ``fuel_range`` are governed by ``metrics.displaySystemOfMeasure``. Either element may
    be ``None`` if not present in the response.

    Parameters
    ----------
    metrics : MetricsBlock
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    tuple[float | None, float | None]
        The ``(fuel_percent, fuel_range)`` pair.
    """
    return scalar_metric_value(metrics.get('fuelLevel')), scalar_metric_value(
        metrics.get('fuelRange'))


def extract_position(metrics: MetricsBlock) -> GPSPosition | None:
    """
    Extract the GPS position payload from a telemetry metrics block.

    Parameters
    ----------
    metrics : MetricsBlock
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    GPSPosition | None
        A :py:class:`~fordpass.typing.GPSPosition` with ``lat``, ``lon`` (always present), plus
        optional ``alt``, ``heading``, ``compass``, and ``update_time`` fields; ``None`` when no
        position is reported.
    """
    position_entry = metrics.get('position')
    position_value = scalar_metric_value(position_entry) or {}
    if not isinstance(position_value, Mapping):
        return None
    location = position_value.get('location') or {}
    if not isinstance(location, Mapping):
        return None
    lat, lon = location.get('lat'), location.get('lon')
    if lat is None or lon is None:
        return None
    result: GPSPosition = {'lat': float(lat), 'lon': float(lon)}
    if (alt := location.get('alt')) is not None:
        result['alt'] = float(alt)
    if (heading_value := scalar_metric_value(metrics.get('heading'))) is not None:
        if isinstance(heading_value, Mapping):
            heading_value = heading_value.get('heading')
        if heading_value is not None:
            result['heading'] = float(heading_value)
    if (compass := scalar_metric_value(metrics.get('compassDirection'))) is not None:
        result['compass'] = cast('CompassDirection', str(compass))
    if isinstance(position_entry, Mapping):  # pragma: no branch
        update_time = position_entry.get('updateTime')  # ty: ignore[invalid-argument-type]
        if update_time is not None:
            result['update_time'] = str(update_time)
    return result


def extract_odometer(metrics: MetricsBlock) -> float | None:
    """
    Extract the odometer reading from a telemetry metrics block.

    Parameters
    ----------
    metrics : MetricsBlock
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    float | None
        The odometer value, or ``None`` if not present.
    """
    return cast('float | None', scalar_metric_value(metrics.get('odometer')))


def extract_oil_life(metrics: MetricsBlock) -> float | None:
    """
    Extract the remaining oil-life percentage from a telemetry metrics block.

    Parameters
    ----------
    metrics : MetricsBlock
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    float | None
        The oil-life value, or ``None`` if not present.
    """
    return cast('float | None', scalar_metric_value(metrics.get('oilLifeRemaining')))


def is_washer_fluid_low(alerts_response: AlertsResponse) -> bool:
    """
    Test whether the washer-fluid-low alert (``E19-374-43``) is active.

    Parameters
    ----------
    alerts_response : AlertsResponse
        The parsed body returned by the vehicle-alerts endpoint.

    Returns
    -------
    bool
        ``True`` if the alert appears in ``alerts``; ``False`` otherwise.
    """
    return any(a.get('alertIdentifier') == 'E19-374-43' for a in alerts_response.get('alerts', []))


def find_preferred_dealer_code(garage: Sequence[GarageVehicle]
                               | Mapping[str, Sequence[GarageVehicle]], vin: str) -> str | None:
    """
    Pluck the ``preferredDealer`` PA code for ``vin`` from a garage response.

    Accepts either the bare JSON array shape (current backend) or the ``{"vehicles": [...]}``
    envelope (older firmware).

    Parameters
    ----------
    garage : Sequence[GarageVehicle] | Mapping[str, Sequence[GarageVehicle]]
        The parsed body returned by the user-garage endpoint.
    vin : str
        The VIN to look up.

    Returns
    -------
    str | None
        The PA code, or ``None`` if the VIN is absent or has no preferred dealer.
    """
    entries: Sequence[GarageVehicle]
    if is_list_like(garage):
        entries = cast('Sequence[GarageVehicle]', garage)
    elif isinstance(garage, Mapping):
        inner = garage.get('vehicles')  # ty: ignore[invalid-argument-type]
        entries = cast('Sequence[GarageVehicle]', inner) if is_list_like(inner) else []
    else:
        entries = []
    for v in entries:
        if isinstance(v, Mapping) and v.get('vin') == vin:
            code = v.get('preferredDealer')
            return code if isinstance(code, str) else None
    return None


def find_next_departure(metrics: MetricsBlock) -> DepartureSchedule | None:
    """
    Walk a telemetry metrics block to find the next-up departure schedule.

    Matches the entry whose ``scheduleId`` equals ``xevNextDepartureTimeScheduleId``. EV/PHEV
    only - ICE vehicles will not populate these metrics.

    Parameters
    ----------
    metrics : MetricsBlock
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    DepartureSchedule | None
        The matching schedule dict, or ``None`` if no schedule was identified.
    """
    next_id = scalar_metric_value(metrics.get('xevNextDepartureTimeScheduleId'))
    if next_id is None:
        return None
    next_id_str = str(next_id)
    tree = scalar_metric_value(metrics.get('xevDepartureSchedules')) or {}
    if not isinstance(tree, Mapping):
        return None
    for loc in tree.get('departureLocations', []) or []:
        for s in loc.get('departureSchedules', []) or []:
            if s.get('scheduleId') == next_id_str:
                return cast('DepartureSchedule', s)
    return None


_DEPARTURE_DAY_ORDER: tuple[str, ...] = ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY',
                                         'SATURDAY', 'SUNDAY')
"""
Canonical Monday-to-Sunday ordering for departure-schedule day groups.

:meta hide-value:
"""


def _parse_time_of_day(value: Any) -> dict[str, int]:
    """
    Convert a telemetry ``"HH:MM"`` time string into a ``{hours, minutes}`` mapping.

    Parameters
    ----------
    value : Any
        The ``timeOfDay`` value from the telemetry tree.

    Returns
    -------
    dict[str, int]
        The parsed time, defaulting to midnight (``{'hours': 0, 'minutes': 0}``) when the input is
        missing or malformed.
    """
    if isinstance(value, str):
        hours, _, minutes = value.partition(':')
        if hours.isdigit() and minutes.isdigit():
            return {'hours': int(hours), 'minutes': int(minutes)}
    return {'hours': 0, 'minutes': 0}


def _departure_slot_from_telemetry(slot: Mapping[str, Any], weekly: Mapping[str, Any],
                                   location_id: str) -> dict[str, Any]:
    """
    Convert one telemetry departure slot into the ``updateDepartureTimes`` write shape.

    Field paths follow ha-fordpass: ``scheduleStatus`` and ``scheduleId`` sit on the slot,
    ``timeOfDay`` lives under ``schedule.weeklySchedule``, and the precondition temperature comes
    from ``oemData.chrg_go_t_prcond_d_stat.stringValue``.

    Parameters
    ----------
    slot : Mapping[str, Any]
        One entry from a location's ``departureSchedules`` list.
    weekly : Mapping[str, Any]
        The slot's ``schedule.weeklySchedule`` sub-object.
    location_id : str
        The owning location's identifier, passed through unchanged.

    Returns
    -------
    dict[str, Any]
        The slot in write shape.
    """
    schedule_id = slot.get('scheduleId')
    if isinstance(schedule_id, str) and schedule_id.isdigit():
        schedule_id = int(schedule_id)
    temperature = walk_mapping(slot, 'oemData', 'chrg_go_t_prcond_d_stat', 'stringValue')
    status = slot.get('scheduleStatus')
    return {
        'locationId': location_id,
        'preconditionTemperature': temperature.upper() if isinstance(temperature, str) else 'OFF',
        'scheduleId': schedule_id,
        'scheduleStatus': status.upper() if isinstance(status, str) else 'OFF',
        'timeOfDay': _parse_time_of_day(weekly.get('timeOfDay'))
    }


def extract_departure_schedule_days(metrics: MetricsBlock) -> list[DepartureScheduleDay]:
    """
    Rebuild the ``updateDepartureTimes`` write shape from a telemetry metrics block.

    Walks ``xevDepartureSchedules.value.departureLocations[*].departureSchedules[*]``, converting
    each slot and grouping them by upper-case day name in Monday-to-Sunday order. EV/PHEV only -
    ICE vehicles never populate the parent metric, so the result is empty for them.

    Parameters
    ----------
    metrics : MetricsBlock
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    list[DepartureScheduleDay]
        One entry per day that has at least one slot, ordered Monday to Sunday.
    """
    tree = scalar_metric_value(metrics.get('xevDepartureSchedules'))
    if not isinstance(tree, Mapping):
        return []
    by_day: dict[str, dict[str, Any]] = {}
    for loc in tree.get('departureLocations', []) or []:
        if not isinstance(loc, Mapping):
            continue
        location_id = str(loc.get('locationId', ''))
        for slot in loc.get('departureSchedules', []) or []:
            weekly = walk_mapping(slot, 'schedule', 'weeklySchedule')
            day = weekly.get('dayOfWeek') if isinstance(weekly, Mapping) else None
            if not isinstance(day, str):
                continue
            day = day.upper()
            group = by_day.setdefault(day, {'dayOfWeek': day, 'schedules': []})
            group['schedules'].append(_departure_slot_from_telemetry(slot, weekly, location_id))
    return cast('list[DepartureScheduleDay]',
                [by_day[day] for day in _DEPARTURE_DAY_ORDER if day in by_day])
