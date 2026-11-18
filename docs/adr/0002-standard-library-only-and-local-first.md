# 2. Standard library only and local-first

Status: Accepted

## Context

An RFI log holds project questions that a company may not want to send to a service. The same code should also run in a browser page through Pyodide, where packages with compiled parts may not be available.

## Decision

The runtime has no dependencies, only the Python standard library (`dependencies = []` in pyproject.toml). The tool makes no network calls and has no server, accounts or upload. Files are read from the machine and results are written to the machine. pytest, pytest-cov, hypothesis, ruff and mypy are in the dev extra and are not shipped.

Options considered:

- A hosted service. Easy to update, but project text leaves the machine.
- A pandas or scikit-learn based tool. Short code, but a large dependency and a harder fit for Pyodide.
- The standard library (chosen). Longer code for CSV reading and text matching, but one wheel runs on a laptop and in a browser.

## Consequences

CSV and plain text are the only inputs. Matching and text scoring are written in this repo. Speed depends on algorithm choices, not on compiled libraries.
