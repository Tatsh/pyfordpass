"""Tests for fordpass.commands.auth."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.main import fordpass

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner
    from pytest_mock import MockerFixture


def test_auth_login_drives_interactive_signin(runner: CliRunner, mocker: MockerFixture,
                                              mock_command_client: object) -> None:
    interactive = mocker.patch('fordpass.commands.auth.interactive_signin',
                               new_callable=mocker.AsyncMock)
    result = runner.invoke(fordpass, ('auth', 'login'))
    assert result.exit_code == 0
    interactive.assert_awaited_once()


def test_auth_refresh_calls_exchange(runner: CliRunner, mocker: MockerFixture,
                                     mock_command_client: object) -> None:
    ensure = mocker.patch('fordpass.commands.auth.ensure_signed_in', new_callable=mocker.AsyncMock)
    mocker.patch('fordpass.commands.auth.persist_tokens')
    result = runner.invoke(fordpass, ('auth', 'refresh'))
    assert result.exit_code == 0
    ensure.assert_awaited_once()
    assert 'TMC bearer refreshed' in result.output


def test_auth_status_no_tokens(runner: CliRunner, mocker: MockerFixture, tmp_path: Path) -> None:
    mocker.patch('fordpass.commands.auth.load_tokens', return_value={})
    result = runner.invoke(fordpass, ('auth', 'status'))
    assert result.exit_code == 0
    assert 'Not signed in' in result.output


def test_auth_status_shows_tokens(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.auth.load_tokens',
                 return_value={
                     'cat': 'X' * 200,
                     'tmc': 'Y' * 100
                 })
    result = runner.invoke(fordpass, ('auth', 'status'))
    assert result.exit_code == 0
    assert 'CAT' in result.output
    assert 'TMC' in result.output


def test_auth_status_json(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('fordpass.commands.auth.load_tokens',
                 return_value={
                     'cat': 'X' * 200,
                     'tmc': 'Y' * 100
                 })
    result = runner.invoke(fordpass, ('auth', 'status', '--json'))
    assert result.exit_code == 0
    assert '"signed_in": true' in result.output


def test_auth_logout_when_file_present(runner: CliRunner, mocker: MockerFixture,
                                       tmp_path: Path) -> None:
    tokens = tmp_path / 'tokens.json'
    tokens.write_text('{}')
    mocker.patch('fordpass.commands.auth.TOKEN_FILE', tokens)
    result = runner.invoke(fordpass, ('auth', 'logout'))
    assert result.exit_code == 0
    assert 'Logged out' in result.output
    assert not tokens.exists()


def test_auth_logout_when_already_out(runner: CliRunner, mocker: MockerFixture,
                                      tmp_path: Path) -> None:
    mocker.patch('fordpass.commands.auth.TOKEN_FILE', tmp_path / 'no-such.json')
    result = runner.invoke(fordpass, ('auth', 'logout'))
    assert result.exit_code == 0
    assert 'Already logged out' in result.output
