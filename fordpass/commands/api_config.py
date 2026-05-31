"""API configuration: inspect and edit the API constants override file."""
from __future__ import annotations

from fordpass.api_config import API_CONFIG_FILE, load_api_config
import click

from .utils import (
    debug_option,
    delete_toml_file,
    delete_toml_key,
    json_option,
    render_config,
    set_toml_key,
)


@click.group(name='api-config')
def api_config() -> None:
    """Inspect and edit the API constants override (``api.toml``)."""


@api_config.command('dump')
@debug_option
@json_option
def api_config_dump(*, as_json: bool) -> None:
    """Print the effective API constants, including the built-in defaults."""
    render_config(load_api_config(), as_json=as_json)


@api_config.command('set')
@debug_option
@click.argument('key')
@click.argument('value')
def api_config_set(key: str, value: str) -> None:
    """Set KEY (a dotted path such as `hosts.login`) to VALUE."""
    set_toml_key(API_CONFIG_FILE, key, value)
    click.secho(f'Set `{key}`.', fg='green')


@api_config.command('delete')
@debug_option
@click.argument('key')
def api_config_delete(key: str) -> None:
    """Delete KEY (a dotted path) from the API constants override."""  # noqa: DOC501
    try:
        delete_toml_key(API_CONFIG_FILE, key)
    except KeyError as exc:
        msg = f'Key not found: {key}'
        raise click.ClickException(msg) from exc
    click.secho(f'Deleted `{key}`.', fg='green')


@api_config.command('reset')
@debug_option
def api_config_reset() -> None:
    """Reset the API constants by deleting the override file, restoring defaults."""
    if delete_toml_file(API_CONFIG_FILE):
        click.secho(f'Deleted {API_CONFIG_FILE}.', fg='green')
    else:
        click.secho('No API configuration file to delete.', fg='yellow')
