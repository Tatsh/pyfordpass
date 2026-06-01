"""Zone-lighting commands: on, off, zone (Ford MPS API)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import ack, debug_option, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.lighting import ZoneLightZone

_ZONE_BY_NAME: dict[str, ZoneLightZone] = {
    'all': '0',
    'front': '1',
    'rear': '2',
    'driver': '3',
    'passenger': '4',
    'off': 'off'
}
"""
Friendly zone name to wire :py:data:`~fordpass.typing.lighting.ZoneLightZone` value.

:meta hide-value:
"""


@click.group()
def lights() -> None:
    """Zone-lighting control (Ford MPS API)."""


@lights.command('on')
@debug_option
@vin_argument
@with_client
async def lights_on(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Turn the zone lighting on."""
    ack(await client.turn_zone_lights_on(vin), 'turnZoneLightsOn')


@lights.command('off')
@debug_option
@vin_argument
@with_client
async def lights_off(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Turn the zone lighting off."""
    ack(await client.turn_zone_lights_off(vin), 'turnZoneLightsOff')


@lights.command('zone')
@debug_option
@vin_argument
@click.argument('zone', type=click.Choice(tuple(_ZONE_BY_NAME)))
@with_client
async def lights_zone(client: AsyncFordPassClient, _ctx: click.Context, vin: str,
                      zone: str) -> None:
    """Select the lit zone: all, front, rear, driver, passenger, or off."""
    resp = await client.set_zone_lighting(vin, _ZONE_BY_NAME[zone])
    if resp is None:
        click.secho(f'Zone lighting already set to {zone}.', fg='green')
        return
    ack(resp, 'setZoneLightsMode')
