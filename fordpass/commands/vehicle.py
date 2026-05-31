"""Garage: list, show, update nickname / plate / mileage."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, cast
import json
import re

from fordpass.utils import is_list_like
from rich.json import JSON
from rich.table import Table
import click

from .utils import (
    check_readiness,
    console,
    debug_option,
    dump_json,
    json_option,
    should_emit_json,
    vin_argument,
    vin_option,
    with_client,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.vehicle import GarageVehicle


@click.group()
def vehicle() -> None:
    """Garage: list, show, update nickname / plate / mileage."""


def _garage_vehicles(
        garage: Sequence[GarageVehicle] | Mapping[str, Sequence[GarageVehicle]]
) -> list[GarageVehicle]:
    """
    Normalise a garage payload to a flat list of vehicle dicts.

    The garage endpoint may return either a bare JSON array or an envelope
    ``{"vehicles": [...]}`` depending on backend version, so the consumer cannot rely on a single
    shape.

    Parameters
    ----------
    garage : Sequence[GarageVehicle] | Mapping[str, Sequence[GarageVehicle]]
        Decoded JSON returned by :py:meth:`fordpass.client.AsyncFordPassClient.list_garage`,
        either the bare list or the ``{"vehicles": [...]}`` envelope.

    Returns
    -------
    list[GarageVehicle]
        The flat list of vehicle records; empty if the payload is neither a list nor a recognised
        envelope.
    """
    if is_list_like(garage):
        return list(cast('Sequence[GarageVehicle]', garage))
    if isinstance(garage, Mapping):
        vs = garage.get('vehicles')  # ty: ignore[invalid-argument-type]
        if is_list_like(vs):
            return list(cast('Sequence[GarageVehicle]', vs))
    return []


@vehicle.command('list')
@debug_option
@json_option
@with_client
async def vehicle_list(client: AsyncFordPassClient, _ctx: click.Context, *, as_json: bool) -> None:
    """List all vehicles in your garage."""
    vehicles = _garage_vehicles(await client.list_garage())
    if should_emit_json(as_json):
        dump_json(vehicles)
        return
    if not vehicles:
        console.print('[dim]The garage is empty.[/dim]')
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
            v.get('licensePlate') or '-', str(prof.get('year') or ''), str(prof.get('model') or ''),
            str(prof.get('color') or v.get('color') or ''))
    console.print(table)


_CAPABILITY_HIDDEN_VALUES = frozenset({'NoDisplay', 'Unavailable', 'None'})
"""
Capability-map values that mark a feature as not applicable to this vehicle.

The garage capability map flags every feature the FordPass app *could* show. Values in this set
mean "do not surface in the UI" - the feature is either absent on this vehicle or hidden by
configuration. They are filtered out of the pretty ``vehicle show`` output.

:meta hide-value:
"""

_EV_ONLY_CAPABILITIES = frozenset({
    'bidirectionalPowerTransferRemoteControl', 'departureTimes', 'displayPreferredChargeTimes',
    'electricVehicleOnDemandConditioning', 'globalStartStopCharge', 'offPlugConditioning',
    'onetimeChargeLimit', 'payForCharge', 'payForChargeUserSubscription', 'plugAndCharge',
    'plugAndChargeUserSubscription', 'proPowerOnBoard', 'showEVBatteryLevel', 'tripAndChargeLogs',
    'vehicleChargingStatusExtended'
})
"""
Capability-map keys that only apply to BEV/PHEV vehicles.

Filtered out of the pretty ``vehicle show`` output when ``profile.engineType`` is ``'ICE'``. Most
of these are already screened out by :py:data:`_CAPABILITY_HIDDEN_VALUES` (the upstream marks them
``NoDisplay``) but a handful (e.g. ``showEVBatteryLevel`` as a Boolean) leak through.

:meta hide-value:
"""

_EV_ONLY_PROFILE_FIELDS = frozenset({'globalChargeSettings', 'highVoltageBatteryPackType'})
"""
Profile fields that only apply to BEV/PHEV vehicles.

Filtered out of the pretty ``vehicle show`` output when ``profile.engineType`` is ``'ICE'``.

