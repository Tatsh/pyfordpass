"""Loader for FordPass API constants."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast
import functools

from fordpass.config import CONFIG_DIR
import tomlkit

if TYPE_CHECKING:
    from .typing.secrets import Secrets

__all__ = ('SECRETS_FILE', 'load_secrets')

SECRETS_FILE = CONFIG_DIR / 'abcdef.toml'
"""
Path to the constants TOML file.

:meta hide-value:
"""


def _require(raw: Mapping[str, object], path: tuple[str, ...]) -> object:
    """
    Return the value at ``raw[path[0]][path[1]]…``, or raise on missing keys.

    Parameters
    ----------
    raw : dict[str, Any]
        The parsed TOML document.
    path : tuple[str, ...]
        Dotted path through nested tables.

    Returns
    -------
    object
        The value at the given path.

    Raises
    ------
    RuntimeError
        If any component of ``path`` is absent.
    """
    cursor: Any = raw
    for part in path:
        if not isinstance(cursor, Mapping) or part not in cursor:
            dotted = '.'.join(path)
            msg = (f'`{dotted}` missing from {SECRETS_FILE}. '
                   f'Please populate it with the appropriate value.')
            raise RuntimeError(msg)
        cursor = cursor[part]
    return cursor


@functools.cache
def load_secrets() -> Secrets:
    """
    Read and validate :data:`SECRETS_FILE`.

    Returns
    -------
    Secrets
        The parsed file with all required keys populated.

    Raises
    ------
    RuntimeError
        If the file is missing, unreadable, or missing required keys.
    """
    if not SECRETS_FILE.exists():
        msg = (f'Constants file not found: {SECRETS_FILE}. '
               f'Create it with the schema documented in fordpass.typing.Secrets.')
        raise RuntimeError(msg)
    raw = tomlkit.loads(SECRETS_FILE.read_text()).unwrap()
    return {
        'application_id': cast('str', _require(raw, ('application_id',))),
        'user_agent': cast('str', _require(raw, ('user_agent',))),
        'profile_groups_default': cast('str', _require(raw, ('profile_groups_default',))),
        'hosts': {
            'foundational': cast('str', _require(raw, ('hosts', 'foundational'))),
            'login': cast('str', _require(raw, ('hosts', 'login'))),
            'tmc': cast('str', _require(raw, ('hosts', 'tmc'))),
            'tmc_accounts': cast('str', _require(raw, ('hosts', 'tmc_accounts'))),
            'vehicle': cast('str', _require(raw, ('hosts', 'vehicle')))
        },
        'auth': {
            'b2c': {
                'client_id': cast('str', _require(raw, ('auth', 'b2c', 'client_id'))),
                'policy_template': cast('str', _require(raw, ('auth', 'b2c', 'policy_template'))),
                'redirect_uri': cast('str', _require(raw, ('auth', 'b2c', 'redirect_uri'))),
                'tenant_id': cast('str', _require(raw, ('auth', 'b2c', 'tenant_id')))
            },
            'tmc': {
                'client_id': cast('str', _require(raw, ('auth', 'tmc', 'client_id')))
            }
        },
        'roadside': {
            'x_source': cast('dict[str, str]', _require(raw, ('roadside', 'x_source')))
        }
    }
