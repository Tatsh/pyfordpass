"""Tests for fordpass.sansio.FordPassClient request builders."""
from __future__ import annotations

from typing import TYPE_CHECKING
import json

from fordpass.sansio import FordPassClient
import pytest

if TYPE_CHECKING:
    from fordpass.typing import APIConfig

_VIN = '1FAHP00000A000000'


def test_init_defaults(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config)
    assert client.cat is None
    assert client.cat_refresh is None
    assert client.tmc is None
    assert client.country == 'USA'
    assert client.locale == 'en-US'
    assert client.brand == 'ford'
    assert client.application_id == 'STUB_APP_ID'


def test_init_with_tokens(core_client: FordPassClient) -> None:
    assert core_client.cat == 'STUB_CAT'
    assert core_client.cat_refresh == 'STUB_CAT_REFRESH'
    assert core_client.tmc == 'STUB_TMC'


def test_init_with_overrides(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config,
                            country='GBR',
                            locale='en-GB',
                            brand='lincoln',
                            cat='X')
    assert client.country == 'GBR'
    assert client.locale == 'en-GB'
    assert client.brand == 'lincoln'


def test_b2c_authorize_url_returns_string(core_client: FordPassClient) -> None:
    url = core_client.b2c_authorize_url(code_challenge='CHALLENGE_X')
    assert isinstance(url, str)
    assert 'stub-login.example' in url
    assert 'CHALLENGE_X' in url
    assert 'STUB_B2C_CLIENT' in url
    assert 'code_challenge_method=S256' in url


def test_b2c_authorize_url_with_overrides(core_client: FordPassClient) -> None:
    url = core_client.b2c_authorize_url(code_challenge='C',
                                        policy='CUSTOM_POLICY',
                                        country='GBR',
                                        locale='en-GB')
    assert 'CUSTOM_POLICY' in url
    assert 'country_code=GBR' in url
    assert 'language_code=en-GB' in url


def test_exchange_b2c_code(core_client: FordPassClient) -> None:
    req = core_client.exchange_b2c_code(code='AUTHZ_CODE', code_verifier='VERIFIER_X')
    assert req['method'] == 'POST'
    assert 'stub-login.example' in req['url']
    assert '/oauth2/v2.0/token' in req['url']
    assert req['data'] is not None
    assert 'AUTHZ_CODE' in req['data']
    assert 'VERIFIER_X' in req['data']
    assert req['headers']['content-type'] == 'application/x-www-form-urlencoded'


def test_mint_cat_from_b2c(core_client: FordPassClient) -> None:
    req = core_client.mint_cat_from_b2c(b2c_access_token='B2C_ACCESS')
    assert req['method'] == 'POST'
    assert '/api/token/v2/cat-with-b2c-access-token' in req['url']
    assert req['data'] is not None
    body = json.loads(req['data'])
    assert body['idpToken'] == 'B2C_ACCESS'


def test_refresh_cat(core_client: FordPassClient) -> None:
    req = core_client.refresh_cat()
    assert req['method'] == 'POST'
    assert '/api/token/v2/cat-with-refresh-token' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['refresh_token'] == 'STUB_CAT_REFRESH'


def test_refresh_cat_without_refresh_token(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config)
    with pytest.raises(RuntimeError, match='cat_refresh'):
        client.refresh_cat()


def test_exchange_cat_for_tmc(core_client: FordPassClient) -> None:
    req = core_client.exchange_cat_for_tmc()
    assert req['method'] == 'POST'
    assert '/v1/auth/oidc/token' in req['url']
    assert req['data'] is not None
    assert 'STUB_CAT_REFRESH' in req['data']
    assert 'subject_issuer=fordpass' in req['data']


def test_exchange_cat_for_tmc_without_cat_refresh(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config)
    with pytest.raises(RuntimeError, match='cat_refresh'):
        client.exchange_cat_for_tmc()


