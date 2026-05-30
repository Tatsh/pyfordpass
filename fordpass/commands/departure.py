"""Departure-time schedules (EV/PHEV only)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import debug_option, dump_json, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def departure() -> None:
    """Departure-time schedules (EV/PHEV only)."""


@departure.command('next')
@debug_option
@vin_argument
@with_client
async def departure_next(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Show the next-upcoming departure schedule entry."""
    nxt = await client.get_next_departure(vin)
    if nxt is None:
        click.echo('No departure is scheduled, or this vehicle is not an EV.')
        return
    dump_json(nxt)
