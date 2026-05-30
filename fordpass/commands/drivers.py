"""Secondary-driver management."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from rich.table import Table
import click

from .utils import (
    console,
    debug_option,
    dump_json,
    json_option,
    should_emit_json,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient


@click.group()
def drivers() -> None:
    """Secondary-driver management."""


@drivers.command('list')
@debug_option
@vin_argument
@json_option
@with_client
async def drivers_list(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       as_json: bool) -> None:
    """List authorised and pending drivers."""
    resp = await client.list_drivers(vin)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    users = (resp.get('authAndPendingUsers') if isinstance(resp, Mapping) else None) or []
    if not users:
        console.print('[dim]No secondary drivers are authorized.[/dim]')
        return
    table = Table(title=f'Drivers - {vin}', title_style='bold cyan')
    table.add_column('Name')
    table.add_column('Status')
    table.add_column('Invite ID', style='dim')
    table.add_column('GUID', style='dim')
    for u in users:
        status = u.get('userAuthStatus') or '?'
        colour = '[green]' if status == 'Authorized' else '[yellow]'
        table.add_row(
            u.get('displayName') or '-', f'{colour}{status}[/]',
            u.get('inviteId') or '-',
            u.get('GUID') or '-')
    console.print(table)


@drivers.command('count')
@debug_option
@vin_argument
@json_option
@with_client
async def drivers_count(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        as_json: bool) -> None:
    """Show the current authorised-user count."""
    resp = await client.get_authorized_user_count(vin)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    n = resp.get('count') if isinstance(resp, Mapping) else None
    if n is None:
        console.print('[dim]The authorised-user count is unknown.[/dim]')
        return
    word = 'driver' if n == 1 else 'drivers'
    console.print(f'[bold cyan]{n}[/bold cyan] authorised {word}')


@drivers.command('invite')
@debug_option
@vin_argument
@click.option('--email', required=True, help="Invitee's email.")
@click.option('--name', 'inviter', required=True, help="Inviter's first name.")
@click.option('--vehicle-name', required=True, help='Display name in the invite email.')
@with_client
async def drivers_invite(client: AsyncFordPassClient, _ctx: click.Context, vin: str, email: str,
                         inviter: str, vehicle_name: str) -> None:
    """Send a secondary-driver invite by email."""  # noqa: DOC501
    res = await client.invite_driver(vin,
                                     secondary_email=email,
                                     inviter_first_name=inviter,
                                     vehicle_display_name=vehicle_name)
    if res.get('errorCode'):
        msg = f"Invite failed: {res.get('errorMessage')} (code {res['errorCode']})."
        raise click.ClickException(msg)
    click.secho('Invite sent.', fg='green')
