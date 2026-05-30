"""OTA: status, toggle auto-updates, release notes."""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .utils import ack, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient


@click.group()
def ota() -> None:
    """Over-the-air updates: status, toggle, release notes."""


@ota.command('status')
@vin_argument
@with_client
async def ota_status(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Queue an ASU-settings read (server pushes result via WS)."""
    ack(await client.get_asu_settings(vin), 'getASUSettingsCommand')


@ota.command('toggle')
@vin_argument
@click.argument('state', type=click.Choice(['on', 'off'], case_sensitive=False))
@with_client
async def ota_toggle(client: FordPassNiquestsClient, _ctx: click.Context, vin: str,
                     state: str) -> None:
    """Toggle automatic software updates."""
    ack(await client.set_asu_enabled(vin, enabled=state.lower() == 'on'),
        f'publishASUSettingsCommand({state.upper()})')


@ota.command('release-notes')
@vin_argument
@with_client
async def ota_release_notes(client: FordPassNiquestsClient, _ctx: click.Context, vin: str) -> None:
    """Fetch release notes for the pending OTA (two-step flow)."""
    notes = await client.get_release_notes(vin)
    if notes is None:
        click.echo('(no MMOTA alert pending — nothing to fetch)')
        return
    click.echo(notes.get('response') or '(empty)')
