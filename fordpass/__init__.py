"""FordPass client.

Public surface:

- :class:`fordpass.sansio.FordPassClient` — sans-I/O protocol core that builds
  :class:`fordpass.sansio.RequestDict` descriptors.
- :class:`fordpass.client.FordPassNiquestsClient` — fully-async niquests wrapper.
- ``fordpass`` command-line tool exposed via :mod:`fordpass.commands`.
"""
from __future__ import annotations

from .client import FordPassNiquestsClient
from .sansio import FordPassClient, RequestDict

__all__ = ('FordPassClient', 'FordPassNiquestsClient', 'RequestDict')
__version__ = '0.1.0'
