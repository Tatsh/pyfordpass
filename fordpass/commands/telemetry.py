"""One-shot telemetry queries (fuel, odometer, oil, tires)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
import json
import re
import urllib.parse
import webbrowser

from fordpass.config import KM_TO_MI, KPA_TO_PSI, load_config
from rich.table import Table
import click

from .utils import console, dump_json, json_option, should_emit_json, vin_argument, with_client

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fordpass.client import FordPassNiquestsClient


@click.group()
def telemetry() -> None:
    """One-shot telemetry queries."""


@telemetry.command('fuel')
@vin_argument
@json_option
@with_client
async def telemetry_fuel(client: FordPassNiquestsClient, _ctx: click.Context, vin: str, *,
                         as_json: bool) -> None:
    """Fuel level + range."""
    pct, rng = await client.get_fuel_level(vin)
    if should_emit_json(as_json):
        dump_json({'level_pct': pct, 'range': rng})
        return
    click.echo(f'fuel: {pct}%' if pct is not None else 'fuel: unknown')
    click.echo(f'range: {rng}' if rng is not None else 'range: unknown')


_DISTANCE_UNIT_ALIASES = {
    'km': 'km',
    'kilometers': 'km',
    'kilometres': 'km',
    'mi': 'mi',
    'miles': 'mi',
}
"""Map of accepted ``--unit`` values to the canonical short form.

:meta hide-value:
"""


@telemetry.command('odometer')
@vin_argument
@click.option('-u',
              '--unit',
              type=click.Choice(sorted(_DISTANCE_UNIT_ALIASES), case_sensitive=False),
              default=None,
              help='Override the distance unit from `config.toml` for this call.')
@with_client
async def telemetry_odometer(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                             unit: str | None) -> None:
    """Vehicle odometer reading."""
    km = await client.get_odometer(vin)
    if km is None:
        click.echo('unknown')
        return
    pref = (_DISTANCE_UNIT_ALIASES[unit.lower()] if unit is not None else load_config(
        locale=client.locale)['units']['distance'])
    if pref == 'mi':
        click.echo(f'{km * KM_TO_MI:.1f} mi')
        return
    click.echo(f'{km:.1f} km')


@telemetry.command('oil')
@vin_argument
@with_client
async def telemetry_oil(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Oil life remaining (%)."""
    pct = await client.get_oil_life(vin)
    click.echo('unknown' if pct is None else f'{pct}%')


_WHEEL_ORDER = ('FRONT_LEFT', 'FRONT_RIGHT', 'REAR_LEFT', 'REAR_RIGHT', 'REAR_LEFT_INNER',
                'REAR_LEFT_OUTER', 'REAR_RIGHT_INNER', 'REAR_RIGHT_OUTER')
"""Canonical display order for wheels in the tire-pressure printout.

:meta hide-value:
"""

_TIRE_OK_RATIO = 0.93
"""Minimum measured/placard pressure ratio rendered as ``OK``.

:meta hide-value:
"""

_TIRE_LOW_RATIO = 0.85
"""Minimum measured/placard pressure ratio rendered as ``LOW`` (below this is ``ALERT``).

:meta hide-value:
"""

_JSON_CELL_MAX = 60
"""Maximum length of a JSON-serialised value rendered inline in a table cell.

:meta hide-value:
"""


@telemetry.command('tires')
@vin_argument
@click.option('-u',
              '--unit',
              type=click.Choice(sorted(_DISTANCE_UNIT_ALIASES), case_sensitive=False),
              default=None,
              help='Override the distance unit from `config.toml` for this call '
              '(also selects PSI when `mi`, kPa when `km`).')
