"""Garage: list, show, update nickname / plate / mileage."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.table import Table
import click

from .utils import console, dump_json, json_option, should_emit_json, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient


@click.group()
def vehicle() -> None:
    """Garage: list, show, update nickname / plate / mileage."""


def _garage_vehicles(garage: Any) -> list[dict[str, Any]]:
    """
    Normalise a garage payload to a flat list of vehicle dicts.

    The garage endpoint may return either a bare JSON array or an envelope
    ``{"vehicles": [...]}`` depending on backend version, so the consumer
    cannot rely on a single shape.

    Parameters
    ----------
    garage : Any
        Decoded JSON returned by :py:meth:`fordpass.client.FordPassNiquestsClient.list_garage`.

    Returns
    -------
    list[dict[str, Any]]
        The flat list of vehicle records; empty if the payload is neither
        a list nor a recognised envelope.
    """
    if isinstance(garage, list):
        return garage
    if isinstance(garage, dict):
        vs = garage.get('vehicles')
        if isinstance(vs, list):
            return vs
    return []


@vehicle.command('list')
@json_option
@with_client
async def vehicle_list(client: FordPassNiquestsClient, _ctx: click.Context, *,
                       as_json: bool) -> None:
    """List all vehicles in your garage."""
    vehicles = _garage_vehicles(await client.list_garage())
    if should_emit_json(as_json):
        dump_json(vehicles)
        return
    if not vehicles:
        console.print('[dim](empty garage)[/dim]')
        return
    table = Table(title='Garage', title_style='bold cyan')
    table.add_column('VIN', style='cyan', no_wrap=True)
    table.add_column('Nickname')
    table.add_column('Plate')
    table.add_column('Year', justify='right')
    table.add_column('Model')
    table.add_column('Colour')
    for v in vehicles:
        prof = v.get('profile') or {}
        table.add_row(
            v.get('vin') or '-',
            v.get('nickName') or '-',
            v.get('licensePlate') or '-',
            str(prof.get('year') or ''),
            str(prof.get('model') or ''),
            str(prof.get('color') or v.get('color') or ''),
        )
    console.print(table)


@vehicle.command('show')
@vin_argument
@with_client
async def vehicle_show(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Dump the full garage entry for a VIN."""  # noqa: DOC501
    for v in _garage_vehicles(await client.list_garage()):
        if v.get('vin') == vin:
            dump_json(v)
            return
    msg = f'VIN {vin} not found in garage.'
    raise click.ClickException(msg)


@vehicle.command('nickname')
@vin_argument
@click.argument('name')
@with_client
async def vehicle_nickname(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                           name: str) -> None:
    """Set the vehicle nickname."""
    dump_json(await client.update_vehicle_details(vin, nick_name=name))


@vehicle.command('plate')
@vin_argument
@click.argument('plate')
@with_client
async def vehicle_plate(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                        plate: str) -> None:
    """Set the license plate."""
    dump_json(await client.update_vehicle_details(vin, license_plate=plate))


@vehicle.command('mileage')
@vin_argument
@click.argument('miles', type=int)
@with_client
async def vehicle_mileage(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                          miles: int) -> None:
    """Record a manual odometer reading."""
    dump_json(await client.update_vehicle_details(vin, mileage=miles))
