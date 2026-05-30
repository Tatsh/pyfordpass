"""Pure helpers that operate on already-fetched FordPass response payloads.

These functions hold no state, perform no I/O, and have no dependency on the client class. They live
here so callers can import the specific helper they need without instantiating
:py:class:`fordpass.sansio.FordPassClient`.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast
import json

if TYPE_CHECKING:
    from .typing import CompassDirection, GPSPosition

__all__ = ('extract_fuel', 'extract_odometer', 'extract_oil_life', 'extract_position',
           'find_next_departure', 'find_preferred_dealer_code', 'is_washer_fluid_low', 'parse_json')


def parse_json(body: bytes) -> Any:
    """
    Decode UTF-8 bytes and parse them as JSON.

    Parameters
    ----------
    body : bytes
        Raw HTTP response body.

    Returns
    -------
    Any
        The parsed JSON value.
    """
    return json.loads(body.decode('utf-8'))


def extract_fuel(metrics: Mapping[str, Any]) -> tuple[float | None, float | None]:
    """
    Extract ``(fuel_percent, fuel_range)`` from a telemetry metrics block.

    Units of ``fuel_range`` are governed by ``metrics.displaySystemOfMeasure``.
    Either element may be ``None`` if not present in the response.

    Parameters
    ----------
    metrics : Mapping[str, Any]
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    tuple[float | None, float | None]
        The ``(fuel_percent, fuel_range)`` pair.
    """
    return ((metrics.get('fuelLevel') or {}).get('value'), (metrics.get('fuelRange')
                                                            or {}).get('value'))


def extract_position(metrics: Mapping[str, Any]) -> GPSPosition | None:
    """
    Extract the GPS position payload from a telemetry metrics block.

    Parameters
    ----------
    metrics : Mapping[str, Any]
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    GPSPosition | None
        A :py:class:`~fordpass.typing.GPSPosition` with ``lat``, ``lon``
        (always present), plus optional ``alt``, ``heading``, ``compass``, and
        ``update_time`` fields; ``None`` when no position is reported.
    """
    position = (metrics.get('position') or {}).get('value') or {}
    location = position.get('location') or {}
    lat, lon = location.get('lat'), location.get('lon')
    if lat is None or lon is None:
        return None
    result: GPSPosition = {'lat': float(lat), 'lon': float(lon)}
    if (alt := location.get('alt')) is not None:
        result['alt'] = float(alt)
    if (heading_value := (metrics.get('heading') or {}).get('value')) is not None:
        if isinstance(heading_value, Mapping):
            heading_value = heading_value.get('heading')
        if heading_value is not None:
            result['heading'] = float(heading_value)
    if (compass := (metrics.get('compassDirection') or {}).get('value')) is not None:
        result['compass'] = cast('CompassDirection', str(compass))
    if (update_time := (metrics.get('position') or {}).get('updateTime')) is not None:
        result['update_time'] = str(update_time)
    return result


def extract_odometer(metrics: Mapping[str, Any]) -> float | None:
    """
    Extract the odometer reading from a telemetry metrics block.

    Parameters
    ----------
    metrics : Mapping[str, Any]
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    float | None
        The odometer value, or ``None`` if not present.
    """
    return (metrics.get('odometer') or {}).get('value')


def extract_oil_life(metrics: Mapping[str, Any]) -> float | None:
    """
    Extract the remaining oil-life percentage from a telemetry metrics block.

    Parameters
    ----------
    metrics : Mapping[str, Any]
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    float | None
        The oil-life value, or ``None`` if not present.
    """
    return (metrics.get('oilLifeRemaining') or {}).get('value')


def is_washer_fluid_low(alerts_response: Mapping[str, Any]) -> bool:
    """
    Test whether the washer-fluid-low alert (``E19-374-43``) is active.

    Parameters
    ----------
    alerts_response : Mapping[str, Any]
        The parsed body returned by the vehicle-alerts endpoint.

    Returns
    -------
    bool
        ``True`` if the alert appears in ``alerts``; ``False`` otherwise.
    """
    for a in alerts_response.get('alerts', []) or []:
        if a.get('alertIdentifier') == 'E19-374-43':
            return True
    return False


def find_preferred_dealer_code(garage: Any, vin: str) -> str | None:
    """
    Pluck the ``preferredDealer`` PA code for ``vin`` from a garage response.

    Accepts either the bare JSON array shape (current backend) or the
    ``{"vehicles": [...]}`` envelope (older firmware).

    Parameters
    ----------
    garage : Any
        The parsed body returned by the user-garage endpoint.
    vin : str
        The VIN to look up.

    Returns
    -------
    str | None
        The PA code, or ``None`` if the VIN is absent or has no preferred dealer.
    """
    if isinstance(garage, list):
        entries = garage
    elif isinstance(garage, Mapping):
        inner = garage.get('vehicles')
        entries = inner if isinstance(inner, list) else []
    else:
        entries = []
    for v in entries:
        if isinstance(v, Mapping) and v.get('vin') == vin:
            code = v.get('preferredDealer')
            return code if isinstance(code, str) else None
    return None


def find_next_departure(metrics: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """
    Walk a telemetry metrics block to find the next-up departure schedule.

    Matches the entry whose ``scheduleId`` equals
    ``xevNextDepartureTimeScheduleId``. EV/PHEV only — ICE vehicles will not
    populate these metrics.

    Parameters
    ----------
    metrics : Mapping[str, Any]
        The ``metrics`` sub-object of a telemetry response.

    Returns
    -------
    Mapping[str, Any] | None
        The matching schedule dict, or ``None`` if no schedule was identified.
    """
    next_id = (metrics.get('xevNextDepartureTimeScheduleId') or {}).get('value')
    if next_id is None:
        return None
    next_id_str = str(next_id)
    tree = (metrics.get('xevDepartureSchedules') or {}).get('value') or {}
    for loc in tree.get('departureLocations', []) or []:
        for s in loc.get('departureSchedules', []) or []:
            if s.get('scheduleId') == next_id_str:
                return cast('Mapping[str, Any]', s)
    return None