@json_option
@with_client
async def telemetry_tires(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                          unit: str | None, *, as_json: bool) -> None:
    """Per-wheel tire pressure."""
    entries = await client.get_tire_pressure(vin)
    if should_emit_json(as_json):
        dump_json(entries)
        return
    if not entries:
        click.echo('(no tire pressure data)')
        return
    pref = (_DISTANCE_UNIT_ALIASES[unit.lower()] if unit is not None else load_config(
        locale=client.locale)['units']['distance'])
    use_psi = pref == 'mi'
    unit_label = 'PSI' if use_psi else 'kPa'

    def _fmt(kpa: float | None) -> str:
        if kpa is None:
            return '?'
        v = kpa * KPA_TO_PSI if use_psi else float(kpa)
        return f'{v:.1f}'

    rows = sorted(entries,
                  key=lambda e: (_WHEEL_ORDER.index(e.get('vehicleWheel'))
                                 if e.get('vehicleWheel') in _WHEEL_ORDER else 99))
    table = Table(title='Tire pressure', title_style='bold cyan')
    table.add_column('Wheel', style='cyan')
    table.add_column(f'Pressure ({unit_label})', justify='right')
    table.add_column('Recommended', justify='right', style='dim')
    table.add_column('Status')
    for e in rows:
        wheel = e.get('vehicleWheel') or '?'
        pressure_val = e.get('value')
        placard = e.get('wheelPlacardFront') if 'FRONT' in wheel else e.get('wheelPlacardRear')
        if (isinstance(pressure_val, (int, float)) and isinstance(placard, (int, float))
                and placard > 0):
            ratio = pressure_val / placard
            status = ('[green]OK[/green]' if ratio >= _TIRE_OK_RATIO else
                      '[yellow]LOW[/yellow]' if ratio >= _TIRE_LOW_RATIO else '[red]ALERT[/red]')
        else:
            status = '[dim]?[/dim]'
        table.add_row(wheel.replace('_', ' ').title(), _fmt(pressure_val), _fmt(placard), status)
    console.print(table)


_METRIC_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('Powertrain', ('engineSpeed', 'engineCoolantTemp', 'engineOilTemp', 'oilLifeRemaining',
                    'fuelLevel', 'fuelRange', 'gearLeverPosition', 'ignitionStatus',
                    'stopStartModeStatus', 'speed', 'odometer')),
    ('Motion', ('position', 'heading', 'compassDirection', 'yawRate', 'acceleration',
                'acceleratorPedalPosition', 'brakePedalStatus', 'brakeTorque',
                'torqueAtTransmission', 'wheelTorqueStatus')),
    ('Battery', ('batteryLoadStatus', 'batteryStateOfCharge', 'batteryVoltage')),
    ('Environment', ('ambientTemp', 'outsideTemperature')),
    ('Security & Status', ('alarmStatus', 'panicAlarmStatus', 'parkingBrakeStatus',
                           'vehicleLifeCycleMode', 'remoteStartCountdownTimer')),
    ('Tires', ('tirePressure', 'tirePressureStatus', 'tirePressureSystemStatus')),
    ('Doors & Body', ('doorStatus', 'doorLockStatus', 'hoodStatus')),
    ('Seats', ('seatBeltStatus', 'seatOccupancyStatus')),
    ('Display', ('displaySystemOfMeasure',)),
)
"""Display grouping for :command:`telemetry all` pretty output.

Each entry is ``(group_title, ordered_metric_keys)``. Metrics not listed in any
group fall into an automatic ``Other`` table so new upstream fields surface
rather than silently disappear.

:meta hide-value:
"""

_ENUM_RE = re.compile(r'^[A-Z][A-Z0-9_]+$')
"""Detect SCREAMING_SNAKE_CASE values like ``NORMAL_OPERATION`` or ``FRONT_LEFT``.

:meta hide-value:
"""

_WHEEL_SHORT = {
    'FRONT_LEFT': 'FL',
    'FRONT_RIGHT': 'FR',
    'REAR_LEFT': 'RL',
    'REAR_RIGHT': 'RR',
    'REAR_LEFT_INNER': 'RLI',
    'REAR_LEFT_OUTER': 'RLO',
    'REAR_RIGHT_INNER': 'RRI',
    'REAR_RIGHT_OUTER': 'RRO',
    'SYSTEM': 'SYS'
}
"""Compact two-or-three-letter wheel labels for tire-pressure summaries.

:meta hide-value:
"""

