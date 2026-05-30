"""Preferred-dealer information."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import debug_option, dump_json, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def dealer() -> None:
    """Preferred-dealer info."""


@dealer.command('preferred')
@debug_option
@vin_argument
@with_client
async def dealer_preferred(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Get full details of the vehicle's preferred dealer (two-step)."""
    d = await client.get_preferred_dealer(vin)
    if d is None:
        click.echo('No preferred dealer is set.')
        return
    dump_json(d)
