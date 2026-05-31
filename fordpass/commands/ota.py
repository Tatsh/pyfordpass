"""OTA: status, enable / disable auto-updates, release notes."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from fordpass.utils import is_list_like, walk_mapping
from rich.table import Table
import click

from .utils import (
    ack,
    console,
    debug_option,
    dump_json,
    format_iso_datetime,
    json_option,
    should_emit_json,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient

_DAY_ORDER = ('SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY')


@click.group()
def ota() -> None:
    """Over-the-air updates: status, enable / disable, release notes."""


@ota.command('status')
@debug_option
@vin_argument
@json_option
@with_client
async def ota_status(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                     as_json: bool) -> None:
    """Show the current automatic-software-update settings."""
    # The gateway returns 502 if the includeMetrics filter is set to a group
    # name (e.g. 'configurations') rather than a scalar metric key, so the call
    # has to be unfiltered. ASU settings appear in two places: an aggregate
    # configurations metric and a dedicated event - prefer whichever has data.
    resp = await client.query_telemetry(vin)
    inner = walk_mapping(resp, 'metrics', 'configurations', 'value')
    event = walk_mapping(resp, 'events', 'automaticSoftwareUpdateUserSettingsEvent', 'value')
    opt_in_cfg = walk_mapping(inner, 'automaticSoftwareUpdateOptInSetting')
    schedule_cfg = walk_mapping(inner, 'automaticSoftwareUpdateScheduleSetting')
    # Event-shape fallback when the configurations block is missing.
    opt_in: Mapping[str, Any] = (opt_in_cfg if isinstance(opt_in_cfg, Mapping) else {
        'value':
            walk_mapping(event, 'optIn'),
        'updateTime':
            walk_mapping(resp, 'events', 'automaticSoftwareUpdateUserSettingsEvent', 'updateTime')
    } if isinstance(event, Mapping) else {})
    schedule_entry: Mapping[str, Any] = (schedule_cfg if isinstance(schedule_cfg, Mapping) else {
        'value': walk_mapping(event, 'schedule'),
        'updateTime': opt_in.get('updateTime')
    } if isinstance(event, Mapping) else {})
    if should_emit_json(as_json):
        dump_json({'optIn': opt_in, 'schedule': schedule_entry})
        return
    if not opt_in and not schedule_entry:
        console.print('[dim]The vehicle has not reported ASU configuration yet.[/dim]')
        return
    state_raw = str(opt_in.get('value') or '').strip().upper()
    state_text = ('[green]Enabled[/green]' if state_raw == 'ON' else
                  '[yellow]Disabled[/yellow]' if state_raw == 'OFF' else '[dim]Unknown[/dim]')
    schedule_value = (schedule_entry.get('value')
                      if isinstance(schedule_entry.get('value'), Mapping) else {})
    if not isinstance(schedule_value, Mapping):  # pragma: no cover
        schedule_value = {}
    table = Table(title=f'OTA - {vin}', title_style='bold cyan')
    table.add_column('Field', style='cyan')
    table.add_column('Value')
    table.add_row('Automatic updates', state_text)
    table.add_row('Last updated', format_iso_datetime(opt_in.get('updateTime')))
    if schedule_value:
        table.add_row(
            'Schedule', f'{schedule_value.get("scheduleType") or "?"} '
            f'({schedule_value.get("scheduleExecutor") or "?"})')
        table.add_row('Time zone', str(schedule_value.get('timeZone') or '-'))
        table.add_row('Schedule last updated',
                      format_iso_datetime(schedule_entry.get('updateTime')))
    elif (err := schedule_entry.get('error')) is not None:
        table.add_row('Schedule', f'[red]error: {err}[/red]')
    console.print(table)
    # Weekly-schedule block (when populated).
    weekly = schedule_value.get('multipleWeeklySchedules')
    entries = weekly.get('dayOfWeekAndTime') if isinstance(weekly, Mapping) else None
    if is_list_like(entries) and entries:
        by_day = {
            str(e.get('dayOfWeek') or '').upper(): str(e.get('timeOfDay') or '-')
            for e in entries if isinstance(e, Mapping)
        }
        console.print('[bold cyan]Weekly schedule[/bold cyan]')
        for day in _DAY_ORDER:
            time_of_day = by_day.get(day, '-')
            console.print(f'  {day.title():9} {time_of_day}')


@ota.command('queue-refresh')
@debug_option
@vin_argument
@with_client
async def ota_queue_refresh(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Queue an ASU-settings read on the server (result arrives via WS)."""
    ack(await client.get_asu_settings(vin), 'getASUSettingsCommand')


@ota.command('enable')
@debug_option
@vin_argument
@with_client
async def ota_enable(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Turn automatic software updates on."""
    ack(await client.set_asu_enabled(vin, enabled=True), 'publishASUSettingsCommand(ON)')


@ota.command('disable')
@debug_option
@vin_argument
@with_client
async def ota_disable(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Turn automatic software updates off."""
    ack(await client.set_asu_enabled(vin, enabled=False), 'publishASUSettingsCommand(OFF)')


@ota.command('release-notes')
@debug_option
@vin_argument
@json_option
@with_client
async def ota_release_notes(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                            as_json: bool) -> None:
    """Fetch release notes for the pending OTA (two-step flow)."""
    notes = await client.get_release_notes(vin)
    if should_emit_json(as_json):
        dump_json(notes)
        return
    if notes is None:
        click.echo('No MMOTA alert is pending, so there is nothing to fetch.')
        return
    click.echo(notes.get('response') or 'The release notes are empty.')
