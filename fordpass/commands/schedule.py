"""Recurring remote-start schedules (SRSM)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from fordpass.utils import is_list_like
from rich.table import Table
import click

from .utils import (
    console,
    debug_option,
    dump_json,
    format_ford_request_date,
    json_option,
    parse_user_datetime,
    parse_user_days,
    parse_user_timezone,
    should_emit_json,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.schedule import ScheduleEntry

_DAY_FIELDS = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')


@click.group()
def schedule() -> None:
    """Manage recurring remote-start schedules."""


@schedule.command('list')
@debug_option
@vin_argument
@json_option
@with_client
async def schedule_list(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        as_json: bool) -> None:
    """Show recurring remote-start schedules for the VIN."""
    resp = await client.list_remote_start_schedules(vin)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    schedules = _extract_schedules(resp)
    if not schedules:
        console.print('[dim]No remote-start schedules are configured.[/dim]')
        return
    table = Table(title=f'Remote-start schedules - {vin}', title_style='bold cyan')
    table.add_column('ID', justify='right', style='cyan')
    table.add_column('Name')
    table.add_column('Time')
    table.add_column('Days')
    table.add_column('Status')
    for s in schedules:
        sid = (s.get('startScheduleId') or s.get('scheduleId') or s.get('id') or '?')
        days = ','.join(d.upper() for d in _DAY_FIELDS if str(s.get(d, '0')) == '1')
        status = str(s.get('status', ''))
        status_txt = ('[green]Active[/green]' if status == '1' else
                      '[dim]Disabled[/dim]' if status == '0' else status or '?')
        table.add_row(str(sid),
                      s.get('name') or '-',
                      s.get('startTime') or '-', days or '-', status_txt)
    console.print(table)


def _extract_schedules(resp: Any) -> list[ScheduleEntry]:
    """
    Pull the schedule list out of the upstream response envelope.

    The Ford SRSM backend marshals schedules with the .NET Newtonsoft.Json array sentinel -
    ``{"startSchedule": {"$values": [...]}, "status": 200}``. Older firmware variants use
    ``{"schedules": [...]}`` or a bare list, so this helper accepts any of those shapes.

    Parameters
    ----------
    resp : Any
        Decoded JSON body returned by
        :py:meth:`fordpass.client.AsyncFordPassClient.list_remote_start_schedules`.

    Returns
    -------
    list[ScheduleEntry]
        The flat list of schedule entries; empty if the payload is unrecognised.
    """
    if is_list_like(resp):
        return list(resp)
    if not isinstance(resp, Mapping):
        return []
    container = resp.get('startSchedule')
    if isinstance(container, Mapping):
        values = container.get('$values')
        if is_list_like(values):
            return list(values)
    if is_list_like(container):
        return list(container)
    fallback = resp.get('schedules')
    if is_list_like(fallback):
        return list(fallback)
    return []


@schedule.command('add')
@debug_option
@vin_argument
@click.option('--start',
              'start',
              required=True,
              help='When the engine should fire - ISO 8601 (e.g. 2026-05-28T13:50:00-04:00) or '
              '"YYYY-MM-DD HH:MM" in the timezone given by --tz.')
@click.option(
    '--tz',
    'tz',
    default=None,
    help='Timezone for the schedule: IANA name (e.g. America/New_York), an integer Ford zone '
    'code, or "local" / unset to use the system timezone.')
@click.option(
    '--days',
    required=True,
    help='Days when the schedule fires. Accepts comma- / space- / slash-separated tokens - full '
    'names, abbreviations, or one-letter shortcuts (e.g. "mon,tue,thu", "M T Th", "mwf").')
@with_client
async def schedule_add(client: AsyncFordPassClient, _ctx: click.Context, vin: str, start: str,
                       tz: str | None, days: str) -> None:
    """Add a new recurring remote-start schedule."""
    dt = parse_user_datetime(start)
    ford_tz_code = parse_user_timezone(tz)
    enabled_days = parse_user_days(days)
    await client.add_remote_start_schedule(vin,
                                           start_time=dt.strftime('%H:%M'),
                                           request_start_date=format_ford_request_date(dt),
                                           time_zone=ford_tz_code,
                                           days=enabled_days)
    console.print(f'[green]Schedule added for {vin} at {dt.strftime("%H:%M")}.[/green]')


@schedule.command('delete')
@debug_option
@click.argument('schedule_id', type=int)
@click.option('--vin', required=True, help='Required alongside scheduleId.')
@with_client
async def schedule_delete(client: AsyncFordPassClient, _ctx: click.Context, schedule_id: int,
                          vin: str) -> None:
    """Delete a schedule entry (DELETE with body)."""
    await client.delete_remote_start_schedule(schedule_id, vin=vin)
    console.print(f'[green]Schedule {schedule_id} deleted.[/green]')


def _as_int(value: Any, *, default: int = 0) -> int:
    """
    Coerce upstream string-or-int fields like ``status='1'`` or ``timeZone=85`` to ``int``.

    Parameters
    ----------
    value : Any
        Anything; non-int / non-digit-string inputs return ``default``.
    default : int
        Fallback when coercion is not possible.

    Returns
    -------
    int
        The coerced integer, or ``default`` when coercion failed.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip('-').isdigit():
        return int(value)
    return default


