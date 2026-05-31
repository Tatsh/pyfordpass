from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    KM_PER_MILE,
    KM_TO_MI,
    KPA_PER_PSI,
    KPA_TO_PSI,
    OUTPUT_ENV_VAR,
    load_config,
    resolve_output_format,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_km_per_mile_constant() -> None:
    assert abs(KM_PER_MILE - 1.609344) < 1e-9


def test_km_to_mi_is_reciprocal() -> None:
    assert abs(KM_TO_MI * KM_PER_MILE - 1.0) < 1e-9


def test_kpa_per_psi_constant() -> None:
    assert abs(KPA_PER_PSI - 6.89475729) < 1e-6


def test_kpa_to_psi_is_reciprocal() -> None:
    assert abs(KPA_TO_PSI * KPA_PER_PSI - 1.0) < 1e-6


def test_output_env_var_name() -> None:
    assert OUTPUT_ENV_VAR == 'PYFORDPASS_OUTPUT'


def test_config_dir_pyfordpass_segment() -> None:
    assert CONFIG_DIR.name == 'pyfordpass'


def test_config_file_under_config_dir() -> None:
    assert CONFIG_FILE.parent == CONFIG_DIR
    assert CONFIG_FILE.name == 'config.toml'


def test_load_config_with_no_file_returns_defaults(tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'no-such-file.toml')
    monkeypatch.setenv('LANG', 'en_US.UTF-8')
    monkeypatch.delenv('LC_ALL', raising=False)
    monkeypatch.delenv('LC_MEASUREMENT', raising=False)
    config = load_config()
    assert config['units']['distance'] == 'mi'
    assert config['units']['temperature'] == 'F'
    assert config['vehicle'] == {}
    assert config['output'] == {}


def test_load_config_locale_argument_takes_precedence(tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'missing.toml')
    monkeypatch.setenv('LANG', 'en_US.UTF-8')
    config = load_config(locale='fr-FR')
    assert config['units']['distance'] == 'km'
    assert config['units']['temperature'] == 'C'


def test_load_config_reads_units_from_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[units]\ndistance = 'km'\ntemperature = 'C'\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    config = load_config(locale='en-US')
    assert config['units']['distance'] == 'km'
    assert config['units']['temperature'] == 'C'


def test_load_config_invalid_units_fall_back_to_locale(tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[units]\ndistance = 'parsecs'\ntemperature = 'K'\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    config = load_config(locale='en-US')
    assert config['units']['distance'] == 'mi'
    assert config['units']['temperature'] == 'F'


def test_load_config_temperature_lowercase_normalises(tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[units]\ntemperature = 'c'\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    config = load_config(locale='en-US')
    assert config['units']['temperature'] == 'C'


def test_load_config_reads_default_vin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[vehicle]\ndefault_vin = '1FA12345678901234'\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    config = load_config(locale='en-US')
    assert config['vehicle']['default_vin'] == '1FA12345678901234'


def test_load_config_ignores_empty_default_vin(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[vehicle]\ndefault_vin = ''\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    config = load_config(locale='en-US')
    assert config['vehicle'] == {}


def test_load_config_reads_output_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[output]\nformat = 'json'\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    config = load_config(locale='en-US')
    assert config['output']['format'] == 'json'


def test_load_config_ignores_invalid_output_format(tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[output]\nformat = 'xml'\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    config = load_config(locale='en-US')
    assert config['output'] == {}


def test_default_distance_falls_back_to_lc_all(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'missing.toml')
    monkeypatch.setenv('LC_ALL', 'en_GB.UTF-8')
    monkeypatch.delenv('LANG', raising=False)
    monkeypatch.delenv('LC_MEASUREMENT', raising=False)
    config = load_config()
    assert config['units']['distance'] == 'mi'
    assert config['units']['temperature'] == 'C'


def test_default_locale_when_no_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'missing.toml')
    monkeypatch.delenv('LC_ALL', raising=False)
    monkeypatch.delenv('LC_MEASUREMENT', raising=False)
    monkeypatch.delenv('LANG', raising=False)
    config = load_config()
    assert config['units']['distance'] == 'km'
    assert config['units']['temperature'] == 'C'


def test_resolve_output_format_cli_flag_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OUTPUT_ENV_VAR, 'pretty')
    assert resolve_output_format(cli_json=True) == 'json'


def test_resolve_output_format_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'missing.toml')
    monkeypatch.setenv(OUTPUT_ENV_VAR, 'json')
    assert resolve_output_format() == 'json'


def test_resolve_output_format_env_var_case_insensitive(tmp_path: Path,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'missing.toml')
    monkeypatch.setenv(OUTPUT_ENV_VAR, 'JSON')
    assert resolve_output_format() == 'json'


def test_resolve_output_format_invalid_env_falls_through(tmp_path: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'missing.toml')
    monkeypatch.setenv(OUTPUT_ENV_VAR, 'xml')
    assert resolve_output_format() == 'pretty'


def test_resolve_output_format_config_file_format(tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / 'config.toml'
    config_path.write_text("[output]\nformat = 'json'\n")
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', config_path)
    monkeypatch.delenv(OUTPUT_ENV_VAR, raising=False)
    assert resolve_output_format() == 'json'


def test_resolve_output_format_default_pretty(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('fordpass.config.CONFIG_FILE', tmp_path / 'missing.toml')
    monkeypatch.delenv(OUTPUT_ENV_VAR, raising=False)
    assert resolve_output_format() == 'pretty'
