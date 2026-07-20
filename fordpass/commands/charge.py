"""EV charging commands: start, cancel, pause, set, target, times, status, logs."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, cast, get_args
import json
import sys

from fordpass.typing.electrification import ChargeMode
from rich.table import Table
import click

from .utils import (
    ack,
    assert_ready_or_abort,
    console,
    debug_option,
    dump_json,
    force_option,
    json_option,
    should_emit_json,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient

_CHARGE_MODES: tuple[str, ...] = get_args(ChargeMode)
"""
Valid ``chargeMode`` values, derived from :py:data:`fordpass.typing.electrification.ChargeMode`.

:meta hide-value:
"""

_INT_SETTING_KEYS = ('globalCurrentLimit', 'globalDCPowerLimit', 'globalDCTargetSoc',
                     'globalReserveSoc', 'globalTargetSoc')
"""
``chargeSettings`` keys whose values are integers.

:meta hide-value:
"""

_STR_SETTING_KEYS = ('autoChargePortUnlock', 'chargeMode')
"""
``chargeSettings`` keys whose values are strings.

:meta hide-value:
"""

_SETTING_KEYS = tuple(sorted((*_INT_SETTING_KEYS, *_STR_SETTING_KEYS)))
"""
All recognised ``chargeSettings`` keys, sorted for the ``charge set`` choice.

:meta hide-value:
"""


def _coerce_setting(key: str, value: str) -> str | int:
    """
    Validate and convert a single ``chargeSettings`` value for ``key``.

    Parameters
    ----------
    key : str
        One of :data:`_SETTING_KEYS`.
    value : str
        Raw string value from the command line.

    Returns
    -------
    str | int
        The converted value (``int`` for numeric keys, ``str`` otherwise).

    Raises
    ------
    click.BadParameter
        If a numeric key receives a non-integer, or ``chargeMode`` receives an unknown value.
    """
    if key in _INT_SETTING_KEYS:
        try:
            return int(value)
        except ValueError as e:
            msg = f'{key} requires an integer value, got {value!r}.'
            raise click.BadParameter(msg) from e
    if key == 'chargeMode' and value not in _CHARGE_MODES:
        choices = ', '.join(_CHARGE_MODES)
        msg = f'{value!r} is not a valid charge mode. Choose from: {choices}.'
        raise click.BadParameter(msg)
    return value


def _load_json_body(raw: str) -> dict[str, object]:
    """
    Parse a JSON object from a ``--data`` value, reading stdin when ``raw`` is ``'-'``.

    Parameters
    ----------
    raw : str
        A JSON object string, or ``'-'`` to read the body from standard input.

    Returns
    -------
    dict[str, object]
        The parsed JSON object.

    Raises
    ------
    click.BadParameter
        If the input is not valid JSON or is not a JSON object.
    """
    text = sys.stdin.read() if raw == '-' else raw
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        msg = f'--data is not valid JSON: {e}.'
        raise click.BadParameter(msg) from e
    if not isinstance(parsed, dict):
        msg = '--data must be a JSON object.'
        raise click.BadParameter(msg)
    return parsed


def _extract_location_id(body: Mapping[str, object]) -> str | None:
    """
    Pull ``location.id`` out of a preferred-charge-times body, if present.

    Parameters
    ----------
    body : Mapping[str, object]
        The request body.

    Returns
    -------
    str | None
        The location identifier, or ``None`` when absent.
    """
    location = body.get('location')
    if isinstance(location, Mapping):
        # Narrowing ``object`` to a bare ``Mapping`` leaves the key/value types as ``Never``; the
        # cast restores them so the keyed lookup type-checks.
        loc_id = cast('Mapping[str, object]', location).get('id')
        if isinstance(loc_id, str):
            return loc_id
    return None


def _print_mapping(title: str, data: Mapping[str, object] | None) -> None:
    """
    Render a flat mapping as a two-column Rich table, or a notice when empty.

    Parameters
    ----------
    title : str
        Table title.
    data : Mapping[str, object] | None
        The mapping to render.
    """
    if not data:
        click.secho('No data returned.', fg='yellow')
        return
    table = Table(title=title)
    table.add_column('Field')
    table.add_column('Value')
    for key in sorted(data):
        table.add_row(str(key), str(data[key]))
    console.print(table)


@click.group()
def charge() -> None:
    """EV charging control and status."""


@charge.command('start')
@debug_option
@vin_argument
@force_option
@with_client
async def charge_start(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       force: bool) -> None:
    """Start a charge session."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.start_global_charge(vin), 'startGlobalChargeCommand')


