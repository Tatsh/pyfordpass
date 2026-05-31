"""Tests for the simpler leaf commands (alerts, dealer, departure, ota, remote)."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from fordpass.main import fordpass
import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner

_VIN = '1FAHP00000A000000'


def test_alerts_current_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alerts.return_value = {
        'alerts': [{
            'alertIdentifier': 'E1',
            'urgency': 'H',
            'colorCode': 'R',
            'alertDescription': 'Boom',
            'eventTimeStamp': 'T'
        }]
    }
    result = runner.invoke(fordpass, ('alerts', 'current', _VIN))
    assert result.exit_code == 0


def test_alerts_current_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alerts.return_value = {'alerts': []}
    result = runner.invoke(fordpass, ('alerts', 'current', _VIN))
    assert result.exit_code == 0
    assert 'No active alerts' in result.output


def test_alerts_current_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alerts.return_value = {'alerts': []}
    result = runner.invoke(fordpass, ('alerts', 'current', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"alerts"' in result.output


def test_alerts_history_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alert_history.return_value = {
        'messages': [{
            'eventTime': 'T',
            'alertType': 'prognostics',
            'messageSubject': 'Foo',
            'messageBody': 'Bar'
        }]
    }
    result = runner.invoke(fordpass, ('alerts', 'history', _VIN))
    assert result.exit_code == 0


def test_alerts_history_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alert_history.return_value = {'messages': []}
    result = runner.invoke(fordpass, ('alerts', 'history', _VIN))
    assert result.exit_code == 0


def test_alerts_history_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alert_history.return_value = {'messages': []}
    result = runner.invoke(fordpass, ('alerts', 'history', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"messages"' in result.output


def test_alerts_washer_low_exits_one(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.is_washer_fluid_low.return_value = True
    result = runner.invoke(fordpass, ('alerts', 'washer', _VIN))
    assert result.exit_code == 1
    assert 'low' in result.output


def test_alerts_washer_ok(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.is_washer_fluid_low.return_value = False
    result = runner.invoke(fordpass, ('alerts', 'washer', _VIN))
    assert result.exit_code == 0
    assert 'ok' in result.output


def test_alerts_washer_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.is_washer_fluid_low.return_value = False
    result = runner.invoke(fordpass, ('alerts', 'washer', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"low": false' in result.output


def test_dealer_preferred_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_dealer.return_value = {
        'paCode': 'P00001',
        'dealerName': 'Test Dealer',
        'phone': '555-1212',
        'address': {
            'street': '1 Lane'
        },
        'hours': ['9-5']
    }
    result = runner.invoke(fordpass, ('dealer', 'preferred', _VIN))
    assert result.exit_code == 0
    assert 'Test Dealer' in result.output


def test_dealer_preferred_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_dealer.return_value = None
    result = runner.invoke(fordpass, ('dealer', 'preferred', _VIN))
    assert result.exit_code == 0
    assert 'No preferred dealer' in result.output


def test_dealer_preferred_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_dealer.return_value = {'paCode': 'P00001'}
    result = runner.invoke(fordpass, ('dealer', 'preferred', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"paCode"' in result.output


def test_departure_next_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_next_departure.return_value = {
        'scheduleId': 'sched-1',
        'departureTime': '07:30',
        'nestedConfig': {
            'k': 'v'
        },
        'days': ['MON']
    }
    result = runner.invoke(fordpass, ('departure', 'next', _VIN))
    assert result.exit_code == 0
    assert 'sched-1' in result.output


def test_departure_next_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_next_departure.return_value = None
    result = runner.invoke(fordpass, ('departure', 'next', _VIN))
    assert result.exit_code == 0
    assert 'No departure' in result.output


def test_departure_next_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_next_departure.return_value = {'scheduleId': 'sched-1'}
    result = runner.invoke(fordpass, ('departure', 'next', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"scheduleId"' in result.output


def test_ota_status_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {}
    result = runner.invoke(fordpass, ('ota', 'status', _VIN))
    assert result.exit_code == 0
    assert 'not reported' in result.output


def test_ota_status_from_configurations(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'metrics': {
            'configurations': {
                'value': {
                    'automaticSoftwareUpdateOptInSetting': {
                        'value': 'ON',
                        'updateTime': '2026-05-30T00:00:00Z'
                    },
                    'automaticSoftwareUpdateScheduleSetting': {
                        'value': {
                            'scheduleType': 'AUTOMATIC',
                            'scheduleExecutor': 'TCU',
                            'timeZone': '85',
                            'multipleWeeklySchedules': {
                                'dayOfWeekAndTime': [{
                                    'dayOfWeek': 'mon',
                                    'timeOfDay': '03:00'
                                }]
                            }
                        },
                        'updateTime': '2026-05-30T00:00:00Z'
                    }
                }
            }
        }
    }
    result = runner.invoke(fordpass, ('ota', 'status', _VIN))
    assert result.exit_code == 0
    assert 'Enabled' in result.output


def test_ota_status_disabled(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'metrics': {
            'configurations': {
                'value': {
                    'automaticSoftwareUpdateOptInSetting': {
                        'value': 'OFF'
                    }
                }
            }
        }
    }
    result = runner.invoke(fordpass, ('ota', 'status', _VIN))
    assert result.exit_code == 0
    assert 'Disabled' in result.output


def test_ota_status_from_event_fallback(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'events': {
            'automaticSoftwareUpdateUserSettingsEvent': {
                'value': {
                    'optIn': 'ON',
                    'schedule': {
                        'error': 'failed to parse'
                    }
                },
                'updateTime': '2026-05-30T00:00:00Z'
            }
        }
    }
    result = runner.invoke(fordpass, ('ota', 'status', _VIN))
    assert result.exit_code == 0


def test_ota_status_schedule_error(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'metrics': {
            'configurations': {
                'value': {
                    'automaticSoftwareUpdateOptInSetting': {
                        'value': 'ON'
                    },
                    'automaticSoftwareUpdateScheduleSetting': {
                        'error': 'unsupported'
                    }
                }
            }
        }
    }
    result = runner.invoke(fordpass, ('ota', 'status', _VIN))
    assert result.exit_code == 0
    assert 'unsupported' in result.output


def test_ota_status_unknown_optin(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'metrics': {
            'configurations': {
                'value': {
                    'automaticSoftwareUpdateOptInSetting': {
                        'value': 'WEIRD'
                    }
                }
            }
        }
    }
    result = runner.invoke(fordpass, ('ota', 'status', _VIN))
    assert result.exit_code == 0
    assert 'Unknown' in result.output


def test_ota_status_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {}
    result = runner.invoke(fordpass, ('ota', 'status', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"optIn"' in result.output


@pytest.mark.parametrize('subcommand', ['enable', 'disable', 'queue-refresh'])
def test_ota_simple_commands(runner: CliRunner, mock_command_client: MagicMock,
                             subcommand: str) -> None:
    response = MagicMock()
    response.status_code = 200
    mapping = {
        'enable': 'set_asu_enabled',
        'disable': 'set_asu_enabled',
        'queue-refresh': 'get_asu_settings'
    }
    getattr(mock_command_client, mapping[subcommand]).return_value = response
    result = runner.invoke(fordpass, ('ota', subcommand, _VIN))
    assert result.exit_code == 0


def test_ota_release_notes_present(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_release_notes.return_value = {'response': 'Release notes body.'}
    result = runner.invoke(fordpass, ('ota', 'release-notes', _VIN))
    assert result.exit_code == 0
    assert 'Release notes body' in result.output


def test_ota_release_notes_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_release_notes.return_value = None
    result = runner.invoke(fordpass, ('ota', 'release-notes', _VIN))
    assert result.exit_code == 0
    assert 'No MMOTA alert' in result.output


def test_ota_release_notes_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_release_notes.return_value = {'response': 'X'}
    result = runner.invoke(fordpass, ('ota', 'release-notes', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"response"' in result.output


@pytest.mark.parametrize(('subcommand', 'client_method'), [('start', 'remote_start'),
                                                           ('stop', 'cancel_remote_start'),
                                                           ('extend', 'extend_remote_start'),
                                                           ('lock', 'lock'), ('unlock', 'unlock')])
def test_remote_force_commands(runner: CliRunner, mock_command_client: MagicMock, subcommand: str,
                               client_method: str) -> None:
    response = MagicMock()
    response.status_code = 200
    getattr(mock_command_client, client_method).return_value = response
    result = runner.invoke(fordpass, ('remote', subcommand, _VIN, '--force'))
    assert result.exit_code == 0


def test_remote_status(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.status_refresh.return_value = response
    result = runner.invoke(fordpass, ('remote', 'status', _VIN))
    assert result.exit_code == 0


def test_remote_panic(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.panic_alarm.return_value = response
    result = runner.invoke(fordpass, ('remote', 'panic', _VIN, '--duration', '5'))
    assert result.exit_code == 0
