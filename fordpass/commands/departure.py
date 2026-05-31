"""Departure-time schedules (EV/PHEV only)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from fordpass.utils import is_list_like
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
