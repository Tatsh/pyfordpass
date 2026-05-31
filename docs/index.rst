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

Configuration
-------------

``pyfordpass`` has two sets of optional settings, each managed with its own subcommand rather than
by editing files by hand. Both live under ``~/.config/pyfordpass`` on Linux (the platform-specific
equivalent elsewhere).

**User preferences** are managed with ``fordpass config``. The most useful is a default VIN, so you
need not pass it to every command:

.. code-block:: shell

   # Set a default VIN, used whenever a command's VIN argument is omitted.
   fordpass config set vehicle.default_vin VIN
   # Distance ("mi"/"km") and temperature ("F"/"C"); both default from your locale.
   fordpass config set units.distance mi
   fordpass config set units.temperature C
   # Default output format: "pretty" (Rich tables) or "json".
   fordpass config set output.format json
   # Show the effective configuration (defaults included), drop a key, or start over.
   fordpass config dump
   fordpass config delete units.distance
   fordpass config reset

**API constants** are managed with ``fordpass api-config``. The built-in defaults target Ford in
the USA, so most users never need to touch them. When Ford rotates a host or client ID you can
patch individual values without waiting for a new release; anything you set is merged over the
defaults, so only the changed keys are required:

.. code-block:: shell

   # Override a single value; everything else falls back to the built-in defaults.
   fordpass api-config set hosts.login https://login.ford.com
   # Show the effective constants (defaults merged with overrides), or discard all overrides.
   fordpass api-config dump
   fordpass api-config reset

Values for other regions and for Lincoln can be copied from `ha-fordpass const.py
<https://github.com/marq24/ha-fordpass/blob/main/custom_components/fordpass/const.py>`_.

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
