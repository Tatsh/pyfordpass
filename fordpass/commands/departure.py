"""Departure-time schedules (EV/PHEV only)."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
import json
import sys

from fordpass.utils import is_list_like
from rich.table import Table
import click

from .utils import (
    ack,
    console,
    debug_option,
    dump_json,
    json_option,
    parse_user_days,
    should_emit_json,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.departure import DepartureScheduleDay

_DAY_FULL_BY_SHORT: dict[str, str] = {
    'sun': 'SUNDAY',
    'mon': 'MONDAY',
    'tue': 'TUESDAY',
    'wed': 'WEDNESDAY',
    'thu': 'THURSDAY',
    'fri': 'FRIDAY',
    'sat': 'SATURDAY'
}
"""
Map of canonical short day keys (from :py:func:`parse_user_days`) to upper-case full names.

:meta hide-value:
"""

_DAY_ORDER: tuple[str, ...] = ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY',
                               'SUNDAY')
"""
Monday-to-Sunday ordering used when grouping ``--add`` slots into day entries.

:meta hide-value:
"""

_TEMPERATURES: frozenset[str] = frozenset({'OFF', 'LOW', 'MEDIUM', 'HIGH'})
"""
Accepted ``preconditionTemperature`` values for a ``--add`` slot.

:meta hide-value:
"""

_STATUSES: frozenset[str] = frozenset({'ON', 'OFF'})
"""
Accepted ``scheduleStatus`` values for a ``--add`` slot.

:meta hide-value:
"""

_MAX_HOUR = 24
"""
Inclusive upper bound for a slot hour (``24`` is the upstream midnight / disabled sentinel).

:meta hide-value:
"""

_MAX_MINUTE = 59
"""
Inclusive upper bound for a slot minute.

:meta hide-value:
"""

_MIN_TIME_PARTS = 2
"""
Minimum colon-separated pieces of a ``--add`` time portion (``HH`` and ``MM``).

:meta hide-value:
"""

_FULL_TIME_PARTS = 3
"""
Colon-separated pieces of a ``--add`` time portion that also carries a ``key=value`` tail.

