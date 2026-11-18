# rfikit

rfikit will find standard citations in engineering RFIs and return normalized designation keys. RFI here means request for information, not radio-frequency interference.

## Status

Being rebuilt. Version 0.1 is not released. The design is in [docs/spec.md](docs/spec.md) and the decisions are in [docs/adr](docs/adr/README.md). The package has the citation extractor, a synthetic data generator, an evaluation and a command line.

## Command line

All commands run on your machine. The package imports no network or subprocess module; tests/test_no_network_imports.py checks that.

Find the standard citations in a text file or in an RFI export and print them as CSV:

```
rfikit extract notes.txt
rfikit extract rfis.csv --out citations.csv
```

A file whose name ends in .csv (any case) is read as an RFI export. Any other file is read as plain text. An export needs the columns rfi_id, subject and question. A response column is optional. For other column names, pass a JSON file such as `{"rfi_id": "RFI No", "subject": "Title", "question": "Body"}` with `--column-map map.json`. Limits: 32 MiB and 100,000 rows per export, 4 MiB per text file, 100,000 characters per value. `--out` replaces an existing file, and it refuses the input file, the column map file and symbolic links. `--column-map` works only with a .csv file. When the output goes to the screen, a bad row found in the middle of a file exits with 1 after part of the CSV was written; use `--out` to get all or nothing.

Output cells are escaped for spreadsheets: a cell gets a leading single quote when it starts with a tab, carriage return or line feed, or when it starts with =, +, - or @ (or the fullwidth forms of those four) after leading white space and invisible characters are skipped (Unicode categories Cc and Cf, such as U+FEFF). Control characters other than tab, carriage return and line feed (and DEL and C1 controls) are written as \xNN in every cell. For a text file the column value is "text" and rfi_id is empty. Offsets count Unicode code points; tests/test_cli.py (test_offsets_are_code_points_csv and test_offsets_are_code_points_text) checks that with emoji in the text.

Write a synthetic corpus with labels (n from 1 to 20000). The folder must be new or empty. If a run fails in the middle, some files can be left, so empty the folder or pick a new one before running again:

```
rfikit generate --seed 42 --n 600 --out data/
```

Score the extractor on a folder made by generate, with an optional second labeled folder, and print precision, recall and F1:

```
rfikit evaluate data/ --written heldout/ --json summary.json
```

For example, after `rfikit generate --seed 42 --n 600 --out data/`, the command `rfikit evaluate data/` prints the line "Leak check: pool 12000, A dropped 0 of 456, B dropped 0 of 144" just before its last line. The leak line counts repeats after cleaning (character map, lower case, white space collapsed), not only exact repeats. The pool is the set of distinct subject and question pairs in the synthetic training corpora, seeds 1 to 10, families A and B. Dropped counts the RFIs in your folder whose pair is in the pool; they are left out of the scores. The last line says "Measured on synthetic data." only when every scored folder has a manifest.json with "synthetic": true.

Write the citations and an analysis of an RFI export into a new or empty folder (a missing folder is created; a folder that is not empty is refused, see ADR 10):

```
rfikit analyze rfis.csv --out results/
rfikit analyze rfis.csv --out results/ --column-map map.json
```

The folder gets four files: citations.csv (the same columns as `rfikit extract`), analysis.md and analysis.html (RFIs read, top 20 base keys, citations per body, citations per RFI, the 10 RFIs with the most citations, and the measured extraction rates), and README.txt with the license notice and the disclaimer. The rates are copied from src/rfikit/measured.json and labeled "measured on synthetic data" for family A, family B and the written set; a level a method does not have prints n/a. The HTML is one static file with no script and no external resource. RFI ids are shown cut to 40 characters and escaped. A base key of NESC alone, which includes the ANSI C2 and IEEE C2 names, is shown as "NESC (no rule given)" with a note in the tables. citations.csv keeps the key NESC. `--synthetic` adds a line saying the input is synthetic data. analyze reads a .csv file only. Peak memory was 205,619,200 bytes for 2.4 million citations (100,000 rows) and 268,976,128 bytes for 4.1 million citations (110 rows), one run each on one Mac. The rows differ, so the two runs do not isolate the effect of citations. The inputs and commands are in ADR 10.

examples/ holds the output for seed 42 and 200 synthetic RFIs; `python scripts/make_examples.py --check` rebuilds it and fails on any byte difference, and CI runs that check. Decision support only, not legal, engineering, tax, accounting or assurance advice. No guarantee of compliance. rfikit does not say whether a standard applies or what it requires; check every citation against the official standard. False positives and misses are expected; the measured rates are shown.

Input errors print one line starting with "rfikit:" and exit with 1. A wrong option prints a usage message and exits with 2.

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
