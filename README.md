# pyfordpass

<!-- WISWA-GENERATED-README:START -->

[![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Tatsh/pyfordpass)](https://github.com/Tatsh/pyfordpass/tags)
[![License](https://img.shields.io/github/license/Tatsh/pyfordpass)](https://github.com/Tatsh/pyfordpass/blob/master/LICENSE.txt)
[![GitHub commits since latest release (by SemVer including pre-releases)](https://img.shields.io/github/commits-since/Tatsh/pyfordpass/v0.0.0/master)](https://github.com/Tatsh/pyfordpass/compare/v0.0.0...master)
[![CodeQL](https://github.com/Tatsh/pyfordpass/actions/workflows/codeql.yml/badge.svg)](https://github.com/Tatsh/pyfordpass/actions/workflows/codeql.yml)
[![QA](https://github.com/Tatsh/pyfordpass/actions/workflows/qa.yml/badge.svg)](https://github.com/Tatsh/pyfordpass/actions/workflows/qa.yml)
[![Tests](https://github.com/Tatsh/pyfordpass/actions/workflows/tests.yml/badge.svg)](https://github.com/Tatsh/pyfordpass/actions/workflows/tests.yml)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-blue?logo=dependabot)](https://github.com/dependabot)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![uv](https://img.shields.io/badge/uv-261230?logo=astral)](https://docs.astral.sh/uv/)
[![pytest](https://img.shields.io/badge/pytest-zz?logo=Pytest&labelColor=black&color=black)](https://docs.pytest.org/en/stable/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
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
