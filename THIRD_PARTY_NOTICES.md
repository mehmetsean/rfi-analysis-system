# Third-party notices

The rfikit code, docs and examples are all rights reserved, see LICENSE.
The parts below belong to other people and keep their own licenses.
None of them are copied into this repo or shipped in the rfikit package. The one exception is the demo site described below, which ships Pyodide and the CPython standard library.

## Runtime

rfikit has no runtime dependencies. It uses only the Python standard library.

## Development and test tools

These are used to test and check the code only.

| Part | License |
| --- | --- |
| pytest | MIT |
| pytest-cov | MIT |
| hypothesis | MPL-2.0 |
| ruff | MIT |
| mypy | MIT |
| playwright (browser extra) | Apache-2.0 |
| hatchling (build backend) | MIT |

These packages pull in their own dependencies. Each keeps its own license.

## Demo site

The Pages site built by scripts/build_site.py serves these files from its own origin. They are downloaded at build time and are not committed to this repo.

| Part | Version | License |
| --- | --- | --- |
| Pyodide (pyodide.js, pyodide.asm.mjs, pyodide.asm.wasm, pyodide-lock.json) | 314.0.8 | MPL-2.0 |
| CPython standard library (python_stdlib.zip) | the version built into Pyodide 314.0.8 | PSF License |

Source and license texts are at https://github.com/pyodide/pyodide and https://docs.python.org/3/license.html. Playwright is used in tests and CI only and is not shipped.
