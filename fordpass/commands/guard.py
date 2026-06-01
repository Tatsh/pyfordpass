"""Guard Mode commands: status, enable, disable (Ford MPS API)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import click

from .utils import debug_option, dump_json, json_option, should_emit_json, vin_argument, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.guard import GuardModeResponse


def _render(resp: GuardModeResponse, *, as_json: bool) -> None:
    """
    Print a Guard Mode response as JSON or a short status line.

    Parameters
    ----------
    resp : GuardModeResponse
        The parsed Guard Mode response.
    as_json : bool
        Emit machine-readable JSON instead of a status line.
    """
    if should_emit_json(as_json):
        dump_json(resp)
        return
    if not isinstance(resp, Mapping) or not resp:
        click.secho('No Guard Mode data returned.', fg='yellow')
        return
    message = resp.get('returnMessage', '')
    code = resp.get('returnCode', '')
    click.secho(f'Guard Mode: {message} (code {code}).', fg='green')


@click.group()
def guard() -> None:
    """Guard Mode status and control (Ford MPS API)."""


@guard.command('status')
@debug_option
@vin_argument
@json_option
@with_client
async def guard_status(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       as_json: bool) -> None:
    """Show the current Guard Mode session state."""
    _render(await client.get_guard_mode(vin), as_json=as_json)


@guard.command('enable')
@debug_option
@vin_argument
@json_option
@with_client
async def guard_enable(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       as_json: bool) -> None:
    """Enable Guard Mode."""
    _render(await client.set_guard_mode(vin), as_json=as_json)


@guard.command('disable')
@debug_option
@vin_argument
@json_option
@with_client
async def guard_disable(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        as_json: bool) -> None:
    """Disable Guard Mode."""
    _render(await client.delete_guard_mode(vin), as_json=as_json)
