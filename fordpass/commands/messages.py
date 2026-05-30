"""In-app message center."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table
import click

from .utils import console, dump_json, json_option, should_emit_json, with_client

if TYPE_CHECKING:
    from fordpass.client import FordPassNiquestsClient

_BODY_PREVIEW_MAX = 80
"""Maximum length of a message body rendered in the inbox table.

:meta hide-value:
"""


@click.group()
def messages() -> None:
    """In-app message center."""


@messages.command('list')
@json_option
@with_client
async def messages_list(client: FordPassNiquestsClient, _ctx: click.Context, *,
                        as_json: bool) -> None:
    """List the message center inbox."""
    resp = await client.get_messages()
    if should_emit_json(as_json):
        dump_json(resp)
        return
    result = resp.get('result') if isinstance(resp, dict) else None
    items = (result.get('messages') if isinstance(result, dict) else None) or []
    if not items:
        console.print('[dim](no messages)[/dim]')
        return
    table = Table(title='Message center', title_style='bold cyan')
    table.add_column('When', style='dim')
    table.add_column('Subject')
    table.add_column('Status')
    table.add_column('Body')
    for m in items:
        read = m.get('isRead')
        flag = '[dim]read[/dim]' if read else '[bold yellow]unread[/bold yellow]'
        body = (m.get('messageBody') or '').strip()
        if len(body) > _BODY_PREVIEW_MAX:
            body = body[:_BODY_PREVIEW_MAX - 3] + '...'
        table.add_row(str(m.get('createdDate') or '-'), str(m.get('messageSubject') or '-'), flag,
                      body)
    console.print(table)


@messages.command('delete')
@click.argument('message_ids', nargs=-1, required=True, type=int)
@json_option
@with_client
async def messages_delete(client: FordPassNiquestsClient, _ctx: click.Context,
                          message_ids: tuple[int, ...], *, as_json: bool) -> None:
    """Delete one or more inbox messages by ID."""
    resp = await client.delete_messages(message_ids)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    console.print(f'[green]Deleted[/green] {len(message_ids)} '
                  f'message{"s" if len(message_ids) != 1 else ""}.')


@messages.command('mark-read')
@click.argument('message_ids', nargs=-1, required=True, type=int)
@json_option
@with_client
async def messages_mark_read(client: FordPassNiquestsClient, _ctx: click.Context,
                             message_ids: tuple[int, ...], *, as_json: bool) -> None:
    """Mark one or more inbox messages as read by ID."""
    resp = await client.mark_messages_read(message_ids)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    console.print(f'[green]Marked read[/green] {len(message_ids)} '
                  f'message{"s" if len(message_ids) != 1 else ""}.')
