pyfordpass
==========

.. include:: badges.rst

FordPass client and CLI.

Installation
------------

.. code-block:: shell

   pip install pyfordpass

Or with ``uv``:

.. code-block:: shell

   uv tool install pyfordpass

Quick start
-----------

The CLI is the primary surface. The library lives behind it for callers who want to integrate
against the same protocol the CLI uses.

.. code-block:: shell

   pyfordpass auth signin
   pyfordpass vehicle list
   pyfordpass remote start

For programmatic use, see :py:class:`fordpass.client.AsyncFordPassClient` (async HTTP client) and
:py:class:`fordpass.sansio.FordPassClient` (sans-I/O protocol core that builds
:py:class:`fordpass.sansio.RequestDict` descriptors).

Command reference
-----------------

.. click:: fordpass.main:ford
   :prog: pyfordpass
   :nested: full

.. only:: html

   .. toctree::
      :hidden:

      library/index

   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
