# Changelog

All notable changes are listed here. The format follows Keep a Changelog.

## 0.1.0 (2026-11-19)

### Added

- Package scaffold: pyproject.toml, src/rfikit with the frozen data types (Rfi, Designation, Citation) and a stub command line.
- Designation keys and base keys, with unit and property tests.
- The citation extractor for standard designations and clause numbers.
- A synthetic RFI generator with labels, and a held-out written set.
- The evaluate command: precision, recall and F1 at several levels, a leak check, and src/rfikit/measured.json with confidence intervals.
- The speed and accuracy benchmark against two baselines, in docs/benchmark.md.
- The in-browser demo built with Pyodide.
- CI on Python 3.11 to 3.14 (ruff, mypy --strict, pytest with a 90 percent coverage gate), a browser test job, CodeQL and Dependabot.
- Architecture decision records 1 to 12.
- The analyze command: citations.csv, analysis.md, analysis.html and README.txt for an RFI export, with the measured rates, and examples/ built from seed 42 (checked by scripts/make_examples.py in CI).
- README rewrite, docs/cli.md, scripts/reproduce_readme.py (checked in CI), SECURITY.md, THIRD_PARTY_NOTICES.md, issue templates and a pull request template.
- All rights reserved license.

### Removed

- The 2025 prototype script rfi_analyzer.py and a stray one-byte file named src. Both stay in git history.
