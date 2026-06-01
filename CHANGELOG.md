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

## [0.0.1] - 2026-05-31

First version.

[unreleased]: https://github.com/Tatsh/pyfordpass/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/Tatsh/pyfordpass/releases/tag/v0.0.1