:meta hide-value:
"""


def _single_day(token: str) -> str:
    """
    Resolve one day token to its upper-case full name via :py:func:`parse_user_days`.

    Parameters
    ----------
    token : str
        A single day name, abbreviation, or one-letter shortcut.

    Returns
    -------
    str
        The upper-case full day name (for example ``'MONDAY'``).

    Raises
    ------
    click.BadParameter
        If the token names zero or more than one day.
    """
    enabled = [short for short, on in parse_user_days(token).items() if on]
    if len(enabled) != 1:
        msg = f'{token!r} must name exactly one day.'
        raise click.BadParameter(msg)
    return _DAY_FULL_BY_SHORT[enabled[0]]


def _parse_add_slot(spec: str) -> tuple[str, dict[str, Any]]:
    """
    Parse one ``--add`` DSL token into a ``(day, slot)`` pair.

    The DSL is ``DAY@HH:MM:loc=<id>,id=<int>,temp=OFF|LOW|MEDIUM|HIGH,status=ON|OFF`` where ``temp``
    defaults to ``OFF`` and ``status`` defaults to ``ON``; ``loc`` and ``id`` are required.

    Parameters
    ----------
    spec : str
        One ``--add`` value.

    Returns
    -------
    tuple[str, dict[str, Any]]
        The upper-case day name and the slot in ``updateDepartureTimes`` write shape.

    Raises
    ------
    click.BadParameter
        If the token is malformed or carries an out-of-range or invalid value.
    """
    day_part, sep, rest = spec.partition('@')
    if not sep or not rest:
        msg = f'{spec!r} must look like DAY@HH:MM:loc=<id>,id=<int>[,temp=...,status=...].'
        raise click.BadParameter(msg)
    day = _single_day(day_part.strip())
    parts = rest.split(':', 2)
    if len(parts) < _MIN_TIME_PARTS or not parts[0].isdigit() or not parts[1].isdigit():
        msg = f'{spec!r} must carry a HH:MM time after the @.'
        raise click.BadParameter(msg)
    hours, minutes = int(parts[0]), int(parts[1])
    if hours > _MAX_HOUR or minutes > _MAX_MINUTE:
        msg = f'{spec!r} time is out of range (hours 0-{_MAX_HOUR}, minutes 0-{_MAX_MINUTE}).'
        raise click.BadParameter(msg)
    kv: dict[str, str] = {}
    for token in filter(None, (parts[2] if len(parts) == _FULL_TIME_PARTS else '').split(',')):
        key, eq, value = token.partition('=')
        if not eq:
            msg = f'{token!r} is not a key=value pair.'
            raise click.BadParameter(msg)
        kv[key.strip().lower()] = value.strip()
    location_id, schedule_id = kv.get('loc'), kv.get('id')
    if not location_id or not schedule_id:
        msg = f'{spec!r} must include both loc=<id> and id=<int>.'
        raise click.BadParameter(msg)
    if not schedule_id.isdigit():
        msg = f'id must be an integer, got {schedule_id!r}.'
        raise click.BadParameter(msg)
    temperature = kv.get('temp', 'OFF').upper()
    status = kv.get('status', 'ON').upper()
    if temperature not in _TEMPERATURES:
        msg = f'temp must be one of {", ".join(sorted(_TEMPERATURES))}, got {temperature!r}.'
        raise click.BadParameter(msg)
    if status not in _STATUSES:
        msg = f'status must be ON or OFF, got {status!r}.'
        raise click.BadParameter(msg)
    return day, {
        'locationId': location_id,
        'preconditionTemperature': temperature,
        'scheduleId': int(schedule_id),
        'scheduleStatus': status,
        'timeOfDay': {
            'hours': hours,
            'minutes': minutes
        }
    }


def _slots_to_days(specs: Sequence[str]) -> list[DepartureScheduleDay]:
    """
    Group ``--add`` DSL tokens into the ``updateDepartureTimes`` day-list shape.

    Parameters
    ----------
    specs : Sequence[str]
        The collected ``--add`` values.

    Returns
    -------
    list[DepartureScheduleDay]
        One entry per named day, ordered Monday to Sunday.
    """
    by_day: dict[str, dict[str, Any]] = {}
    for spec in specs:
        day, slot = _parse_add_slot(spec)
        by_day.setdefault(day, {'dayOfWeek': day, 'schedules': []})['schedules'].append(slot)
    return cast('list[DepartureScheduleDay]', [by_day[day] for day in _DAY_ORDER if day in by_day])


def _load_schedules_from_json(path: Path) -> list[DepartureScheduleDay]:
    """
    Load the full ``departureSchedules`` array from a JSON file (or stdin when ``path`` is ``-``).

    Accepts either a bare array or an object carrying a ``departureSchedules`` array.

    Parameters
    ----------
    path : Path
        The JSON file to read, or ``Path('-')`` to read standard input.

    Returns
    -------
    list[DepartureScheduleDay]
        The parsed schedule day list.

    Raises
    ------
    click.BadParameter
        If the input is not valid JSON or is not a schedule array.
    """
    text = sys.stdin.read() if str(path) == '-' else path.read_text(encoding='utf-8')
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        msg = f'--from-json is not valid JSON: {e}.'
        raise click.BadParameter(msg) from e
    if isinstance(parsed, Mapping):
        parsed = parsed.get('departureSchedules', parsed)
    if not is_list_like(parsed):
        msg = ('--from-json must be a departureSchedules array, or an object with a '
               '`departureSchedules` array.')
        raise click.BadParameter(msg)
    return cast('list[DepartureScheduleDay]', list(parsed))


def _resolve_update_input(from_json: Path | None, adds: tuple[str,
                                                              ...]) -> list[DepartureScheduleDay]:
    """
    Resolve the ``update`` schedule list from exactly one of its two input modes.

    Parameters
    ----------
    from_json : Path | None
        The ``--from-json`` path, or ``None`` when unset.
    adds : tuple[str, ...]
        The collected ``--add`` values.

    Returns
    -------
    list[DepartureScheduleDay]
        The complete schedule day list to install.

    Raises
    ------
    click.UsageError
        If both inputs are given or neither is.
    """
    if bool(from_json) == bool(adds):
        msg = 'Pass exactly one of --from-json or one or more --add.'
        raise click.UsageError(msg)
    return _load_schedules_from_json(from_json) if from_json is not None else _slots_to_days(adds)


def _days_to_drop(days: str) -> list[str]:
    """
    Resolve a user day-list string to upper-case full day names for ``delete-by-day``.

    Parameters
    ----------
    days : str
        Day names, abbreviations, or one-letter shortcuts (for example ``'mon,wed,fri'``).

    Returns
    -------
    list[str]
        The matched upper-case full day names.

    Raises
    ------
    click.UsageError
        If no day is recognised.
    """
    enabled = [_DAY_FULL_BY_SHORT[short] for short, on in parse_user_days(days).items() if on]
    if not enabled:
        msg = 'No days recognised; pass at least one day, e.g. mon,wed,fri.'
        raise click.UsageError(msg)
    return enabled


@click.group()
def departure() -> None:
    """Departure-time schedules (EV/PHEV only)."""


@departure.command('next')
@debug_option
@vin_argument
@json_option
@with_client
async def departure_next(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                         as_json: bool) -> None:
    """Show the next-upcoming departure schedule entry."""
    nxt = await client.get_next_departure(vin)
    if nxt is None:
        console.print('[dim]No departure is scheduled, or this vehicle is not an EV.[/dim]')
        return
    if should_emit_json(as_json):
        dump_json(nxt)
        return
    table = Table(title=f'Next departure - {vin}', title_style='bold cyan', show_header=True)
    table.add_column('Field', style='cyan')
    table.add_column('Value')
    for key, value in nxt.items():
        if isinstance(value, Mapping) or is_list_like(value):
            continue
        table.add_row(str(key), '-' if value is None else str(value))
    console.print(table)


@departure.command('enable')
@debug_option
@vin_argument
@with_client
async def departure_enable(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Enable the departure-time schedules."""
    ack(await client.enable_departure_times(vin), 'enableDepartureTimes')