def _as_str(value: Any, *, default: str = '') -> str:
    """
    Coerce an upstream string field to ``str``, falling back to ``default`` on missing.

    Parameters
    ----------
    value : Any
        Anything; ``None`` returns ``default``, all other values stringify.
    default : str
        Fallback when ``value`` is ``None``.

    Returns
    -------
    str
        The coerced string.
    """
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


async def _set_schedule_status(client: AsyncFordPassClient, vin: str, schedule_id: int, *,
                               status: int) -> ScheduleEntry:
    """
    Fetch ``schedule_id`` for ``vin``, flip its ``status`` field, and PUT it back.

    Parameters
    ----------
    client : AsyncFordPassClient
        The signed-in client.
    vin : str
        Vehicle VIN that owns the schedule.
    schedule_id : int
        Server-assigned schedule identifier.
    status : int
        New status - ``1`` to enable, ``0`` to disable.

    Returns
    -------
    ScheduleEntry
        The parsed PUT response.

    Raises
    ------
    click.ClickException
        If no schedule with ``schedule_id`` exists for the given VIN.
    """
    schedules = _extract_schedules(await client.list_remote_start_schedules(vin))
    target = next((
        s for s in schedules
        if str(s.get('startScheduleId') or s.get('scheduleId') or s.get('id')) == str(schedule_id)),
                  None)
    if target is None:
        msg = f'Schedule {schedule_id} not found for VIN {vin}.'
        raise click.ClickException(msg)
    # The PUT endpoint mirrors the *add* shape - int status / day flags, the original
    # ``requestStartDate`` field name (read side calls it ``requestDateTime``), and a mandatory
    # ``vin``. Spreading the raw read response sends the wrong field names, the wrong types
    # (strings instead of ints), and Newtonsoft sentinels ($id, $type), all of which the gateway
    # rejects as 400.
    body: dict[str, str | int | None] = {
        'vin': vin,
        'requestStartDate': (_as_str(target.get('requestStartDate'))
                             or _as_str(target.get('requestDateTime'))),
        'startTime': _as_str(target.get('startTime')),
        'timeZone': _as_int(target.get('timeZone')),
        'status': status,
        **{
            d: _as_int(target.get(d))
            for d in _DAY_FIELDS
        }
    }
    return await client.toggle_remote_start_schedule(schedule_id,
                                                     schedule_body=cast(
                                                         'Mapping[str, str | int | None]', body))


@schedule.command('enable')
@debug_option
@click.argument('schedule_id', type=int)
@vin_argument
@with_client
async def schedule_enable(client: AsyncFordPassClient, _ctx: click.Context, schedule_id: int,
                          vin: str) -> None:
    """Mark the schedule active (``status = 1``)."""
    await _set_schedule_status(client, vin, schedule_id, status=1)
    console.print(f'[green]Schedule {schedule_id} enabled.[/green]')


@schedule.command('disable')
@debug_option
@click.argument('schedule_id', type=int)
@vin_argument
@with_client
async def schedule_disable(client: AsyncFordPassClient, _ctx: click.Context, schedule_id: int,
                           vin: str) -> None:
    """Mark the schedule disabled (``status = 0``)."""
    await _set_schedule_status(client, vin, schedule_id, status=0)
    console.print(f'[green]Schedule {schedule_id} disabled.[/green]')
