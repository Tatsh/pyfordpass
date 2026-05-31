"""Tests for the public helpers in fordpass.commands.utils."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfoNotFoundError
import asyncio
import json
import threading

from fordpass.commands.utils import (
    Readiness,
    assert_ready_or_abort,
    check_readiness,
    duration_range,
    ensure_signed_in,
    format_ford_request_date,
    format_iso_date,
    format_iso_datetime,
    format_iso_time,
    install_loop,
    interactive_signin,
    load_tokens,
    make_client,
    parse_user_datetime,
    parse_user_days,
    parse_user_timezone,
    persist_tokens,
    run_async,
    save_tokens,
    should_emit_json,
    validate_message_ids_exist,
    validate_vin,
)
from fordpass.main import fordpass
import click
import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner
    from pytest_mock import MockerFixture

_VIN = '1FAHP00000A000000'

# `validate_vin` ignores its first two args (they're prefixed `_ctx`, `_param`); passing None at
# the call sites needs casts to satisfy the Click-derived parameter annotations.
_NULL_CTX = cast('click.Context', None)
_NULL_PARAM = cast('click.Parameter', None)


def test_load_tokens_when_file_missing() -> None:
    assert load_tokens() == {}


def test_save_tokens_then_load(tmp_path: Path, mocker: MockerFixture) -> None:
    token_file = tmp_path / 'tokens.json'
    mocker.patch('fordpass.commands.utils.TOKEN_FILE', token_file)
    save_tokens({'cat': 'A', 'cat_refresh': 'B', 'tmc': 'C'})
    assert token_file.exists()
    assert load_tokens() == {'cat': 'A', 'cat_refresh': 'B', 'tmc': 'C'}


def test_persist_tokens(mocker: MockerFixture, tmp_path: Path) -> None:
    token_file = tmp_path / 'tokens.json'
    mocker.patch('fordpass.commands.utils.TOKEN_FILE', token_file)
    client = MagicMock()
    client.cat = 'X'
    client.cat_refresh = 'Y'
    client.tmc = 'Z'
    persist_tokens(client)
    assert token_file.exists()
    assert json.loads(token_file.read_text()) == {'cat': 'X', 'cat_refresh': 'Y', 'tmc': 'Z'}


def test_validate_vin_accepts_valid() -> None:
    assert validate_vin(_NULL_CTX, _NULL_PARAM, _VIN) == _VIN


def test_validate_vin_passes_none_through() -> None:
    assert validate_vin(_NULL_CTX, _NULL_PARAM, None) is None


def test_validate_vin_rejects_bad_charset() -> None:
    with pytest.raises(click.BadParameter, match='not a valid'):
        validate_vin(_NULL_CTX, _NULL_PARAM, 'IOQ12345678901234')


def test_validate_vin_rejects_check_digit() -> None:
    with pytest.raises(click.BadParameter, match='check-digit'):
        validate_vin(_NULL_CTX, _NULL_PARAM, '1FA12345678901234')


def test_should_emit_json_true_when_flag_set(mocker: MockerFixture) -> None:
    assert should_emit_json(as_json=True) is True


def test_should_emit_json_default(mocker: MockerFixture) -> None:
    assert should_emit_json(as_json=False) is False


def test_duration_range() -> None:
    rng = duration_range(1, 10)
    assert rng.min == 1
    assert rng.max == 10


def test_format_iso_datetime_with_z() -> None:
    out = format_iso_datetime('2026-05-30T07:00:00Z')
    assert len(out) == len('2026-05-30 07:00')


def test_format_iso_datetime_with_offset() -> None:
    out = format_iso_datetime('2026-05-30T07:00:00+00:00')
    assert ':' in out


def test_format_iso_datetime_naive() -> None:
    out = format_iso_datetime('2026-05-30T07:00:00')
    assert '2026' in out


def test_format_iso_datetime_bad_input_string() -> None:
    assert format_iso_datetime('not a date') == 'not a date'


def test_format_iso_datetime_non_string() -> None:
    assert format_iso_datetime(None) == '-'
    assert format_iso_datetime(42) == '-'
    assert format_iso_datetime('') == '-'


def test_format_iso_date() -> None:
    assert format_iso_date('2026-05-30T07:00:00Z') == '2026-05-30'


def test_format_iso_date_missing() -> None:
    assert format_iso_date(None) == '-'


def test_format_iso_time() -> None:
    assert format_iso_time('2026-05-30T07:00:00+00:00').count(':') == 1


def test_format_iso_time_missing() -> None:
    assert format_iso_time(None) == '-'


def test_parse_user_datetime_iso_full() -> None:
    dt = parse_user_datetime('2026-05-30T07:00:00+00:00')
    assert dt.year == 2026
    assert dt.tzinfo is not None


def test_parse_user_datetime_with_z() -> None:
    dt = parse_user_datetime('2026-05-30T07:00:00Z')
    assert dt.tzinfo == timezone.utc


def test_parse_user_datetime_naive_attaches_local_tz() -> None:
    dt = parse_user_datetime('2026-05-30T07:00:00')
    assert dt.tzinfo is not None


def test_parse_user_datetime_date_only() -> None:
    dt = parse_user_datetime('2026-05-30')
    assert dt.year == 2026


def test_parse_user_datetime_invalid() -> None:
    with pytest.raises(Exception, match='ISO 8601'):
        parse_user_datetime('not a date')


def test_parse_user_days_full_names() -> None:
    out = parse_user_days('monday,tuesday,thursday')
    assert out == {'sun': 0, 'mon': 1, 'tue': 1, 'wed': 0, 'thu': 1, 'fri': 0, 'sat': 0}


def test_parse_user_days_abbr() -> None:
    out = parse_user_days('mon,tue,thu')
    assert out['mon'] == 1
    assert out['thu'] == 1
    assert out['fri'] == 0


def test_parse_user_days_letter_run() -> None:
    out = parse_user_days('mwf')
    assert out == {'sun': 0, 'mon': 1, 'tue': 0, 'wed': 1, 'thu': 0, 'fri': 1, 'sat': 0}


def test_parse_user_days_letters_split() -> None:
    out = parse_user_days('M T Th')
    assert out['mon'] == 1
    assert out['thu'] == 1


def test_parse_user_days_empty() -> None:
    out = parse_user_days('')
    assert out == {'sun': 0, 'mon': 0, 'tue': 0, 'wed': 0, 'thu': 0, 'fri': 0, 'sat': 0}


def test_parse_user_days_unrecognised() -> None:
    with pytest.raises(Exception, match='not a recognised day'):
        parse_user_days('blursday')


def test_parse_user_timezone_integer_pass_through() -> None:
    assert parse_user_timezone('85') == 85


def test_parse_user_timezone_negative_integer() -> None:
    assert parse_user_timezone('-1') == -1


def test_parse_user_timezone_iana() -> None:
    code = parse_user_timezone('America/New_York')
    assert isinstance(code, int)


def test_parse_user_timezone_rejects_offset() -> None:
    with pytest.raises(Exception, match='UTC offset'):
        parse_user_timezone('+05:00')


def test_parse_user_timezone_unknown_iana() -> None:
    with pytest.raises(Exception, match='IANA'):
        parse_user_timezone('Not/AReal/Tz')


def test_parse_user_timezone_iana_no_ford_code() -> None:
    # `Etc/GMT-1` is a real ZoneInfo but typically not in the Ford zone map.
    with pytest.raises(Exception, match='No Ford zone code'):
        parse_user_timezone('Etc/GMT-1')


def test_format_ford_request_date_morning() -> None:
    dt = datetime(2026, 5, 28, 1, 50, 0, tzinfo=timezone.utc)
    assert format_ford_request_date(dt) == '5-28-2026 1:50:00 AM'


def test_format_ford_request_date_afternoon() -> None:
    dt = datetime(2026, 5, 28, 13, 50, 0, tzinfo=timezone.utc)
    assert format_ford_request_date(dt) == '5-28-2026 1:50:00 PM'


def test_format_ford_request_date_midnight() -> None:
    dt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert format_ford_request_date(dt) == '1-1-2026 12:00:00 AM'


def test_format_ford_request_date_noon() -> None:
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert format_ford_request_date(dt) == '1-1-2026 12:00:00 PM'


async def test_validate_message_ids_exist_happy(mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {
        'result': {
            'messages': [{
                'messageId': '1'
            }, {
                'messageId': '2'
            }]
        }
    }
    await validate_message_ids_exist(mock_command_client, [1, 2])


async def test_validate_message_ids_exist_missing(mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {'result': {'messages': [{'messageId': '1'}]}}
    with pytest.raises(Exception, match='not in inbox'):
        await validate_message_ids_exist(mock_command_client, [1, 99])


async def test_validate_message_ids_exist_empty_inbox(mock_command_client: MagicMock) -> None:
    mock_command_client.get_messages.return_value = {'result': {'messages': []}}
    with pytest.raises(click.ClickException, match='not in inbox'):
        await validate_message_ids_exist(mock_command_client, [1])


async def test_validate_message_ids_exist_non_mapping_items_skipped(
        mock_command_client: MagicMock) -> None:
    # Exercises the `if not isinstance(m, Mapping): continue` defensive branch.
    mock_command_client.get_messages.return_value = {
        'result': {
            'messages': ['not a mapping', {
                'messageId': '1'
            }]
        }
    }
    await validate_message_ids_exist(mock_command_client, [1])


def test_parse_user_days_consecutive_separators() -> None:
    # Exercises the `if not chunk: continue` branch when separator collapsing leaves empties.
    out = parse_user_days(',,,mon,,,tue,,,')
    assert out['mon'] == 1
    assert out['tue'] == 1


def test_parse_user_timezone_offset_unresolvable(mocker: MockerFixture) -> None:
    # `+05:00` would normally resolve via Etc/GMT-5; forcing ZoneInfoNotFoundError takes the
    # else-branch where _parse_offset_tz returns None and the IANA-lookup path rejects it.
    mocker.patch('fordpass.commands.utils.ZoneInfo', side_effect=ZoneInfoNotFoundError('boom'))
    with pytest.raises(click.BadParameter, match='IANA'):
        parse_user_timezone('+05:00')


async def test_check_readiness_ok(mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'metrics': {
            'batteryVoltage': {
                'value': 12.6
            },
            'batteryStateOfCharge': {
                'value': 92.0
            },
            'batteryLoadStatus': {
                'value': 'OK'
            },
            'vehicleLifeCycleMode': {
                'value': 'NORMAL'
            }
        },
        'states': {},
        'events': {}
    }
    result = await check_readiness(mock_command_client, _VIN)
    assert result.ok is True
    assert result.life_cycle_mode == 'NORMAL'
    assert result.voltage == pytest.approx(12.6)


async def test_check_readiness_blocked(mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {
        'metrics': {},
        'states': {
            'commandPreclusion': {
                'value': {
                    'data': {
                        'commandPreclusionCauses': {
                            'deepSleepCommandPreclusionState': 'COMMANDS_PRECLUDED_BY_DEEP_SLEEP'
                        }
                    }
                }
            }
        },
        'events': {
            'batteryEvent': {
                'conditions': {
                    'lowBatteryCharge': True
                }
            }
        }
    }
    result = await check_readiness(mock_command_client, _VIN)
    assert result.ok is False
    assert any('Battery Saver' in r for r in result.reasons)
    assert 'lowBatteryCharge' in result.battery_conditions


async def test_check_readiness_empty_response(mock_command_client: MagicMock) -> None:
    mock_command_client.query_telemetry.return_value = {}
    result = await check_readiness(mock_command_client, _VIN)
    assert result.ok is True
    assert result.voltage is None


async def test_assert_ready_or_abort_force_skips(mock_command_client: MagicMock) -> None:
    await assert_ready_or_abort(mock_command_client, _VIN, force=True)


async def test_assert_ready_or_abort_ok(mocker: MockerFixture,
                                        mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.utils.check_readiness',
                 new_callable=mocker.AsyncMock,
                 return_value=Readiness(battery_conditions=(),
                                        life_cycle_mode='NORMAL',
                                        load_status='OK',
                                        ok=True,
                                        raw={},
                                        reasons=(),
                                        state_of_charge=92.0,
                                        voltage=12.6))
    await assert_ready_or_abort(mock_command_client, _VIN, force=False)


async def test_assert_ready_or_abort_blocked(mocker: MockerFixture,
                                             mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.utils.check_readiness',
                 new_callable=mocker.AsyncMock,
                 return_value=Readiness(battery_conditions=(),
                                        life_cycle_mode='DEEP_SLEEP',
                                        load_status='UNKNOWN',
                                        ok=False,
                                        raw={'state': 'X'},
                                        reasons=('Battery Saver mode',),
                                        state_of_charge=None,
                                        voltage=None))
    import click
    with pytest.raises(click.Abort):
        await assert_ready_or_abort(mock_command_client, _VIN, force=False)


def test_install_loop_lets_run_async_dispatch(mocker: MockerFixture) -> None:
    async def task() -> int:
        await asyncio.sleep(0)
        return 42

    loop = asyncio.new_event_loop()
    install_loop(loop)
    try:
        thread = threading.Thread(target=loop.run_forever)
        thread.start()
        result = run_async(task())
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
    finally:
        loop.close()
        # Reset the module-level loop so subsequent tests aren't using a closed one.
        mocker.patch('fordpass.commands.utils._LOOP', None)
    assert result == 42


def test_run_async_without_install_raises(mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.utils._LOOP', None)

    async def task() -> int:
        await asyncio.sleep(0)
        return 1

    coro = task()
    with pytest.raises(RuntimeError, match='Event loop'):
        run_async(coro)
    coro.close()


async def test_ensure_signed_in_when_already_signed_in() -> None:
    client = MagicMock()
    client.cat = 'X'
    ctx = MagicMock()
    await ensure_signed_in(client, ctx)


async def test_ensure_signed_in_when_not_signed_in_runs_interactive(mocker: MockerFixture) -> None:
    interactive = mocker.patch('fordpass.commands.utils.interactive_signin', new_callable=AsyncMock)
    mocker.patch('fordpass.commands.utils.click.confirm', return_value=True)
    client = MagicMock()
    client.cat = None
    ctx = MagicMock()
    await ensure_signed_in(client, ctx)
    interactive.assert_awaited_once()


async def test_ensure_signed_in_user_declines(mocker: MockerFixture) -> None:
    interactive = mocker.patch('fordpass.commands.utils.interactive_signin', new_callable=AsyncMock)
    mocker.patch('fordpass.commands.utils.click.confirm', return_value=False)
    client = MagicMock()
    client.cat = None
    ctx = MagicMock()
    ctx.exit.side_effect = SystemExit(1)
    with pytest.raises(SystemExit):
        await ensure_signed_in(client, ctx)
    ctx.exit.assert_called_once_with(1)
    interactive.assert_not_called()


def test_make_client_default_construction(mocker: MockerFixture) -> None:
    fake_client = MagicMock()
    mocker.patch('fordpass.commands.utils.load_tokens',
                 return_value={
                     'cat': 'A',
                     'cat_refresh': 'B',
                     'tmc': 'C'
                 })
    mocker.patch('fordpass.commands.utils.AsyncFordPassClient', return_value=fake_client)
    result = make_client()
    assert result is fake_client


def test_with_client_persists_when_tokens_change(runner: CliRunner, mocker: MockerFixture,
                                                 mock_command_client: MagicMock) -> None:
    # The mock_command_client fixture already starts with all three tokens set; flipping cat
    # mid-command should trigger persist_tokens via the with_client wrapper.
    persist = mocker.patch('fordpass.commands.utils.persist_tokens')

    async def changing_get_alerts(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        await asyncio.sleep(0)
        mock_command_client.cat = 'NEW_CAT'
        return {'alerts': []}

    mock_command_client.get_alerts = AsyncMock(side_effect=changing_get_alerts)
    result = runner.invoke(fordpass, ('alerts', 'current', _VIN))
    assert result.exit_code == 0
    assert persist.called


async def test_interactive_signin_happy(mocker: MockerFixture,
                                        mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.utils.click.prompt',
                 return_value='fordapp://userauthorized?code=AUTHZ_CODE_X')
    mock_command_client.b2c_authorize_url = MagicMock(
        return_value='https://stub-login.example/authorize')
    mock_command_client.exchange_b2c_code = AsyncMock(return_value={'access_token': 'B2C_X'})
    mock_command_client.mint_cat_from_b2c = AsyncMock(return_value={})
    mock_command_client.exchange_cat_for_tmc = AsyncMock(return_value={})
    await interactive_signin(mock_command_client)
    mock_command_client.exchange_b2c_code.assert_awaited_once()
    mock_command_client.mint_cat_from_b2c.assert_awaited_once_with(b2c_access_token='B2C_X')
    mock_command_client.exchange_cat_for_tmc.assert_awaited_once()


async def test_interactive_signin_decodes_kid(mocker: MockerFixture,
                                              mock_command_client: MagicMock) -> None:
    import base64
    header = base64.urlsafe_b64encode(b'{"kid":"KID_X"}').rstrip(b'=').decode()
    fake_code = f'{header}.payload.sig'
    mocker.patch('fordpass.commands.utils.click.prompt',
                 return_value=f'fordapp://userauthorized?code={fake_code}')
    mock_command_client.b2c_authorize_url = MagicMock(return_value='url')
    mock_command_client.exchange_b2c_code = AsyncMock(return_value={'access_token': 'B2C_X'})
    mock_command_client.mint_cat_from_b2c = AsyncMock(return_value={})
    mock_command_client.exchange_cat_for_tmc = AsyncMock(return_value={})
    await interactive_signin(mock_command_client)
    mock_command_client.exchange_b2c_code.assert_awaited_once()


async def test_interactive_signin_missing_code(mocker: MockerFixture,
                                               mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.utils.click.prompt',
                 return_value='fordapp://userauthorized?other=X')
    mock_command_client.b2c_authorize_url = MagicMock(return_value='url')
    with pytest.raises(click.ClickException, match='No `code='):
        await interactive_signin(mock_command_client)


async def test_interactive_signin_b2c_returns_no_token(mocker: MockerFixture,
                                                       mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.utils.click.prompt',
                 return_value='fordapp://userauthorized?code=X')
    mock_command_client.b2c_authorize_url = MagicMock(return_value='url')
    mock_command_client.exchange_b2c_code = AsyncMock(return_value={})
    with pytest.raises(click.ClickException, match='no access_token'):
        await interactive_signin(mock_command_client)


def test_parse_user_timezone_local_falls_back_to_system(mocker: MockerFixture) -> None:
    fake_zone = MagicMock()
    fake_zone.key = 'America/New_York'
    fake_now = MagicMock()
    fake_now.astimezone.return_value.tzinfo = fake_zone
    fake_datetime = mocker.patch('fordpass.commands.utils.datetime')
    fake_datetime.now.return_value = fake_now
    assert parse_user_timezone('local') == parse_user_timezone('America/New_York')


def test_parse_user_timezone_system_no_iana(mocker: MockerFixture) -> None:
    fake_zone = MagicMock(spec=[])  # No `key` attribute.
    fake_now = MagicMock()
    fake_now.astimezone.return_value.tzinfo = fake_zone
    fake_datetime = mocker.patch('fordpass.commands.utils.datetime')
    fake_datetime.now.return_value = fake_now
    with pytest.raises(click.BadParameter, match='system timezone'):
        parse_user_timezone('local')


def test_parse_user_timezone_offset_with_minutes_skipped() -> None:
    # `+05:30` has non-zero minutes - the parser returns None, treated as "not an offset",
    # then the IANA-lookup path takes over and rejects unknown IANA names.
    with pytest.raises(click.BadParameter, match='IANA'):
        parse_user_timezone('+05:30')


def test_parse_user_days_unknown_letter() -> None:
    with pytest.raises(click.BadParameter, match='not a recognised day'):
        parse_user_days('xyz')


def test_vin_argument_falls_back_to_config_default(runner: CliRunner, mocker: MockerFixture,
                                                   mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.utils.load_config',
                 return_value={'vehicle': {
                     'default_vin': _VIN
                 }})
    mock_command_client.get_alerts.return_value = {'alerts': []}
    result = runner.invoke(fordpass, ('alerts', 'current'))
    assert result.exit_code == 0


def test_vin_argument_no_value_no_config(runner: CliRunner, mocker: MockerFixture,
                                         mock_command_client: MagicMock) -> None:
    mocker.patch('fordpass.commands.utils.load_config', return_value={'vehicle': {}})
    result = runner.invoke(fordpass, ('alerts', 'current'))
    assert result.exit_code != 0
    assert 'VIN is required' in result.output
