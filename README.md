# rfikit

rfikit will find standard citations in engineering RFIs and return normalized designation keys. RFI here means request for information, not radio-frequency interference.

## Status

Being rebuilt. Version 0.1 is not released. The design is in [docs/spec.md](docs/spec.md) and the decisions are in [docs/adr](docs/adr/README.md). The package has the citation extractor, a synthetic data generator, an evaluation and a command line. The analyze command is not built yet.

## Command line

All commands run on your machine. The package imports no network or subprocess module; tests/test_no_network_imports.py checks that.

Find the standard citations in a text file or in an RFI export and print them as CSV:

```
rfikit extract notes.txt
rfikit extract rfis.csv --out citations.csv
```

A file whose name ends in .csv (any case) is read as an RFI export. Any other file is read as plain text. An export needs the columns rfi_id, subject and question. A response column is optional. For other column names, pass a JSON file such as `{"rfi_id": "RFI No", "subject": "Title", "question": "Body"}` with `--column-map map.json`. Limits: 32 MiB and 100,000 rows per export, 4 MiB per text file, 100,000 characters per value. `--out` replaces an existing file, and it refuses the input file itself and symbolic links.

Output cells are escaped for spreadsheets: a cell gets a leading single quote when it starts with a tab, carriage return or line feed, or when it starts with =, +, - or @ (or the fullwidth forms of those four) after leading white space and a U+FEFF are skipped. For a text file the column value is "text" and rfi_id is empty. Offsets count Unicode code points; tests/test_cli.py (test_offsets_are_code_points_csv and test_offsets_are_code_points_text) checks that with emoji in the text.

Write a synthetic corpus with labels (n from 1 to 20000). The folder must be new, empty or an earlier rfikit corpus:

```
rfikit generate --seed 42 --n 600 --out data/
```

Score the extractor on a folder made by generate, with an optional second labeled folder, and print precision, recall and F1:

```
rfikit evaluate data/ --written heldout/ --json summary.json
```

The leak line, for example "Leak check: pool 12000, A dropped 2 of 16", counts exact repeats. The pool is the set of distinct subject and question pairs (cleaned, lower case, white space collapsed) in the synthetic training corpora, seeds 1 to 10, families A and B. Dropped counts the RFIs in your folder whose pair is in the pool; they are left out of the scores. The last line says "Measured on synthetic data." only when every scored folder has a manifest.json with "synthetic": true.

Errors print one line starting with "rfikit:" and exit with 1. A wrong option exits with 2.

## Development quickstart

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

To run with the coverage gate used in CI:

```
pytest --cov=rfikit --cov-report=term-missing --cov-fail-under=90
```

## Contributions

Outside code contributions are not accepted. Bug reports by issue are fine.

## License

All rights reserved. You may view the code and run it to evaluate it. Commercial use needs a paid license from Mehmet Tuzunkan: https://www.linkedin.com/in/mstuzunkan