@departure.command('disable')
@debug_option
@vin_argument
@with_client
async def departure_disable(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Disable all departure-time schedules."""
    ack(await client.disable_departure_times(vin), 'disableDepartureTimes')


@departure.command('update')
@debug_option
@vin_argument
@click.option('--from-json',
              'from_json',
              type=click.Path(path_type=Path, allow_dash=True),
              default=None,
              help='Read the full departureSchedules array from a JSON file (`-` for stdin).')
@click.option('--add',
              'adds',
              multiple=True,
              metavar='DAY@HH:MM:loc=...,id=...',
              help='Add one slot. Repeatable. Mutually exclusive with --from-json.')
@with_client
async def departure_update(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                           from_json: Path | None, adds: tuple[str, ...]) -> None:
    """Replace the full departure-time schedule list."""
    schedules = _resolve_update_input(from_json, adds)
    ack(await client.update_departure_times(vin, schedules=schedules), 'updateDepartureTimes')


@departure.command('delete-by-id')
@debug_option
@vin_argument
@click.argument('ids', nargs=-1, required=True, type=int)
@with_client
async def departure_delete_by_id(client: AsyncFordPassClient, _ctx: click.Context, vin: str,
                                 ids: tuple[int, ...]) -> None:
    """Remove departure slots by scheduleId (VIN first, then one or more IDs)."""
    ack(await client.delete_departure_schedules_by_ids(vin, ids), 'updateDepartureTimes')


@departure.command('delete-by-day')
@debug_option
@vin_argument
@click.argument('days')
@with_client
async def departure_delete_by_day(client: AsyncFordPassClient, _ctx: click.Context, vin: str,
                                  days: str) -> None:
    """Remove whole-day departure groups (for example `mon,wed,fri`)."""
    ack(await client.delete_departure_schedules_by_days(vin, _days_to_drop(days)),
        'updateDepartureTimes')
