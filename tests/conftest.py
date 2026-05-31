"""Configuration for Pytest."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn
from unittest.mock import AsyncMock, MagicMock
import asyncio
import json
import os

from click.testing import CliRunner
from fordpass.abcdef import load_secrets
from fordpass.client import AsyncFordPassClient
from fordpass.sansio import FordPassClient
import pytest

if TYPE_CHECKING:
    from fordpass.typing import Secrets
    from pytest_mock import MockerFixture

if os.getenv('_PYTEST_RAISE', '0') != '0':  # pragma no cover

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call: pytest.CallInfo[None]) -> NoReturn:
        assert call.excinfo is not None
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo: pytest.ExceptionInfo[BaseException]) -> NoReturn:
        raise excinfo.value


@pytest.fixture(autouse=True)
def recover_stale_process_cwd(request: pytest.FixtureRequest) -> None:
    """
    Recover when the process cwd was removed mid-session.

    Gentoo Portage test phases often run pytest with aggressive temporary-directory retention.
    The process working directory can then point at a path that no longer exists, so
    ``Path.cwd()`` raises ``FileNotFoundError`` before ``monkeypatch.chdir`` can save the
    prior cwd.
    """
    try:
        Path.cwd()
    except FileNotFoundError:
        os.chdir(Path(request.config.rootpath))


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def clear_module_caches() -> None:
    """Reset `@functools.cache`-decorated public loaders between tests."""
    load_secrets.cache_clear()


@pytest.fixture(autouse=True)
def isolate_platform_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect every `platformdirs`-derived path at a per-test tmp_path subtree.

    Prevents tests from reading or writing the real user config or state directories.
    """
    config_dir = tmp_path / 'config'
    state_dir = tmp_path / 'state'
    config_dir.mkdir()
    state_dir.mkdir()
    monkeypatch.setattr('fordpass.config.CONFIG_DIR', config_dir)
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_dir / 'config.toml')
    monkeypatch.setattr('fordpass.abcdef.SECRETS_FILE', config_dir / 'abcdef.toml')
    monkeypatch.setattr('fordpass.commands.utils.STATE_DIR', state_dir)
    monkeypatch.setattr('fordpass.commands.utils.TOKEN_FILE', state_dir / 'tokens.json')
    monkeypatch.setattr('fordpass.commands.auth.TOKEN_FILE', state_dir / 'tokens.json')


@pytest.fixture
def stub_secrets() -> Secrets:
    return {
        'application_id': 'STUB_APP_ID',
        'user_agent': 'STUB_USER_AGENT',
        'profile_groups_default': 'STUB_PROFILE_GROUPS',
        'hosts': {
            'foundational': 'https://stub-foundational.example',
            'login': 'https://stub-login.example',
            'tmc': 'https://stub-tmc.example',
            'tmc_accounts': 'https://stub-tmc-accounts.example',
            'vehicle': 'https://stub-vehicle.example',
        },
        'auth': {
            'b2c': {
                'client_id': 'STUB_B2C_CLIENT',
                'policy_template': 'B2C_1A_{locale}_STUB',
                'redirect_uri': 'stub://callback',
                'tenant_id': 'stub-tenant',
            },
            'tmc': {
                'client_id': 'STUB_TMC_CLIENT'
            },
        },
        'roadside': {
            'x_source': {
                'ford': 'stub-x-source-ford',
                'lincoln': 'stub-x-source-lincoln'
            }
        },
    }


@pytest.fixture
def core_client(stub_secrets: Secrets) -> FordPassClient:
    return FordPassClient(secrets=stub_secrets,
                          cat='STUB_CAT',
                          cat_refresh='STUB_CAT_REFRESH',
                          tmc='STUB_TMC')


def _make_response(*,
                   status_code: int = 200,
                   json_body: Any = None,
                   content: bytes | None = None,
                   text: str = '') -> MagicMock:
    """Build a MagicMock that mimics niquests.Response / curl_cffi.Response."""
    response = MagicMock()
    response.status_code = status_code
    if content is None:
        content = b'{}' if json_body is None else json.dumps(json_body).encode()
    response.content = content
    response.text = text or content.decode()
    response.json = MagicMock(return_value=json_body if json_body is not None else {})
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def fake_response_factory() -> Any:
    return _make_response


@pytest.fixture
def fake_session(mocker: MockerFixture) -> MagicMock:
    session: MagicMock = mocker.MagicMock()
    session.request = mocker.AsyncMock(return_value=_make_response(json_body={'ok': True}))
    session.close = mocker.AsyncMock()
    return session


@pytest.fixture
def fake_auth_session(mocker: MockerFixture) -> MagicMock:
    session: MagicMock = mocker.MagicMock()
    session.request = mocker.AsyncMock(return_value=_make_response(json_body={
        'access_token': 'NEW_CAT',
        'refresh_token': 'NEW_REFRESH'
    }))
    session.close = mocker.AsyncMock()
    return session


@pytest.fixture
def async_client(stub_secrets: Secrets, fake_session: MagicMock,
                 fake_auth_session: MagicMock) -> AsyncFordPassClient:
    return AsyncFordPassClient(secrets=stub_secrets,
                               cat='STUB_CAT',
                               cat_refresh='STUB_CAT_REFRESH',
                               tmc='STUB_TMC',
                               session=fake_session,
                               auth_session=fake_auth_session)


@pytest.fixture
def mock_command_client(mocker: MockerFixture) -> MagicMock:
    """Patch the Click command harness so tests can drive the CLI without real I/O.

    Returns a `MagicMock(spec=AsyncFordPassClient)` standing in for the real client. Async methods
    discovered by the spec are converted to `AsyncMock` instances so `await client.X(...)`
    resolves to whatever `return_value` the test sets per call.
    """
    client = MagicMock(spec=AsyncFordPassClient)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.cat = 'STUB_CAT'
    client.cat_refresh = 'STUB_CAT_REFRESH'
    client.tmc = 'STUB_TMC'
    client.locale = 'en-US'
    client.country = 'USA'
    for name, attr in vars(AsyncFordPassClient).items():
        if not name.startswith('_') and asyncio.iscoroutinefunction(attr):
            setattr(client, name, AsyncMock(return_value=None))
    mocker.patch('fordpass.commands.utils.make_client', return_value=client)
    mocker.patch('fordpass.commands.utils.ensure_signed_in', new_callable=AsyncMock)
    mocker.patch('fordpass.commands.utils.persist_tokens')
    mocker.patch('fordpass.commands.utils.run_async', side_effect=asyncio.run)
    command_modules = ('alerts', 'auth', 'dealer', 'departure', 'drivers', 'messages', 'ota',
                       'profile', 'remote', 'roadside', 'schedule', 'service', 'telemetry',
                       'vehicle')
    for mod in command_modules:
        mocker.patch(f'fordpass.commands.{mod}.make_client', return_value=client, create=True)
        mocker.patch(f'fordpass.commands.{mod}.ensure_signed_in',
                     new_callable=AsyncMock,
                     create=True)
        mocker.patch(f'fordpass.commands.{mod}.persist_tokens', create=True)
        mocker.patch(f'fordpass.commands.{mod}.run_async', side_effect=asyncio.run, create=True)
    return client
