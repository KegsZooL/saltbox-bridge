# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [UNRELEASED] - YYYY-MM-DD

### Added

### Changed

- Salt version bumped to 3007.13

### Fixed

### Removed

## [0.2.0] - 2026-04-06

### Added

- Sending message to core about error on run job
- Merge guard policy
- Make custom salt files optionally syncable
- Implement sync macro
- Helper script to rebuild an image
- Git safe.directory for dev

### Changed

- README.md description for `/srv/migrator` dir
- Drop obsolete commit related to sshfs-manager
- Extend sshfs-manager to provide access to all salt top files

### Fixed

- PEP 639
- CI stages
- Remove obsolete `get_gpg.sh`
- core_pillar error handling
- Incorrect dict key in job retry fallback logic
- Refactor Redis pillar loading and add JSON decoding

## [0.1.2] - 2025-12-22

### Added

- GPG generation
- Encrypt secured pillars

### Changed

- Update requirements

### Fixed

- Gathering minions by pillars

## [0.1.1] - 2025-11-15

### Added

- Creating jobs by ZeroMQ
- Optimizations

### Changed

- Move metrics to separate service 

## [0.1.0] - 2025-09-29

### Added

- Faststream messages and Salt `job/*/new` events performance test generators.
- `inventory` SaltStack module and state.

### Changed

- Move image to ALT Linux with onedir SaltStack install.
- Replace GitFS with Rsync based synchronization.
- Make Master auth process more reliable.
- Notify Core on sync completion.

## [0.0.1] - 2025-05-16

### Added

- Initial version tag.