@charge.command('cancel')
@debug_option
@vin_argument
@force_option
@with_client
async def charge_cancel(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        force: bool) -> None:
    """Cancel an active charge session."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.cancel_global_charge(vin), 'cancelGlobalChargeCommand')


@charge.command('pause')
@debug_option
@vin_argument
@force_option
@with_client
async def charge_pause(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       force: bool) -> None:
    """Pause an active charge session."""
    await assert_ready_or_abort(client, vin, force=force)
    ack(await client.pause_global_charge(vin), 'pauseGlobalChargeCommand')


@charge.command('set')
@debug_option
@vin_argument
@click.argument('key', type=click.Choice(_SETTING_KEYS))
@click.argument('value')
@with_client
async def charge_set(client: AsyncFordPassClient, _ctx: click.Context, vin: str, key: str,
                     value: str) -> None:
    """Update a single charge setting (KEY VALUE)."""
    settings: dict[str, str | int] = {key: _coerce_setting(key, value)}
    ack(await client.update_charge_settings(vin, settings=settings), 'updateChargeSettingsCommand')


@charge.command('target')
@debug_option
@vin_argument
@click.option('--location-id',
              default=None,
              help='Charge-location id. Defaults to `location.id` from --data.')
@click.option('--data',
              'data_',
              required=True,
              help="Preferred-charge-times JSON body ('-' reads standard input).")
@json_option
@with_client
async def charge_target(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        location_id: str | None, data_: str, as_json: bool) -> None:
    """Set the preferred-charge-times profile for a location."""  # ruff:ignore[docstring-missing-exception]
    body = _load_json_body(data_)
    resolved = location_id or _extract_location_id(body)
    if not resolved:
        msg = 'No location id: pass --location-id or include `location.id` in --data.'
        raise click.UsageError(msg)
    resp = await client.set_preferred_charge_times(vin, location_id=resolved, body=body)
    if should_emit_json(as_json):
        dump_json(resp)
        return
    click.secho('Charge target updated.', fg='green')


@charge.command('times')
@debug_option
@vin_argument
@json_option
@with_client
async def charge_times(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       as_json: bool) -> None:
    """Show the preferred-charge-times profile."""
    data = await client.get_preferred_charge_times(vin)
    if should_emit_json(as_json):
        dump_json(data)
        return
    _print_mapping('Preferred Charge Times', data)


@charge.command('status')
@debug_option
@vin_argument
@json_option
@with_client
async def charge_status(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                        as_json: bool) -> None:
    """Show the live energy-transfer status."""
    data = await client.get_energy_transfer_status(vin)
    if should_emit_json(as_json):
        dump_json(data)
        return
    _print_mapping('Energy Transfer Status', data)


@charge.command('logs')
@debug_option
@vin_argument
@click.option('--max-records',
              type=click.IntRange(min=1),
              default=20,
              show_default=True,
              help='Maximum number of log records to fetch.')
@json_option
@with_client
async def charge_logs(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                      max_records: int, as_json: bool) -> None:
    """Show recent energy-transfer logs."""
    data = await client.get_energy_transfer_logs(vin, max_records=max_records)
    if should_emit_json(as_json):
        dump_json(data)
        return
    logs = (data.get('energyTransferLogs') if isinstance(data, Mapping) else None) or []
    if not logs:
        click.secho('No energy-transfer logs found.', fg='yellow')
        return
    table = Table(title='Energy Transfer Logs')
    table.add_column('#')
    table.add_column('Record')
    for index, record in enumerate(logs, start=1):
        table.add_row(str(index), str(record))
    console.print(table)