_UNIT_SUFFIXES = {
    'fuelLevel': '%',
    'oilLifeRemaining': '%',
    'batteryStateOfCharge': '%',
    'batteryVoltage': ' V',
    'engineSpeed': ' rpm'
}
"""Static unit suffix appended after the scalar value of these metrics.

Temperature metrics deliberately omitted — they go through :py:func:`_format_temperature` which
honours :py:data:`UnitsConfig.temperature`.

:meta hide-value:
"""

_DISTANCE_METRICS: frozenset[str] = frozenset({'odometer', 'fuelRange'})
"""Scalar metrics whose raw value is kilometres; converted on demand to miles.

:meta hide-value:
"""

_SPEED_METRICS: frozenset[str] = frozenset({'speed'})
"""Scalar metrics whose raw value is km/h; converted on demand to mph.

:meta hide-value:
"""

_TEMPERATURE_METRICS: frozenset[str] = frozenset(
    {'ambientTemp', 'engineCoolantTemp', 'engineOilTemp', 'outsideTemperature'})
"""Scalar metrics whose raw value is degrees Celsius.

:meta hide-value:
"""


def _format_temperature(celsius: float, pref_temperature: str) -> str:
    """
    Render a Celsius temperature value in the user's preferred unit.

    Parameters
    ----------
    celsius : float
        The raw value (always Celsius per TMC telemetry convention).
    pref_temperature : str
        ``'F'`` to convert to Fahrenheit; ``'C'`` to leave alone.

    Returns
    -------
    str
        Display string with the appropriate ``°C`` or ``°F`` suffix.
    """
    if pref_temperature == 'F':
        return f'{celsius * 9.0 / 5.0 + 32.0:.1f}°F'
    return f'{celsius:.1f}°C'


def _humanize_key(key: str) -> str:
    """
    Render a camelCase metric key as title-spaced text.

    Parameters
    ----------
    key : str
        Camel-case key from the telemetry response (e.g. ``'oilLifeRemaining'``).

    Returns
    -------
    str
        Spaced form (e.g. ``'Oil Life Remaining'``).
    """
    spaced = re.sub(r'(?<!^)([A-Z])', r' \1', key)
    return spaced[:1].upper() + spaced[1:]


def _humanize_enum(value: str) -> str:
    """
    Convert ``SCREAMING_SNAKE_CASE`` to sentence case, leaving other strings intact.

    Parameters
    ----------
    value : str
        Candidate string value.

    Returns
    -------
    str
        ``'Normal operation'`` for ``'NORMAL_OPERATION'``; ``value`` unchanged otherwise.
    """
    if not _ENUM_RE.match(value):
        return value
    return value.replace('_', ' ').capitalize()


def _format_scalar(key: str, value: Any, pref_distance: str, pref_temperature: str) -> str:
    """
    Format the inner ``value`` field of a typical telemetry metric.

    Parameters
    ----------
    key : str
        The metric key (used to pick unit conversion / suffix).
    value : Any
        The raw scalar value (``str`` for enums, ``float`` / ``int`` for numerics).
    pref_distance : str
        ``'mi'`` or ``'km'`` from :py:func:`fordpass.config.load_config`.
    pref_temperature : str
        ``'F'`` or ``'C'`` from :py:func:`fordpass.config.load_config`.

    Returns
    -------
    str
        Display-ready string with any appropriate unit suffix appended.
    """
    if value is None:
        return '-'
    if isinstance(value, str):
        return _humanize_enum(value)
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, (int, float)):
        return _format_numeric(key, value, pref_distance, pref_temperature)
    return str(value)


