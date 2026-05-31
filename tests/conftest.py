"""Configuration for Pytest."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, NoReturn
import os

from click.testing import CliRunner
from fordpass.sansio import FordPassClient
import pytest

if TYPE_CHECKING:
    from fordpass.typing import Secrets

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
    from fordpass.abcdef import load_secrets
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
