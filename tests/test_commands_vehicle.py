"""Tests for fordpass.commands.vehicle."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fordpass.commands.utils import Readiness
from fordpass.main import fordpass

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from click.testing import CliRunner
    from pytest_mock import MockerFixture

_VIN = '1FAHP00000A000000'


def _ready_ok(**overrides: Any) -> Readiness:
    base: dict[str, Any] = {
        'battery_conditions': (),
        'life_cycle_mode': 'NORMAL',
        'load_status': 'OK',
        'ok': True,
        'raw': {
            'mode': 'NORMAL'
        },
        'reasons': (),
        'state_of_charge': 92.0,
        'voltage': 12.6
    }
    base.update(overrides)
    return Readiness(**base)


def test_vehicle_list_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = [{
        'vin': _VIN,
        'nickName': 'Lightning',
        'licensePlate': 'ABC-123',
        'color': 'Red',
        'profile': {
            'year': 2024,
            'model': 'F-150'
        }
    }]
    result = runner.invoke(fordpass, ('vehicle', 'list'))
    assert result.exit_code == 0
    assert 'Lightning' in result.output


def test_vehicle_list_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = []
    result = runner.invoke(fordpass, ('vehicle', 'list'))
    assert result.exit_code == 0
    assert 'garage is empty' in result.output


def test_vehicle_list_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = []
    result = runner.invoke(fordpass, ('vehicle', 'list', '--json'))
    assert result.exit_code == 0
    assert result.output.strip() == '[]'


def test_vehicle_show_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = [{
        'vin': _VIN,
        'nickName': 'Lightning',
        'licensePlate': 'ABC-123',
        'color': 'Red',
        'preferredDealer': 'P00001',
        'sourceOfPreferredDealer': 'Customer',
        'userAuthStatus': 'Authorized',
        'profile': {
            'make': 'Ford',
            'model': 'F-150',
            'year': 2024,
            'engineType': 'BEV',
            'transmissionIndicator': 'A',
            'recallCount': 0,
            'nonRecallCount': 2,
            'globalChargeSettings': 'On',
            'paakPairingType': 'PinCode'
        },
        'capabilities': {
            'remoteStart': 'On',
            'remoteLock': 'On',
            'paak': 'NoDisplay',
            'showEVBatteryLevel': True
        }
    }]
    result = runner.invoke(fordpass, ('vehicle', 'show', _VIN))
    assert result.exit_code == 0
    assert 'Lightning' in result.output


def test_vehicle_show_ice_filters_ev_only(runner: CliRunner,
                                          mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = [{
        'vin': _VIN,
        'profile': {
            'engineType': 'ICE',
            'globalChargeSettings': 'On'
        },
        'capabilities': {
            'remoteStart': 'On',
            'departureTimes': 'On',
            'showEVBatteryLevel': True
        }
    }]
    result = runner.invoke(fordpass, ('vehicle', 'show', _VIN))
    assert result.exit_code == 0


def test_vehicle_show_no_capabilities(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = [{
        'vin': _VIN,
        'profile': {
            'engineType': 'ICE'
        },
        'capabilities': {
            'remoteStart': 'NoDisplay'
        }
    }]
    result = runner.invoke(fordpass, ('vehicle', 'show', _VIN))
    assert result.exit_code == 0
    assert 'No capabilities' in result.output


def test_vehicle_show_not_found(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = []
    result = runner.invoke(fordpass, ('vehicle', 'show', _VIN))
    assert result.exit_code != 0
    assert 'not found in garage' in result.output


def test_vehicle_show_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = [{'vin': _VIN, 'nickName': 'X'}]
    result = runner.invoke(fordpass, ('vehicle', 'show', _VIN, '--json'))
    assert result.exit_code == 0
    assert _VIN in result.output


def test_vehicle_ready_ok(runner: CliRunner, mocker: MockerFixture,
                          mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.vehicle.check_readiness',
                 new_callable=mocker.AsyncMock,
                 return_value=_ready_ok())
    result = runner.invoke(fordpass, ('vehicle', 'ready', _VIN))
    assert result.exit_code == 0
    assert 'Ready' in result.output


def test_vehicle_ready_blocked(runner: CliRunner, mocker: MockerFixture,
                               mock_command_client: MagicMock) -> None:
    blocked = _ready_ok(ok=False, reasons=('Deep sleep mode', 'Firmware updating'))
    mocker.patch('fordpass.commands.vehicle.check_readiness',
                 new_callable=mocker.AsyncMock,
                 return_value=blocked)
    result = runner.invoke(fordpass, ('vehicle', 'ready', _VIN))
    assert result.exit_code == 0
    assert 'Battery Saver' in result.output
    assert 'Deep sleep mode' in result.output


def test_vehicle_ready_minimal_fields(runner: CliRunner, mocker: MockerFixture,
                                      mock_command_client: MagicMock) -> None:
    minimal = _ready_ok(state_of_charge=None,
                        voltage=None,
                        load_status=None,
                        life_cycle_mode=None,
                        raw={})
    mocker.patch('fordpass.commands.vehicle.check_readiness',
                 new_callable=mocker.AsyncMock,
                 return_value=minimal)
    result = runner.invoke(fordpass, ('vehicle', 'ready', _VIN))
    assert result.exit_code == 0


def test_vehicle_ready_json(runner: CliRunner, mocker: MockerFixture,
                            mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.vehicle.check_readiness',
                 new_callable=mocker.AsyncMock,
                 return_value=_ready_ok())
    result = runner.invoke(fordpass, ('vehicle', 'ready', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"ok": true' in result.output


def test_vehicle_nickname(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.update_vehicle_details.return_value = None
    result = runner.invoke(fordpass, ('vehicle', 'nickname', '--vin', _VIN, 'Lightning'))
    assert result.exit_code == 0
    assert 'Lightning' in result.output


def test_vehicle_plate(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.update_vehicle_details.return_value = None
    result = runner.invoke(fordpass, ('vehicle', 'plate', '--vin', _VIN, 'ABC-123'))
    assert result.exit_code == 0
    assert 'ABC-123' in result.output


def test_vehicle_mileage(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.update_vehicle_details.return_value = None
    result = runner.invoke(fordpass, ('vehicle', 'mileage', '--vin', _VIN, '12345'))
    assert result.exit_code == 0
    assert '12345' in result.output


def test_vehicle_list_envelope_shape(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = {'vehicles': [{'vin': _VIN, 'nickName': 'X'}]}
    result = runner.invoke(fordpass, ('vehicle', 'list'))
    assert result.exit_code == 0


def test_vehicle_list_unknown_shape(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = {'unknown_envelope': []}
    result = runner.invoke(fordpass, ('vehicle', 'list'))
    assert result.exit_code == 0
    assert 'garage is empty' in result.output


def test_vehicle_list_non_list_non_mapping(runner: CliRunner,
                                           mock_command_client: MagicMock) -> None:
    mock_command_client.list_garage.return_value = None
    result = runner.invoke(fordpass, ('vehicle', 'list'))
    assert result.exit_code == 0
    assert 'garage is empty' in result.output
