"""Cross-cutting type aliases and primitive shapes used across the FordPass typing tree."""
from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict

__all__ = ('CompassDirection', 'CountryHeaderCasing', 'DistanceUnit', 'EngineType', 'GPSPosition',
           'TemperatureUnit', 'TokenType', 'UserAuthStatus', 'VehicleBrand')

CompassDirection: TypeAlias = Literal['EAST', 'NORTH', 'NORTHEAST', 'NORTHWEST', 'SOUTH',
                                      'SOUTHEAST', 'SOUTHWEST', 'WEST']
"""
One of the eight cardinal/intercardinal directions reported by ``compassDirection``.

:meta hide-value:
"""

CountryHeaderCasing: TypeAlias = Literal['Country-Code', 'country-code', 'countryCode',
                                         'countrycode']
"""
Exact spelling of the country header expected by a Ford gateway endpoint.

The Ford gateway is strict about per-endpoint casing despite RFC 7230 calling header
names case-insensitive. Four casings appear across the API surface, each used by a
different microservice; see :py:meth:`fordpass.sansio.FordPassClient._ford_headers`
for which endpoints consume which casing.

:meta hide-value:
"""

DistanceUnit: TypeAlias = Literal['km', 'mi']
"""
Preferred distance unit.

:meta hide-value:
"""

EngineType: TypeAlias = Literal['BEV', 'FCV', 'HEV', 'ICE', 'PHEV']
"""
Powertrain category: internal-combustion, battery EV, plug-in hybrid, etc.

:meta hide-value:
"""

TemperatureUnit: TypeAlias = Literal['C', 'F']
"""
Preferred temperature unit (Celsius / Fahrenheit).

:meta hide-value:
"""

TokenType: TypeAlias = Literal['Bearer']
"""
OAuth-style ``token_type`` echoed in token responses.

:meta hide-value:
"""

UserAuthStatus: TypeAlias = Literal['Authorized', 'Declined', 'Pending']
"""
User-authorisation status on a vehicle.

:meta hide-value:
"""

VehicleBrand: TypeAlias = Literal['Ford', 'Lincoln']
"""
Marketing brand of a vehicle.

:meta hide-value:
"""


class GPSPosition(TypedDict, total=False):
    """Normalised GPS payload returned by :py:func:`fordpass.utils.extract_position`."""

    alt: float
    """Altitude in metres above the WGS-84 ellipsoid."""
    compass: CompassDirection
    """Cardinal direction (``'NORTH'``, ``'NORTHEAST'``, …)."""
    heading: float
    """Heading in degrees (``0`` = north, ``90`` = east)."""
    lat: float
    """Latitude in decimal degrees."""
    lon: float
    """Longitude in decimal degrees."""
    update_time: str
    """ISO-8601 timestamp of the fix."""