def _format_numeric(key: str, value: float, pref_distance: str, pref_temperature: str) -> str:
    """
    Format a numeric metric value, applying unit conversion and suffixes.

    Parameters
    ----------
    key : str
        The metric key (used to pick unit conversion / suffix).
    value : int | float
        The raw numeric value.
    pref_distance : str
        ``'mi'`` or ``'km'`` from :py:func:`fordpass.config.load_config`.
    pref_temperature : str
        ``'F'`` or ``'C'`` from :py:func:`fordpass.config.load_config`.

    Returns
    -------
    str
        Display-ready string with any appropriate unit suffix appended.
    """
    numeric = float(value)
    if key in _DISTANCE_METRICS:
        return f'{numeric * KM_TO_MI:.1f} mi' if pref_distance == 'mi' else f'{numeric:.1f} km'
    if key in _SPEED_METRICS:
        return f'{numeric * KM_TO_MI:.1f} mph' if pref_distance == 'mi' else f'{numeric:.1f} km/h'
    if key in _TEMPERATURE_METRICS:
        return _format_temperature(numeric, pref_temperature)
    suffix = _UNIT_SUFFIXES.get(key, '')
    if isinstance(value, int) and not suffix:
        return str(value)
    return f'{numeric:.1f}{suffix}'


def _format_nested(key: str, value: dict[str, Any]) -> str | None:
    """
    Render the value-dict shape of a known nested-metric (e.g. position, acceleration).

    Parameters
    ----------
    key : str
        The metric key.
    value : dict[str, Any]
        The ``entry['value']`` payload.

    Returns
    -------
    str | None
        Display string when ``key`` has a known nested shape, ``None`` otherwise.
    """
    if key == 'position':
        loc = value.get('location') or {}
        lat, lon, alt = loc.get('lat'), loc.get('lon'), loc.get('alt')
        if lat is None or lon is None:
            return None
        parts = [f'{lat:.4f}, {lon:.4f}']
        if alt is not None:
            parts.append(f'alt {alt:.0f} m')
        return '  '.join(parts)
    if key == 'heading':
        h = value.get('heading')
        return f'{float(h):.0f}°' if h is not None else None
    if key == 'acceleration':
        return (f'({value.get("x", 0):.2f}, {value.get("y", 0):.2f}, '
                f'{value.get("z", 0):.2f})')
    return None


def _format_list_metric(key: str, entries: list[dict[str, Any]], pref_distance: str) -> str:
    """
    Summarise a list-shaped metric (tires, doors, locks, seats) on a single line.

    Parameters
    ----------
    key : str
        The metric key.
    entries : list[dict[str, Any]]
        The per-instance entries from ``metrics[<key>]``.
    pref_distance : str
        ``'mi'`` (use PSI) or ``'km'`` (use kPa) for tire-pressure entries.

    Returns
    -------
    str
        A compact, humanised summary line.
    """
    if not entries:
        return '-'
    if key == 'tirePressure':
        use_psi = pref_distance == 'mi'
        parts = []
        for e in sorted(entries, key=lambda x: x.get('vehicleWheel') or ''):
            wheel = _WHEEL_SHORT.get(e.get('vehicleWheel') or '', '?')
            val = e.get('value')
            if isinstance(val, (int, float)):
                converted = val * KPA_TO_PSI if use_psi else val
                parts.append(f'{wheel} {converted:.1f}')
            else:
                parts.append(f'{wheel} ?')
        unit = 'PSI' if use_psi else 'kPa'
        return ' / '.join(parts) + f' {unit}'
    if key in {'tirePressureStatus', 'tirePressureSystemStatus'}:
        statuses = {e.get('value') for e in entries}
        if statuses in ({'NORMAL'}, {'NORMAL_OPERATION'}):
            return 'All normal'
        return ', '.join(f'{_WHEEL_SHORT.get(e.get("vehicleWheel") or "", "?")} '
                         f'{_humanize_enum(str(e.get("value") or "?"))}' for e in entries)
    if key == 'doorStatus':
        open_doors = [e for e in entries if (e.get('value') or '') not in {'CLOSED', ''}]
        if not open_doors:
            return 'All closed'
        labels = [_humanize_enum(str(e.get('vehicleDoor') or '?')) for e in open_doors]
        return f'{len(open_doors)} open: ' + ', '.join(labels)
    if key == 'doorLockStatus':
        unlocked = [e for e in entries if (e.get('value') or '') not in {'LOCKED', ''}]
        if not unlocked:
            return 'All locked'
        return ', '.join(f'{_humanize_enum(str(e.get("vehicleDoor") or "?"))}: '
                         f'{_humanize_enum(str(e.get("value") or "?"))}' for e in entries)
    if key in {'seatBeltStatus', 'seatOccupancyStatus'}:
        return ', '.join(f'{_humanize_enum(str(e.get("vehicleOccupantRole") or "?"))}: '
                         f'{_humanize_enum(str(e.get("value") or "?"))}' for e in entries)
    # Fallback: list length only — better than dumping raw JSON.
    return f'{len(entries)} entries'


