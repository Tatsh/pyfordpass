"""Preconditioning commands: start, extend, stop (Autonomic TMC, experimental)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import ack, debug_option, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def precondition() -> None:
    """Cabin preconditioning (experimental)."""


@precondition.command('start')
@debug_option
@vin_argument
@with_client
async def precondition_start(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Start cabin preconditioning (experimental)."""
    ack(await client.start_on_demand_preconditioning(vin), 'startOnDemandPreconditioning')


@precondition.command('extend')
@debug_option
@vin_argument
@with_client
async def precondition_extend(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Extend an active preconditioning session (experimental)."""
    ack(await client.extend_on_demand_preconditioning(vin), 'extendOnDemandPreconditioning')


@precondition.command('stop')
@debug_option
@vin_argument
@with_client
async def precondition_stop(client: AsyncFordPassClient, _ctx: click.Context, vin: str) -> None:
    """Stop an active preconditioning session (experimental)."""
    ack(await client.stop_on_demand_preconditioning(vin), 'stopOnDemandPreconditioning')
