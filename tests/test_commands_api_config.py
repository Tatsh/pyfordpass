from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.main import fordpass

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner


def test_api_config_dump_shows_defaults(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('api-config', 'dump'))
    assert result.exit_code == 0
    assert 'login = "https://login.ford.com"' in result.output
    assert 'user_agent = "okhttp/4.12.0"' in result.output


def test_api_config_dump_json(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('api-config', 'dump', '--json'))
    assert result.exit_code == 0
    assert '"hosts"' in result.output


def test_api_config_set_writes_override(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(fordpass, ('api-config', 'set', 'hosts.login', 'https://example.test'))
    assert result.exit_code == 0
    assert 'login = "https://example.test"' in (tmp_path / 'config' / 'api.toml').read_text()


def test_api_config_set_then_dump_merges_over_defaults(runner: CliRunner) -> None:
    set_result = runner.invoke(fordpass,
                               ('api-config', 'set', 'hosts.login', 'https://example.test'))
    assert set_result.exit_code == 0
    result = runner.invoke(fordpass, ('api-config', 'dump'))
    assert result.exit_code == 0
    assert 'https://example.test' in result.output
    assert 'user_agent = "okhttp/4.12.0"' in result.output


def test_api_config_delete_removes_override(runner: CliRunner, tmp_path: Path) -> None:
    api_file = tmp_path / 'config' / 'api.toml'
    api_file.write_text("user_agent = 'custom'\n")
    result = runner.invoke(fordpass, ('api-config', 'delete', 'user_agent'))
    assert result.exit_code == 0
    assert 'custom' not in api_file.read_text()


def test_api_config_delete_missing_key_fails(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('api-config', 'delete', 'hosts.login'))
    assert result.exit_code != 0
    assert 'Key not found' in result.output


def test_api_config_reset_removes_file(runner: CliRunner, tmp_path: Path) -> None:
    api_file = tmp_path / 'config' / 'api.toml'
    api_file.write_text("user_agent = 'custom'\n")
    result = runner.invoke(fordpass, ('api-config', 'reset'))
    assert result.exit_code == 0
    assert not api_file.exists()


def test_api_config_reset_when_absent(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('api-config', 'reset'))
    assert result.exit_code == 0
    assert 'No API configuration file' in result.output
