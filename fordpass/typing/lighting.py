"""Ford MPS zone-lighting request shapes."""
from __future__ import annotations

from typing import Literal, TypeAlias

__all__ = ('ZONE_LIGHT_OFF', 'ZoneLightZone')

ZoneLightZone: TypeAlias = Literal['0', '1', '2', '3', '4', 'off']
"""
Wire value accepted by the zone-lighting endpoints.

``'0'`` lights every zone (the default), ``'1'`` front, ``'2'`` rear, ``'3'`` driver side, ``'4'``
passenger side, and ``'off'`` is the sentinel meaning "turn the lights off" rather than a zone.

:meta hide-value:
"""

ZONE_LIGHT_OFF: ZoneLightZone = 'off'
"""
Sentinel :py:data:`ZoneLightZone` value meaning the lights should be turned off.

:meta hide-value:
"""