@pytest.mark.parametrize(('method_name', 'expected_type'),
                         [('remote_start', 'remoteStart'),
                          ('cancel_remote_start', 'cancelRemoteStart'),
                          ('extend_remote_start', 'remoteStart'), ('lock', 'lock'),
                          ('unlock', 'unlock'), ('status_refresh', 'statusRefresh')])
def test_simple_command_builders(core_client: FordPassClient, method_name: str,
                                 expected_type: str) -> None:
    req = getattr(core_client, method_name)(_VIN)
    assert req['method'] == 'POST'
    assert '/v1/command/vehicles/1FAHP00000A000000/commands' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['type'] == expected_type
    assert body['wakeUp'] is True


def test_get_asu_settings_uses_beta(core_client: FordPassClient) -> None:
    req = core_client.get_asu_settings(_VIN)
    assert '/v1beta/command/' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['type'] == 'getASUSettingsCommand'
    assert body['version'] == '1.0.0'


def test_panic_alarm(core_client: FordPassClient) -> None:
    req = core_client.panic_alarm(_VIN, duration_s=5)
    body = json.loads(req['data'] or '{}')
    assert body['type'] == 'startPanicCue'
    assert body['properties']['duration'] == 5


def test_set_asu_enabled_on(core_client: FordPassClient) -> None:
    req = core_client.set_asu_enabled(_VIN, enabled=True)
    body = json.loads(req['data'] or '{}')
    assert body['type'] == 'publishASUSettingsCommand'
    assert body['properties']['ASUState'] == 'ON'


def test_set_asu_enabled_off(core_client: FordPassClient) -> None:
    req = core_client.set_asu_enabled(_VIN, enabled=False)
    body = json.loads(req['data'] or '{}')
    assert body['properties']['ASUState'] == 'OFF'


def test_set_asu_schedule(core_client: FordPassClient) -> None:
    req = core_client.set_asu_schedule(_VIN,
                                       day_schedules=[{
                                           'dayOfWeek': 'MONDAY',
                                           'timeOfDay': '03:00'
                                       }],
                                       activation_setting='LATEST_OFF_PLUG')
    body = json.loads(req['data'] or '{}')
    assert body['type'] == 'scheduleASUActivationCommand'
    assert body['properties']['activationScheduleSetting'] == 'LATEST_OFF_PLUG'
    assert body['properties']['OTAActivationDaySchedule'][0]['dayOfWeek'] == 'MONDAY'


def test_query_telemetry_no_filter(core_client: FordPassClient) -> None:
    req = core_client.query_telemetry(_VIN)
    assert req['method'] == 'POST'
    assert ':query' in req['url']
    assert _VIN in req['url']
    body = json.loads(req['data'] or '{}')
    assert 'includeMetrics' not in body


def test_query_telemetry_with_metric_filter(core_client: FordPassClient) -> None:
    req = core_client.query_telemetry(_VIN, metrics=['odometer', 'fuelLevel'])
    body = json.loads(req['data'] or '{}')
    assert body['includeMetrics'] == ['odometer', 'fuelLevel']


@pytest.mark.parametrize('method_name', [
    'get_fuel_level', 'get_odometer', 'get_position', 'get_tire_pressure', 'get_oil_life',
    'get_next_departure'
])
def test_telemetry_helpers(core_client: FordPassClient, method_name: str) -> None:
    req = getattr(core_client, method_name)(_VIN)
    assert req['method'] == 'POST'
    assert _VIN in req['url']
    body = json.loads(req['data'] or '{}')
    assert 'includeMetrics' in body


def test_list_remote_start_schedules(core_client: FordPassClient) -> None:
    req = core_client.list_remote_start_schedules(_VIN)
    assert req['method'] == 'POST'
    assert '/api/srsm/vehicles/v3/getschedules' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['vin'] == _VIN


