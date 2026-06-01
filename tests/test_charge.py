"""Tests for EV charging request builders and CLI commands."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
import json

from fordpass.main import fordpass
import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner
    from fordpass.client import AsyncFordPassClient
    from fordpass.sansio import FordPassClient

_VIN = '1FAHP00000A000000'


@pytest.mark.parametrize(('method_name', 'expected_type'),
                         [('start_global_charge', 'startGlobalChargeCommand'),
                          ('cancel_global_charge', 'cancelGlobalChargeCommand'),
                          ('pause_global_charge', 'pauseGlobalChargeCommand')])
def test_global_charge_commands_omit_properties(core_client: FordPassClient, method_name: str,
                                                expected_type: str) -> None:
    req = getattr(core_client, method_name)(_VIN)
    assert req['method'] == 'POST'
    assert '/v1beta/command/' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['type'] == expected_type
    assert body['version'] == '1.0.1'
    assert body['wakeUp'] is True
    assert 'properties' not in body


def test_update_charge_settings_pass_through(core_client: FordPassClient) -> None:
    req = core_client.update_charge_settings(_VIN, settings={'chargeMode': 'CHARGE_NOW'})
    assert req['method'] == 'POST'
    body = json.loads(req['data'] or '{}')
    assert body['type'] == 'updateChargeSettingsCommand'
    assert body['version'] == '1.0.1'
    assert body['properties']['chargeSettings'] == {'chargeMode': 'CHARGE_NOW'}


def test_update_charge_settings_soc_rule_rounds_and_syncs(core_client: FordPassClient) -> None:
    req = core_client.update_charge_settings(_VIN, settings={'globalTargetSoc': 55})
    charge_settings = json.loads(req['data'] or '{}')['properties']['chargeSettings']
    assert charge_settings == {
        'globalDCTargetSoc': 50,
        'globalReserveSoc': 50,
        'globalTargetSoc': 50
    }


def test_update_charge_settings_soc_at_floor_untouched(core_client: FordPassClient) -> None:
    req = core_client.update_charge_settings(_VIN, settings={'globalTargetSoc': 90})
    charge_settings = json.loads(req['data'] or '{}')['properties']['chargeSettings']
    assert charge_settings == {'globalTargetSoc': 90}


def test_get_preferred_charge_times(core_client: FordPassClient) -> None:
    req = core_client.get_preferred_charge_times(_VIN)
    assert req['method'] == 'GET'
    assert '/api/electrification/experiences/v2/vehicles/preferred-charge-times' in req['url']
    assert req['headers']['vin'] == _VIN


def test_set_preferred_charge_times(core_client: FordPassClient) -> None:
    req = core_client.set_preferred_charge_times(_VIN, location_id='LOC1', body={'a': 1})
    assert req['method'] == 'POST'
    assert '/vehicles/preferred-charge-times/locations/LOC1' in req['url']
    assert req['headers']['vin'] == _VIN
    assert json.loads(req['data'] or '{}') == {'a': 1}


def test_get_energy_transfer_status(core_client: FordPassClient) -> None:
    req = core_client.get_energy_transfer_status(_VIN)
    assert req['method'] == 'GET'
    assert '/devices/energy-transfer-status' in req['url']
    assert req['headers']['deviceId'] == _VIN


def test_get_energy_transfer_logs_default_max(core_client: FordPassClient) -> None:
    req = core_client.get_energy_transfer_logs(_VIN)
    assert req['method'] == 'GET'
    assert 'maxRecords=20' in req['url']
    assert req['headers']['deviceId'] == _VIN


def test_get_energy_transfer_logs_custom_max(core_client: FordPassClient) -> None:
    req = core_client.get_energy_transfer_logs(_VIN, max_records=5)
    assert 'maxRecords=5' in req['url']


@pytest.mark.parametrize(('subcommand', 'client_method'), [('start', 'start_global_charge'),
                                                           ('cancel', 'cancel_global_charge'),
                                                           ('pause', 'pause_global_charge')])
def test_charge_force_commands(runner: CliRunner, mock_command_client: MagicMock, subcommand: str,
                               client_method: str) -> None:
    response = MagicMock()
    response.status_code = 200
    getattr(mock_command_client, client_method).return_value = response
    result = runner.invoke(fordpass, ('charge', subcommand, _VIN, '--force'))
    assert result.exit_code == 0
    getattr(mock_command_client, client_method).assert_called_once()


def test_charge_set_int_key(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.update_charge_settings.return_value = response
    result = runner.invoke(fordpass, ('charge', 'set', _VIN, 'globalTargetSoc', '70'))
    assert result.exit_code == 0
    _, kwargs = mock_command_client.update_charge_settings.call_args
    assert kwargs['settings'] == {'globalTargetSoc': 70}


def test_charge_set_string_key(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.update_charge_settings.return_value = response
    result = runner.invoke(fordpass, ('charge', 'set', _VIN, 'chargeMode', 'CHARGE_NOW'))
    assert result.exit_code == 0
    _, kwargs = mock_command_client.update_charge_settings.call_args
    assert kwargs['settings'] == {'chargeMode': 'CHARGE_NOW'}


def test_charge_set_invalid_mode(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass, ('charge', 'set', _VIN, 'chargeMode', 'BOGUS'))
    assert result.exit_code != 0


def test_charge_set_non_integer(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass, ('charge', 'set', _VIN, 'globalTargetSoc', 'abc'))
    assert result.exit_code != 0


def test_charge_set_unknown_key(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass, ('charge', 'set', _VIN, 'bogusKey', '1'))
    assert result.exit_code != 0


def test_charge_times_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_charge_times.return_value = {'foo': 'bar'}
    result = runner.invoke(fordpass, ('charge', 'times', _VIN))
    assert result.exit_code == 0
    assert 'foo' in result.output


def test_charge_times_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_charge_times.return_value = {'foo': 'bar'}
    result = runner.invoke(fordpass, ('charge', 'times', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"foo"' in result.output


def test_charge_status_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_energy_transfer_status.return_value = None
    result = runner.invoke(fordpass, ('charge', 'status', _VIN))
    assert result.exit_code == 0
    assert 'No data' in result.output


def test_charge_logs_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_energy_transfer_logs.return_value = {'energyTransferLogs': [{'id': 1}]}
    result = runner.invoke(fordpass, ('charge', 'logs', _VIN, '--max-records', '5'))
    assert result.exit_code == 0


def test_charge_logs_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_energy_transfer_logs.return_value = {'energyTransferLogs': []}
    result = runner.invoke(fordpass, ('charge', 'logs', _VIN))
    assert result.exit_code == 0
    assert 'No energy-transfer logs' in result.output


def test_charge_logs_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_energy_transfer_logs.return_value = {'energyTransferLogs': []}
    result = runner.invoke(fordpass, ('charge', 'logs', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"energyTransferLogs"' in result.output


def test_charge_target_with_location_id(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_preferred_charge_times.return_value = {'ok': True}
    result = runner.invoke(fordpass,
                           ('charge', 'target', _VIN, '--location-id', 'L1', '--data', '{"x": 1}'))
    assert result.exit_code == 0
    _, kwargs = mock_command_client.set_preferred_charge_times.call_args
    assert kwargs['location_id'] == 'L1'
    assert kwargs['body'] == {'x': 1}


def test_charge_target_location_from_body(runner: CliRunner,
                                          mock_command_client: MagicMock) -> None:
    mock_command_client.set_preferred_charge_times.return_value = None
    result = runner.invoke(fordpass,
                           ('charge', 'target', _VIN, '--data', '{"location": {"id": "L9"}}'))
    assert result.exit_code == 0
    _, kwargs = mock_command_client.set_preferred_charge_times.call_args
    assert kwargs['location_id'] == 'L9'


def test_charge_target_missing_location(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass, ('charge', 'target', _VIN, '--data', '{"x": 1}'))
    assert result.exit_code != 0


def test_charge_target_bad_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass,
                           ('charge', 'target', _VIN, '--location-id', 'L1', '--data', 'not json'))
    assert result.exit_code != 0


def test_charge_target_non_object_data(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass, ('charge', 'target', _VIN, '--data', '[]'))
    assert result.exit_code != 0


def test_charge_target_location_id_not_string(runner: CliRunner,
                                              mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass,
                           ('charge', 'target', _VIN, '--data', '{"location": {"id": 123}}'))
    assert result.exit_code != 0


def test_charge_target_json_output(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_preferred_charge_times.return_value = {'ok': True}
    result = runner.invoke(
        fordpass, ('charge', 'target', _VIN, '--location-id', 'L1', '--data', '{"x": 1}', '--json'))
    assert result.exit_code == 0
    assert '"ok"' in result.output


def test_charge_status_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_energy_transfer_status.return_value = {'foo': 'bar'}
    result = runner.invoke(fordpass, ('charge', 'status', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"foo"' in result.output


@pytest.mark.parametrize('method_name',
                         ['start_global_charge', 'cancel_global_charge', 'pause_global_charge'])
async def test_charge_command_wrappers(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                       method_name: str) -> None:
    await getattr(async_client, method_name)(_VIN)
    fake_session.request.assert_awaited_once()


async def test_update_charge_settings_wrapper(async_client: AsyncFordPassClient,
                                              fake_session: MagicMock) -> None:
    await async_client.update_charge_settings(_VIN, settings={'chargeMode': 'CHARGE_NOW'})
    fake_session.request.assert_awaited_once()


async def test_get_preferred_charge_times_wrapper(async_client: AsyncFordPassClient,
                                                  fake_session: MagicMock) -> None:
    result = await async_client.get_preferred_charge_times(_VIN)
    assert result == {'ok': True}
    fake_session.request.assert_awaited_once()


async def test_set_preferred_charge_times_wrapper(async_client: AsyncFordPassClient,
                                                  fake_session: MagicMock) -> None:
    result = await async_client.set_preferred_charge_times(_VIN, location_id='L1', body={'x': 1})
    assert result == {'ok': True}
    fake_session.request.assert_awaited_once()


async def test_get_energy_transfer_status_wrapper(async_client: AsyncFordPassClient,
                                                  fake_session: MagicMock) -> None:
    result = await async_client.get_energy_transfer_status(_VIN)
    assert result == {'ok': True}
    fake_session.request.assert_awaited_once()


async def test_get_energy_transfer_logs_wrapper(async_client: AsyncFordPassClient,
                                                fake_session: MagicMock,
                                                fake_response_factory: Any) -> None:
    fake_session.request.return_value = fake_response_factory(json_body={'energyTransferLogs': []})
    result = await async_client.get_energy_transfer_logs(_VIN, max_records=5)
    assert result['energyTransferLogs'] == []
    fake_session.request.assert_awaited_once()
