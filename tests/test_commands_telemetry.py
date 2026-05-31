"""Tests for fordpass.commands.telemetry."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from fordpass.main import ford

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture


_VIN = '1FAHP00000A000000'


def test_telemetry_fuel_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_fuel_level.return_value = (75.0, 400.0)
    result = runner.invoke(ford, ('telemetry', 'fuel', _VIN))
    assert result.exit_code == 0
    assert '75' in result.output


def test_telemetry_fuel_unknown(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_fuel_level.return_value = (None, None)
    result = runner.invoke(ford, ('telemetry', 'fuel', _VIN))
    assert result.exit_code == 0
    assert 'unknown' in result.output


def test_telemetry_fuel_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_fuel_level.return_value = (75.0, 400.0)
    result = runner.invoke(ford, ('telemetry', 'fuel', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"level_pct"' in result.output


def test_telemetry_odometer_pretty_mi(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = 20000.0
    result = runner.invoke(ford, ('telemetry', 'odometer', _VIN, '--unit', 'mi'))
    assert result.exit_code == 0
    assert 'mi' in result.output


def test_telemetry_odometer_pretty_km(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = 20000.0
    result = runner.invoke(ford, ('telemetry', 'odometer', _VIN, '--unit', 'km'))
    assert result.exit_code == 0
    assert 'km' in result.output


def test_telemetry_odometer_unknown(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = None
    result = runner.invoke(ford, ('telemetry', 'odometer', _VIN))
    assert result.exit_code == 0
    assert 'unknown' in result.output


def test_telemetry_odometer_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = 20000.0
    result = runner.invoke(ford, ('telemetry', 'odometer', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"value"' in result.output


def test_telemetry_odometer_json_unknown(runner: CliRunner,
                                          mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = None
    result = runner.invoke(ford, ('telemetry', 'odometer', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"value": null' in result.output


def test_telemetry_oil_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_oil_life.return_value = 80.0
    result = runner.invoke(ford, ('telemetry', 'oil', _VIN))
    assert result.exit_code == 0
    assert '80' in result.output


def test_telemetry_oil_unknown(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_oil_life.return_value = None
    result = runner.invoke(ford, ('telemetry', 'oil', _VIN))
    assert result.exit_code == 0
    assert 'unknown' in result.output


def test_telemetry_oil_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_oil_life.return_value = 80.0
    result = runner.invoke(ford, ('telemetry', 'oil', _VIN, '--json'))
    assert result.exit_code == 0


def test_telemetry_tires_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_tire_pressure.return_value = [
        {'vehicleWheel': 'FRONT_LEFT', 'value': 220.5, 'wheelPlacardFront': 220.0},
        {'vehicleWheel': 'REAR_RIGHT', 'value': 100.0, 'wheelPlacardRear': 220.0},
        {'vehicleWheel': 'FRONT_RIGHT', 'value': 50.0, 'wheelPlacardFront': 220.0},
        {'vehicleWheel': 'REAR_LEFT', 'value': None, 'wheelPlacardRear': None},
        {'vehicleWheel': 'UNKNOWN', 'value': 220.0, 'wheelPlacardRear': 220.0},
    ]
    result = runner.invoke(ford, ('telemetry', 'tires', _VIN))
    assert result.exit_code == 0
    assert 'OK' in result.output


def test_telemetry_tires_psi(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_tire_pressure.return_value = [
        {'vehicleWheel': 'FRONT_LEFT', 'value': 220.0, 'wheelPlacardFront': 220.0},
    ]
    result = runner.invoke(ford, ('telemetry', 'tires', _VIN, '--unit', 'mi'))
    assert result.exit_code == 0
    assert 'PSI' in result.output


def test_telemetry_tires_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_tire_pressure.return_value = []
    result = runner.invoke(ford, ('telemetry', 'tires', _VIN))
    assert result.exit_code == 0
    assert 'No tire pressure' in result.output


def test_telemetry_tires_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_tire_pressure.return_value = []
    result = runner.invoke(ford, ('telemetry', 'tires', _VIN, '--json'))
    assert result.exit_code == 0


def test_telemetry_all_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'updateTime': '2026-05-30T00:00:00Z',
        'metrics': {
            'odometer': {'value': 20000.0, 'updateTime': '2026-05-30T00:00:00Z'},
            'fuelLevel': {'value': 75.0},
            'engineCoolantTemp': {'value': 90.0},
            'ambientTemp': {'value': None},
            'speed': {'value': 60.0},
            'gearLeverPosition': {'value': 'PARK'},
            'position': {
                'value': {'location': {'lat': 1.0, 'lon': 2.0}},
                'updateTime': '2026-05-30T00:00:00Z'
            },
            'heading': {'value': 90.0},
            'compassDirection': {'value': 'NORTH'},
            'acceleration': {'value': {'x': 0.1, 'y': 0.0, 'z': 9.8}},
            'tirePressure': [{
                'vehicleWheel': 'FRONT_LEFT', 'value': 220.0,
                'wheelPlacardFront': 220.0,
            }],
            'tirePressureStatus': [{'vehicleWheel': 'FRONT_LEFT', 'value': 'NORMAL_OPERATION'}],
            'tirePressureSystemStatus': [{'value': 'NORMAL'}],
            'doorStatus': [
                {'vehicleDoor': 'FRONT_LEFT', 'value': 'CLOSED'},
                {'vehicleDoor': 'FRONT_RIGHT', 'value': 'OPEN'},
            ],
            'doorLockStatus': [
                {'vehicleDoor': 'FRONT_LEFT', 'value': 'LOCKED'},
                {'vehicleDoor': 'FRONT_RIGHT', 'value': 'UNLOCKED'},
            ],
            'seatBeltStatus': [{'vehicleOccupantRole': 'DRIVER', 'value': 'BUCKLED'}],
            'displaySystemOfMeasure': {'value': 'IMPERIAL'},
            'batteryStateOfCharge': {'value': 92.0},
            'batteryVoltage': {'value': 12.6},
            'batteryLoadStatus': {'value': 'OK'},
            'panicAlarmStatus': {'value': True},
            'indicators': {
                'value': {
                    'lowFuelWarning': {'value': False},
                    'oilLow': {'error': {'errorName': 'X', 'errorSource': 'Y'}},
                    'engineOilLow': 'not a mapping',
                }
            },
            'configurations': {
                'value': {
                    'someConfig': {'value': 'SETTING_A', 'updateTime': '2026-05-30T00:00:00Z'},
                    'errorConfig': {'error': {'errorName': 'E', 'errorSource': 'src'}},
                    'directScalar': 'just a string',
                    'directList': [1, 2],
                    'nestedValue': {'value': {'inner': 'X'}},
                    'listValue': {'value': [1, 2, 3]},
                }
            },
            'extraUnknown': {'value': 42},
            'doorClosedList': [{'vehicleDoor': 'FRONT_LEFT', 'value': 'CLOSED'}],
            'doorLockedList': [{'vehicleDoor': 'FRONT_LEFT', 'value': 'LOCKED'}],
        }
    }
    result = runner.invoke(ford, ('telemetry', 'all', _VIN))
    assert result.exit_code == 0


def test_telemetry_all_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {}
    result = runner.invoke(ford, ('telemetry', 'all', _VIN))
    assert result.exit_code == 0
    assert 'No telemetry' in result.output


def test_telemetry_all_with_metrics_filter(runner: CliRunner,
                                              mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'metrics': {'odometer': {'value': 100.0}}
    }
    result = runner.invoke(ford, ('telemetry', 'all', _VIN, '-m', 'odometer'))
    assert result.exit_code == 0


def test_telemetry_all_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {'metrics': {}}
    result = runner.invoke(ford, ('telemetry', 'all', _VIN, '--json'))
    assert result.exit_code == 0


def test_telemetry_position_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_position.return_value = {
        'lat': 40.7,
        'lon': -74.0,
        'alt': 10.0,
        'heading': 90.0,
        'compass': 'NORTH',
        'update_time': '2026-05-30T00:00:00Z',
    }
    result = runner.invoke(ford, ('telemetry', 'position', _VIN))
    assert result.exit_code == 0
    assert '40' in result.output


def test_telemetry_position_minimal(runner: CliRunner,
                                      mock_command_client: MagicMock) -> None:
    mock_command_client.get_position.return_value = {'lat': 1.0, 'lon': 2.0}
    result = runner.invoke(ford, ('telemetry', 'position', _VIN))
    assert result.exit_code == 0


def test_telemetry_position_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_position.return_value = None
    result = runner.invoke(ford, ('telemetry', 'position', _VIN))
    assert result.exit_code == 0
    assert 'No position' in result.output


def test_telemetry_position_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_position.return_value = {'lat': 1.0, 'lon': 2.0}
    result = runner.invoke(ford, ('telemetry', 'position', _VIN, '--json'))
    assert result.exit_code == 0


def test_telemetry_position_maps_uri(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_position.return_value = {'lat': 40.7, 'lon': -74.0}
    result = runner.invoke(ford, ('telemetry', 'position', _VIN, '--maps-uri'))
    assert result.exit_code == 0
    assert 'google.com/maps' in result.output


def test_telemetry_position_maps_uri_no_position(runner: CliRunner,
                                                   mock_command_client: MagicMock) -> None:
    mock_command_client.get_position.return_value = None
    result = runner.invoke(ford, ('telemetry', 'position', _VIN, '--maps-uri'))
    assert result.exit_code != 0
    assert 'No position' in result.output


def test_telemetry_position_open_maps(runner: CliRunner, mocker: MockerFixture,
                                        mock_command_client: MagicMock) -> None:
    mock_command_client.get_position.return_value = {'lat': 1.0, 'lon': 2.0}
    opener = mocker.patch('fordpass.commands.telemetry.webbrowser.open')
    result = runner.invoke(ford, ('telemetry', 'position', _VIN, '--open-maps'))
    assert result.exit_code == 0
    opener.assert_called_once()
