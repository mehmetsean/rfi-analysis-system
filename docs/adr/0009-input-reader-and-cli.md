# 9. Input reader and command line

Status: Accepted

## Context

The extract command reads a user's RFI export or a text file. A user's file is less tidy than the files that write_corpus makes: Excel writes a BOM, columns have other names, and nobody checked the size. The commands also print to a terminal, so errors must be one clear line.

## Decision

Module rfikit.io. read_rfis(path, column_map) returns Rfi values, read_text(path) returns a string, read_column_map(path) reads the JSON map. One error type, InputError (a ValueError), covers every problem with a user file. A message names the file and never the folder path.

Reader rules, the same as the label reader in evaluate.py: symbolic links and non-regular files are refused, one read with a byte cap, an OSError becomes "file cannot be read", UTF-8 is required, strict CSV parsing, a row with the wrong cell count is an error.

Differences for user input:

- A leading UTF-8 BOM is accepted and removed. The label reader refuses it because write_corpus never writes one.
- Required columns are rfi_id, subject and question. response is optional. Extra columns are ignored. A duplicate column name is an error.
- The column map is a JSON object whose keys are rfi_id, subject, question or response and whose values are column names in the file. Unknown keys, values that are not non-empty strings and mapped columns missing from the file are errors. Fields that are not in the map keep their default names.
- Blank lines are skipped. An empty rfi_id or a repeated rfi_id is an error with the line number.

Caps, as constants in io.py: 32 MiB per file, 100,000 rows, 100,000 characters per field. They are far above a real RFI export (a few thousand rows, a few thousand characters per field) and low enough to keep memory use small. A file over a cap is refused, never cut.

Formula escape. A cell that starts with =, +, - or @ is written with a leading single quote, so a spreadsheet does not run it as a formula. Tab and carriage return are in the same list, since spreadsheets treat them the same way. The function is report.escape_cell and report.csv_text applies it to every cell, the rfi_id and the header included. Cells of key and offsets cannot start with those characters, but the rule is not checked per column, so it cannot be forgotten.

Sharing with evaluate. evaluate._read_rows stays as it is. It raises LabelError, refuses a BOM, and requires a fixed header, and its output feeds measured.json. Sharing the byte reading would save about fifteen lines but would tie the two error types and the BOM rules together, so a change for user files could move a published number. The duplication is small and each reader has its own tests.

Command line. argparse with one subcommand per command: extract, generate, evaluate and analyze (still a stub that exits 1). evaluate runs evaluate(DATA, written, EvalPlan()) without baselines and prints the numbers from measured.summarize, so the terminal and measured.json agree. The table prints n/a for an undefined value and for a level a method does not have (baselines have strict and overlap only, see ADR 8). generate accepts n from 1 to 20,000.

Exit codes: 0 ok, 1 input error (one line on stderr starting with "rfikit:", no traceback), 2 usage error (argparse). A text file is scanned as column "text" with an empty rfi_id. --out is refused when it is a symbolic link.

## Options considered

- Reject a BOM like the label reader. Excel on Windows writes one, so users would hit it at once.
- Use the csv module's field size limit instead of a constant. It is global state and gives a less clear message.
- Escape only the text cell. A user rfi_id can start with =, so every cell is escaped.
- One shared reader. See "Sharing with evaluate".

## Consequences

An escaped cell is changed, so a program that reads the extract output back sees the leading quote on a cell that began with one of the listed characters. The output is for people and spreadsheets. The caps may need a flag later if a user has a larger export.
