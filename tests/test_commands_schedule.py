"""Tests for fordpass.commands.schedule."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from fordpass.main import ford

if TYPE_CHECKING:
    from click.testing import CliRunner


_VIN = '1FAHP00000A000000'


def test_schedule_list_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': [{
                'startScheduleId': '42',
                'name': 'Weekday',
                'startTime': '07:30',
                'status': '1',
                'sun': '0',
                'mon': '1',
                'tue': '1',
                'wed': '1',
                'thu': '1',
                'fri': '1',
                'sat': '0',
            }, {
                'scheduleId': '43',
                'startTime': '08:00',
                'status': '0',
                'sat': '1'
            }]
        }
    }
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0
    assert 'Weekday' in result.output


def test_schedule_list_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': []
        }
    }
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0
    assert 'No remote-start schedules' in result.output


def test_schedule_list_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': []
        }
    }
    result = runner.invoke(ford, ('schedule', 'list', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"startSchedule"' in result.output


def test_schedule_list_legacy_envelope(runner: CliRunner,
                                          mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'schedules': [{
            'scheduleId': '7'
        }]
    }
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0


def test_schedule_list_bare_list(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = [{
        'scheduleId': '7'
    }]
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0


def test_schedule_list_startschedule_as_list(runner: CliRunner,
                                                mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': [{
            'scheduleId': '9'
        }]
    }
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0


def test_schedule_list_unknown_shape(runner: CliRunner,
                                        mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = 'unexpected'
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0
    assert 'No remote-start schedules' in result.output


def test_schedule_list_values_not_list(runner: CliRunner,
                                          mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': 'not a list'
        }
    }
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0


def test_schedule_list_empty_mapping(runner: CliRunner,
                                        mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {}
    result = runner.invoke(ford, ('schedule', 'list', _VIN))
    assert result.exit_code == 0
    assert 'No remote-start schedules' in result.output


def test_schedule_enable_non_string_field(runner: CliRunner,
                                             mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': [{
                'startScheduleId': '42',
                'startTime': 730,
                'requestStartDate': 20260530,
                'timeZone': 'oops',
                'mon': 'not a number',
            }]
        }
    }
    mock_command_client.toggle_remote_start_schedule.return_value = None
    result = runner.invoke(ford, ('schedule', 'enable', '42', _VIN))
    assert result.exit_code == 0


def test_schedule_add(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.add_remote_start_schedule.return_value = None
    result = runner.invoke(ford, ('schedule', 'add', _VIN, '--start', '2026-05-30T07:30',
                                   '--days', 'mon,tue', '--tz', 'America/New_York'))
    assert result.exit_code == 0
    assert 'Schedule added' in result.output


def test_schedule_add_with_numeric_tz(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.add_remote_start_schedule.return_value = None
    result = runner.invoke(ford, ('schedule', 'add', _VIN, '--start', '2026-05-30T07:30',
                                   '--days', 'mwf', '--tz', '85'))
    assert result.exit_code == 0


def test_schedule_delete(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.delete_remote_start_schedule.return_value = None
    result = runner.invoke(ford, ('schedule', 'delete', '42', '--vin', _VIN))
    assert result.exit_code == 0
    assert 'Schedule 42 deleted' in result.output


def test_schedule_enable(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': [{
                'startScheduleId': '42',
                'requestStartDate': '2026-05-30T07:30',
                'startTime': '07:30',
                'timeZone': '85',
                'mon': '1'
            }]
        }
    }
    mock_command_client.toggle_remote_start_schedule.return_value = None
    result = runner.invoke(ford, ('schedule', 'enable', '42', _VIN))
    assert result.exit_code == 0
    assert 'Schedule 42 enabled' in result.output


def test_schedule_disable(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': [{
                'startScheduleId': '42',
                'requestDateTime': '2026-05-30T07:30',
                'startTime': '07:30',
                'timeZone': 85,
                'mon': 1,
                'tue': True,
                'wed': '0',
            }]
        }
    }
    mock_command_client.toggle_remote_start_schedule.return_value = None
    result = runner.invoke(ford, ('schedule', 'disable', '42', _VIN))
    assert result.exit_code == 0


def test_schedule_enable_not_found(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_remote_start_schedules.return_value = {
        'startSchedule': {
            '$values': []
        }
    }
    result = runner.invoke(ford, ('schedule', 'enable', '42', _VIN))
    assert result.exit_code != 0
    assert 'not found' in result.output