:meta hide-value:
"""

_PROFILE_HIDDEN_VALUES = frozenset({'None', 'Unavailable'})
"""
Profile-block values that mark the field as not applicable to this vehicle.

Filtered out of the pretty ``vehicle show`` output the same way :py:data:`_CAPABILITY_HIDDEN_VALUES`
are.

:meta hide-value:
"""

_ACRONYMS = frozenset({
    'AC', 'ASU', 'BEV', 'CCS', 'DC', 'DEF', 'EV', 'EVSE', 'GPS', 'HMI', 'HV', 'ICE', 'IP', 'JSON',
    'OEM', 'OTA', 'PAAK', 'PHEV', 'SDN', 'SOC', 'TCU', 'TMC', 'TPMS', 'URL', 'USB', 'VIN', 'XEV'
})
"""
Tokens that should be rendered in all-caps after camelCase splitting.

The default :py:func:`_humanize_camel` would otherwise produce ``Ccs Connectivity`` or ``Xev
Battery Range`` - title-casing every token. Anything whose uppercase form is in this set is
re-uppercased post-split.

:meta hide-value:
"""


def _humanize_camel(key: str) -> str:
    """
    Convert a camelCase / PascalCase identifier into a human-readable title.

    Parameters
    ----------
    key : str
        The camelCase / PascalCase identifier.

    Returns
    -------
    str
        The space-separated title, with known acronyms (per :py:data:`_ACRONYMS`) rendered in
        all-caps.
    """
    spaced = re.sub(r'(?<=[a-z0-9])([A-Z])', r' \1', key)
    spaced = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced)
    capitalised = spaced[:1].upper() + spaced[1:]
    return ' '.join(
        token.upper() if token.upper() in _ACRONYMS else token for token in capitalised.split(' '))


def _render_kv_table(title: str, rows: list[tuple[str, str]]) -> Table:
    """
    Build a two-column ``Field`` / ``Value`` Rich table.

    Parameters
    ----------
    title : str
        Title shown above the table.
    rows : list[tuple[str, str]]
        ``(field_label, value)`` pairs to populate.

    Returns
    -------
    Table
        The populated Rich table.
    """
    table = Table(title=title, title_style='bold cyan', show_header=True)
    table.add_column('Field', style='cyan')
    table.add_column('Value')
    for label, value in rows:
        table.add_row(label, value)
    return table


@vehicle.command('show')
@debug_option
@json_option
@vin_argument
@with_client
async def vehicle_show(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       as_json: bool) -> None:
    """Show details for one vehicle from your garage."""  # noqa: DOC501
    target = next((v for v in _garage_vehicles(await client.list_garage()) if v.get('vin') == vin),
                  None)
    if target is None:
        msg = f'VIN {vin} not found in garage.'
        raise click.ClickException(msg)
    if should_emit_json(as_json):
        dump_json(target)
        return
    # Identity block.
    profile = target.get('profile') or {}
    identity_rows = [('VIN', str(target.get('vin') or '-')),
                     ('Nickname', str(target.get('nickName') or '-')),
                     ('Licence plate', str(target.get('licensePlate') or '-')),
                     ('Make / Model / Year',
                      f'{profile.get("make") or "?"} {profile.get("model") or "?"} '
                      f'{profile.get("year") or "?"}'.strip()),
                     ('Colour', str(target.get('color') or profile.get('paintDescription') or '-')),
                     ('Engine type', str(profile.get('engineType') or '-')),
                     ('Transmission', str(profile.get('transmissionIndicator') or '-')),
                     ('Preferred dealer', (f'{target.get("preferredDealer") or "-"} '
                                           f'({target.get("sourceOfPreferredDealer") or "?"})')),
                     ('Auth status', str(target.get('userAuthStatus') or '-')),
                     ('Recalls (open / closed)',
                      f'{profile.get("recallCount", 0)} / {profile.get("nonRecallCount", 0)}')]
    console.print(_render_kv_table(f'Vehicle - {vin}', identity_rows))
    is_ice = str(profile.get('engineType') or '').upper() == 'ICE'
    # Profile block - drop the keys already shown in identity, hidden values,
    # and (for ICE) EV-only fields.
    shown_in_identity = {
        'make', 'model', 'year', 'paintDescription', 'engineType', 'transmissionIndicator',
        'recallCount', 'nonRecallCount'
    }
    profile_rows = sorted(
        (_humanize_camel(k), str(v)) for k, v in profile.items()
        if k not in shown_in_identity and not (is_ice and k in _EV_ONLY_PROFILE_FIELDS)
        and v is not None and str(v) and str(v) not in _PROFILE_HIDDEN_VALUES)
    if profile_rows:
        console.print(_render_kv_table('Profile', profile_rows))
    # Capabilities - drop NoDisplay / Unavailable / None and (for ICE) EV-only ones.
    caps = target.get('capabilities') or {}
    visible_caps = sorted((_humanize_camel(k), str(v)) for k, v in caps.items()
                          if v not in {None, ''} and str(v) not in _CAPABILITY_HIDDEN_VALUES
                          and not (is_ice and k in _EV_ONLY_CAPABILITIES))
    if visible_caps:
        console.print(_render_kv_table('Capabilities', visible_caps))
    else:
        console.print('[dim]No capabilities are enabled.[/dim]')


@vehicle.command('ready')
@debug_option
@json_option
@vin_argument
@with_client
async def vehicle_ready(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        as_json: bool) -> None:
    """Report whether the vehicle is out of Battery Saver mode for remote commands."""
    readiness = await check_readiness(client, vin)
    if should_emit_json(as_json):
        dump_json({
            'lifeCycleMode': readiness.life_cycle_mode,
            'loadStatus': readiness.load_status,
            'ok': readiness.ok,
            'raw': readiness.raw,
            'reasons': list(readiness.reasons),
            'stateOfCharge': readiness.state_of_charge,
            'voltage': readiness.voltage
        })
        return
    table = Table(title=f'Remote-command readiness - {vin}', title_style='bold cyan')
    table.add_column('Field', style='cyan')
    table.add_column('Value')
    verdict = ('[green]Ready[/green]' if readiness.ok else '[red]Battery Saver mode[/red]')
    table.add_row('Status', verdict)
    table.add_row('12V voltage',
                  f'{readiness.voltage:.2f} V' if readiness.voltage is not None else '-')
    table.add_row(
        '12V state of charge',
        f'{readiness.state_of_charge:.0f}%' if readiness.state_of_charge is not None else '-')
    table.add_row('Battery load status', readiness.load_status or '-')
    table.add_row('Life-cycle mode', readiness.life_cycle_mode or '-')
    console.print(table)
    for reason in readiness.reasons:
        console.print(f'  [yellow]•[/yellow] {reason}')
    if not readiness.ok:
        console.print('[dim]Start the vehicle to clear Battery Saver mode, or pass --force '
                      'on a remote-* command to send anyway.[/dim]')
    if readiness.raw:
        console.print()
        console.print('[bold cyan]Diagnostic payload[/bold cyan] '
                      '[dim]- server-side preclusion state.[/dim]')
        console.print(JSON(json.dumps(readiness.raw, default=str, sort_keys=True)))


@vehicle.command('nickname')
@debug_option
@vin_option
@click.argument('name')
@with_client
async def vehicle_nickname(client: AsyncFordPassClient, _ctx: click.Context, name: str,
                           vin: str) -> None:
    """Set the vehicle nickname."""
    await client.update_vehicle_details(vin, nick_name=name)
    console.print(f'[green]Nickname updated to {name!r}.[/green]')


@vehicle.command('plate')
@debug_option
@vin_option
@click.argument('plate')
@with_client
async def vehicle_plate(client: AsyncFordPassClient, _ctx: click.Context, plate: str,
                        vin: str) -> None:
    """Set the license plate."""
    await client.update_vehicle_details(vin, license_plate=plate)
    console.print(f'[green]Licence plate updated to {plate!r}.[/green]')


@vehicle.command('mileage')
@debug_option
@vin_option
@click.argument('miles', type=int)
@with_client
async def vehicle_mileage(client: AsyncFordPassClient, _ctx: click.Context, miles: int,
                          vin: str) -> None:
    """Record a manual odometer reading."""
    await client.update_vehicle_details(vin, mileage=miles)
    console.print(f'[green]Mileage recorded: {miles}.[/green]')
