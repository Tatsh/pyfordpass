"""Departure-time schedules (EV/PHEV only)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import dump_json, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient


@click.group()
def departure() -> None:
    """Departure-time schedules (EV/PHEV only)."""


@departure.command('next')
@vin_argument
@with_client
async def departure_next(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Show the next-upcoming departure schedule entry."""
    nxt = await client.get_next_departure(vin)
    if nxt is None:
        click.echo('(no departure scheduled / not an EV)')
        return
    dump_json(nxt)