def test_add_remote_start_schedule(core_client: FordPassClient) -> None:
    req = core_client.add_remote_start_schedule(_VIN,
                                                start_time='07:30',
                                                request_start_date='2026-05-30T07:30',
                                                time_zone=85,
                                                days={
                                                    'mon': 1,
                                                    'tue': 0,
                                                    'wed': 0,
                                                    'thu': 0,
                                                    'fri': 0,
                                                    'sat': 0,
                                                    'sun': 0
                                                })
    assert req['method'] == 'POST'
    body = json.loads(req['data'] or '{}')
    assert body['startTime'] == '07:30'
    assert body['timeZone'] == 85
    assert body['mon'] == 1
    assert body['tue'] == 0


def test_delete_remote_start_schedule(core_client: FordPassClient) -> None:
    req = core_client.delete_remote_start_schedule(42, vin=_VIN)
    assert req['method'] == 'DELETE'
    assert '/startschedules/42' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['vin'] == _VIN


def test_toggle_remote_start_schedule(core_client: FordPassClient) -> None:
    req = core_client.toggle_remote_start_schedule(42, schedule_body={'vin': _VIN, 'status': 1})
    assert req['method'] == 'PUT'
    assert '/startschedules/42' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['status'] == 1


def test_list_garage(core_client: FordPassClient) -> None:
    req = core_client.list_garage()
    assert req['method'] == 'GET'
    assert 'stub-vehicle.example' in req['url']
    assert '/api/fpcpl-user-garage-service/v1/user/garage' in req['url']


def test_update_vehicle_details_nickname(core_client: FordPassClient) -> None:
    req = core_client.update_vehicle_details(_VIN, nick_name='Lightning')
    body = json.loads(req['data'] or '{}')
    assert body['nickName'] == 'Lightning'


def test_update_vehicle_details_plate(core_client: FordPassClient) -> None:
    req = core_client.update_vehicle_details(_VIN, license_plate='ABC-123')
    body = json.loads(req['data'] or '{}')
    assert body['licenseplate'] == 'ABC-123'


def test_update_vehicle_details_mileage(core_client: FordPassClient) -> None:
    req = core_client.update_vehicle_details(_VIN, mileage=42000)
    body = json.loads(req['data'] or '{}')
    assert body['mileage'] == 42000


def test_update_vehicle_details_preferred_dealer(core_client: FordPassClient) -> None:
    req = core_client.update_vehicle_details(_VIN, preferred_dealer='P00001')
    body = json.loads(req['data'] or '{}')
    assert body['preferredDealer'] == 'P00001'


def test_get_profile_no_groups(core_client: FordPassClient) -> None:
    req = core_client.get_profile()
    assert req['method'] == 'GET'
    assert 'STUB_PROFILE_GROUPS' in req['url']


def test_get_profile_explicit_groups(core_client: FordPassClient) -> None:
    req = core_client.get_profile(profile_groups='names,address')
    assert 'names%2Caddress' in req['url']


def test_save_profile(core_client: FordPassClient) -> None:
    req = core_client.save_profile(names={'firstName': 'Alice'})
    assert req['method'] == 'PATCH'
    body = json.loads(req['data'] or '{}')
    assert body['names']['firstName'] == 'Alice'


def test_get_messages(core_client: FordPassClient) -> None:
    req = core_client.get_messages()
    assert req['method'] == 'GET'
    assert '/api/messagecenter/v3/messages' in req['url']


def test_delete_messages(core_client: FordPassClient) -> None:
    req = core_client.delete_messages([1, 2, 3])
    assert req['method'] == 'DELETE'
    body = json.loads(req['data'] or '{}')
    assert body['messageIds'] == [1, 2, 3]


def test_mark_messages_read(core_client: FordPassClient) -> None:
    req = core_client.mark_messages_read([4, 5])
    assert req['method'] == 'PUT'
    body = json.loads(req['data'] or '{}')
    assert body['messageIds'] == [4, 5]


def test_get_alerts(core_client: FordPassClient) -> None:
    req = core_client.get_alerts(_VIN)
    assert req['method'] == 'POST'
    assert '/api/expvehiclealerts/v3/details' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['VIN'] == _VIN


