"""Tests for Ford MPS zone-lighting builders, the two-step client flow, and CLI."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock
import json

from fordpass.main import fordpass
import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner
    from fordpass.client import AsyncFordPassClient
    from fordpass.sansio import FordPassClient
    from pytest_mock import MockerFixture

_VIN = '1FAHP00000A000000'


def test_turn_zone_lights_on_builder(core_client: FordPassClient) -> None:
    req = core_client.turn_zone_lights_on(_VIN)
    assert req['method'] == 'PUT'
    assert req['url'] == 'https://stub-mps.example/vehicles/vpfi/zonelightingactivation'
    assert json.loads(req['data'] or '{}') == {'vin': _VIN}
    assert req['headers']['content-type'] == 'application/json'


def test_turn_zone_lights_off_carries_body(core_client: FordPassClient) -> None:
    req = core_client.turn_zone_lights_off(_VIN)
    assert req['method'] == 'DELETE'
    assert req['url'] == 'https://stub-mps.example/vehicles/vpfi/zonelightingactivation'
    # The DELETE deliberately carries a JSON body - verify it is present.
    assert req['data'] is not None
    assert json.loads(req['data']) == {'vin': _VIN}


def test_set_zone_lights_mode_builder(core_client: FordPassClient) -> None:
    req = core_client.set_zone_lights_mode(_VIN, zone='2')
    assert req['method'] == 'PUT'
    assert req['url'] == 'https://stub-mps.example/vehicles/vpfi/2/zonelightingzone'
    assert json.loads(req['data'] or '{}') == {'vin': _VIN}


async def test_set_zone_lighting_off(async_client: AsyncFordPassClient,
                                     fake_session: MagicMock) -> None:
    await async_client.set_zone_lighting(_VIN, 'off')
    assert fake_session.request.await_count == 1
    assert fake_session.request.await_args.kwargs['method'] == 'DELETE'


async def test_set_zone_lighting_from_off_turns_on_then_sets(async_client: AsyncFordPassClient,
                                                             fake_session: MagicMock,
                                                             mocker: MockerFixture) -> None:
    sleep = mocker.patch('fordpass.client.asyncio.sleep')
    await async_client.set_zone_lighting(_VIN, '1', current='off')
    assert fake_session.request.await_count == 2
    methods = [c.kwargs['method'] for c in fake_session.request.await_args_list]
    assert methods == ['PUT', 'PUT']
    urls = [c.kwargs['url'] for c in fake_session.request.await_args_list]
    assert urls[0].endswith('/zonelightingactivation')
    assert urls[1].endswith('/1/zonelightingzone')
    sleep.assert_awaited_once()


async def test_set_zone_lighting_already_set_noop(async_client: AsyncFordPassClient,
                                                  fake_session: MagicMock) -> None:
    result = await async_client.set_zone_lighting(_VIN, '1', current='1')
    assert result is None
    fake_session.request.assert_not_awaited()


async def test_set_zone_lighting_switch_mode_only(async_client: AsyncFordPassClient,
                                                  fake_session: MagicMock) -> None:
    await async_client.set_zone_lighting(_VIN, '1', current='2')
    assert fake_session.request.await_count == 1
    assert fake_session.request.await_args.kwargs['url'].endswith('/1/zonelightingzone')


async def test_set_zone_lighting_unknown_current_assumes_on(async_client: AsyncFordPassClient,
                                                            fake_session: MagicMock) -> None:
    await async_client.set_zone_lighting(_VIN, '3')
    assert fake_session.request.await_count == 1
    assert fake_session.request.await_args.kwargs['url'].endswith('/3/zonelightingzone')


@pytest.mark.parametrize(('subcommand', 'client_method'), [('on', 'turn_zone_lights_on'),
                                                           ('off', 'turn_zone_lights_off')])
def test_lights_on_off_cli(runner: CliRunner, mock_command_client: MagicMock, subcommand: str,
                           client_method: str) -> None:
    response = MagicMock()
    response.status_code = 200
    getattr(mock_command_client, client_method).return_value = response
    result = runner.invoke(fordpass, ('lights', subcommand, _VIN))
    assert result.exit_code == 0


def test_lights_zone_cli(runner: CliRunner, mock_command_client: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    mock_command_client.set_zone_lighting.return_value = response
    result = runner.invoke(fordpass, ('lights', 'zone', _VIN, 'front'))
    assert result.exit_code == 0
    mock_command_client.set_zone_lighting.assert_awaited_once_with(_VIN, '1')


def test_lights_zone_cli_already_set(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.set_zone_lighting.return_value = None
    result = runner.invoke(fordpass, ('lights', 'zone', _VIN, 'all'))
    assert result.exit_code == 0
    assert 'already set' in result.output
