"""Tests for fordpass.client.AsyncFordPassClient."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
import json

from fordpass.client import AsyncFordPassClient
import pytest

if TYPE_CHECKING:

    from fordpass.typing import Secrets
    from pytest_mock import MockerFixture

_VIN = '1FA12345678901234'


def _make_response(*, status_code: int = 200, json_body: Any = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.content = b'{}' if json_body is None else json.dumps(json_body).encode()
    response.text = response.content.decode()
    response.json = MagicMock(return_value=json_body or {})
    response.raise_for_status = MagicMock()
    return response


def test_default_construction_uses_load_secrets(mocker: MockerFixture) -> None:
    stub = {
        'application_id': 'X',
        'user_agent': 'X',
        'profile_groups_default': 'X',
        'hosts': {
            'foundational': 'X',
            'login': 'X',
            'tmc': 'X',
            'tmc_accounts': 'X',
            'vehicle': 'X'
        },
        'auth': {
            'b2c': {
                'client_id': 'X',
                'policy_template': 'X{locale}',
                'redirect_uri': 'X',
                'tenant_id': 'X'
            },
            'tmc': {
                'client_id': 'X'
            },
        },
        'roadside': {
            'x_source': {
                'ford': 'X'
            }
        }
    }
    mocker.patch('fordpass.client.load_secrets', return_value=stub)
    mocker.patch('fordpass.client.niquests.AsyncSession')
    mocker.patch('fordpass.client.CurlAsyncSession')
    client = AsyncFordPassClient()
    assert client.core.application_id == 'X'


def test_token_properties_round_trip(async_client: AsyncFordPassClient) -> None:
    assert async_client.cat == 'STUB_CAT'
    assert async_client.cat_refresh == 'STUB_CAT_REFRESH'
    assert async_client.tmc == 'STUB_TMC'
    async_client.cat = 'NEW_CAT'
    async_client.cat_refresh = 'NEW_REFRESH'
    async_client.tmc = 'NEW_TMC'
    assert async_client.core.cat == 'NEW_CAT'
    assert async_client.core.cat_refresh == 'NEW_REFRESH'
    assert async_client.core.tmc == 'NEW_TMC'


def test_locale_country_pass_through(async_client: AsyncFordPassClient) -> None:
    assert async_client.locale == 'en-US'
    assert async_client.country == 'USA'


def test_b2c_authorize_url_delegates(async_client: AsyncFordPassClient) -> None:
    url = async_client.b2c_authorize_url(code_challenge='C')
    assert 'stub-login.example' in url


async def test_exchange_b2c_code(async_client: AsyncFordPassClient,
                                 fake_auth_session: MagicMock) -> None:
    fake_auth_session.request.return_value = _make_response(json_body={'access_token': 'B2C_X'})
    result = await async_client.exchange_b2c_code(code='AUTHZ', code_verifier='V')
    assert result['access_token'] == 'B2C_X'
    fake_auth_session.request.assert_awaited_once()


async def test_mint_cat_from_b2c_updates_state(async_client: AsyncFordPassClient,
                                               fake_auth_session: MagicMock) -> None:
    fake_auth_session.request.return_value = _make_response(json_body={
        'access_token': 'NEW_CAT',
        'refresh_token': 'NEW_REFRESH'
    })
    result = await async_client.mint_cat_from_b2c(b2c_access_token='B2C_X')
    assert result['access_token'] == 'NEW_CAT'
    assert async_client.cat == 'NEW_CAT'
    assert async_client.cat_refresh == 'NEW_REFRESH'


async def test_refresh_cat_updates_state(async_client: AsyncFordPassClient,
                                         fake_auth_session: MagicMock) -> None:
    fake_auth_session.request.return_value = _make_response(json_body={
        'access_token': 'CAT_V2',
        'refresh_token': 'REFRESH_V2'
    })
    result = await async_client.refresh_cat()
    assert result['access_token'] == 'CAT_V2'
    assert async_client.cat == 'CAT_V2'
    assert async_client.cat_refresh == 'REFRESH_V2'


async def test_exchange_cat_for_tmc_updates_state(async_client: AsyncFordPassClient,
                                                  fake_auth_session: MagicMock) -> None:
    fake_auth_session.request.return_value = _make_response(json_body={'access_token': 'TMC_V2'})
    result = await async_client.exchange_cat_for_tmc()
    assert result['access_token'] == 'TMC_V2'
    assert async_client.tmc == 'TMC_V2'


@pytest.mark.parametrize('method_name', [
    'remote_start', 'cancel_remote_start', 'extend_remote_start', 'lock', 'unlock',
    'status_refresh', 'get_asu_settings'
])
async def test_simple_remote_commands(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                      method_name: str) -> None:
    await getattr(async_client, method_name)(_VIN)
    fake_session.request.assert_awaited_once()


async def test_panic_alarm(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    await async_client.panic_alarm(_VIN, 5)
    fake_session.request.assert_awaited_once()


async def test_set_asu_enabled(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    await async_client.set_asu_enabled(_VIN, enabled=True)
    fake_session.request.assert_awaited_once()


async def test_set_asu_schedule(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    await async_client.set_asu_schedule(_VIN,
                                        day_schedules=[{
                                            'dayOfWeek': 'MON',
                                            'timeOfDay': '03:00'
                                        }],
                                        activation_setting='X')
    fake_session.request.assert_awaited_once()


async def test_query_telemetry(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={'metrics': {
            'odometer': {
                'value': 100.0
            }
        }})
    result = await async_client.query_telemetry(_VIN)
    assert 'metrics' in result


async def test_get_fuel_level(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={'metrics': {
            'fuelLevel': {
                'value': 75.0
            },
            'fuelRange': {
                'value': 400.0
            }
        }})
    pct, rng = await async_client.get_fuel_level(_VIN)
    assert pct == pytest.approx(75.0)
    assert rng == pytest.approx(400.0)


async def test_get_odometer(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={'metrics': {
            'odometer': {
                'value': 12345.0
            }
        }})
    km = await async_client.get_odometer(_VIN)
    assert km == pytest.approx(12345.0)


async def test_get_oil_life(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={'metrics': {
            'oilLifeRemaining': {
                'value': 80.0
            }
        }})
    pct = await async_client.get_oil_life(_VIN)
    assert pct == pytest.approx(80.0)


async def test_get_position(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={'metrics': {
            'position': {
                'value': {
                    'location': {
                        'lat': 40.7,
                        'lon': -74.0
                    }
                }
            }
        }})
    pos = await async_client.get_position(_VIN)
    assert pos is not None
    assert pos['lat'] == pytest.approx(40.7)


async def test_get_tire_pressure(async_client: AsyncFordPassClient,
                                 fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={'metrics': {
            'tirePressure': [{
                'vehicleWheel': 'FRONT_LEFT',
                'value': 220.0
            }]
        }})
    entries = await async_client.get_tire_pressure(_VIN)
    assert len(entries) == 1


async def test_get_next_departure(async_client: AsyncFordPassClient,
                                  fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={
            'metrics': {
                'xevNextDepartureTimeScheduleId': {
                    'value': 'sched-1'
                },
                'xevDepartureSchedules': {
                    'value': {
                        'departureLocations': [{
                            'departureSchedules': [{
                                'scheduleId': 'sched-1'
                            }]
                        }]
                    }
                }
            }
        })
    result = await async_client.get_next_departure(_VIN)
    assert result is not None
    assert result['scheduleId'] == 'sched-1'


async def test_list_remote_start_schedules(async_client: AsyncFordPassClient,
                                           fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'startSchedule': {'$values': []}})
    result = await async_client.list_remote_start_schedules(_VIN)
    assert 'startSchedule' in result


async def test_add_remote_start_schedule(async_client: AsyncFordPassClient,
                                         fake_session: MagicMock) -> None:
    await async_client.add_remote_start_schedule(_VIN,
                                                 start_time='07:30',
                                                 request_start_date='2026-05-30T07:30',
                                                 time_zone=85,
                                                 days={'mon': 1})
    fake_session.request.assert_awaited_once()


async def test_delete_remote_start_schedule(async_client: AsyncFordPassClient,
                                            fake_session: MagicMock) -> None:
    await async_client.delete_remote_start_schedule(42, vin=_VIN)
    fake_session.request.assert_awaited_once()


async def test_toggle_remote_start_schedule(async_client: AsyncFordPassClient,
                                            fake_session: MagicMock) -> None:
    await async_client.toggle_remote_start_schedule(42, schedule_body={'status': 1})
    fake_session.request.assert_awaited_once()


async def test_list_garage(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body=[{
        'vin': _VIN,
        'preferredDealer': 'P0001'
    }])
    result = await async_client.list_garage()
    assert len(result) == 1


async def test_update_vehicle_details(async_client: AsyncFordPassClient,
                                      fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'status': 'OK'})
    result = await async_client.update_vehicle_details(_VIN, nick_name='Lightning')
    assert result == {'status': 'OK'}


async def test_get_profile(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={
        'userGuid': 'GUID_X',
        'names': {
            'firstName': 'Alice'
        }
    })
    result = await async_client.get_profile()
    assert result['userGuid'] == 'GUID_X'


async def test_save_profile(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    await async_client.save_profile(names={'firstName': 'Bob'})
    fake_session.request.assert_awaited_once()


async def test_get_messages(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'result': {'messages': []}})
    result = await async_client.get_messages()
    assert 'result' in result


async def test_delete_messages(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    result = await async_client.delete_messages([1, 2])
    assert result is None or isinstance(result, dict)


async def test_delete_messages_handles_204(async_client: AsyncFordPassClient,
                                           fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(status_code=204)
    fake_session.request.return_value.content = b''
    result = await async_client.delete_messages([1])
    assert result is None


async def test_mark_messages_read(async_client: AsyncFordPassClient,
                                  fake_session: MagicMock) -> None:
    await async_client.mark_messages_read([1])
    fake_session.request.assert_awaited_once()


async def test_get_alerts(async_client: AsyncFordPassClient, fake_session: MagicMock,
                          mocker: MockerFixture) -> None:
    mocker.patch('fordpass.client.uuid.uuid4',
                 return_value=mocker.MagicMock(__str__=lambda _: 'UUID-X'))
    fake_session.request.return_value = _make_response(json_body={'alerts': []})
    result = await async_client.get_alerts(_VIN)
    assert 'alerts' in result


async def test_get_alert_history(async_client: AsyncFordPassClient,
                                 fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'messages': []})
    result = await async_client.get_alert_history(_VIN)
    assert 'messages' in result


async def test_is_washer_fluid_low(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                   mocker: MockerFixture) -> None:
    mocker.patch('fordpass.client.uuid.uuid4',
                 return_value=mocker.MagicMock(__str__=lambda _: 'UUID-X'))
    fake_session.request.return_value = _make_response(
        json_body={'alerts': [{
            'alertIdentifier': 'E19-374-43'
        }]})
    assert await async_client.is_washer_fluid_low(_VIN) is True


async def test_get_service_planner_upcoming(async_client: AsyncFordPassClient,
                                            fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'upcomingServiceActions': []})
    result = await async_client.get_service_planner_upcoming(vin=_VIN, odometer=10000)
    assert 'upcomingServiceActions' in result


async def test_get_service_planner_history(async_client: AsyncFordPassClient,
                                           fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'completedServiceActions': []})
    result = await async_client.get_service_planner_history(vin=_VIN)
    assert 'completedServiceActions' in result


async def test_get_service_action_detail(async_client: AsyncFordPassClient,
                                         fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'id': 'ACT_X'})
    result = await async_client.get_service_action_detail('ACT_X', vin=_VIN)
    assert result['id'] == 'ACT_X'


async def test_get_completed_service_action_detail(async_client: AsyncFordPassClient,
                                                   fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'id': 'EVT_Y'})
    result = await async_client.get_completed_service_action_detail('EVT_Y', vin=_VIN)
    assert result['id'] == 'EVT_Y'


async def test_get_release_notes_two_step(async_client: AsyncFordPassClient,
                                          fake_session: MagicMock) -> None:
    fake_session.request.side_effect = [
        _make_response(json_body={'mmotaAlertsDetails': [{
            'releaseNotesUrl': 'https://x'
        }]}),
        _make_response(json_body={'response': 'Notes body'}),
    ]
    notes = await async_client.get_release_notes(_VIN)
    assert notes is not None
    assert notes['response'] == 'Notes body'


async def test_get_release_notes_when_no_mmota(async_client: AsyncFordPassClient,
                                               fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'mmotaAlertsDetails': []})
    assert await async_client.get_release_notes(_VIN) is None


async def test_get_dealer_by_pa_code(async_client: AsyncFordPassClient,
                                     fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'paCode': 'P00001'})
    result = await async_client.get_dealer_by_pa_code('P00001')
    assert result is not None
    assert result['paCode'] == 'P00001'


async def test_get_dealer_by_pa_code_204(async_client: AsyncFordPassClient,
                                         fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(status_code=204)
    fake_session.request.return_value.content = b''
    assert await async_client.get_dealer_by_pa_code('P00001') is None


async def test_get_preferred_dealer_via_garage(async_client: AsyncFordPassClient,
                                               fake_session: MagicMock) -> None:
    fake_session.request.side_effect = [
        _make_response(json_body=[{
            'vin': _VIN,
            'preferredDealer': 'P00001'
        }]),
        _make_response(json_body={
            'paCode': 'P00001',
            'dealerName': 'Test Dealer'
        }),
    ]
    result = await async_client.get_preferred_dealer(_VIN)
    assert result is not None
    assert result['paCode'] == 'P00001'


async def test_get_preferred_dealer_no_dealer_set(async_client: AsyncFordPassClient,
                                                  fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body=[{'vin': _VIN}])
    assert await async_client.get_preferred_dealer(_VIN) is None


async def test_get_preferred_dealer_hydration_failed(async_client: AsyncFordPassClient,
                                                     fake_session: MagicMock) -> None:
    no_content = _make_response(status_code=204)
    no_content.content = b''
    fake_session.request.side_effect = [
        _make_response(json_body=[{
            'vin': _VIN,
            'preferredDealer': 'P00001'
        }]),
        no_content,
    ]
    result = await async_client.get_preferred_dealer(_VIN)
    assert result == {'paCode': 'P00001'}


async def test_get_roadside_symptoms(async_client: AsyncFordPassClient,
                                     fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'symptoms': []})
    result = await async_client.get_roadside_symptoms()
    assert 'symptoms' in result


async def test_get_roadside_location_types(async_client: AsyncFordPassClient,
                                           fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'locationTypes': []})
    result = await async_client.get_roadside_location_types()
    assert 'locationTypes' in result


async def test_get_roadside_active_event(async_client: AsyncFordPassClient,
                                         fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'eventId': 'EVT_X'})
    result = await async_client.get_roadside_active_event(_VIN)
    assert result is not None
    assert result['eventId'] == 'EVT_X'


async def test_predraft_roadside_event(async_client: AsyncFordPassClient,
                                       fake_session: MagicMock) -> None:
    await async_client.predraft_roadside_event(_VIN, customer_name='A', customer_phone='1')
    fake_session.request.assert_awaited_once()


async def test_list_drivers(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'authorizedUsers': []})
    await async_client.list_drivers(_VIN)
    fake_session.request.assert_awaited_once()


async def test_get_authorized_user_count(async_client: AsyncFordPassClient,
                                         fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(json_body={'count': 2})
    result = await async_client.get_authorized_user_count(_VIN)
    assert result.get('count') == 2


async def test_invite_driver(async_client: AsyncFordPassClient, fake_session: MagicMock) -> None:
    await async_client.invite_driver(_VIN,
                                     secondary_email='x@example.com',
                                     inviter_first_name='Bob',
                                     vehicle_display_name='F-150')
    fake_session.request.assert_awaited_once()


async def test_aclose_skips_externally_owned_sessions(async_client: AsyncFordPassClient,
                                                      fake_session: MagicMock,
                                                      fake_auth_session: MagicMock) -> None:
    await async_client.aclose()
    fake_session.close.assert_not_called()
    fake_auth_session.close.assert_not_called()


async def test_aclose_closes_owned_sessions(stub_secrets: Secrets, mocker: MockerFixture) -> None:
    niquests_session = mocker.MagicMock()
    niquests_session.close = mocker.AsyncMock()
    curl_session = mocker.MagicMock()
    curl_session.close = mocker.AsyncMock()
    mocker.patch('fordpass.client.niquests.AsyncSession', return_value=niquests_session)
    mocker.patch('fordpass.client.CurlAsyncSession', return_value=curl_session)
    client = AsyncFordPassClient(secrets=stub_secrets, cat='X', tmc='Y')
    await client.aclose()
    niquests_session.close.assert_awaited_once()
    curl_session.close.assert_awaited_once()


async def test_context_manager(async_client: AsyncFordPassClient) -> None:
    async with async_client as c:
        assert c is async_client


async def test_send_retries_on_401(async_client: AsyncFordPassClient, fake_session: MagicMock,
                                   fake_auth_session: MagicMock) -> None:
    unauthorized = _make_response(status_code=401)
    success = _make_response(json_body={'ok': True})
    fake_session.request.side_effect = [unauthorized, success]
    fake_auth_session.request.return_value = _make_response(json_body={'access_token': 'NEW_TMC'})
    # remote_start uses TMC plane; the retry path rotates the TMC bearer.
    await async_client.remote_start(_VIN)
    # Called twice: once for the original 401, once for the retry.
    assert fake_session.request.call_count == 2


async def test_send_retries_cat_plane_on_401(async_client: AsyncFordPassClient,
                                             fake_session: MagicMock,
                                             fake_auth_session: MagicMock) -> None:
    unauthorized = _make_response(status_code=401)
    garage_ok = _make_response(json_body=[{'vin': _VIN}])
    fake_session.request.side_effect = [unauthorized, garage_ok]
    fake_auth_session.request.return_value = _make_response(json_body={
        'access_token': 'NEW_CAT',
        'refresh_token': 'NEW_REFRESH'
    })
    # list_garage uses Ford plane (auth-token header); retry path rotates the CAT.
    await async_client.list_garage()
    assert fake_session.request.call_count == 2
    assert async_client.cat == 'NEW_CAT'


async def test_send_no_retry_without_cat_refresh(stub_secrets: Secrets, mocker: MockerFixture,
                                                 fake_session: MagicMock,
                                                 fake_auth_session: MagicMock) -> None:
    client = AsyncFordPassClient(secrets=stub_secrets,
                                 cat='STUB_CAT',
                                 tmc='STUB_TMC',
                                 session=fake_session,
                                 auth_session=fake_auth_session)
    unauthorized = _make_response(status_code=401)
    unauthorized.raise_for_status.side_effect = Exception('HTTP 401')
    fake_session.request.return_value = unauthorized
    with pytest.raises(Exception, match='HTTP 401'):
        await client.list_garage()
    assert fake_session.request.call_count == 1


async def test_send_auth_json_raises_on_error_status(async_client: AsyncFordPassClient,
                                                     fake_auth_session: MagicMock) -> None:
    failure = _make_response(status_code=500)
    failure.text = 'server boom'
    fake_auth_session.request.return_value = failure
    with pytest.raises(RuntimeError, match='auth request failed'):
        await async_client.refresh_cat()


async def test_get_release_notes_when_url_empty(async_client: AsyncFordPassClient,
                                                fake_session: MagicMock) -> None:
    fake_session.request.return_value = _make_response(
        json_body={'mmotaAlertsDetails': [{
            'releaseNotesUrl': ''
        }]})
    assert await async_client.get_release_notes(_VIN) is None


async def test_mint_cat_skips_state_update_when_keys_missing(async_client: AsyncFordPassClient,
                                                             fake_auth_session: MagicMock) -> None:
    fake_auth_session.request.return_value = _make_response(json_body={})
    before_cat = async_client.cat
    before_refresh = async_client.cat_refresh
    await async_client.mint_cat_from_b2c(b2c_access_token='B')
    assert async_client.cat == before_cat
    assert async_client.cat_refresh == before_refresh


async def test_refresh_cat_skips_state_update_when_keys_missing(
        async_client: AsyncFordPassClient, fake_auth_session: MagicMock) -> None:
    fake_auth_session.request.return_value = _make_response(json_body={})
    before_cat = async_client.cat
    before_refresh = async_client.cat_refresh
    await async_client.refresh_cat()
    assert async_client.cat == before_cat
    assert async_client.cat_refresh == before_refresh


async def test_exchange_cat_for_tmc_skips_state_update_when_key_missing(
        async_client: AsyncFordPassClient, fake_auth_session: MagicMock) -> None:
    fake_auth_session.request.return_value = _make_response(json_body={})
    before_tmc = async_client.tmc
    await async_client.exchange_cat_for_tmc()
    assert async_client.tmc == before_tmc
