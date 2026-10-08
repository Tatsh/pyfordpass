<!-- markdownlint-configure-file {"MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.1/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

## [0.1.0] - 2026-10-08

### Added

- A `fordpass charge` command group (`start`, `cancel`, `pause`, `set`, `target`, `times`,
  `status`, and `logs`) for EV/PHEV charging, with matching `AsyncFordPassClient` methods and
  sans-I/O request builders for the global-charge TMC commands and the electrification
  energy-transfer endpoints.
- A `fordpass guard` command group (`status`, `enable`, and `disable`) for Guard Mode, backed by
  the Ford MPS API (single HTTP call, no polling), with a new `mps` host constant and the
  `GuardModeResponse` type.
- A `fordpass lights` command group (`on`, `off`, and `zone`) for zone lighting, backed by the Ford
  MPS API, including the two-step 'turn on then select zone' flow in
  `AsyncFordPassClient.set_zone_lighting` and a `ZoneLightZone` type.
- Experimental Autonomic TMC commands ported from `ha-fordpass` (flagged unverified upstream):
  `fordpass trailer check` (`on` and `off`), `fordpass precondition` (`start`, `extend`, and
  `stop`), and `fordpass ppo` (`refresh`, `stream`, and `cancel`), plus a `honk_and_flash` client
  convenience alias over `startPanicCue`.
- Write subcommands for `fordpass departure` (`enable`, `disable`, `update` with `--from-json` or
  repeatable `--add DAY@HH:MM:loc=...,id=...` slots, `delete-by-id`, and `delete-by-day`), with
  matching `AsyncFordPassClient` methods, sans-I/O builders for the
  `enableDepartureTimes` / `disableDepartureTimes` / `updateDepartureTimes` beta TMC commands, and
  the `DepartureScheduleDay` / `DepartureScheduleSlot` / `TimeOfDay` types.
- A `fordpass climate` command group (`show` and `set`) for Remote Climate Control, backed by the
  Ford vehicle API, with `AsyncFordPassClient.get_remote_climate` and a sparse-merge
  `set_remote_climate`, sans-I/O builders for the `rcc/profile/status` read and `rcc/profile/update`
  write, `encode_rcc_temperature` / `decode_rcc_temperature` / `merge_rcc_preferences` helpers, and
  the `RCCPreference` / `RCCProfile` / `RCCPreferenceKey` / `RCCSeatLevel` / `RCCToggle` types.

### Fixed

- VIN validation no longer rejects Ford vehicles built outside North America (for example
  Thai-built models sold in Australia with a VIN starting `MN`). The second character is no longer
  restricted to `F` or `L`, and the check digit is verified only for North American VINs (first
  character `1` to `5`) ([#86](https://github.com/Tatsh/pyfordpass/issues/86)).

### Removed

- Support for Python 3.10. Python 3.11 or later is now required.

## [0.0.1] - 2026-05-31

First version.

[unreleased]: https://github.com/Tatsh/pyfordpass/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Tatsh/pyfordpass/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/Tatsh/pyfordpass/releases/tag/v0.0.1
