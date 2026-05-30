"""Roadside-assistance lookups."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from rich.table import Table
import click

from .utils import console, dump_json, json_option, should_emit_json, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient
    from fordpass.typing import IDNameEntry


@click.group()
def roadside() -> None:
    """Roadside-assistance lookups."""


def _print_id_name_table(title: str, items: Sequence[IDNameEntry]) -> None:
    """Render an ``{"id", "name"}`` list as a two-column Rich table."""
    if not items:
        console.print('[dim](nothing returned)[/dim]')
        return
    table = Table(title=title, title_style='bold cyan')
    table.add_column('ID', style='dim')
    table.add_column('Name')
    for item in items:
        table.add_row(str(item.get('id') or '-'), str(item.get('name') or '-'))
    console.print(table)


@roadside.command('symptoms')
@click.option('--bev', is_flag=True, help='Filter for battery-EV symptoms.')
@json_option
@with_client
async def roadside_symptoms(client: FordPassNiquestsClient, _ctx: click.Context, *, bev: bool,
                            as_json: bool) -> None:
    """List supported roadside symptoms."""
    resp = await client.get_roadside_symptoms(is_bev=bev)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    items = (resp.get('symptoms') if isinstance(resp, Mapping) else None) or []
    _print_id_name_table('Roadside symptoms', items)


@roadside.command('locations')
@json_option
@with_client
async def roadside_locations(client: FordPassNiquestsClient, _ctx: click.Context, *,
                             as_json: bool) -> None:
    """List supported location types."""
    resp = await client.get_roadside_location_types()
    if should_emit_json(as_json):
        dump_json(resp)
        return
    items = (resp.get('locationTypes') if isinstance(resp, Mapping) else None) or []
    _print_id_name_table('Roadside location types', items)


@roadside.command('active')
@vin_argument
@json_option
@with_client
async def roadside_active(client: FordPassNiquestsClient, _ctx: click.Context, vin: str, *,
                          as_json: bool) -> None:
    """Show the active roadside event for the VIN, if any."""
    resp = await client.get_roadside_active_event(vin)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    if resp is None or resp == {}:
        console.print('[dim](no active roadside event)[/dim]')
        return
    dump_json(resp)


@roadside.command('predraft')
@vin_argument
@click.option('--name', required=True, help='Customer name.')
@click.option('--phone', default='', help='Customer phone.')
@with_client
async def roadside_predraft(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                            name: str, phone: str) -> None:
    """Create a roadside pre-draft."""
    dump_json(await client.predraft_roadside_event(vin, customer_name=name, customer_phone=phone))
