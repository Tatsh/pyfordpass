"""Loader for FordPass API constants."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast
import copy
import functools

from fordpass.config import CONFIG_DIR
import tomlkit

if TYPE_CHECKING:
    from .typing.api_config import APIConfig

__all__ = ('API_CONFIG_FILE', 'DEFAULT_API_CONFIG', 'load_api_config')

API_CONFIG_FILE = CONFIG_DIR / 'api.toml'
"""
Path to the optional constants-override TOML file.

When present, its contents are merged over :data:`DEFAULT_API_CONFIG`, letting a user patch
individual values (for example a rotated host or client ID) without waiting for a new release.

:meta hide-value:
"""

DEFAULT_API_CONFIG: APIConfig = {
    'application_id': 'BFE8C5ED-D687-4C19-A5DD-F92CDFC4503A',
    'user_agent': 'okhttp/4.12.0',
    'profile_groups_default': ('names,address,phoneNumbers,emails,country,languages,'
                               'unitsOfMeasure,namesExtensions'),
    'hosts': {
        'foundational': 'https://api.foundational.ford.com',
        'login': 'https://login.ford.com',
        'tmc': 'https://api.autonomic.ai',
        'tmc_accounts': 'https://accounts.autonomic.ai',
        'vehicle': 'https://api.vehicle.ford.com'
    },
    'auth': {
        'b2c': {
            'client_id': '09852200-05fd-41f6-8c21-d36d3497dc64',
            'policy_template': 'B2C_1A_SignInSignUp_{locale}',
            'redirect_uri': 'fordapp://userauthorized',
            'tenant_id': '4566605f-43a7-400a-946e-89cc9fdb0bd7'
        },
        'tmc': {
            'client_id': 'fordpass-prod'
        }
    },
    'roadside': {
        'x_source': {
            'ford': 'FORD',
            'lincoln': 'LINCOLN'
        }
    }
}
"""
Built-in FordPass API constants captured from the official mobile app.

These serve as the default bundle when :data:`API_CONFIG_FILE` is absent.

:meta hide-value:
"""


def _merge_into(base: dict[str, Any], override: Mapping[str, Any]) -> None:
    """
    Recursively overlay ``override`` onto ``base`` in place.

    Nested mappings are merged key by key; any other value (scalar, list, ...) replaces the value in
    ``base`` wholesale.

    Parameters
    ----------
    base : dict[str, Any]
        The mapping to mutate. Typically a deep copy of :data:`DEFAULT_API_CONFIG`.
    override : Mapping[str, Any]
        The values to layer on top, such as a parsed override file.
    """
    for key, value in override.items():
        existing = base.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            _merge_into(existing, value)
        else:
            base[key] = value


@functools.cache
def load_api_config() -> APIConfig:
    """
    Return the FordPass API constants, merging any override file over the defaults.

    The result starts from a copy of :data:`DEFAULT_API_CONFIG`. When :data:`API_CONFIG_FILE`
    exists, its parsed contents are deep-merged on top, so an override may patch as few or as many
    values as it likes.

    Returns
    -------
    APIConfig
        The effective constants bundle.
    """
    merged = cast('dict[str, Any]', copy.deepcopy(DEFAULT_API_CONFIG))
    if API_CONFIG_FILE.exists():
        _merge_into(merged, tomlkit.loads(API_CONFIG_FILE.read_text()).unwrap())
    return cast('APIConfig', merged)
