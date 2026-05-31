"""Service planner: upcoming + completed history (summary + per-row detail)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from fordpass.config import KM_TO_MI
from fordpass.utils import is_list_like
from rich.table import Table
import click

from .utils import (
    UOM_CHOICE,
    console,
    debug_option,
    dump_json,
    format_iso_date,
    json_option,
    should_emit_json,
    vin_argument,
    with_client,
)


def _format_money(price: object) -> str:
    """
    Render a ``price`` block as ``"$0.00"`` / ``"€12.34"`` / ``-``.

    Parameters
    ----------
    price : object
        Either a mapping with ``{total, currencyCode}`` or ``None`` / missing.

    Returns
    -------
    str
        The formatted currency string, or ``'-'`` when no total is present.
    """
    if not isinstance(price, Mapping):
        return '-'
    price_map = cast('Mapping[str, Any]', price)
    total = price_map.get('total')
    currency = str(price_map.get('currencyCode') or '')
    if total is None or not isinstance(total, (int, float)):
        return '-'
    symbol = {'USD': '$', 'EUR': '€', 'GBP': '£', 'CAD': 'C$'}.get(currency, currency)
    return f'{symbol}{float(total):.2f}'


def _format_tags(tags: object) -> str:
    """
    Render a tags list as comma-joined uppercase markers.

    Parameters
    ----------
    tags : object
        A list-like value (or anything else, which renders as ``'-'``).

    Returns
    -------
    str
        Comma-joined uppercase markers, or ``'-'`` when ``tags`` is empty / not a list.
    """
    if not is_list_like(tags) or not tags:
        return '-'
    return ', '.join(str(t) for t in tags)


if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.common import DistanceUnit
    from fordpass.typing.service import ServiceActionDetail


async def _resolve_odometer(client: AsyncFordPassClient, vin: str, odometer: int | None,
                            uom: str) -> int:
    """
    Return ``odometer`` if supplied; otherwise fetch the live reading from telemetry.

    The service-planner endpoints declare ``odometer`` as a nullable query param but the upstream
    gateway returns HTTP 400 when it is omitted, so the CLI falls back to a telemetry call rather
    than confronting the user with a manual lookup.

    Parameters
    ----------
    client : AsyncFordPassClient
        The signed-in client used to fetch telemetry on fallback.
    vin : str
        VIN of the target vehicle.
    odometer : int | None
        Explicit odometer reading the caller provided (in ``uom`` units), or ``None`` to trigger
        the telemetry fallback.
    uom : str
        Unit of measure (``'mi'`` or ``'km'``) of the returned value.

    Returns
    -------
    int
        The resolved odometer reading in ``uom`` units, rounded to the nearest integer.

    Raises
    ------
    click.ClickException
        If the vehicle does not report an odometer reading.
    """
    if odometer is not None:
        return odometer
    km = await client.get_odometer(vin)
    if km is None:
        msg = ('Could not determine the current odometer reading; pass --odometer '
               'explicitly.')
        raise click.ClickException(msg)
    return round(km * KM_TO_MI) if uom == 'mi' else round(km)


@click.group()
def service() -> None:
    """Service planner: upcoming + completed history."""


_UPCOMING_TYPE_STYLE = {'MAINTENANCE': '[cyan]Maintenance[/cyan]', 'RECALL': '[red]Recall[/red]'}
"""
Display style per upcoming-action ``type`` value.

