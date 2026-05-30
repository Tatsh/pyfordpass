"""Loader for the user's CLI configuration file.

Reads ``~/.config/fordpass/config.toml`` (via :mod:`platformdirs`) and fills in
locale-derived defaults so callers can dereference any configured key directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
import os

from platformdirs import user_config_dir
import tomlkit

if TYPE_CHECKING:
    from fordpass.typing import (
        Config,
        DistanceUnit,
        OutputConfig,
        OutputFormat,
        TemperatureUnit,
        UnitsConfig,
        VehicleConfig,
    )

__all__ = ('CONFIG_DIR', 'CONFIG_FILE', 'KM_PER_MILE', 'KM_TO_MI', 'KPA_PER_PSI', 'KPA_TO_PSI',
           'OUTPUT_ENV_VAR', 'load_config', 'resolve_output_format')

OUTPUT_ENV_VAR = 'FORDPASS_OUTPUT'
"""Name of the environment variable that overrides the configured output format.

Accepted values are ``'json'`` and ``'pretty'`` (case-insensitive).

:meta hide-value:
"""

CONFIG_DIR = Path(user_config_dir(appname='fordpass', appauthor=False))
"""Directory holding the user configuration file (``~/.config/fordpass`` on Linux).

:meta hide-value:
"""

CONFIG_FILE = CONFIG_DIR / 'config.toml'
"""Path to the user configuration TOML.

:meta hide-value:
"""

KM_PER_MILE = 1.609344
"""Exact conversion factor: one statute mile in kilometres.

:meta hide-value:
"""

KM_TO_MI = 1.0 / KM_PER_MILE
"""Multiplier converting a kilometre value to miles.

:meta hide-value:
"""

KPA_PER_PSI = 6.89475729
"""Exact conversion factor: one PSI in kilopascals.

:meta hide-value:
"""

KPA_TO_PSI = 1.0 / KPA_PER_PSI
"""Multiplier converting a kilopascal value to PSI.

:meta hide-value:
"""

_MILES_LOCALES = frozenset({'en-gb', 'en-us'})
"""Locales whose users typically prefer miles for road distance.

:meta hide-value:
"""

_FAHRENHEIT_LOCALES = frozenset({'en-us'})
"""Locales whose users typically prefer Fahrenheit for temperature.

The United Kingdom uses miles for road distance but Celsius for temperature, so it is intentionally
absent from this set even though it appears in :data:`_MILES_LOCALES`.

:meta hide-value:
"""


def _normalise_locale(raw: str) -> str:
    """
    Normalise a BCP-47 / POSIX locale tag to lowercase ``aa-bb`` form.

    Parameters
    ----------
    raw : str
        A locale string such as ``en_US.UTF-8``, ``en-GB``, or ``fr_FR``.

    Returns
    -------
    str
        The leading language-region pair, lower-cased, with underscore
        rewritten to hyphen, and codeset stripped.
    """
    return raw.split('.', 1)[0].replace('_', '-').lower()


def _default_distance_unit(locale: str | None = None) -> DistanceUnit:
    """
    Derive the default distance unit from a locale tag.

    The supplied ``locale`` (typically :attr:`fordpass.client.FordPassNiquestsClient.locale`)
    takes precedence; when it is ``None`` the active POSIX locale environment
    variables are inspected instead.

    Parameters
    ----------
    locale : str | None
        Explicit locale tag (BCP-47, e.g. ``'en-US'``). When ``None`` the
        ``LC_ALL`` / ``LC_MEASUREMENT`` / ``LANG`` env vars are consulted.

    Returns
    -------
    DistanceUnit
        ``'mi'`` when the resolved locale is ``en-US`` or ``en-GB``;
        ``'km'`` otherwise.
    """
    raw = locale or (os.environ.get('LC_ALL') or os.environ.get('LC_MEASUREMENT')
                     or os.environ.get('LANG') or '')
    return 'mi' if _normalise_locale(raw) in _MILES_LOCALES else 'km'


def _default_temperature_unit(locale: str | None = None) -> TemperatureUnit:
    """
    Derive the default temperature unit from a locale tag.

    Parameters
    ----------
    locale : str | None
        Explicit locale tag (e.g. ``'en-US'``). When ``None`` the
        ``LC_ALL`` / ``LC_MEASUREMENT`` / ``LANG`` env vars are consulted.

    Returns
    -------
    TemperatureUnit
        ``'F'`` when the resolved locale is ``en-US``; ``'C'`` otherwise
        (including ``en-GB``, which uses Celsius despite using miles).
    """
    raw = locale or (os.environ.get('LC_ALL') or os.environ.get('LC_MEASUREMENT')
                     or os.environ.get('LANG') or '')
    return 'F' if _normalise_locale(raw) in _FAHRENHEIT_LOCALES else 'C'


def load_config(*, locale: str | None = None) -> Config:
    """
    Read the user config TOML and merge in locale-derived defaults.

    Parameters
    ----------
    locale : str | None
        Optional explicit locale (e.g. ``client.locale``, ``'en-US'``) used to
        seed the default distance unit. When ``None`` the OS locale env vars
        are inspected as a fallback.

    Returns
    -------
    Config
        The merged configuration. Missing keys are populated so callers can
        dereference ``load_config()['units']['distance']`` unconditionally.
    """
    raw: dict[str, Any] = {}
    if CONFIG_FILE.exists():
        raw = tomlkit.loads(CONFIG_FILE.read_text()).unwrap()
    units_raw = raw.get('units') or {}
    distance = units_raw.get('distance')
    if distance not in {'km', 'mi'}:
        distance = _default_distance_unit(locale)
    temperature = units_raw.get('temperature')
    if isinstance(temperature, str):
        temperature = temperature.upper()
    if temperature not in {'C', 'F'}:
        temperature = _default_temperature_unit(locale)
    units: UnitsConfig = {
        'distance': cast('DistanceUnit', distance),
        'temperature': cast('TemperatureUnit', temperature)
    }
    vehicle_raw = raw.get('vehicle') or {}
    vehicle: VehicleConfig = {}
    default_vin = vehicle_raw.get('default_vin')
    if isinstance(default_vin, str) and default_vin:
        vehicle['default_vin'] = default_vin
    output_raw = raw.get('output') or {}
    output: OutputConfig = {}
    fmt = output_raw.get('format')
    if fmt in {'json', 'pretty'}:
        output['format'] = fmt
    return {'output': output, 'units': units, 'vehicle': vehicle}


def resolve_output_format(*, cli_json: bool = False) -> OutputFormat:
    """
    Resolve the effective output format for a command.

    Precedence (highest first): the ``--json`` CLI flag, the ``FORDPASS_OUTPUT``
    environment variable, ``[output] format`` in ``config.toml``, then the
    built-in default of ``'pretty'``.

    Parameters
    ----------
    cli_json : bool
        ``True`` when the caller's ``--json`` flag was passed.

    Returns
    -------
    OutputFormat
        ``'json'`` or ``'pretty'``.
    """
    if cli_json:
        return 'json'
    env = (os.environ.get(OUTPUT_ENV_VAR) or '').strip().lower()
    if env in {'json', 'pretty'}:
        return cast('OutputFormat', env)
    cfg_fmt = (load_config().get('output') or {}).get('format')
    if cfg_fmt in {'json', 'pretty'}:
        return cfg_fmt
    return 'pretty'
