"""
FordPass client.

Public surface:

- :class:`fordpass.sansio.FordPassClient` - sans-I/O protocol core that builds
  :class:`fordpass.sansio.RequestDict` descriptors.
- :class:`fordpass.client.AsyncFordPassClient` - fully-async niquests wrapper.
- ``fordpass`` command-line tool exposed via :mod:`fordpass.commands`.
"""
from __future__ import annotations

from .client import AsyncFordPassClient
from .sansio import FordPassClient, RequestDict

__all__ = ('AsyncFordPassClient', 'FordPassClient', 'RequestDict')
__version__ = '0.1.0'
