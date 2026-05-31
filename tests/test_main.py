from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.main import ford

if TYPE_CHECKING:
    from click.testing import CliRunner


def test_main(runner: CliRunner) -> None:
    """Test the top-level CLI group shows help and exits cleanly."""
    result = runner.invoke(ford, ['--help'])
    assert result.exit_code == 0
