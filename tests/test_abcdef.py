from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.abcdef import SECRETS_FILE, load_secrets
import pytest

if TYPE_CHECKING:
    from pathlib import Path

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


def test_secrets_file_name() -> None:
    assert SECRETS_FILE.name == 'abcdef.toml'


def test_load_secrets_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'abcdef.toml'
    path.write_text(_STUB_TOML)
    monkeypatch.setattr('fordpass.abcdef.SECRETS_FILE', path)
    secrets = load_secrets()
    assert secrets['application_id'] == 'STUB_APP_ID'
    assert secrets['user_agent'] == 'STUB_USER_AGENT'
    assert secrets['profile_groups_default'] == 'STUB_PROFILE_GROUPS'
    assert secrets['hosts']['foundational'] == 'https://stub-foundational.example'
    assert secrets['hosts']['login'] == 'https://stub-login.example'
    assert secrets['hosts']['tmc'] == 'https://stub-tmc.example'
    assert secrets['hosts']['tmc_accounts'] == 'https://stub-tmc-accounts.example'
    assert secrets['hosts']['vehicle'] == 'https://stub-vehicle.example'
    assert secrets['auth']['b2c']['client_id'] == 'STUB_B2C_CLIENT'
    assert secrets['auth']['b2c']['policy_template'] == 'B2C_1A_{locale}_STUB'
    assert secrets['auth']['b2c']['redirect_uri'] == 'stub://callback'
    assert secrets['auth']['b2c']['tenant_id'] == 'stub-tenant'
    assert secrets['auth']['tmc']['client_id'] == 'STUB_TMC_CLIENT'
    assert secrets['roadside']['x_source']['ford'] == 'stub-x-source-ford'
    assert secrets['roadside']['x_source']['lincoln'] == 'stub-x-source-lincoln'


def test_load_secrets_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.abcdef.SECRETS_FILE', tmp_path / 'no-such-file.toml')
    with pytest.raises(RuntimeError, match='Constants file not found'):
        load_secrets()


def test_load_secrets_missing_top_level_key(tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'abcdef.toml'
    path.write_text("user_agent = 'X'\n")
    monkeypatch.setattr('fordpass.abcdef.SECRETS_FILE', path)
    with pytest.raises(RuntimeError, match='application_id'):
        load_secrets()


def test_load_secrets_missing_nested_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'abcdef.toml'
    path.write_text("""application_id = 'A'
user_agent = 'U'
profile_groups_default = 'P'

[hosts]
foundational = 'h1'
""")
    monkeypatch.setattr('fordpass.abcdef.SECRETS_FILE', path)
    with pytest.raises(RuntimeError, match=r'hosts\.login'):
        load_secrets()


def test_load_secrets_non_mapping_at_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'abcdef.toml'
    path.write_text("""application_id = 'A'
user_agent = 'U'
profile_groups_default = 'P'

[hosts]
foundational = 'h1'
login = 'h2'
tmc = 'h3'
tmc_accounts = 'h4'
vehicle = 'h5'

[auth]
b2c = 'not-a-table'
""")
    monkeypatch.setattr('fordpass.abcdef.SECRETS_FILE', path)
    with pytest.raises(RuntimeError, match=r'auth\.b2c\.client_id'):
        load_secrets()
