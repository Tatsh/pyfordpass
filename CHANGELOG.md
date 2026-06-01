<!-- markdownlint-configure-file {"MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- EV/PHEV charging support: a `fordpass charge` command group (`start`, `cancel`, `pause`, `set`,
  `target`, `times`, `status`, and `logs`), with matching `AsyncFordPassClient` methods and
  sans-I/O request builders for the global-charge TMC commands and the electrification
  energy-transfer endpoints.
- Guard Mode support: a `fordpass guard` command group (`status`, `enable`, `disable`) backed by
  the Ford MPS API (single HTTP call, no polling), with a new `mps` host constant and the
  `GuardModeResponse` type.
- Zone-lighting support: a `fordpass lights` command group (`on`, `off`, `zone`) backed by the
  Ford MPS API, including the two-step "turn on then select zone" flow in
  `AsyncFordPassClient.set_zone_lighting` and a `ZoneLightZone` type.
- Experimental Autonomic TMC commands ported from `ha-fordpass` (flagged unverified upstream):
  `fordpass trailer check` (`on`, `off`), `fordpass precondition` (`start`, `extend`, `stop`), and
  `fordpass ppo` (`refresh`, `stream`, `cancel`), plus a `honk_and_flash` client convenience alias
  over `startPanicCue`.
- Departure-schedule write side: `fordpass departure` gains `enable`, `disable`, `update`
  (`--from-json` or repeatable `--add DAY@HH:MM:loc=...,id=...` slots), `delete-by-id`, and
  `delete-by-day`, with matching `AsyncFordPassClient` methods, sans-I/O builders for the
  `enableDepartureTimes` / `disableDepartureTimes` / `updateDepartureTimes` beta TMC commands, and
  the `DepartureScheduleDay` / `DepartureScheduleSlot` / `TimeOfDay` types.

## [0.0.1] - 2026-05-31

First version.

[unreleased]: https://github.com/Tatsh/pyfordpass/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/Tatsh/pyfordpass/releases/tag/v0.0.1
