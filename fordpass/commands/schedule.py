"""Recurring remote-start schedules (SRSM)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from rich.table import Table
import click

from .utils import console, dump_json, json_option, should_emit_json, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient
    from fordpass.typing import ScheduleEntry

_DAY_FIELDS = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')


@click.group()
def schedule() -> None:
    """Manage recurring remote-start schedules."""


@schedule.command('list')
@vin_argument
@json_option
@with_client
async def schedule_list(client: FordPassNiquestsClient, _ctx: click.Context, vin: str, *,
                        as_json: bool) -> None:
    """Show recurring remote-start schedules for the VIN."""
    resp = await client.list_remote_start_schedules(vin)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    schedules = _extract_schedules(resp)
    if not schedules:
        console.print('[dim](no schedules)[/dim]')
        return
    table = Table(title=f'Remote-start schedules — {vin}', title_style='bold cyan')
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

    The Ford SRSM backend marshals schedules with the .NET Newtonsoft.Json
    array sentinel — ``{"startSchedule": {"$values": [...]}, "status": 200}``.
    Older firmware variants use ``{"schedules": [...]}`` or a bare list, so this
    helper accepts any of those shapes.

    Parameters
    ----------
    resp : Any
        Decoded JSON body returned by
        :py:meth:`fordpass.client.FordPassNiquestsClient.list_remote_start_schedules`.

    Returns
    -------
    list[ScheduleEntry]
        The flat list of schedule entries; empty if the payload is unrecognised.
    """
    if isinstance(resp, list):
        return resp
    if not isinstance(resp, Mapping):
        return []
    container = resp.get('startSchedule')
    if isinstance(container, Mapping):
        values = container.get('$values')
        if isinstance(values, list):
            return values
    if isinstance(container, list):
        return container
    fallback = resp.get('schedules')
    if isinstance(fallback, list):
        return fallback
    return []


@schedule.command('add')
@vin_argument
@click.option('--time', 'start_time', required=True, help='HH:MM (24h)')
@click.option('--date',
              'request_date',
              required=True,
              help='M-D-YYYY h:mm:ss AM/PM, e.g. "5-28-2026 1:50:00 PM"')
@click.option('--tz',
              'time_zone',
              type=int,
              required=True,
              help='Ford internal zone code (e.g. 85 = US Eastern)')
@click.option('--days', required=True, help='Comma-separated day flags, e.g. "mon,tue,thu"')
@with_client
async def schedule_add(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                       start_time: str, request_date: str, time_zone: int, days: str) -> None:
    """Add a new recurring schedule."""
    enabled = {d.strip().lower(): 1 for d in days.split(',') if d.strip()}
    dump_json(await client.add_remote_start_schedule(vin,
                                                     start_time=start_time,
                                                     request_start_date=request_date,
                                                     time_zone=time_zone,
                                                     days=enabled))


@schedule.command('delete')
@click.argument('schedule_id', type=int)
@click.option('--vin', required=True, help='Required alongside scheduleId.')
@with_client
async def schedule_delete(client: FordPassNiquestsClient, _ctx: click.Context, schedule_id: int,
                          vin: str) -> None:
    """Delete a schedule entry (DELETE with body)."""
    dump_json(await client.delete_remote_start_schedule(schedule_id, vin=vin))


async def _set_schedule_status(client: FordPassNiquestsClient, vin: str, schedule_id: int, *,
                               status: str) -> ScheduleEntry:
    """
    Fetch ``schedule_id`` for ``vin``, flip its ``status`` field, and PUT it back.

    Parameters
    ----------
    client : FordPassNiquestsClient
        The signed-in client.
    vin : str
        Vehicle VIN that owns the schedule.
    schedule_id : int
        Server-assigned schedule identifier.
    status : str
        New status — ``'1'`` to enable, ``'0'`` to disable.

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
    body = cast('Mapping[str, str | int | None]', {**target, 'status': status})
    return await client.toggle_remote_start_schedule(schedule_id, schedule_body=body)


@schedule.command('enable')
@click.argument('schedule_id', type=int)
@vin_argument
@with_client
async def schedule_enable(client: FordPassNiquestsClient, _ctx: click.Context, schedule_id: int,
                          vin: str) -> None:
    """Mark the schedule active (``status = 1``)."""
    dump_json(await _set_schedule_status(client, vin, schedule_id, status='1'))


@schedule.command('disable')
@click.argument('schedule_id', type=int)
@vin_argument
@with_client
async def schedule_disable(client: FordPassNiquestsClient, _ctx: click.Context, schedule_id: int,
                           vin: str) -> None:
    """Mark the schedule disabled (``status = 0``)."""
    dump_json(await _set_schedule_status(client, vin, schedule_id, status='0'))
