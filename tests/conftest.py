"""Configuration for Pytest."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn
from unittest.mock import MagicMock
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
    session = mocker.MagicMock()
    session.request = mocker.AsyncMock(return_value=_make_response(json_body={'ok': True}))
    session.close = mocker.AsyncMock()
    return session


@pytest.fixture
def fake_auth_session(mocker: MockerFixture) -> MagicMock:
    session = mocker.MagicMock()
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
