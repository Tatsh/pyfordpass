"""Persistent CLI configuration loaded from ``~/.config/pyfordpass/config.toml``."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

if TYPE_CHECKING:
    from fordpass.typing.common import DistanceUnit, TemperatureUnit

__all__ = ('Config', 'HTTPConfig', 'OutputConfig', 'OutputFormat', 'UnitsConfig', 'VehicleConfig')

OutputFormat: TypeAlias = Literal['json', 'pretty']
"""
Preferred output format for multi-value command responses.

:meta hide-value:
"""


class UnitsConfig(TypedDict, total=False):
    """Unit preferences read from the user's ``config.toml``."""

    distance: DistanceUnit
    """Preferred distance unit: ``'mi'`` (miles) or ``'km'`` (kilometres)."""
    temperature: TemperatureUnit
    """Preferred temperature unit: ``'F'`` (Fahrenheit) or ``'C'`` (Celsius)."""


class VehicleConfig(TypedDict, total=False):
    """Vehicle-related preferences read from ``[vehicle]``."""

    default_vin: str
    """Fallback VIN used when the CLI ``VIN`` argument is omitted."""


class OutputConfig(TypedDict, total=False):
    """Output-format preferences read from ``[output]``."""

    format: OutputFormat
    """``'pretty'`` (Rich tables; default) or ``'json'`` (machine-readable)."""


class HTTPConfig(TypedDict, total=False):
    """HTTP-transport preferences read from ``[http]``."""

    impersonate: str
    """
    curl-cffi browser-impersonation profile used for the OAuth/token endpoints
    (e.g. ``'chrome146'``, ``'firefox144'``, ``'safari180'``). Defaults to
    ``'chrome146'`` when unset.
    """


class Config(TypedDict, total=False):
    """Persistent CLI configuration loaded from ``~/.config/pyfordpass/config.toml``."""

    http: HTTPConfig
    """HTTP-transport preferences."""
    output: OutputConfig
    """Output-format preferences."""
    units: UnitsConfig
    """Display-unit preferences."""
    vehicle: VehicleConfig
    """Vehicle-related defaults (such as the fallback VIN)."""