def _format_metric_value(key: str, entry: Any, pref_distance: str, pref_temperature: str) -> str:
    """
    Top-level dispatcher converting a telemetry entry into a display string.

    Parameters
    ----------
    key : str
        The metric key.
    entry : Any
        Raw ``metrics[<key>]`` payload.
    pref_distance : str
        ``'mi'`` or ``'km'`` from the user's resolved distance preference.
    pref_temperature : str
        ``'F'`` or ``'C'`` from the user's resolved temperature preference.

    Returns
    -------
    str
        A short, humanised value ready for a Rich cell.
    """
    if entry is None:
        return '-'
    if isinstance(entry, list):
        return _format_list_metric(key, entry, pref_distance)
    if not isinstance(entry, dict):
        return str(entry)
    value = entry.get('value', entry)
    if isinstance(value, dict):
        rendered = _format_nested(key, value)
        if rendered is not None:
            return rendered
        text = json.dumps(value, default=str)
        return text if len(text) <= _JSON_CELL_MAX else text[:_JSON_CELL_MAX - 3] + '...'
    if isinstance(value, list):
        return _format_list_metric(key, value, pref_distance)
    return _format_scalar(key, value, pref_distance, pref_temperature)


def _format_metric_updated(entry: Any) -> str:
    """
    Extract and shorten the ``updateTime`` of a metric entry.

    Returns
    -------
    str
        The shortened timestamp, or an empty string when none is present.
    """
    if isinstance(entry, dict):
        ts = entry.get('updateTime')
        if not ts and isinstance(entry.get('value'), dict):
            ts = entry['value'].get('updateTime')
        return str(ts).replace('T', ' ').replace('Z', '').split('.', 1)[0] if ts else ''
    if isinstance(entry, list) and entry:
        first = entry[0]
        if isinstance(first, dict):
            ts = first.get('updateTime')
            return (str(ts).replace('T', ' ').replace('Z', '').split('.', 1)[0] if ts else '')
    return ''


def _telemetry_table(title: str, metrics: Mapping[str, object], keys: tuple[str, ...],
                     pref_distance: str, pref_temperature: str) -> Table | None:
    """
    Build one Rich :py:class:`~rich.table.Table` for a metric group.

    Parameters
    ----------
    title : str
        Title to display above the table.
    metrics : dict[str, Any]
        The ``metrics`` block from the telemetry response.
    keys : tuple[str, ...]
        Ordered metric names that belong to this group.
    pref_distance : str
        ``'mi'`` or ``'km'`` from the user's resolved distance preference.
    pref_temperature : str
        ``'F'`` or ``'C'`` from the user's resolved temperature preference.

    Returns
    -------
    Table | None
        The populated table, or ``None`` when none of ``keys`` were present.
    """
    present = sorted((k for k in keys if k in metrics), key=_humanize_key)
    if not present:
        return None
    table = Table(title=title, title_style='bold cyan')
    table.add_column('Metric', style='cyan')
    table.add_column('Value')
    table.add_column('Updated', style='dim')
    for k in present:
        entry = metrics[k]
        table.add_row(_humanize_key(k),
                      _format_metric_value(k, entry, pref_distance, pref_temperature),
                      _format_metric_updated(entry))
    return table