def test_get_alerts_with_trace_id(core_client: FordPassClient) -> None:
    req = core_client.get_alerts(_VIN, trace_id='TRACE_X')
    assert req['headers']['Trace-id'] == 'TRACE_X'


def test_get_alert_history(core_client: FordPassClient) -> None:
    req = core_client.get_alert_history(_VIN)
    assert req['method'] == 'GET'
    assert '/vehicle-alert-history/v1/getAlertHistory' in req['url']
    assert f'vin={_VIN}' in req['url']
    assert 'brand=ford' in req['url']


def test_get_alert_history_with_brand(core_client: FordPassClient) -> None:
    req = core_client.get_alert_history(_VIN, brand='lincoln')
    assert 'brand=lincoln' in req['url']


def test_get_service_planner_upcoming(core_client: FordPassClient) -> None:
    req = core_client.get_service_planner_upcoming(vin=_VIN, odometer=12345, uom='mi')
    assert req['method'] == 'GET'
    assert '/fpcpl-service-planner/service-actions/planner-summary' in req['url']
    assert 'odometer=12345' in req['url']
    assert 'uom=mi' in req['url']
    assert req['headers']['vin'] == _VIN


def test_get_service_planner_upcoming_no_odometer(core_client: FordPassClient) -> None:
    req = core_client.get_service_planner_upcoming(vin=_VIN)
    assert 'odometer' not in req['url']


def test_get_service_planner_history(core_client: FordPassClient) -> None:
    req = core_client.get_service_planner_history(vin=_VIN, odometer=12345, uom='km')
    assert req['method'] == 'GET'
    assert '/fpcpl-service-planner/v1/completed-service-actions/planner-summary' in req['url']


def test_get_service_action_detail(core_client: FordPassClient) -> None:
    req = core_client.get_service_action_detail('ACT_X', vin=_VIN, odometer=12345)
    assert 'ACT_X' in req['url']
    assert req['headers']['vin'] == _VIN


def test_get_completed_service_action_detail(core_client: FordPassClient) -> None:
    req = core_client.get_completed_service_action_detail('EVT_Y', vin=_VIN)
    assert 'EVT_Y' in req['url']


def test_get_mmota_details(core_client: FordPassClient) -> None:
    req = core_client.get_mmota_details(_VIN)
    assert req['method'] == 'GET'
    assert '/api/mmota/v2/details' in req['url']
    assert f'vin={_VIN}' in req['url']


def test_get_release_notes(core_client: FordPassClient) -> None:
    req = core_client.get_release_notes('https://example.test/notes/1')
    assert req['method'] == 'GET'
    assert '/api/expvsureleasenotes/v2/details' in req['url']
    assert req['headers']['releaseNotesUrl'] == 'https://example.test/notes/1'


def test_get_dealer_by_pa_code(core_client: FordPassClient) -> None:
    req = core_client.get_dealer_by_pa_code('P00001')
    assert req['method'] == 'POST'
    assert '/api/dealersearch/v2/dealer' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['pa_code'] == 'P00001'
    assert body['brand'] == 'ford'
    assert body['language'] == 'en'


def test_get_dealer_by_pa_code_with_brand(core_client: FordPassClient) -> None:
    req = core_client.get_dealer_by_pa_code('P00001', brand='lincoln')
    body = json.loads(req['data'] or '{}')
    assert body['brand'] == 'lincoln'


def test_get_roadside_symptoms_ford(core_client: FordPassClient) -> None:
    req = core_client.get_roadside_symptoms(is_bev=False)
    assert req['method'] == 'GET'
    assert 'isBEV=false' in req['url']
    assert req['headers']['x-source'] == 'stub-x-source-ford'


def test_get_roadside_symptoms_bev(core_client: FordPassClient) -> None:
    req = core_client.get_roadside_symptoms(is_bev=True)
    assert 'isBEV=true' in req['url']


