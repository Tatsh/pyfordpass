"""Tests for the simpler leaf commands (alerts, dealer, departure, ota, remote)."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from fordpass.main import ford
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
    result = runner.invoke(ford, ('alerts', 'current', _VIN))
    assert result.exit_code == 0


def test_alerts_current_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alerts.return_value = {'alerts': []}
    result = runner.invoke(ford, ('alerts', 'current', _VIN))
    assert result.exit_code == 0
    assert 'No active alerts' in result.output


def test_alerts_current_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alerts.return_value = {'alerts': []}
    result = runner.invoke(ford, ('alerts', 'current', _VIN, '--json'))
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
    result = runner.invoke(ford, ('alerts', 'history', _VIN))
    assert result.exit_code == 0


def test_alerts_history_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_alert_history.return_value = {'messages': []}
    result = runner.invoke(ford, ('alerts', 'history', _VIN))
    assert result.exit_code == 0


def test_alerts_washer_low_exits_one(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.is_washer_fluid_low.return_value = True
    result = runner.invoke(ford, ('alerts', 'washer', _VIN))
    assert result.exit_code == 1
    assert 'low' in result.output


def test_alerts_washer_ok(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.is_washer_fluid_low.return_value = False
    result = runner.invoke(ford, ('alerts', 'washer', _VIN))
    assert result.exit_code == 0
    assert 'ok' in result.output


def test_alerts_washer_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.is_washer_fluid_low.return_value = False
    result = runner.invoke(ford, ('alerts', 'washer', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"low": false' in result.output


def test_dealer_preferred_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_dealer.return_value = {
        'paCode': 'P00001',
        'dealerName': 'Test Dealer',
        'phone': '555-1212'
    }
    result = runner.invoke(ford, ('dealer', 'preferred', _VIN))
    assert result.exit_code == 0
    assert 'Test Dealer' in result.output


def test_dealer_preferred_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_dealer.return_value = None
    result = runner.invoke(ford, ('dealer', 'preferred', _VIN))
    assert result.exit_code == 0
    assert 'No preferred dealer' in result.output


def test_dealer_preferred_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_preferred_dealer.return_value = {'paCode': 'P00001'}
    result = runner.invoke(ford, ('dealer', 'preferred', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"paCode"' in result.output


def test_departure_next_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_next_departure.return_value = {
        'scheduleId': 'sched-1',
        'departureTime': '07:30'
    }
    result = runner.invoke(ford, ('departure', 'next', _VIN))
    assert result.exit_code == 0
    assert 'sched-1' in result.output


def test_departure_next_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_next_departure.return_value = None
    result = runner.invoke(ford, ('departure', 'next', _VIN))
    assert result.exit_code == 0
    assert 'No departure' in result.output


def test_departure_next_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_next_departure.return_value = {'scheduleId': 'sched-1'}
    result = runner.invoke(ford, ('departure', 'next', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"scheduleId"' in result.output


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
    result = runner.invoke(ford, ('ota', subcommand, _VIN))
    assert result.exit_code == 0


def test_ota_release_notes_present(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_release_notes.return_value = {'response': 'Release notes body.'}
    result = runner.invoke(ford, ('ota', 'release-notes', _VIN))
    assert result.exit_code == 0
    assert 'Release notes body' in result.output


def test_ota_release_notes_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_release_notes.return_value = None
    result = runner.invoke(ford, ('ota', 'release-notes', _VIN))
    assert result.exit_code == 0
    assert 'No MMOTA alert' in result.output


def test_ota_release_notes_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_release_notes.return_value = {'response': 'X'}
    result = runner.invoke(ford, ('ota', 'release-notes', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"response"' in result.output


@pytest.mark.parametrize(('subcommand', 'client_method'), [
    ('start', 'remote_start'),
    ('stop', 'cancel_remote_start'),
    ('extend', 'extend_remote_start'),
    ('lock', 'lock'),
    ('unlock', 'unlock'),
])
def test_remote_force_commands(runner: CliRunner, mock_command_client: MagicMock, subcommand: str,
                                client_method: str) -> None:
    response = MagicMock()
    response.status_code = 200
    getattr(mock_command_client, client_method).return_value = response
    result = runner.invoke(ford, ('remote', subcommand, _VIN, '--force'))
    assert result.exit_code == 0


def test_remote_status(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.status_refresh.return_value = response
    result = runner.invoke(ford, ('remote', 'status', _VIN))
    assert result.exit_code == 0


def test_remote_panic(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.panic_alarm.return_value = response
    result = runner.invoke(ford, ('remote', 'panic', _VIN, '--duration', '5'))
    assert result.exit_code == 0
