"""Tests for Ford MPS Guard Mode builders, client wrappers, and CLI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.main import fordpass
import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from click.testing import CliRunner
    from fordpass.client import AsyncFordPassClient
    from fordpass.sansio import FordPassClient

_VIN = '1FAHP00000A000000'


@pytest.mark.parametrize(('method', 'verb'), [('get_guard_mode', 'GET'), ('set_guard_mode', 'PUT'),
                                              ('delete_guard_mode', 'DELETE')])
def test_guard_mode_builders(core_client: FordPassClient, method: str, verb: str) -> None:
    req = getattr(core_client, method)(_VIN)
    assert req['method'] == verb
    assert req['url'] == 'https://stub-mps.example/api/gmfi/v1/session'
    assert req['data'] is None
    # ``X-Vin`` must be proper-case (distinct from the lowercase ``vin`` electrification header).
    assert req['headers']['X-Vin'] == _VIN
    assert 'vin' not in req['headers']
    assert req['headers']['auth-token'] == 'STUB_CAT'


@pytest.mark.parametrize('method_name', ['get_guard_mode', 'set_guard_mode', 'delete_guard_mode'])
async def test_client_guard_mode(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                 method_name: str) -> None:
    fake_session.request.return_value.json.return_value = {
        'returnCode': 200,
        'returnMessage': 'The request was Successful.'
    }
    result = await getattr(async_client, method_name)(_VIN)
    assert result['returnCode'] == 200
    fake_session.request.assert_awaited_once()


@pytest.mark.parametrize('subcommand', ['status', 'enable', 'disable'])
def test_guard_cli_pretty(runner: CliRunner, mock_command_client: MagicMock,
                          subcommand: str) -> None:
    method = {
        'status': 'get_guard_mode',
        'enable': 'set_guard_mode',
        'disable': 'delete_guard_mode'
    }[subcommand]
    getattr(mock_command_client, method).return_value = {
        'returnCode': 200,
        'returnMessage': 'The request was Successful.'
    }
    result = runner.invoke(fordpass, ('guard', subcommand, _VIN))
    assert result.exit_code == 0
    assert 'Guard Mode' in result.output


def test_guard_cli_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_guard_mode.return_value = {'returnCode': 300}
    result = runner.invoke(fordpass, ('guard', 'status', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"returnCode"' in result.output


def test_guard_cli_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_guard_mode.return_value = {}
    result = runner.invoke(fordpass, ('guard', 'status', _VIN))
    assert result.exit_code == 0
    assert 'No Guard Mode data' in result.output
