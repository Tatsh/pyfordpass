"""User account profile."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from fordpass.utils import is_list_like
from rich.table import Table
import click

from .utils import ack, console, debug_option, dump_json, json_option, should_emit_json, with_client

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.profile import SaveProfileFields


@click.group()
def profile() -> None:
    """User account profile."""


@profile.command('show')
@debug_option
@click.option('--groups', help='Comma-separated section filter.')
@json_option
@with_client
async def profile_show(client: AsyncFordPassClient, _ctx: click.Context, groups: str | None, *,
                       as_json: bool) -> None:
    """Get account info."""
    resp = await client.get_profile(profile_groups=groups)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    if not resp:
        console.print('[dim]No profile data was returned.[/dim]')
        return
    table = Table(title='Profile', title_style='bold cyan', show_lines=True)
    table.add_column('Section', style='cyan')
    table.add_column('Field')
    table.add_column('Value')
    # ``ProfileResponse`` is a ``TypedDict`` whose keys depend on the requested
    # ``profileGroups``; iterate it as a plain mapping for dynamic-key access.
    sections = cast('Mapping[str, Any]', resp)
    for section in sorted(sections):
        if section == 'userGuid':
            continue
        for label, value in _flatten_section(sections[section]):
            table.add_row(section, label, value)
    if guid := sections.get('userGuid'):
        table.add_row('userGuid', '', str(guid))
    console.print(table)


def _flatten_section(block: Any) -> list[tuple[str, str]]:
    """
    Flatten one ``profile`` section into ``(label, value)`` rows.

    Parameters
    ----------
    block : Any
        The raw section payload - typically a ``dict`` (most sections) or a
        ``list`` of ``{"fieldName": ..., "value": ...}`` entries
        (``namesExtensions``).

    Returns
    -------
    list[tuple[str, str]]
        Rows ready to feed into :py:class:`rich.table.Table.add_row`.
    """
    if isinstance(block, Mapping):
        items = cast('Mapping[str, Any]', block).items()
        return [(k, '' if v is None else str(v)) for k, v in sorted(items)]
    if is_list_like(block):
        rows: list[tuple[str, str]] = []
        for item in block:
            if isinstance(item, Mapping) and 'fieldName' in item:
                rows.append((str(
                    item['fieldName']), '' if item.get('value') is None else str(item['value'])))
            else:
                rows.append(('', str(item)))
        return rows
    return [('', '' if block is None else str(block))]


@profile.command('update')
@debug_option
@click.option('--field',
              '-f',
              multiple=True,
              help='`section.key=value` - e.g. `phoneNumbers.mobilePhoneNumber=+15555551234`.')
@with_client
async def profile_update(client: AsyncFordPassClient, _ctx: click.Context,
                         field: tuple[str, ...]) -> None:
    """Partial-update account info."""  # ruff:ignore[docstring-missing-exception]
    payload: dict[str, dict[str, Any]] = {}
    for f in field:
        key, _, val = f.partition('=')
        section, _, leaf = key.partition('.')
        if not section or not leaf:
            msg = f'Bad --field syntax: {f!r}. Use section.key=value.'
            raise click.ClickException(msg)
        payload.setdefault(section, {})[leaf] = val
    ack(await client.save_profile(**cast('SaveProfileFields', payload)), 'PATCH profile')
