"""Tests for Remote Climate Control builders, codecs, client wrappers, and CLI."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
import json

from fordpass.main import fordpass
from fordpass.utils import (
    decode_rcc_temperature,
    encode_rcc_temperature,
    merge_rcc_preferences,
)
import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from click.testing import CliRunner
    from fordpass.client import AsyncFordPassClient
    from fordpass.sansio import FordPassClient
    from fordpass.typing.rcc import RCCPreference, RCCPreferenceKey

_VIN = '1FAHP00000A000000'

_TEMPS = [round(-40.0 + 0.5 * i, 1) for i in range(181)]


def test_get_remote_climate_builder(core_client: FordPassClient) -> None:
    req = core_client.get_remote_climate(_VIN)
    assert req['method'] == 'POST'
    assert req['url'] == 'https://stub-vehicle.example/api/rcc/profile/status'
    assert json.loads(req['data'] or '{}') == {'vin': _VIN}
    assert req['headers']['content-type'] == 'application/json'
    assert req['headers']['auth-token'] == 'STUB_CAT'


def test_set_remote_climate_builder(core_client: FordPassClient) -> None:
    prefs: list[RCCPreference] = [{'preferenceType': 'SetPointTemp_Rq', 'preferenceValue': '22_0'}]
    req = core_client.set_remote_climate(_VIN, state_flag='On', user_preferences=prefs)
    assert req['method'] == 'PUT'
    assert req['url'] == 'https://stub-vehicle.example/api/rcc/profile/update'
    assert json.loads(req['data'] or '{}') == {
        'crccStateFlag': 'On',
        'userPreferences': prefs,
        'vin': _VIN
    }


@pytest.mark.parametrize('celsius', _TEMPS)
def test_temperature_codec_round_trip(celsius: float) -> None:
    assert decode_rcc_temperature(encode_rcc_temperature(celsius)) == celsius


@pytest.mark.parametrize(('celsius', 'wire'), [(22.0, '22_0'), (22.5, '22_5'), (-40.0, '-40_0')])
def test_encode_rcc_temperature(celsius: float, wire: str) -> None:
    assert encode_rcc_temperature(celsius) == wire


def test_decode_rcc_temperature_invalid() -> None:
    with pytest.raises(ValueError, match='could not convert'):
        decode_rcc_temperature('not_a_number')


def test_merge_rcc_preferences_replaces_and_appends() -> None:
    current: list[RCCPreference] = [{
        'preferenceType': 'SetPointTemp_Rq',
        'preferenceValue': '22_0'
    }, {
        'preferenceType': 'RccRearDefrost_Rq',
        'preferenceValue': 'Off'
    }]
    result = merge_rcc_preferences(current, {
        'SetPointTemp_Rq': '23_0',
        'RccHeatedWindshield_Rq': 'On'
    })
    assert result == [{
        'preferenceType': 'SetPointTemp_Rq',
        'preferenceValue': '23_0'
    }, {
        'preferenceType': 'RccRearDefrost_Rq',
        'preferenceValue': 'Off'
    }, {
        'preferenceType': 'RccHeatedWindshield_Rq',
        'preferenceValue': 'On'
    }]
    assert current[0]['preferenceValue'] == '22_0'


async def test_client_get_remote_climate(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                         fake_response_factory: Any) -> None:
    profile = {
        'rccUserProfiles': [{
            'preferenceType': 'SetPointTemp_Rq',
            'preferenceValue': '22_0'
        }]
    }
    fake_session.request.return_value = fake_response_factory(json_body=profile)
    result = await async_client.get_remote_climate(_VIN)
    assert result == profile
    assert fake_session.request.await_args.kwargs['url'].endswith('/api/rcc/profile/status')


async def test_client_set_remote_climate_merges(async_client: AsyncFordPassClient,
                                                fake_session: MagicMock,
                                                fake_response_factory: Any) -> None:
    current = {
        'rccUserProfiles': [{
            'preferenceType': 'SetPointTemp_Rq',
            'preferenceValue': '22_0'
        }, {
            'preferenceType': 'RccRearDefrost_Rq',
            'preferenceValue': 'Off'
        }]
    }
    fake_session.request.side_effect = [
        fake_response_factory(json_body=current),
        fake_response_factory(json_body={'status': 200})
    ]
    ok = await async_client.set_remote_climate(_VIN, updates={'SetPointTemp_Rq': '23_0'})
    assert ok is True
    body = json.loads(fake_session.request.call_args_list[-1].kwargs['data'])
    assert body['vin'] == _VIN
    assert body['crccStateFlag'] == 'On'
    assert body['userPreferences'] == [{
        'preferenceType': 'SetPointTemp_Rq',
        'preferenceValue': '23_0'
    }, {
        'preferenceType': 'RccRearDefrost_Rq',
        'preferenceValue': 'Off'
    }]


async def test_client_set_remote_climate_empty_body_true(async_client: AsyncFordPassClient,
                                                         fake_session: MagicMock,
                                                         fake_response_factory: Any) -> None:
    current = {
        'rccUserProfiles': [{
            'preferenceType': 'SetPointTemp_Rq',
            'preferenceValue': '22_0'
        }]
    }
    fake_session.request.side_effect = [
        fake_response_factory(json_body=current),
        fake_response_factory(status_code=204, content=b'')
    ]
    ok = await async_client.set_remote_climate(_VIN,
                                               updates={'SetPointTemp_Rq': '23_0'},
                                               state_flag='Active')
    assert ok is True
    body = json.loads(fake_session.request.call_args_list[-1].kwargs['data'])
    assert body['crccStateFlag'] == 'Active'


async def test_client_set_remote_climate_error_status_false(async_client: AsyncFordPassClient,
                                                            fake_session: MagicMock,
                                                            fake_response_factory: Any) -> None:
    current = {
        'rccUserProfiles': [{
            'preferenceType': 'SetPointTemp_Rq',
            'preferenceValue': '22_0'
        }]
    }
    fake_session.request.side_effect = [
        fake_response_factory(json_body=current),
        fake_response_factory(json_body={'status': 500})
    ]
    ok = await async_client.set_remote_climate(_VIN, updates={'SetPointTemp_Rq': '23_0'})
    assert ok is False


async def test_client_set_remote_climate_unknown_key(async_client: AsyncFordPassClient) -> None:
    with pytest.raises(ValueError, match='Unknown RCC'):
        await async_client.set_remote_climate(_VIN,
                                              updates=cast('dict[RCCPreferenceKey, str]',
                                                           {'Bogus_Rq': 'On'}))


def test_climate_show_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_remote_climate.return_value = {
        'rccUserProfiles': [{
            'preferenceType': 'RccHeatedWindshield_Rq',
            'preferenceValue': 'Off'
        }, {
            'preferenceType': 'SetPointTemp_Rq',
            'preferenceValue': '22_0'
        }]
    }
    result = runner.invoke(fordpass, ('climate', 'show', _VIN))
    assert result.exit_code == 0
    assert 'Heated windshield' in result.output
    assert '°F' in result.output


def test_climate_show_celsius(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.locale = 'en-GB'
    mock_command_client.get_remote_climate.return_value = {
        'rccUserProfiles': [{
            'preferenceType': 'SetPointTemp_Rq',
            'preferenceValue': '22_0'
        }]
    }
    result = runner.invoke(fordpass, ('climate', 'show', _VIN))
    assert result.exit_code == 0
    assert '°C' in result.output


def test_climate_show_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_remote_climate.return_value = {}
    result = runner.invoke(fordpass, ('climate', 'show', _VIN))
    assert result.exit_code == 0
    assert 'No remote climate profile' in result.output


def test_climate_show_bad_temperature(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_remote_climate.return_value = {
        'rccUserProfiles': [{
            'preferenceType': 'SetPointTemp_Rq',
            'preferenceValue': 'bad'
        }]
    }
    result = runner.invoke(fordpass, ('climate', 'show', _VIN))
    assert result.exit_code == 0
    assert 'bad' in result.output


def test_climate_show_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_remote_climate.return_value = {'rccUserProfiles': []}
    result = runner.invoke(fordpass, ('climate', 'show', _VIN, '--json'))
    assert result.exit_code == 0
    assert '"rccUserProfiles"' in result.output


def test_climate_set_toggle(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_remote_climate.return_value = True
    result = runner.invoke(fordpass, ('climate', 'set', _VIN, '--rear-defrost', 'on'))
    assert result.exit_code == 0
    assert 'submitted' in result.output
    assert mock_command_client.set_remote_climate.await_args.kwargs['updates'] == {
        'RccRearDefrost_Rq': 'On'
    }


def test_climate_set_seat(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_remote_climate.return_value = True
    result = runner.invoke(fordpass, ('climate', 'set', _VIN, '--seat-lf', 'medium'))
    assert result.exit_code == 0
    assert mock_command_client.set_remote_climate.await_args.kwargs['updates'] == {
        'RccLeftFrontClimateSeat_Rq': 'Medium'
    }


def test_climate_set_temp_fahrenheit(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_remote_climate.return_value = True
    result = runner.invoke(fordpass, ('climate', 'set', _VIN, '--temp', '71.6'))
    assert result.exit_code == 0
    assert mock_command_client.set_remote_climate.await_args.kwargs['updates'] == {
        'SetPointTemp_Rq': '22_0'
    }


def test_climate_set_temp_celsius(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.locale = 'en-GB'
    mock_command_client.set_remote_climate.return_value = True
    result = runner.invoke(fordpass, ('climate', 'set', _VIN, '--temp', '21.5'))
    assert result.exit_code == 0
    assert mock_command_client.set_remote_climate.await_args.kwargs['updates'] == {
        'SetPointTemp_Rq': '21_5'
    }


def test_climate_set_requires_option(runner: CliRunner, mock_command_client: MagicMock) -> None:
    result = runner.invoke(fordpass, ('climate', 'set', _VIN))
    assert result.exit_code == 2
    assert 'at least one setting' in result.output


def test_climate_set_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_remote_climate.return_value = True
    result = runner.invoke(fordpass,
                           ('climate', 'set', _VIN, '--heated-windshield', 'on', '--json'))
    assert result.exit_code == 0
    assert '"submitted"' in result.output
    assert '"updates"' in result.output


def test_climate_set_rejected(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_remote_climate.return_value = False
    result = runner.invoke(fordpass, ('climate', 'set', _VIN, '--seat-rr', 'low'))
    assert result.exit_code == 0
    assert 'not accepted' in result.output
