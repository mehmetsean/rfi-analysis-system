# rfikit

rfikit will find standard citations in engineering RFIs and return normalized designation keys. RFI here means request for information, not radio-frequency interference.

## Status

Being rebuilt. Version 0.1 is not released. The design is in [docs/spec.md](docs/spec.md) and the decisions are in [docs/adr](docs/adr/README.md). The package has the citation extractor, a synthetic data generator, the evaluation and a command line. The analyze command is not built yet.

## Command line

All commands run on your machine and make no network calls.

Find the standard citations in a text file or in an RFI export and print them as CSV:

```
rfikit extract notes.txt
rfikit extract rfis.csv --out citations.csv
```

A CSV file needs the columns rfi_id, subject and question. A response column is optional. For other column names, pass a JSON file such as `{"rfi_id": "RFI No", "subject": "Title", "question": "Body"}` with `--column-map map.json`. Cells that start with =, +, - or @ get a leading single quote so a spreadsheet does not run them. For a text file the column value is "text" and rfi_id is empty. Offsets count Unicode code points.

Write a synthetic corpus with labels (n from 1 to 20000):

```
rfikit generate --seed 42 --n 600 --out data/
```

Score the extractor on a folder made by generate, with an optional second folder, and print precision, recall and F1:

```
rfikit evaluate data/ --written heldout/ --json summary.json
```

The numbers are measured on synthetic data. Errors print one line and exit with 1. A wrong option exits with 2.

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
