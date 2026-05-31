"""Tests for messages / profile / drivers / roadside command modules."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from fordpass.main import ford

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture


_VIN = '1FAHP00000A000000'


# ----- messages -----


def test_messages_list_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {
        'result': {
            'messages': [{
                'messageId': '101',
                'messageSubject': 'Hello',
                'createdDate': '2026-05-30T00:00:00Z',
                'isRead': False,
                'messageBody': 'Short body.',
            }, {
                'messageId': '102',
                'messageSubject': 'World',
                'createdDate': '2026-05-30T00:00:00Z',
                'isRead': True,
                'messageBody': 'Long body ' * 30,
            }]
        }
    }
    result = runner.invoke(ford, ('messages', 'list'))
    assert result.exit_code == 0
    assert '101' in result.output


def test_messages_list_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {'result': {'messages': []}}
    result = runner.invoke(ford, ('messages', 'list'))
    assert result.exit_code == 0
    assert 'inbox is empty' in result.output


def test_messages_list_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {'result': {'messages': []}}
    result = runner.invoke(ford, ('messages', 'list', '--json'))
    assert result.exit_code == 0
    assert '"result"' in result.output


def test_messages_show_present(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {
        'result': {
            'messages': [{
                'messageId': '42',
                'messageSubject': 'Hi',
                'createdDate': 'T',
                'isRead': True,
                'messageType': 'X',
                'contentType': 'Text',
                'relevantVin': _VIN,
                'priority': 1,
                'messageBody': 'Body',
            }]
        }
    }
    result = runner.invoke(ford, ('messages', 'show', '42'))
    assert result.exit_code == 0
    assert 'Hi' in result.output
    assert 'Body' in result.output


def test_messages_show_missing(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {'result': {'messages': []}}
    result = runner.invoke(ford, ('messages', 'show', '99'))
    assert result.exit_code == 1
    assert 'not found' in result.output


def test_messages_show_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {
        'result': {
            'messages': [{
                'messageId': '7'
            }]
        }
    }
    result = runner.invoke(ford, ('messages', 'show', '7', '--json'))
    assert result.exit_code == 0
    assert '"messageId"' in result.output


def test_messages_show_empty_body(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {
        'result': {
            'messages': [{
                'messageId': '5',
                'messageBody': ''
            }]
        }
    }
    result = runner.invoke(ford, ('messages', 'show', '5'))
    assert result.exit_code == 0
    assert 'no body' in result.output


def test_messages_delete(runner: CliRunner, mock_command_client: MagicMock,
                          mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.messages.validate_message_ids_exist', new_callable=mocker.AsyncMock)
    mock_command_client.delete_messages.return_value = None
    result = runner.invoke(ford, ('messages', 'delete', '1', '2'))
    assert result.exit_code == 0
    assert 'Deleted' in result.output


def test_messages_delete_single(runner: CliRunner, mock_command_client: MagicMock,
                                 mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.messages.validate_message_ids_exist', new_callable=mocker.AsyncMock)
    mock_command_client.delete_messages.return_value = None
    result = runner.invoke(ford, ('messages', 'delete', '1'))
    assert result.exit_code == 0
    assert '1 message' in result.output


def test_messages_mark_read(runner: CliRunner, mock_command_client: MagicMock,
                             mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.messages.validate_message_ids_exist', new_callable=mocker.AsyncMock)
    mock_command_client.mark_messages_read.return_value = None
    result = runner.invoke(ford, ('messages', 'mark-read', '3'))
    assert result.exit_code == 0
    assert 'Marked read' in result.output


def test_messages_delete_json(runner: CliRunner, mock_command_client: MagicMock,
                                mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.messages.validate_message_ids_exist', new_callable=mocker.AsyncMock)
    mock_command_client.delete_messages.return_value = {'status': 'ok'}
    result = runner.invoke(ford, ('messages', 'delete', '1', '--json'))
    assert result.exit_code == 0
    assert '"status"' in result.output


def test_messages_mark_read_json(runner: CliRunner, mock_command_client: MagicMock,
                                   mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.messages.validate_message_ids_exist', new_callable=mocker.AsyncMock)
    mock_command_client.mark_messages_read.return_value = {'status': 'ok'}
    result = runner.invoke(ford, ('messages', 'mark-read', '1', '--json'))
    assert result.exit_code == 0
    assert '"status"' in result.output


# ----- profile -----


def test_profile_show_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_profile.return_value = {
        'userGuid': 'GUID_X',
        'names': {
            'firstName': 'Alice'
        },
        'namesExtensions': [{
            'fieldName': 'suffix',
            'value': 'Jr'
        }, {
            'value': 'noFieldName'
        }],
    }
    result = runner.invoke(ford, ('profile', 'show'))
    assert result.exit_code == 0
    assert 'Alice' in result.output
    assert 'GUID_X' in result.output


def test_profile_show_with_groups_filter(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_profile.return_value = {'names': {'firstName': 'Alice'}}
    result = runner.invoke(ford, ('profile', 'show', '--groups', 'names'))
    assert result.exit_code == 0
    mock_command_client.get_profile.assert_awaited_once_with(profile_groups='names')


def test_profile_show_empty_response(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_profile.return_value = {}
    result = runner.invoke(ford, ('profile', 'show'))
    assert result.exit_code == 0
    assert 'No profile' in result.output


def test_profile_show_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_profile.return_value = {'names': {'firstName': 'A'}}
    result = runner.invoke(ford, ('profile', 'show', '--json'))
    assert result.exit_code == 0
    assert '"names"' in result.output


def test_profile_show_scalar_section(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_profile.return_value = {'simpleField': 'value'}
    result = runner.invoke(ford, ('profile', 'show'))
    assert result.exit_code == 0


def test_profile_update_happy_path(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.save_profile.return_value = response
    result = runner.invoke(ford,
                            ('profile', 'update', '--field', 'names.firstName=Alice'))
    assert result.exit_code == 0


def test_profile_update_bad_syntax(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(ford, ('profile', 'update', '--field', 'oops_no_dot=value'))
    assert result.exit_code != 0
    assert 'Bad --field syntax' in result.output


# ----- drivers -----


def test_drivers_list_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_drivers.return_value = {
        'authAndPendingUsers': [{
            'displayName': 'Alice',
            'userAuthStatus': 'Authorized',
            'inviteId': 'I1',
            'GUID': 'G1'
        }, {
            'displayName': 'Bob',
            'userAuthStatus': 'Pending'
        }]
    }
    result = runner.invoke(ford, ('drivers', 'list', _VIN))
    assert result.exit_code == 0
    assert 'Alice' in result.output


def test_drivers_list_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_drivers.return_value = {'authAndPendingUsers': []}
    result = runner.invoke(ford, ('drivers', 'list', _VIN))
    assert result.exit_code == 0
    assert 'No secondary drivers' in result.output


def test_drivers_list_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.list_drivers.return_value = {'authAndPendingUsers': []}
    result = runner.invoke(ford, ('drivers', 'list', _VIN, '--json'))
    assert result.exit_code == 0


def test_drivers_count_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_authorized_user_count.return_value = {'count': 3}
    result = runner.invoke(ford, ('drivers', 'count', _VIN))
    assert result.exit_code == 0
    assert '3' in result.output
    assert 'drivers' in result.output


def test_drivers_count_singular(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_authorized_user_count.return_value = {'count': 1}
    result = runner.invoke(ford, ('drivers', 'count', _VIN))
    assert result.exit_code == 0
    assert 'driver' in result.output


def test_drivers_count_unknown(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_authorized_user_count.return_value = {}
    result = runner.invoke(ford, ('drivers', 'count', _VIN))
    assert result.exit_code == 0
    assert 'unknown' in result.output


def test_drivers_count_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_authorized_user_count.return_value = {'count': 0}
    result = runner.invoke(ford, ('drivers', 'count', _VIN, '--json'))
    assert result.exit_code == 0


def test_drivers_invite_success(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.invite_driver.return_value = {}
    result = runner.invoke(ford,
                            ('drivers', 'invite', _VIN, '--email', 'x@example.com', '--name',
                             'Bob', '--vehicle-name', 'F-150'))
    assert result.exit_code == 0
    assert 'Invite sent' in result.output


def test_drivers_invite_failure(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.invite_driver.return_value = {
        'errorCode': 'E1',
        'errorMessage': 'Email already pending'
    }
    result = runner.invoke(ford,
                            ('drivers', 'invite', _VIN, '--email', 'x@example.com', '--name',
                             'Bob', '--vehicle-name', 'F-150'))
    assert result.exit_code != 0
    assert 'Email already pending' in result.output


# ----- roadside -----


def test_roadside_symptoms(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_symptoms.return_value = {
        'symptoms': [{
            'id': 1,
            'name': 'Flat tyre'
        }]
    }
    result = runner.invoke(ford, ('roadside', 'symptoms'))
    assert result.exit_code == 0
    assert 'Flat tyre' in result.output


def test_roadside_symptoms_bev(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_symptoms.return_value = {'symptoms': []}
    result = runner.invoke(ford, ('roadside', 'symptoms', '--bev'))
    assert result.exit_code == 0


def test_roadside_symptoms_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_symptoms.return_value = {'symptoms': []}
    result = runner.invoke(ford, ('roadside', 'symptoms'))
    assert result.exit_code == 0
    assert 'nothing' in result.output


def test_roadside_symptoms_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_symptoms.return_value = {'symptoms': []}
    result = runner.invoke(ford, ('roadside', 'symptoms', '--json'))
    assert result.exit_code == 0


def test_roadside_locations(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_location_types.return_value = {
        'locationTypes': [{
            'id': 'HOME',
            'name': 'Home'
        }]
    }
    result = runner.invoke(ford, ('roadside', 'locations'))
    assert result.exit_code == 0
    assert 'Home' in result.output


def test_roadside_locations_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_location_types.return_value = {'locationTypes': []}
    result = runner.invoke(ford, ('roadside', 'locations', '--json'))
    assert result.exit_code == 0


def test_roadside_active_present(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_active_event.return_value = {
        'eventId': 'EVT_X',
        'status': 'in-progress',
        'nested': {
            'skipped': True
        },
        'list': [1, 2]
    }
    result = runner.invoke(ford, ('roadside', 'active', _VIN))
    assert result.exit_code == 0
    assert 'EVT_X' in result.output


def test_roadside_active_none(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_active_event.return_value = None
    result = runner.invoke(ford, ('roadside', 'active', _VIN))
    assert result.exit_code == 0
    assert 'No active roadside' in result.output


def test_roadside_active_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_active_event.return_value = {}
    result = runner.invoke(ford, ('roadside', 'active', _VIN))
    assert result.exit_code == 0
    assert 'No active roadside' in result.output


def test_roadside_active_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_roadside_active_event.return_value = {'eventId': 'X'}
    result = runner.invoke(ford, ('roadside', 'active', _VIN, '--json'))
    assert result.exit_code == 0


def test_roadside_predraft(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.predraft_roadside_event.return_value = {'draftId': 'D1'}
    result = runner.invoke(ford, ('roadside', 'predraft', _VIN, '--name', 'Alice'))
    assert result.exit_code == 0
    assert 'pre-draft created' in result.output


def test_roadside_predraft_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.predraft_roadside_event.return_value = {'draftId': 'D1'}
    result = runner.invoke(ford,
                            ('roadside', 'predraft', _VIN, '--name', 'Alice', '--json'))
    assert result.exit_code == 0
    assert '"draftId"' in result.output
