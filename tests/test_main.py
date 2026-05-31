from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.main import ford, main
import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner


def test_ford_help(runner: CliRunner) -> None:
    result = runner.invoke(ford, ['--help'])
    assert result.exit_code == 0
    assert 'FordPass CLI' in result.output


def test_main_runs_ford_via_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('sys.argv', ['pyfordpass', '--help'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
