"""Config: inspect and edit the user configuration file."""
from __future__ import annotations

from fordpass.config import CONFIG_FILE, effective_config
import click

from .utils import (
    debug_option,
    delete_toml_file,
    delete_toml_key,
    json_option,
    render_config,
    set_toml_key,
)


@click.group()
def config() -> None:
    """Inspect and edit the user configuration (``config.toml``)."""


@config.command('dump')
@debug_option
@json_option
def config_dump(*, as_json: bool) -> None:
    """Print the effective configuration, including injected defaults."""
    render_config(effective_config(), as_json=as_json)


@config.command('set')
@debug_option
@click.argument('key')
@click.argument('value')
def config_set(key: str, value: str) -> None:
    """Set KEY (a dotted path such as `vehicle.default_vin`) to VALUE."""
    set_toml_key(CONFIG_FILE, key, value)
    click.secho(f'Set `{key}`.', fg='green')


@config.command('delete')
@debug_option
@click.argument('key')
def config_delete(key: str) -> None:
    """Delete KEY (a dotted path) from the configuration."""  # noqa: DOC501
    try:
        delete_toml_key(CONFIG_FILE, key)
    except KeyError as exc:
        msg = f'Key not found: {key}'
        raise click.ClickException(msg) from exc
    click.secho(f'Deleted `{key}`.', fg='green')


@config.command('reset')
@debug_option
def config_reset() -> None:
    """Reset the configuration by deleting the file, restoring defaults."""
    if delete_toml_file(CONFIG_FILE):
        click.secho(f'Deleted {CONFIG_FILE}.', fg='green')
    else:
        click.secho('No configuration file to delete.', fg='yellow')
