"""Tests for the departure-schedule write side (builders, client, converter, CLI)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
import json

from fordpass.main import fordpass
from fordpass.utils import extract_departure_schedule_days
import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner
    from fordpass.client import AsyncFordPassClient
    from fordpass.sansio import FordPassClient, RequestDict
    from fordpass.typing.departure import DepartureScheduleDay

_VIN = '1FAHP00000A000000'

_TELEMETRY: dict[str, Any] = {
    'metrics': {
        'xevDepartureSchedules': {
            'value': {
                'departureLocations': [{
                    'locationId':
                        'LOC1',
                    'departureSchedules': [{
                        'scheduleId': '1',
                        'scheduleStatus': 'ON',
                        'schedule': {
                            'weeklySchedule': {
                                'dayOfWeek': 'MONDAY',
                                'timeOfDay': '07:30'
                            }
                        }
                    }, {
                        'scheduleId': '2',
                        'scheduleStatus': 'OFF',
                        'schedule': {
                            'weeklySchedule': {
                                'dayOfWeek': 'MONDAY',
                                'timeOfDay': '08:00'
                            }
                        }
                    }, {
                        'scheduleId': '3',
                        'scheduleStatus': 'ON',
                        'schedule': {
                            'weeklySchedule': {
                                'dayOfWeek': 'FRIDAY',
                                'timeOfDay': '06:15'
                            }
                        }
                    }]
                }]
            }
        }
    }
}


def _body(req: RequestDict) -> Any:
    return json.loads(req['data'] or '{}')


def _update_schedules(session: MagicMock) -> Any:
    for call in session.request.call_args_list:
        if '/v1beta/command/' in call.kwargs.get('url', ''):
            return json.loads(call.kwargs['data'])['properties']['departureSchedules']
    msg = 'no updateDepartureTimes call was sent'
    raise AssertionError(msg)


@pytest.mark.parametrize(('method', 'type_'),
                         [('enable_departure_times', 'enableDepartureTimes'),
                          ('disable_departure_times', 'disableDepartureTimes')])
def test_enable_disable_builders(core_client: FordPassClient, method: str, type_: str) -> None:
    req = getattr(core_client, method)(_VIN)
    assert req['method'] == 'POST'
    assert '/v1beta/command/vehicles/1FAHP00000A000000/commands' in req['url']
    body = _body(req)
    assert body['type'] == type_
    assert body['version'] == '1'
    assert body['properties'] == {}
    assert body['wakeUp'] is True


def test_update_departure_builder(core_client: FordPassClient) -> None:
    days: list[DepartureScheduleDay] = [{
        'dayOfWeek':
            'MONDAY',
        'schedules': [{
            'locationId': 'LOC1',
            'preconditionTemperature': 'MEDIUM',
            'scheduleId': 1,
            'scheduleStatus': 'ON',
            'timeOfDay': {
                'hours': 7,
                'minutes': 30
            }
        }]
    }]
    req = core_client.update_departure_times(_VIN, schedules=days)
    assert '/v1beta/command/' in req['url']
    body = _body(req)
    assert body['type'] == 'updateDepartureTimes'
    assert body['version'] == '1'
    assert body['properties']['isDepartureTimeEnabled'] is True
    assert body['properties']['departureSchedules'] == days


@pytest.mark.parametrize('method', ['enable_departure_times', 'disable_departure_times'])
async def test_client_enable_disable(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                     method: str) -> None:
    await getattr(async_client, method)(_VIN)
    fake_session.request.assert_awaited_once()


async def test_client_update(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    await async_client.update_departure_times(_VIN, schedules=[])
    fake_session.request.assert_awaited_once()


def test_extract_departure_schedule_days_full() -> None:
    metrics: dict[str, Any] = {
        'xevDepartureSchedules': {
            'value': {
                'departureLocations': [
                    'not-a-mapping', {
                        'locationId':
                            'LOC1',
                        'departureSchedules': [
                            {
                                'scheduleId': '9'
                            },
                            {
                                'scheduleId': '8',
                                'schedule': {
                                    'weeklySchedule': {
                                        'dayOfWeek': 123,
                                        'timeOfDay': '01:00'
                                    }
                                }
                            },
                            {
                                'scheduleId': '1',
                                'scheduleStatus': 'on',
                                'schedule': {
                                    'weeklySchedule': {
                                        'dayOfWeek': 'monday',
                                        'timeOfDay': '07:30'
                                    }
                                },
                                'oemData': {
                                    'chrg_go_t_prcond_d_stat': {
                                        'stringValue': 'medium'
                                    }
                                }
                            },
                            {
                                'scheduleId': 2,
                                'schedule': {
                                    'weeklySchedule': {
                                        'dayOfWeek': 'MONDAY',
                                        'timeOfDay': 700
                                    }
                                }
                            },
                            {
                                'scheduleId': 'abc',
                                'scheduleStatus': 'OFF',
                                'schedule': {
                                    'weeklySchedule': {
                                        'dayOfWeek': 'FRIDAY',
                                        'timeOfDay': 'x:y'
                                    }
                                }
                            },
                        ]
                    }
                ]
            }
        }
    }
    assert extract_departure_schedule_days(metrics) == [{
        'dayOfWeek':
            'MONDAY',
        'schedules': [{
            'locationId': 'LOC1',
            'preconditionTemperature': 'MEDIUM',
            'scheduleId': 1,
            'scheduleStatus': 'ON',
            'timeOfDay': {
                'hours': 7,
                'minutes': 30
            }
        }, {
            'locationId': 'LOC1',
            'preconditionTemperature': 'OFF',
            'scheduleId': 2,
            'scheduleStatus': 'OFF',
            'timeOfDay': {
                'hours': 0,
                'minutes': 0
            }
        }]
    }, {
        'dayOfWeek':
            'FRIDAY',
        'schedules': [{
            'locationId': 'LOC1',
            'preconditionTemperature': 'OFF',
            'scheduleId': 'abc',
            'scheduleStatus': 'OFF',
            'timeOfDay': {
                'hours': 0,
                'minutes': 0
            }
        }]
    }]


@pytest.mark.parametrize('metrics', [
    {},
    {
        'xevDepartureSchedules': {
            'value': 'nope'
        }
    },
    {
        'xevDepartureSchedules': {
            'value': {}
        }
    },
])
def test_extract_departure_schedule_days_empty(metrics: dict[str, Any]) -> None:
    assert extract_departure_schedule_days(metrics) == []


async def test_delete_by_ids(async_client: AsyncFordPassClient, fake_session: MagicMock,
                             fake_response_factory: Any) -> None:
    fake_session.request.return_value = fake_response_factory(json_body=_TELEMETRY)
    await async_client.delete_departure_schedules_by_ids(_VIN, [1, 3])
    schedules = _update_schedules(fake_session)
    assert [day['dayOfWeek'] for day in schedules] == ['MONDAY']
    assert [slot['scheduleId'] for slot in schedules[0]['schedules']] == [2]


async def test_delete_by_days(async_client: AsyncFordPassClient, fake_session: MagicMock,
                              fake_response_factory: Any) -> None:
    fake_session.request.return_value = fake_response_factory(json_body=_TELEMETRY)
    await async_client.delete_departure_schedules_by_days(_VIN, ['friday'])
    schedules = _update_schedules(fake_session)
    assert [day['dayOfWeek'] for day in schedules] == ['MONDAY']
    assert [slot['scheduleId'] for slot in schedules[0]['schedules']] == [1, 2]


async def test_delete_by_ids_no_schedules(async_client: AsyncFordPassClient,
                                          fake_session: MagicMock,
                                          fake_response_factory: Any) -> None:
    fake_session.request.return_value = fake_response_factory(json_body={})
    await async_client.delete_departure_schedules_by_ids(_VIN, [1])
    assert _update_schedules(fake_session) == []


@pytest.mark.parametrize(('args', 'client_method'), [
    (('departure', 'enable'), 'enable_departure_times'),
    (('departure', 'disable'), 'disable_departure_times'),
])
def test_cli_enable_disable(runner: CliRunner, mock_command_client: MagicMock,
                            args: tuple[str, ...], client_method: str) -> None:
    response = MagicMock()
    response.status_code = 200
    getattr(mock_command_client, client_method).return_value = response
    result = runner.invoke(fordpass, (*args, _VIN))
    assert result.exit_code == 0
    getattr(mock_command_client, client_method).assert_awaited_once_with(_VIN)


def test_cli_update_add_round_trip(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.update_departure_times.return_value = response
    result = runner.invoke(
        fordpass,
        ('departure', 'update', _VIN, '--add', 'MON@07:30:loc=ABC,id=1,temp=MEDIUM,status=ON',
         '--add', 'mon@09:00:loc=ABC,id=2'))
    assert result.exit_code == 0
    mock_command_client.update_departure_times.assert_awaited_once_with(
        _VIN,
        schedules=[{
            'dayOfWeek':
                'MONDAY',
            'schedules': [{
                'locationId': 'ABC',
                'preconditionTemperature': 'MEDIUM',
                'scheduleId': 1,
                'scheduleStatus': 'ON',
                'timeOfDay': {
                    'hours': 7,
                    'minutes': 30
                }
            }, {
                'locationId': 'ABC',
                'preconditionTemperature': 'OFF',
                'scheduleId': 2,
                'scheduleStatus': 'ON',
                'timeOfDay': {
                    'hours': 9,
                    'minutes': 0
                }
            }]
        }])


def test_cli_update_from_json_file(runner: CliRunner, mock_command_client: MagicMock,
                                   tmp_path: Any) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.update_departure_times.return_value = response
    payload = [{'dayOfWeek': 'MONDAY', 'schedules': []}]
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps(payload))
    result = runner.invoke(fordpass, ('departure', 'update', _VIN, '--from-json', str(path)))
    assert result.exit_code == 0
    mock_command_client.update_departure_times.assert_awaited_once_with(_VIN, schedules=payload)


def test_cli_update_from_json_object_wrapper(runner: CliRunner,
                                             mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.update_departure_times.return_value = response
    body = json.dumps({'departureSchedules': [{'dayOfWeek': 'TUESDAY', 'schedules': []}]})
    result = runner.invoke(fordpass, ('departure', 'update', _VIN, '--from-json', '-'), input=body)
    assert result.exit_code == 0
    mock_command_client.update_departure_times.assert_awaited_once_with(_VIN,
                                                                        schedules=[{
                                                                            'dayOfWeek': 'TUESDAY',
                                                                            'schedules': []
                                                                        }])


@pytest.mark.parametrize('extra', [(), ('--add', 'MON@07:30:loc=A,id=1', '--from-json', '-')])
def test_cli_update_requires_exactly_one_input(runner: CliRunner, mock_command_client: MagicMock,
                                               extra: tuple[str, ...]) -> None:
    result = runner.invoke(fordpass, ('departure', 'update', _VIN, *extra), input='[]')
    assert result.exit_code != 0
    mock_command_client.update_departure_times.assert_not_awaited()


@pytest.mark.parametrize('payload', ['not json', '{"no": "schedules"}'])
def test_cli_update_from_json_invalid(runner: CliRunner, mock_command_client: MagicMock,
                                      payload: str) -> None:
    result = runner.invoke(fordpass, ('departure', 'update', _VIN, '--from-json', '-'),
                           input=payload)
    assert result.exit_code != 0
    mock_command_client.update_departure_times.assert_not_awaited()


@pytest.mark.parametrize('spec', [
    'MON',
    'MON@xx:yy:loc=A,id=1',
    'MON@25:00:loc=A,id=1',
    'MON@07:99:loc=A,id=1',
    'MON@07:30:locA',
    'MON@07:30:temp=LOW',
    'MON@07:30:loc=A,id=x',
    'MON@07:30:loc=A,id=1,temp=WARM',
    'MON@07:30:loc=A,id=1,status=MAYBE',
    'mwf@07:30:loc=A,id=1',
])
def test_cli_update_add_invalid(runner: CliRunner, mock_command_client: MagicMock,
                                spec: str) -> None:
    result = runner.invoke(fordpass, ('departure', 'update', _VIN, '--add', spec))
    assert result.exit_code != 0
    mock_command_client.update_departure_times.assert_not_awaited()


def test_cli_delete_by_id(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.delete_departure_schedules_by_ids.return_value = response
    result = runner.invoke(fordpass, ('departure', 'delete-by-id', _VIN, '1', '3'))
    assert result.exit_code == 0
    mock_command_client.delete_departure_schedules_by_ids.assert_awaited_once_with(_VIN, (1, 3))


def test_cli_delete_by_day(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.delete_departure_schedules_by_days.return_value = response
    result = runner.invoke(fordpass, ('departure', 'delete-by-day', _VIN, 'mon,fri'))
    assert result.exit_code == 0
    mock_command_client.delete_departure_schedules_by_days.assert_awaited_once_with(
        _VIN, ['MONDAY', 'FRIDAY'])


def test_cli_delete_by_day_none_recognised(runner: CliRunner,
                                           mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass, ('departure', 'delete-by-day', _VIN, ''))
    assert result.exit_code != 0
    mock_command_client.delete_departure_schedules_by_days.assert_not_awaited()
