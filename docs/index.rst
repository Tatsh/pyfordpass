pyfordpass
==========

.. include:: badges.rst

FordPass client and CLI. A third-party reverse-engineered client for the same private mobile-app
endpoints the FordPass™ app uses, packaged as a Python library plus a ``fordpass`` command-line
tool.

Disclaimer
----------

This project is **not** an official Ford product. It is **not** affiliated with, endorsed by,
sponsored by, or otherwise connected to Ford Motor Company or any of its subsidiaries. "FordPass",
"The Lincoln Way", "Ford", and "Lincoln" are trademarks of Ford Motor Company.

Because this client speaks to private endpoints rather than a documented public API, Ford may
change, throttle, or revoke access without notice - and the maintainer cannot guarantee that any
particular feature will keep working.

.. warning::

   **Use of this software may cause your FordPass™ / The Lincoln Way™ account to be (temporarily)
   locked or suspended.** Traffic from any unofficial client can look anomalous to Ford's fraud
   and abuse detection. **Use at your own risk.**

It is **strongly recommended** to use a **separate, secondary FordPass™ account** for this
software rather than your primary account:

1. In the FordPass app on a phone (signed in as the primary owner), invite a secondary email
   address as an additional driver for the vehicle. The invited address must be reachable from
   that phone for verification.
2. Sign up for a new FordPass account using that secondary email and accept the driver invitation.
3. Configure ``pyfordpass`` (``fordpass auth login``) with the secondary account's credentials.

If the secondary account is later suspended, your primary account, warranty records, and
roadside-assistance enrolment remain unaffected.

See the `ha-fordpass project's general disclaimer and account-setup guidance
<https://github.com/marq24/ha-fordpass#general-disclaimer>`_ for the same procedure written up
from the Home Assistant integration's perspective - the steps are identical regardless of which
third-party client consumes the credentials.

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
against the same protocol the CLI uses. A typical first-time flow:

.. code-block:: shell

   fordpass auth login       # Interactive sign-in against the secondary account.
   fordpass vehicle list     # See what's in the garage.
   fordpass vehicle show VIN # Detailed view for one vehicle.
   fordpass remote start VIN # Remote-start command.

Every subcommand supports ``--help`` and most data-returning subcommands support ``--json`` for
machine-readable output.

For programmatic use, see :py:class:`fordpass.client.AsyncFordPassClient` (async HTTP client) and
:py:class:`fordpass.sansio.FordPassClient` (sans-I/O protocol core that builds
:py:class:`fordpass.sansio.RequestDict` descriptors).

Command reference
-----------------

.. click:: fordpass.main:fordpass
   :prog: fordpass
   :nested: full

.. only:: html

   .. toctree::
      :hidden:

      library/index

   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
