# Changelog

All notable changes are listed here. The format follows Keep a Changelog.

## Unreleased

### Added

- Package scaffold: pyproject.toml, src/rfikit with the frozen data types (Rfi, Designation, Citation) and a stub command line.
- Designation keys and base keys, with unit and property tests.
- CI on Python 3.11 to 3.14 (ruff, mypy --strict, pytest with a 90 percent coverage gate), CodeQL and Dependabot.
- Architecture decision records 1 to 5.

### Removed

- The 2025 prototype script rfi_analyzer.py and a stray one-byte file named src. Both stay in git history.
