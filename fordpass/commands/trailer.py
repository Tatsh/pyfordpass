"""Trailer light-check commands: check on / off (Autonomic TMC)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import ack, debug_option, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def trailer() -> None:
    """Trailer functions."""


@trailer.group('check')
def trailer_check() -> None:
    """Trailer light check (experimental)."""


@trailer_check.command('on')
@debug_option
@vin_argument
@with_client
async def trailer_check_on(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Flash the trailer lights to verify the connection (experimental)."""
    ack(await client.start_trailer_light_check(vin), 'startTrailerLightCheck')


@trailer_check.command('off')
@debug_option
@vin_argument
@with_client
async def trailer_check_off(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Stop an active trailer-light check (experimental)."""
    ack(await client.stop_trailer_light_check(vin), 'stopTrailerLightCheck')
