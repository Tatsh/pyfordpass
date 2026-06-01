"""PPO commands: refresh, stream, cancel (Autonomic TMC, experimental)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import ack, debug_option, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def ppo() -> None:
    """Programmable Parameter Override refresh (experimental)."""


@ppo.command('refresh')
@debug_option
@vin_argument
@with_client
async def ppo_refresh(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Trigger a one-shot PPO refresh (experimental)."""
    ack(await client.ppo_refresh(vin), 'ppoRefresh')


@ppo.command('stream')
@debug_option
@vin_argument
@click.option('--frequency-min',
              type=click.IntRange(min=1),
              default=3,
              show_default=True,
              help='Refresh frequency in minutes.')
@click.option('--duration-min',
              type=click.IntRange(min=1),
              default=10,
              show_default=True,
              help='Total duration in minutes.')
@with_client
async def ppo_stream(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                     frequency_min: int, duration_min: int) -> None:
    """Start a continuous PPO refresh (experimental)."""
    ack(
        await client.ppo_refresh_continuous(vin,
                                            frequency_min=frequency_min,
                                            duration_min=duration_min), 'ppoRefreshContinuous')


@ppo.command('cancel')
@debug_option
@vin_argument
@with_client
async def ppo_cancel(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Cancel a continuous PPO refresh (experimental)."""
    ack(await client.ppo_refresh_cancel(vin), 'ppoRefreshContinuousCancel')