def test_get_roadside_location_types(core_client: FordPassClient) -> None:
    req = core_client.get_roadside_location_types()
    assert req['method'] == 'GET'
    assert '/api/roadsideassistancena/v1/locationtypes' in req['url']


def test_get_roadside_active_event_single_vin(core_client: FordPassClient) -> None:
    req = core_client.get_roadside_active_event(_VIN)
    assert req['method'] == 'GET'
    assert f'vins={_VIN}' in req['url']


def test_get_roadside_active_event_multiple_vins(core_client: FordPassClient) -> None:
    req = core_client.get_roadside_active_event(['VIN_A', 'VIN_B'])
    assert 'vins=VIN_A%2CVIN_B' in req['url']


def test_predraft_roadside_event(core_client: FordPassClient) -> None:
    req = core_client.predraft_roadside_event(_VIN, customer_name='Alice', customer_phone='555-X')
    assert req['method'] == 'PUT'
    body = json.loads(req['data'] or '{}')
    assert body['vin'] == _VIN
    assert body['customer']['name'] == 'Alice'
    assert body['customer']['phone'] == '555-X'


def test_list_drivers(core_client: FordPassClient) -> None:
    req = core_client.list_drivers(_VIN)
    assert req['method'] == 'POST'
    assert '/getAuthorizedUsers' in req['url']
    body = json.loads(req['data'] or '{}')
    assert body['vin'] == _VIN


def test_get_authorized_user_count(core_client: FordPassClient) -> None:
    req = core_client.get_authorized_user_count(_VIN)
    assert req['method'] == 'POST'
    assert '/authorized-user-count' in req['url']


def test_invite_driver(core_client: FordPassClient) -> None:
    req = core_client.invite_driver(_VIN,
                                    secondary_email='friend@example.com',
                                    inviter_first_name='Bob',
                                    vehicle_display_name='F-150')
    assert req['method'] == 'POST'
    body = json.loads(req['data'] or '{}')
    assert body['secondaryEmail'] == 'friend@example.com'
    assert body['userFirstName'] == 'Bob'
    assert body['vehicleName'] == 'F-150'


def test_roadside_x_source_lincoln_brand(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config, brand='lincoln', cat='STUB_CAT')
    req = client.get_roadside_symptoms()
    assert req['headers']['x-source'] == 'stub-x-source-lincoln'


def test_roadside_x_source_unknown_brand(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config, brand='tesla', cat='STUB_CAT')
    with pytest.raises(RuntimeError, match='Unsupported brand'):
        client.get_roadside_symptoms()


def test_ford_headers_have_application_id_and_auth(core_client: FordPassClient) -> None:
    req = core_client.list_garage()
    assert req['headers']['application-id'] == 'STUB_APP_ID'
    assert req['headers']['auth-token'] == 'STUB_CAT'


def test_ford_headers_require_cat(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config)
    with pytest.raises(RuntimeError, match='cat is unset'):
        client.list_garage()


def test_tmc_command_requires_tmc(stub_api_config: APIConfig) -> None:
    client = FordPassClient(api_config=stub_api_config, cat='STUB_CAT')
    with pytest.raises(RuntimeError, match='tmc is unset'):
        client.remote_start(_VIN)


def test_country_header_casing_for_alerts(core_client: FordPassClient) -> None:
    req = core_client.get_alerts(_VIN)
    # The alerts endpoint uses camelCase `countryCode`, not the default `country-code`.
    assert 'countryCode' in req['headers']
    assert req['headers']['countryCode'] == 'USA'


def test_country_header_casing_for_service_planner(core_client: FordPassClient) -> None:
    req = core_client.get_service_planner_upcoming(vin=_VIN)
    assert req['headers']['countrycode'] == 'USA'


def test_country_header_casing_for_vehicle_update(core_client: FordPassClient) -> None:
    req = core_client.update_vehicle_details(_VIN, nick_name='X')
    assert req['headers']['Country-Code'] == 'USA'