def _indicators_table(entry: Any) -> Table | None:
    """
    Render the ``indicators`` metric as a table of currently-active warnings.

    The metric is a dict of per-warning ``{value: bool}`` entries; only the
    indicators whose value is truthy are shown.

    Parameters
    ----------
    entry : Any
        The raw ``metrics['indicators']`` payload.

    Returns
    -------
    Table | None
        A table of active indicators, or ``None`` when the metric is missing
        or its inner ``value`` block is absent.
    """
    if not isinstance(entry, dict):
        return None
    inner = entry.get('value')
    if not isinstance(inner, dict) or not inner:
        return None
    active = sorted(
        (name for name, sub in inner.items() if isinstance(sub, dict) and sub.get('value')),
        key=_humanize_key)
    table = Table(title='Indicators', title_style='bold cyan')
    table.add_column('Indicator', style='cyan')
    table.add_column('Active')
    if not active:
        table.add_row(f'({len(inner)} monitored)', '[green]none active[/green]')
        return table
    for name in active:
        table.add_row(_humanize_key(name), '[red]Active[/red]')
    return table


def _configurations_table(entry: Any, pref_distance: str, pref_temperature: str) -> Table | None:
    """
    Render the ``configurations`` metric — a dict of vehicle settings — as a table.

    Parameters
    ----------
    entry : Any
        The raw ``metrics['configurations']`` payload.
    pref_distance : str
        ``'mi'`` or ``'km'`` (currently unused; reserved for distance-typed settings).
    pref_temperature : str
        ``'F'`` or ``'C'`` (currently unused; reserved for temperature-typed settings).

    Returns
    -------
    Table | None
        A table of configuration settings, or ``None`` when the metric is missing
        or its inner ``value`` block is absent.
    """
    if not isinstance(entry, dict):
        return None
    inner_raw = entry.get('value')
    if not isinstance(inner_raw, dict) or not inner_raw:
        return None
    inner = cast('dict[str, Any]', inner_raw)
    table = Table(title='Configurations', title_style='bold cyan')
    table.add_column('Setting', style='cyan')
    table.add_column('Value')
    table.add_column('Updated', style='dim')
    for name in sorted(inner, key=_humanize_key):
        sub = inner[name]
        if not isinstance(sub, dict):
            table.add_row(_humanize_key(name), str(sub), '')
            continue
        if 'error' in sub:
            err = sub['error']
            err_text = (f'[red]error: {err.get("errorName", "?")} '
                        f'({err.get("errorSource", "?")})[/red]'
                        if isinstance(err, dict) else '[red]error[/red]')
            table.add_row(_humanize_key(name), err_text, _format_metric_updated(sub))
            continue
        value = sub.get('value')
        if isinstance(value, (dict, list)):
            text = json.dumps(value, default=str)
            display = (text if len(text) <= _JSON_CELL_MAX else text[:_JSON_CELL_MAX - 3] + '...')
        else:
            display = _format_scalar(name, value, pref_distance, pref_temperature)
        table.add_row(_humanize_key(name), display, _format_metric_updated(sub))
    return table


@telemetry.command('all')
@vin_argument
@click.option('--metrics',
              '-m',
              multiple=True,
              help='Restrict to these metric names; repeat the option.')
