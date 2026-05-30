"""Service planner: upcoming + completed history."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

import click

from .utils import dump_json, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient
    from fordpass.typing import DistanceUnit


@click.group()
def service() -> None:
    """Service planner: upcoming + completed history."""


@service.command('upcoming')
@click.option('--odometer', type=int, required=True)
@click.option('--uom', type=click.Choice(['mi', 'km']), default='mi', show_default=True)
@with_client
async def service_upcoming(client: FordPassNiquestsClient, _ctx: click.Context, odometer: int,
                           uom: str) -> None:
    """List upcoming service actions for the given odometer."""
    dump_json(await client.get_service_planner_upcoming(odometer=odometer,
                                                        uom=cast('DistanceUnit', uom)))


@service.command('history')
@click.option('--odometer', type=int, required=True)
@click.option('--uom', type=click.Choice(['mi', 'km']), default='mi', show_default=True)
@with_client
async def service_history(client: FordPassNiquestsClient, _ctx: click.Context, odometer: int,
                          uom: str) -> None:
    """List completed service actions."""
    dump_json(await client.get_service_planner_history(odometer=odometer,
                                                       uom=cast('DistanceUnit', uom)))
