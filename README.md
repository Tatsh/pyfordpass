# pyfordpass

<!-- WISWA-GENERATED-README:START -->

[![Python versions](https://img.shields.io/pypi/pyversions/pyfordpass.svg?color=blue&logo=python&logoColor=white)](https://www.python.org/)
[![PyPI - Version](https://img.shields.io/pypi/v/pyfordpass)](https://pypi.org/project/pyfordpass/)
[![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Tatsh/pyfordpass)](https://github.com/Tatsh/pyfordpass/tags)
[![License](https://img.shields.io/github/license/Tatsh/pyfordpass)](https://github.com/Tatsh/pyfordpass/blob/master/LICENSE.txt)
[![GitHub commits since latest release (by SemVer including pre-releases)](https://img.shields.io/github/commits-since/Tatsh/pyfordpass/v0.0.1/master)](https://github.com/Tatsh/pyfordpass/compare/v0.0.1...master)
[![CodeQL](https://github.com/Tatsh/pyfordpass/actions/workflows/codeql.yml/badge.svg)](https://github.com/Tatsh/pyfordpass/actions/workflows/codeql.yml)
[![QA](https://github.com/Tatsh/pyfordpass/actions/workflows/qa.yml/badge.svg)](https://github.com/Tatsh/pyfordpass/actions/workflows/qa.yml)
[![Tests](https://github.com/Tatsh/pyfordpass/actions/workflows/tests.yml/badge.svg)](https://github.com/Tatsh/pyfordpass/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/Tatsh/pyfordpass/badge.svg?branch=master)](https://coveralls.io/github/Tatsh/pyfordpass?branch=master)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-blue?logo=dependabot)](https://github.com/dependabot)
[![Documentation Status](https://readthedocs.org/projects/pyfordpass/badge/?version=latest)](https://pyfordpass.readthedocs.org/?badge=latest)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![uv](https://img.shields.io/badge/uv-261230?logo=astral)](https://docs.astral.sh/uv/)
[![pytest](https://img.shields.io/badge/pytest-zz?logo=Pytest&labelColor=black&color=black)](https://docs.pytest.org/en/stable/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Downloads](https://static.pepy.tech/badge/pyfordpass/month)](https://pepy.tech/project/pyfordpass)
[![Stargazers](https://img.shields.io/github/stars/Tatsh/pyfordpass?logo=github&style=flat)](https://github.com/Tatsh/pyfordpass/stargazers)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Prettier](https://img.shields.io/badge/Prettier-black?logo=prettier)](https://prettier.io/)

[![@Tatsh](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpublic.api.bsky.app%2Fxrpc%2Fapp.bsky.actor.getProfile%2F%3Factor=did%3Aplc%3Auq42idtvuccnmtl57nsucz72&query=%24.followersCount&label=Follow+%40Tatsh&logo=bluesky&style=social)](https://bsky.app/profile/Tatsh.bsky.social)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Tatsh-black?logo=buymeacoffee)](https://buymeacoffee.com/Tatsh)
[![Libera.Chat](https://img.shields.io/badge/Libera.Chat-Tatsh-black?logo=liberadotchat)](irc://irc.libera.chat/Tatsh)
[![Mastodon Follow](https://img.shields.io/mastodon/follow/109370961877277568?domain=hostux.social&style=social)](https://hostux.social/@Tatsh)
[![Patreon](https://img.shields.io/badge/Patreon-Tatsh2-F96854?logo=patreon)](https://www.patreon.com/Tatsh2)

<!-- WISWA-GENERATED-README:STOP -->

FordPass client and CLI. A third-party reverse-engineered client for the same private mobile-app
endpoints the FordPass™ app uses, packaged as a Python library plus a `fordpass` command-line
tool.

## Disclaimer

This project is **not** an official Ford product. It is **not** affiliated with, endorsed by,
sponsored by, or otherwise connected to Ford Motor Company or any of its subsidiaries.
"FordPass", "The Lincoln Way", "Ford", and "Lincoln" are trademarks of Ford Motor Company.

Because this client speaks to private endpoints rather than a documented public API, Ford may
change, throttle, or revoke access without notice - and the maintainer cannot guarantee that any
particular feature will keep working.

> **Use of this software may cause your FordPass™ / The Lincoln Way™ account to be (temporarily)
> locked or suspended.** Traffic from any unofficial client can look anomalous to Ford's fraud
> and abuse detection. **Use at your own risk.**

It is **strongly recommended** to use a **separate, secondary FordPass™ account** for this
software rather than your primary account:

1. In the FordPass app on a phone (signed in as the primary owner), invite a secondary email
   address as an additional driver for the vehicle. The invited address must be reachable from
   that phone for verification.
2. Sign up for a new FordPass account using that secondary email and accept the driver
   invitation.
3. Configure `pyfordpass` (`fordpass auth login`) with the secondary account's credentials.

If the secondary account is later suspended, your primary account, warranty records, and
roadside-assistance enrolment remain unaffected.

See the [ha-fordpass project's general disclaimer and account-setup
guidance](https://github.com/marq24/ha-fordpass#general-disclaimer) for the same procedure
written up from the Home Assistant integration's perspective - the steps are identical
regardless of which third-party client consumes the credentials.

## Installation

```shell
pip install pyfordpass
```

## Usage

Add `-d` to show debug logs. Run with no arguments to see the top-level command list:

```shell
fordpass
```

A typical first-time flow:

```shell
fordpass auth login       # Interactive sign-in against the secondary account.
fordpass vehicle list     # See what's in the garage.
fordpass vehicle show VIN # Detailed view for one vehicle.
fordpass remote start VIN # Remote-start command.
```

Every subcommand supports `--help` and most data-returning subcommands support `--json` for
machine-readable output.

## Charging (EV/PHEV)

For electric and plug-in-hybrid vehicles, `fordpass charge` controls charging and reads charge
state:

```shell
fordpass charge start VIN              # Start a charge session.
fordpass charge pause VIN              # Pause an active session.
fordpass charge cancel VIN             # Cancel an active session.
fordpass charge set VIN globalTargetSoc 80   # Update one charge setting.
fordpass charge set VIN chargeMode CHARGE_NOW
fordpass charge times VIN              # Show the preferred-charge-times profile.
fordpass charge status VIN             # Live energy-transfer status (only at a charge location).
fordpass charge logs VIN --max-records 20    # Recent energy-transfer logs.
```

`charge set` accepts `autoChargePortUnlock`, `chargeMode`, `globalCurrentLimit`,
`globalDCPowerLimit`, `globalDCTargetSoc`, `globalReserveSoc`, and `globalTargetSoc`. Ford only
persists state-of-charge targets below 80% in multiples of ten, so a sub-80 value is rounded down
to the nearest ten and applied to all three state-of-charge keys at once.

To write a full preferred-charge-times profile, pass the JSON body with `--data` (use `-` to read
it from standard input; the location id is taken from `location.id` when `--location-id` is
omitted):

```shell
fordpass charge target VIN --location-id LOCATION_ID --data - < profile.json
```

## Departure schedules (EV/PHEV)

For electric and plug-in-hybrid vehicles, `fordpass departure` reads and writes the departure-time
schedules (the timed pre-conditioning / charge-ready windows):

```shell
fordpass departure next VIN     # Show the next-upcoming departure.
fordpass departure enable VIN   # Enable the departure-time schedules.
fordpass departure disable VIN  # Disable all departure-time schedules.
```

The wire protocol has no partial update: `update` replaces the **complete** schedule list. Provide
it either as a JSON array with `--from-json` (use `-` to read it from standard input) or as one or
more `--add` slots (mutually exclusive with `--from-json`):

```shell
fordpass departure update VIN --from-json profile.json
fordpass departure update VIN --from-json - < profile.json
fordpass departure update VIN \
  --add 'MON@07:30:loc=LOCATION_ID,id=1,temp=MEDIUM,status=ON' \
  --add 'FRI@06:15:loc=LOCATION_ID,id=2'
```

Each `--add` slot is `DAY@HH:MM:loc=<id>,id=<int>,temp=OFF|LOW|MEDIUM|HIGH,status=ON|OFF`, where
`temp` defaults to `OFF`, `status` defaults to `ON`, and `loc`/`id` are required. The JSON array
matches the body Ford expects:

```json
[
  {
    "dayOfWeek": "MONDAY",
    "schedules": [
      {
        "locationId": "LOCATION_ID",
        "preconditionTemperature": "MEDIUM",
        "scheduleId": 1,
        "scheduleStatus": "ON",
        "timeOfDay": { "hours": 7, "minutes": 30 }
      }
    ]
  }
]
```

The two `delete` subcommands are read-modify-write helpers that fetch the current schedule, drop the
matching parts, and write the remainder back:

```shell
fordpass departure delete-by-id VIN 1 3   # Drop slots by scheduleId.
fordpass departure delete-by-day VIN mon,fri  # Drop whole-day groups.
```

## Guard Mode

On supported models, `fordpass guard` reads and toggles the Guard Mode session. These calls go to
the Ford MPS API rather than the telemetry plane, so they are a single HTTP request each (no
polling):

```shell
fordpass guard status VIN  # Show the current Guard Mode session state.
fordpass guard enable VIN  # Enable Guard Mode.
fordpass guard disable VIN # Disable Guard Mode.
```

Each subcommand supports `--json`. The response carries a `returnCode` (`200` on success) and a
`returnMessage`; a disable can legitimately report code `300` with "Enrollment is still in
progress."

## Zone lighting

For vehicles with zone lighting, `fordpass lights` controls the exterior lighting zones:

```shell
fordpass lights on VIN         # Turn the zone lighting on.
fordpass lights off VIN        # Turn the zone lighting off.
fordpass lights zone VIN front # Light one zone: all|front|rear|driver|passenger|off.
```

`lights zone` accepts `all`, `front`, `rear`, `driver`, `passenger`, and `off`. When the lights are
currently off, selecting a zone turns them on first, waits for the activation to settle, and then
applies the zone.

## Experimental commands

The following command groups are ported from `ha-fordpass`, whose author flags them as
**unverified** - they ship here as experimental and may return an error for your vehicle.

`fordpass trailer check` flashes the trailer lights to verify a connection:

```shell
fordpass trailer check on VIN  # Flash the trailer lights.
fordpass trailer check off VIN # Stop an active trailer-light check.
```

`fordpass precondition` controls cabin preconditioning, independent of remote start:

```shell
fordpass precondition start VIN  # Start cabin preconditioning.
fordpass precondition extend VIN # Extend an active session.
fordpass precondition stop VIN   # Stop an active session.
```

`fordpass ppo` triggers a Programmable Parameter Override refresh:

```shell
fordpass ppo refresh VIN                                    # One-shot refresh.
fordpass ppo stream VIN --frequency-min 3 --duration-min 10 # Continuous refresh.
fordpass ppo cancel VIN                                     # Cancel a continuous refresh.
```

## Configuration

`pyfordpass` has two sets of optional settings, each managed with its own subcommand rather than
by editing files by hand. Both live under `~/.config/pyfordpass` on Linux (the platform-specific
equivalent elsewhere).

**User preferences** are managed with `fordpass config`. The most useful is a default VIN, so you
need not pass it to every command:

```shell
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
```

**API constants** are managed with `fordpass api-config`. The built-in defaults target Ford in the
USA, so most users never need to touch them. When Ford rotates a host or client ID you can patch
individual values without waiting for a new release; anything you set is merged over the defaults,
so only the changed keys are required:

```shell
# Override a single value; everything else falls back to the built-in defaults.
fordpass api-config set hosts.login https://login.ford.com
# Show the effective constants (defaults merged with overrides), or discard all overrides.
fordpass api-config dump
fordpass api-config reset
```

Values for other regions and for Lincoln can be copied from
[ha-fordpass `const.py`](https://github.com/marq24/ha-fordpass/blob/main/custom_components/fordpass/const.py).
