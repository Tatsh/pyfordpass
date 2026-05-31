from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.main import fordpass

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner


def test_config_dump_includes_injected_defaults(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('config', 'dump'))
    assert result.exit_code == 0
    assert '[units]' in result.output
    assert 'format = "pretty"' in result.output
    assert 'impersonate = "chrome146"' in result.output


def test_config_dump_json(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('config', 'dump', '--json'))
    assert result.exit_code == 0
    assert '"units"' in result.output


def test_config_set_writes_value(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(fordpass, ('config', 'set', 'vehicle.default_vin', '1FT00000000000000'))
    assert result.exit_code == 0
    assert 'default_vin = "1FT00000000000000"' in (tmp_path / 'config' / 'config.toml').read_text()


def test_config_set_then_dump_roundtrip(runner: CliRunner) -> None:
    set_result = runner.invoke(fordpass,
                               ('config', 'set', 'vehicle.default_vin', '1FT00000000000000'))
    assert set_result.exit_code == 0
    result = runner.invoke(fordpass, ('config', 'dump'))
    assert result.exit_code == 0
    assert '1FT00000000000000' in result.output


def test_config_delete_removes_value(runner: CliRunner, tmp_path: Path) -> None:
    config_file = tmp_path / 'config' / 'config.toml'
    config_file.write_text("[units]\ndistance = 'km'\n")
    result = runner.invoke(fordpass, ('config', 'delete', 'units.distance'))
    assert result.exit_code == 0
    assert 'distance' not in config_file.read_text()


def test_config_delete_missing_key_fails(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('config', 'delete', 'units.distance'))
    assert result.exit_code != 0
    assert 'Key not found' in result.output


def test_config_reset_removes_file(runner: CliRunner, tmp_path: Path) -> None:
    config_file = tmp_path / 'config' / 'config.toml'
    config_file.write_text("[units]\ndistance = 'km'\n")
    result = runner.invoke(fordpass, ('config', 'reset'))
    assert result.exit_code == 0
    assert not config_file.exists()


def test_config_reset_when_absent(runner: CliRunner) -> None:
    result = runner.invoke(fordpass, ('config', 'reset'))
    assert result.exit_code == 0
    assert 'No configuration file' in result.output
