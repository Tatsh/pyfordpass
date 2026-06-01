"""Tests for the Autonomic TMC builders and CLI (trailer, precondition, PPO, honk)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
import json

from fordpass.main import fordpass
import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner
    from fordpass.client import AsyncFordPassClient
    from fordpass.sansio import FordPassClient, RequestDict

_VIN = '1FAHP00000A000000'


def _body(req: RequestDict) -> Any:
    return json.loads(req['data'] or '{}')


def test_trailer_builders_omit_version(core_client: FordPassClient) -> None:
    for method, type_ in (('start_trailer_light_check', 'startTrailerLightCheck'),
                          ('stop_trailer_light_check', 'stopTrailerLightCheck')):
        req = getattr(core_client, method)(_VIN)
        assert req['method'] == 'POST'
        assert '/v1/command/vehicles/1FAHP00000A000000/commands' in req['url']
        body = _body(req)
        assert body['type'] == type_
        assert body['properties'] == {}
        assert 'version' not in body
        assert body['wakeUp'] is True


@pytest.mark.parametrize(('method', 'type_', 'setting'),
                         [('start_on_demand_preconditioning', 'startOnDemandPreconditioning', 2),
                          ('extend_on_demand_preconditioning', 'extendOnDemandPreconditioning', 2)])
def test_precondition_start_extend(core_client: FordPassClient, method: str, type_: str,
                                   setting: int) -> None:
    req = getattr(core_client, method)(_VIN)
    assert '/v1beta/command/' in req['url']
    body = _body(req)
    assert body['type'] == type_
    assert body['version'] == '1'
    assert body['properties'] == {
        'preconditioningDuration': 0,
        'vehiclePreconditionSetting': setting
    }


def test_precondition_stop_omits_version(core_client: FordPassClient) -> None:
    req = core_client.stop_on_demand_preconditioning(_VIN)
    assert '/v1beta/command/' in req['url']
    body = _body(req)
    assert body['type'] == 'stopOnDemandPreconditioning'
    assert 'version' not in body
    assert body['properties'] == {'preconditioningDuration': 0, 'vehiclePreconditionSetting': 1}


def test_precondition_custom_duration_setting(core_client: FordPassClient) -> None:
    req = core_client.start_on_demand_preconditioning(_VIN, duration=15, setting=3)
    assert _body(req)['properties'] == {
        'preconditioningDuration': 15,
        'vehiclePreconditionSetting': 3
    }


def test_ppo_refresh(core_client: FordPassClient) -> None:
    req = core_client.ppo_refresh(_VIN)
    assert '/v1beta/command/' in req['url']
    body = _body(req)
    assert body['type'] == 'ppoRefresh'
    assert body['version'] == '1.0.0'
    assert body['properties'] == {}


def test_ppo_refresh_continuous_defaults(core_client: FordPassClient) -> None:
    req = core_client.ppo_refresh_continuous(_VIN)
    body = _body(req)
    assert body['type'] == 'ppoRefreshContinuous'
    assert body['version'] == '1.0.0'
    assert body['properties'] == {'frequencyAndDuration': {'frequency': 3, 'duration': 10}}


def test_ppo_refresh_continuous_custom(core_client: FordPassClient) -> None:
    req = core_client.ppo_refresh_continuous(_VIN, frequency_min=5, duration_min=30)
    assert _body(req)['properties'] == {'frequencyAndDuration': {'frequency': 5, 'duration': 30}}


def test_ppo_refresh_cancel(core_client: FordPassClient) -> None:
    req = core_client.ppo_refresh_cancel(_VIN)
    body = _body(req)
    assert body['type'] == 'ppoRefreshContinuousCancel'
    assert body['version'] == '1.0.0'
    assert body['properties'] == {'frequencyAndDuration': {'frequency': 0, 'duration': 0}}


def test_honk_and_flash_matches_panic_alarm(core_client: FordPassClient) -> None:
    assert core_client.honk_and_flash(_VIN) == core_client.panic_alarm(_VIN, 3)
    req = core_client.honk_and_flash(_VIN, duration_s=5)
    body = _body(req)
    assert body['type'] == 'startPanicCue'
    assert body['properties'] == {'duration': 5}
    assert 'version' not in body


@pytest.mark.parametrize('method_name', [
    'start_trailer_light_check', 'stop_trailer_light_check', 'start_on_demand_preconditioning',
    'extend_on_demand_preconditioning', 'stop_on_demand_preconditioning', 'ppo_refresh',
    'ppo_refresh_continuous', 'ppo_refresh_cancel', 'honk_and_flash'
])
async def test_client_tmc_wrappers(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                   method_name: str) -> None:
    await getattr(async_client, method_name)(_VIN)
    fake_session.request.assert_awaited_once()


@pytest.mark.parametrize(('args', 'client_method'),
                         [(('trailer', 'check', 'on'), 'start_trailer_light_check'),
                          (('trailer', 'check', 'off'), 'stop_trailer_light_check'),
                          (('precondition', 'start'), 'start_on_demand_preconditioning'),
                          (('precondition', 'extend'), 'extend_on_demand_preconditioning'),
                          (('precondition', 'stop'), 'stop_on_demand_preconditioning'),
                          (('ppo', 'refresh'), 'ppo_refresh'),
                          (('ppo', 'cancel'), 'ppo_refresh_cancel')])
def test_tmc_cli_commands(runner: CliRunner, mock_command_client: MagicMock, args: tuple[str, ...],
                          client_method: str) -> None:
    response = MagicMock()
    response.status_code = 200
    getattr(mock_command_client, client_method).return_value = response
    result = runner.invoke(fordpass, (*args, _VIN))
    assert result.exit_code == 0


def test_ppo_stream_cli(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.ppo_refresh_continuous.return_value = response
    result = runner.invoke(fordpass,
                           ('ppo', 'stream', _VIN, '--frequency-min', '5', '--duration-min', '30'))
    assert result.exit_code == 0
    mock_command_client.ppo_refresh_continuous.assert_awaited_once_with(_VIN,
                                                                        frequency_min=5,
                                                                        duration_min=30)
