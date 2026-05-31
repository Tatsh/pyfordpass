from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.api_config import API_CONFIG_FILE, DEFAULT_API_CONFIG, load_api_config

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_STUB_TOML = """application_id = 'STUB_APP_ID'
user_agent = 'STUB_USER_AGENT'
profile_groups_default = 'STUB_PROFILE_GROUPS'

[hosts]
foundational = 'https://stub-foundational.example'
login = 'https://stub-login.example'
tmc = 'https://stub-tmc.example'
tmc_accounts = 'https://stub-tmc-accounts.example'
vehicle = 'https://stub-vehicle.example'

[auth.b2c]
client_id = 'STUB_B2C_CLIENT'
policy_template = 'B2C_1A_{locale}_STUB'
redirect_uri = 'stub://callback'
tenant_id = 'stub-tenant'

[auth.tmc]
client_id = 'STUB_TMC_CLIENT'

[roadside.x_source]
ford = 'stub-x-source-ford'
lincoln = 'stub-x-source-lincoln'
"""


def test_api_config_file_name() -> None:
    assert API_CONFIG_FILE.name == 'api.toml'


def test_load_api_config_defaults_when_file_absent(tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.api_config.API_CONFIG_FILE', tmp_path / 'no-such-file.toml')
    assert load_api_config() == DEFAULT_API_CONFIG


def test_load_api_config_full_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'api.toml'
    path.write_text(_STUB_TOML)
    monkeypatch.setattr('fordpass.api_config.API_CONFIG_FILE', path)
    api_config = load_api_config()
    assert api_config['application_id'] == 'STUB_APP_ID'
    assert api_config['user_agent'] == 'STUB_USER_AGENT'
    assert api_config['profile_groups_default'] == 'STUB_PROFILE_GROUPS'
    assert api_config['hosts']['foundational'] == 'https://stub-foundational.example'
    assert api_config['hosts']['login'] == 'https://stub-login.example'
    assert api_config['hosts']['tmc'] == 'https://stub-tmc.example'
    assert api_config['hosts']['tmc_accounts'] == 'https://stub-tmc-accounts.example'
    assert api_config['hosts']['vehicle'] == 'https://stub-vehicle.example'
    assert api_config['auth']['b2c']['client_id'] == 'STUB_B2C_CLIENT'
    assert api_config['auth']['b2c']['policy_template'] == 'B2C_1A_{locale}_STUB'
    assert api_config['auth']['b2c']['redirect_uri'] == 'stub://callback'
    assert api_config['auth']['b2c']['tenant_id'] == 'stub-tenant'
    assert api_config['auth']['tmc']['client_id'] == 'STUB_TMC_CLIENT'
    assert api_config['roadside']['x_source']['ford'] == 'stub-x-source-ford'
    assert api_config['roadside']['x_source']['lincoln'] == 'stub-x-source-lincoln'


def test_load_api_config_partial_override_merges(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'api.toml'
    path.write_text("user_agent = 'PATCHED_AGENT'\n\n[hosts]\nlogin = 'https://patched.example'\n")
    monkeypatch.setattr('fordpass.api_config.API_CONFIG_FILE', path)
    api_config = load_api_config()
    assert api_config['user_agent'] == 'PATCHED_AGENT'
    assert api_config['hosts']['login'] == 'https://patched.example'
    assert api_config['application_id'] == DEFAULT_API_CONFIG['application_id']
    assert api_config['hosts']['vehicle'] == DEFAULT_API_CONFIG['hosts']['vehicle']
    assert api_config['auth']['b2c']['tenant_id'] == DEFAULT_API_CONFIG['auth']['b2c']['tenant_id']


def test_load_api_config_does_not_mutate_defaults(tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'api.toml'
    path.write_text("[hosts]\nlogin = 'https://patched.example'\n")
    monkeypatch.setattr('fordpass.api_config.API_CONFIG_FILE', path)
    load_api_config()
    assert DEFAULT_API_CONFIG['hosts']['login'] == 'https://login.ford.com'
