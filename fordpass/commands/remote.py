"""Remote commands: start, stop, lock, unlock, status, panic."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import (
    ack,
    assert_ready_or_abort,
    debug_option,
    duration_range,
    force_option,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def remote() -> None:
    """Send commands: start, stop, lock, unlock, status, panic."""


@remote.command('start')
@debug_option
@vin_argument
@force_option
@with_client
async def remote_start(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       force: bool) -> None:
    """Remote start (also used to extend an active session)."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.remote_start(vin), 'remoteStart')


@remote.command('stop')
@debug_option
@vin_argument
@force_option
@with_client
async def remote_stop(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                      force: bool) -> None:
    """Cancel an active remote start."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.cancel_remote_start(vin), 'cancelRemoteStart')


@remote.command('extend')
@debug_option
@vin_argument
@force_option
@with_client
async def remote_extend(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        force: bool) -> None:
    """Extend an active remote-start session."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.extend_remote_start(vin), 'extendStart')


@remote.command('lock')
@debug_option
@vin_argument
@force_option
@with_client
async def remote_lock(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                      force: bool) -> None:
    """Lock the doors."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.lock(vin), 'lock')


@remote.command('unlock')
@debug_option
@vin_argument
@force_option
@with_client
async def remote_unlock(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        force: bool) -> None:
    """Unlock the doors."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.unlock(vin), 'unlock')


@remote.command('status')
@debug_option
@vin_argument
@with_client
async def remote_status(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Force the TCU to push fresh state."""
    ack(await client.status_refresh(vin), 'statusRefresh')


@remote.command('panic')
@debug_option
@vin_argument
@click.option('--duration',
              type=duration_range(1, 10),
              default=3,
              show_default=True,
              help='Seconds to sound horn / flash lights (1-10).')
@with_client
async def remote_panic(client: AsyncFordPassClient, _ctx: click.Context, vin: str,
                       duration: int) -> None:
    """Sound horn + flash lights."""
    ack(await client.panic_alarm(vin, duration), 'startPanicCue')