:meta hide-value:
"""


@service.command('upcoming')
@debug_option
@vin_argument
@click.option('--odometer',
              type=int,
              default=None,
              help='Current odometer reading; auto-fetched from telemetry when omitted.')
@click.option('--uom', type=UOM_CHOICE, default='mi', show_default=True)
@json_option
@with_client
async def service_upcoming(client: AsyncFordPassClient, _ctx: click.Context, vin: str,
                           odometer: int | None, uom: str, *, as_json: bool) -> None:
    """List upcoming service actions."""
    odo = await _resolve_odometer(client, vin, odometer, uom)
    resp = await client.get_service_planner_upcoming(vin,
                                                     odometer=odo,
                                                     uom=cast('DistanceUnit', uom))
    if should_emit_json(as_json):
        dump_json(resp)
        return
    actions_raw = resp.get('upcomingServiceActions') if isinstance(resp, Mapping) else None
    actions: list[Any] = list(actions_raw) if is_list_like(actions_raw) else []
    if not actions:
        console.print('[dim]No upcoming service actions are scheduled.[/dim]')
        return
    table = Table(title=f'Upcoming service - {vin}', title_style='bold cyan')
    table.add_column('ID', style='dim')
    table.add_column('Due', style='dim')
    table.add_column('Type')
    table.add_column('Title')
    table.add_column('Tags', style='dim')
    for a in actions:
        if not isinstance(a, Mapping):
            continue
        action_type = str(a.get('type') or '-')
        table.add_row(str(a.get('id') or '-'), format_iso_date(a.get('date')),
                      _UPCOMING_TYPE_STYLE.get(action_type, action_type), str(
                          a.get('title') or '-'), _format_tags(a.get('tags')))
    console.print(table)


@service.command('history')
@debug_option
@vin_argument
@click.option('--odometer',
              type=int,
              default=None,
              help='Current odometer reading; auto-fetched from telemetry when omitted.')
@click.option('--uom', type=UOM_CHOICE, default='mi', show_default=True)
@json_option
@with_client
async def service_history(client: AsyncFordPassClient, _ctx: click.Context, vin: str,
                          odometer: int | None, uom: str, *, as_json: bool) -> None:
    """List completed service actions."""
    odo = await _resolve_odometer(client, vin, odometer, uom)
    resp = await client.get_service_planner_history(vin,
                                                    odometer=odo,
                                                    uom=cast('DistanceUnit', uom))
    if should_emit_json(as_json):
        dump_json(resp)
        return
    actions_raw = resp.get('completedServiceActions') if isinstance(resp, Mapping) else None
    actions: list[Any] = list(actions_raw) if is_list_like(actions_raw) else []
    if not actions:
        console.print('[dim]No service history is recorded.[/dim]')
        return
    # Sort newest first by ISO date string (lexicographic order matches chronological).
    sorted_actions = sorted((a for a in actions if isinstance(a, Mapping)),
                            key=lambda a: str(a.get('date') or ''),
                            reverse=True)
    table = Table(title=f'Service history - {vin}', title_style='bold cyan')
    table.add_column('ID', style='dim')
    table.add_column('Date', style='dim')
    table.add_column('Dealer / title')
    table.add_column('Cost', justify='right')
    table.add_column('Tags', style='dim')
    for a in sorted_actions:
        table.add_row(str(a.get('id') or '-'), format_iso_date(a.get('date')),
                      str(a.get('title') or '-'), _format_money(a.get('price')),
                      _format_tags(a.get('tags')))
    console.print(table)


def _render_maintenance_detail(resp: ServiceActionDetail, odometer_cell: str) -> None:
    """Render the ``maintenanceItem`` branch of the upcoming-detail response."""
    item = resp.get('maintenanceItem') if isinstance(resp.get('maintenanceItem'), Mapping) else {}
    details = (item.get('maintenanceDetails') if isinstance(item, Mapping)
               and isinstance(item.get('maintenanceDetails'), Mapping) else {})
    summary = Table(title=f'Upcoming maintenance - {resp.get("id") or "?"}',
                    title_style='bold cyan')
    summary.add_column('Field', style='cyan')
    summary.add_column('Value')
    summary.add_row('Title', str(resp.get('title') or '-'))
    summary.add_row('Type', '[cyan]Maintenance[/cyan]')
    summary.add_row(
        'Due',
        format_iso_date(details.get('maintenanceDate')) if isinstance(details, Mapping) else '-')
    summary.add_row('Odometer', odometer_cell)
    console.print(summary)
    overview = details.get('overview') if isinstance(details, Mapping) else None
    if is_list_like(overview) and overview:
        console.print('[bold cyan]Work items[/bold cyan]')
        for item_text in overview:
            console.print(f'  • {item_text}')


def _render_recall_detail(resp: ServiceActionDetail, odometer_cell: str) -> None:
    """Render the ``recallItem`` branch of the upcoming-detail response."""
    item = resp.get('recallItem') if isinstance(resp.get('recallItem'), Mapping) else {}
    if not isinstance(item, Mapping):
        item = {}
    summary = Table(title=f'Recall - {resp.get("id") or "?"}', title_style='bold red')
    summary.add_column('Field', style='cyan')
    summary.add_column('Value')
    summary.add_row('Title', str(resp.get('title') or '-'))
    summary.add_row('Campaign #', str(item.get('campaignNumber') or '-'))
    summary.add_row('NHTSA #', str(item.get('nhtsaNumber') or '-'))
    summary.add_row('Type', str(item.get('recallType') or '-'))
    summary.add_row('Issued', format_iso_date(item.get('recallDate')))
    summary.add_row('Odometer', odometer_cell)
    console.print(summary)
    for label, key in (('Description', 'description'), ('Safety risk', 'safetyRisk'), ('Remedy',
                                                                                       'remedy')):
        text = item.get(key)
        if isinstance(text, str) and text.strip():
            console.print(f'[bold cyan]{label}[/bold cyan]')
            console.print(f'  {text}')


@service.command('upcoming-detail')
@debug_option
@click.argument('service_action_id')
@vin_argument
@click.option('--odometer',
              type=int,
              default=None,
              help='Current odometer reading; auto-fetched from telemetry when omitted.')
@click.option('--uom', type=UOM_CHOICE, default='mi', show_default=True)
@json_option
@with_client
async def service_upcoming_detail(client: AsyncFordPassClient, _ctx: click.Context,
                                  service_action_id: str, vin: str, odometer: int | None, uom: str,
                                  *, as_json: bool) -> None:
    """Show detail for one upcoming service action."""
    odo = await _resolve_odometer(client, vin, odometer, uom)
    resp = await client.get_service_action_detail(service_action_id,
                                                  vin=vin,
                                                  odometer=odo,
                                                  uom=cast('DistanceUnit', uom))
    if should_emit_json(as_json):
        dump_json(resp)
        return
    odometer_reading = resp.get('odometerReading')
    odometer_cell = (f'{float(odometer_reading):,.1f} {uom}' if isinstance(
        odometer_reading, (int, float)) else '-')
    service_type = str(resp.get('serviceType') or '').upper()
    if service_type == 'MAINTENANCE':
        _render_maintenance_detail(resp, odometer_cell)
    elif service_type == 'RECALL':
        _render_recall_detail(resp, odometer_cell)
    else:
        # Unknown variant: fall back to JSON so we don't hide anything.
        dump_json(resp)


@service.command('history-detail')
@debug_option
@click.argument('service_event_id')
@vin_argument
@click.option('--odometer',
              type=int,
              default=None,
              help='Current odometer reading; auto-fetched from telemetry when omitted.')
@click.option('--uom', type=UOM_CHOICE, default='mi', show_default=True)
@json_option
@with_client
async def service_history_detail(client: AsyncFordPassClient, _ctx: click.Context,
                                 service_event_id: str, vin: str, odometer: int | None, uom: str, *,
                                 as_json: bool) -> None:
    """Show detail for one completed service event."""
    odo = await _resolve_odometer(client, vin, odometer, uom)
    resp = await client.get_completed_service_action_detail(service_event_id,
                                                            vin=vin,
                                                            odometer=odo,
                                                            uom=cast('DistanceUnit', uom))
    if should_emit_json(as_json):
        dump_json(resp)
        return
    # Header / summary table.
    odometer_reading = resp.get('odometerReading')
    odometer_cell = (f'{float(odometer_reading):,.1f} {uom}' if isinstance(
        odometer_reading, (int, float)) else '-')
    summary = Table(title=f'Service event - {resp.get("id") or service_event_id}',
                    title_style='bold cyan',
                    show_header=True)
    summary.add_column('Field', style='cyan')
    summary.add_column('Value')
    summary.add_row('Dealer', str(resp.get('dealerName') or '-'))
    summary.add_row('Date', format_iso_date(resp.get('serviceDate')))
    summary.add_row('Odometer', odometer_cell)
    summary.add_row('Cost', _format_money(resp.get('price')))
    summary.add_row('Type', str(resp.get('serviceType') or '-'))
    summary.add_row('Editable', 'Yes' if resp.get('editable') else 'No')
    console.print(summary)
    # Services performed.
    services = resp.get('servicesPerformed')
    if is_list_like(services) and services:
        console.print('[bold cyan]Services performed[/bold cyan]')
        for s in services:
            console.print(f'  • {s}')
    else:
        console.print('[dim]No services were recorded for this event.[/dim]')
    # Inspections performed.
    inspections = resp.get('inspectionsPerformed')
    if is_list_like(inspections) and inspections:
        console.print('[bold cyan]Inspections performed[/bold cyan]')
        for inspection in inspections:
            console.print(f'  • {inspection}')
