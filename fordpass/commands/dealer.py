"""Preferred-dealer information."""
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
def dealer() -> None:
    """Preferred-dealer info."""


@dealer.command('preferred')
@debug_option
@vin_argument
@json_option
@with_client
async def dealer_preferred(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                           as_json: bool) -> None:
    """Get full details of the vehicle's preferred dealer (two-step)."""
    d = await client.get_preferred_dealer(vin)
    if d is None:
        console.print('[dim]No preferred dealer is set.[/dim]')
        return
    if should_emit_json(as_json):
        dump_json(d)
        return
    table = Table(title=f'Preferred dealer - {vin}', title_style='bold cyan', show_header=True)
    table.add_column('Field', style='cyan')
    table.add_column('Value')
    for key, value in d.items():
        if isinstance(value, Mapping) or is_list_like(value):
            continue
        table.add_row(str(key), '-' if value is None else str(value))
    console.print(table)
