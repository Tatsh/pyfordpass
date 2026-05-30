"""Remote commands: start, stop, lock, unlock, status, panic."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import ack, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient


@click.group()
def remote() -> None:
    """Send commands: start, stop, lock, unlock, status, panic."""


@remote.command('start')
@vin_argument
@with_client
async def remote_start(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Remote start (also used to extend an active session)."""
    ack(await client.remote_start(vin), 'remoteStart')


@remote.command('stop')
@vin_argument
@with_client
async def remote_stop(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Cancel an active remote start."""
    ack(await client.cancel_remote_start(vin), 'cancelRemoteStart')


@remote.command('extend')
@vin_argument
@with_client
async def remote_extend(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Extend an active remote-start session."""
    ack(await client.extend_remote_start(vin), 'extendStart')


@remote.command('lock')
@vin_argument
@with_client
async def remote_lock(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Lock the doors."""
    ack(await client.lock(vin), 'lock')


@remote.command('unlock')
@vin_argument
@with_client
async def remote_unlock(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Unlock the doors."""
    ack(await client.unlock(vin), 'unlock')


@remote.command('status')
@vin_argument
@with_client
async def remote_status(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Force the TCU to push fresh state."""
    ack(await client.status_refresh(vin), 'statusRefresh')


@remote.command('panic')
@vin_argument
@click.option('--duration',
              type=int,
              default=3,
              show_default=True,
              help='Seconds to sound horn / flash lights.')
@with_client
async def remote_panic(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                       duration: int) -> None:
    """Sound horn + flash lights."""
    ack(await client.panic_alarm(vin, duration), 'startPanicCue')