@json_option
@with_client
async def telemetry_all(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                        metrics: tuple[str, ...], *, as_json: bool) -> None:
    """Full telemetry snapshot (or restricted via --metrics)."""
    resp = await client.query_telemetry(vin, metrics=list(metrics) or None)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    metrics_block = (resp.get('metrics') if isinstance(resp, dict) else None) or {}
    if not metrics_block:
        console.print('[dim](no telemetry returned)[/dim]')
        return
    update_time = (resp.get('updateTime') if isinstance(resp, dict) else None) or ''
    console.print(f'[bold cyan]Telemetry[/bold cyan] — {vin}' +
                  (f'  [dim](updated {update_time})[/dim]' if update_time else ''))
    units = load_config(locale=client.locale)['units']
    pref_distance = units['distance']
    pref_temperature = units['temperature']
    grouped_keys: set[str] = {'indicators', 'configurations'}
    for title, keys in _METRIC_GROUPS:
        grouped_keys.update(keys)
        table = _telemetry_table(title, metrics_block, keys, pref_distance, pref_temperature)
        if table is not None:
            console.print(table)
    indicators = _indicators_table(metrics_block.get('indicators'))
    if indicators is not None:
        console.print(indicators)
    configurations = _configurations_table(metrics_block.get('configurations'), pref_distance,
                                           pref_temperature)
    if configurations is not None:
        console.print(configurations)
    other_keys = tuple(sorted(k for k in metrics_block if k not in grouped_keys))
    other = _telemetry_table('Other', metrics_block, other_keys, pref_distance, pref_temperature)
    if other is not None:
        console.print(other)


def _google_maps_url(lat: float, lon: float) -> str:
    """
    Build a Google Maps search URL centred on ``(lat, lon)``.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.

    Returns
    -------
    str
        A URL using the documented Google Maps URL API ``search`` action.
    """
    query = urllib.parse.urlencode({'api': 1, 'query': f'{lat},{lon}'})
    return f'https://www.google.com/maps/search/?{query}'


@telemetry.command('position')
@vin_argument
@click.option('--open-maps',
              is_flag=True,
              default=False,
              help='Open the coordinates in Google Maps using the default browser.')
@click.option('--maps-uri',
              is_flag=True,
              default=False,
              help='Print only the Google Maps URI (suitable for shell pipelines).')
@json_option
@with_client
async def telemetry_position(client: FordPassNiquestsClient, _ctx: click.Context, vin: str, *,
                             open_maps: bool, maps_uri: bool, as_json: bool) -> None:
    """Show the vehicle's last known GPS position."""  # noqa: DOC501
    position = await client.get_position(vin)
    if maps_uri:
        if position is None:
            msg = 'No position reported.'
            raise click.ClickException(msg)
        click.echo(_google_maps_url(position['lat'], position['lon']))
        return
    if should_emit_json(as_json):
        dump_json(position)
        return
    if position is None:
        console.print('[dim](no position reported)[/dim]')
        return
    lat, lon = position['lat'], position['lon']
    maps_url = _google_maps_url(lat, lon)
    table = Table(title=f'Position — {vin}', title_style='bold cyan')
    table.add_column('Field', style='cyan')
    table.add_column('Value')
    table.add_row('Latitude', f'{lat:.6f}')
    table.add_row('Longitude', f'{lon:.6f}')
    if (alt := position.get('alt')) is not None:
        table.add_row('Altitude', f'{alt:.1f} m')
    if (heading := position.get('heading')) is not None:
        table.add_row('Heading', f'{heading:.0f}°')
    if (compass := position.get('compass')) is not None:
        table.add_row('Compass', _humanize_enum(compass))
    if (update_time := position.get('update_time')) is not None:
        table.add_row('Updated',
                      str(update_time).replace('T', ' ').replace('Z', '').split('.', 1)[0])
    table.add_row('Google Maps', f'[link={maps_url}]{maps_url}[/link]')
    console.print(table)
    if open_maps:
        console.print(f'[dim]Opening {maps_url}…[/dim]')
        webbrowser.open(maps_url)
