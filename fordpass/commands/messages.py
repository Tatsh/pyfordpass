"""In-app message center."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from rich.table import Table
import click

from .utils import (
    console,
    debug_option,
    dump_json,
    format_iso_datetime,
    json_option,
    should_emit_json,
    validate_message_ids_exist,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient

_BODY_PREVIEW_MAX = 80
"""
Maximum length of a message body rendered in the inbox table.

:meta hide-value:
"""


@click.group()
def messages() -> None:
    """In-app message center."""


@messages.command('list')
@debug_option
@json_option
@with_client
async def messages_list(client: AsyncFordPassClient, _ctx: click.Context, *, as_json: bool) -> None:
    """List the message center inbox."""
    resp = await client.get_messages()
    if should_emit_json(as_json):
        dump_json(resp)
        return
    result = resp.get('result') if isinstance(resp, Mapping) else None
    items = (result.get('messages') if isinstance(result, Mapping) else None) or []
    if not items:
        console.print('[dim]The inbox is empty.[/dim]')
        return
    table = Table(title='Message center', title_style='bold cyan')
    table.add_column('ID', style='dim')
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
        # ``messageId`` is the numeric id consumed by ``messages delete`` /
        # ``messages mark-read``; the upstream also returns an inner sequential
        # ``id`` field but that one isn't used by the delete / mark-read payload.
        table.add_row(str(m.get('messageId') or m.get('id') or '-'),
                      format_iso_datetime(m.get('createdDate')), str(
                          m.get('messageSubject') or '-'), flag, body)
    console.print(table)


@messages.command('show')
@debug_option
@click.argument('message_id', type=int)
@json_option
@with_client
async def messages_show(client: AsyncFordPassClient, _ctx: click.Context, message_id: int, *,
                        as_json: bool) -> None:
    """Show the full body of one inbox message by ID."""  # noqa: DOC501
    resp = await client.get_messages()
    result = resp.get('result') if isinstance(resp, Mapping) else None
    items = (result.get('messages') if isinstance(result, Mapping) else None) or []
    needle = str(message_id)
    target = next((m for m in items if isinstance(m, Mapping) and (
        m.get('messageId') == needle or str(m.get('id') or '') == needle)), None)
    if target is None:
        msg = f'Message {message_id} not found in the inbox.'
        raise click.ClickException(msg)
    if should_emit_json(as_json):
        dump_json(target)
        return
    header = Table(title=f'Message - {target.get("messageId") or message_id}',
                   title_style='bold cyan')
    header.add_column('Field', style='cyan')
    header.add_column('Value')
    header.add_row('Subject', str(target.get('messageSubject') or '-'))
    header.add_row('When', format_iso_datetime(target.get('createdDate')))
    header.add_row('Status', 'Read' if target.get('isRead') else 'Unread')
    header.add_row('Type', str(target.get('messageType') or '-'))
    header.add_row('Content', str(target.get('contentType') or '-'))
    if (vin := target.get('relevantVin')) is not None:
        header.add_row('VIN', str(vin))
    if (priority := target.get('priority')) is not None:
        header.add_row('Priority', str(priority))
    console.print(header)
    body = str(target.get('messageBody') or '').strip()
    if body:
        console.print('[bold cyan]Body[/bold cyan]')
        console.print(f'  {body}')
    else:
        console.print('[dim]The message has no body.[/dim]')


@messages.command('delete')
@debug_option
@click.argument('message_ids', nargs=-1, required=True, type=int)
@json_option
@with_client
async def messages_delete(client: AsyncFordPassClient, _ctx: click.Context,
                          message_ids: tuple[int, ...], *, as_json: bool) -> None:
    """Delete one or more inbox messages by ID."""
    await validate_message_ids_exist(client, message_ids)
    resp = await client.delete_messages(message_ids)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    console.print(f'[green]Deleted[/green] {len(message_ids)} '
                  f'message{"s" if len(message_ids) != 1 else ""}.')


@messages.command('mark-read')
@debug_option
@click.argument('message_ids', nargs=-1, required=True, type=int)
@json_option
@with_client
async def messages_mark_read(client: AsyncFordPassClient, _ctx: click.Context,
                             message_ids: tuple[int, ...], *, as_json: bool) -> None:
    """Mark one or more inbox messages as read by ID."""
    await validate_message_ids_exist(client, message_ids)
    resp = await client.mark_messages_read(message_ids)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    console.print(f'[green]Marked read[/green] {len(message_ids)} '
                  f'message{"s" if len(message_ids) != 1 else ""}.')
