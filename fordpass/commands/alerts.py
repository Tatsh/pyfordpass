"""Vehicle alerts: current state, history, washer-fluid."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
import sys

from rich.table import Table
import click

from .utils import (
    console,
    debug_option,
    dump_json,
    json_option,
    should_emit_json,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def alerts() -> None:
    """Show current state and history of vehicle alerts."""


@alerts.command('current')
@debug_option
@vin_argument
@json_option
@with_client
async def alerts_current(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                         as_json: bool) -> None:
    """Active vehicle alerts."""
    resp = await client.get_alerts(vin)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    items = (resp.get('alerts') if isinstance(resp, Mapping) else None) or []
    if not items:
        console.print('[dim]No active alerts.[/dim]')
        return
    table = Table(title=f'Active alerts - {vin}', title_style='bold cyan')
    table.add_column('When', style='dim')
    table.add_column('Type')
    table.add_column('Urgency')
    table.add_column('Icon', style='dim')
    table.add_column('Detail')
    for a in items:
        urg = a.get('urgency') or '-'
        urg_txt = ('[red]HIGH[/red]' if urg == 'H' else '[yellow]MED[/yellow]'
                   if urg == 'M' else '[green]NORMAL[/green]' if urg == 'N' else urg)
        prog = a.get('prognostics') or {}
        detail = (prog.get('featureType') or a.get('alertDescription') or a.get('wilCode') or '-')
        table.add_row(str(a.get('eventTimeStamp') or '-'), str(a.get('alertType') or '-'), urg_txt,
                      str(a.get('iconName') or '-'), str(detail))
    console.print(table)


@alerts.command('history')
@debug_option
@vin_argument
@json_option
@with_client
async def alerts_history(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                         as_json: bool) -> None:
    """Historical alert log."""
    resp = await client.get_alert_history(vin)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    items = (resp.get('messages') if isinstance(resp, Mapping) else None) or []
    if not items:
        console.print('[dim]No alert history is recorded.[/dim]')
        return
    table = Table(title=f'Alert history - {vin}', title_style='bold cyan')
    table.add_column('When', style='dim')
    table.add_column('Type')
    table.add_column('Subject')
    table.add_column('Body')
    for m in items:
        table.add_row(str(m.get('eventTime') or '-'), str(m.get('alertType') or '-'),
                      str(m.get('messageSubject') or '-'), str(m.get('messageBody') or '-'))
    console.print(table)


@alerts.command('washer')
@debug_option
@vin_argument
@json_option
@with_client
async def alerts_washer(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        as_json: bool) -> None:
    """Washer-fluid status."""
    low = await client.is_washer_fluid_low(vin)
    if should_emit_json(as_json):
        dump_json({'low': low})
    else:
        click.echo('low' if low else 'ok')
    if low:
        sys.exit(1)
