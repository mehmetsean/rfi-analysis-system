# 9. Input reader and command line

Status: Accepted

## Context

The extract command reads a user's RFI export or a text file. A user's file is less tidy than the files that write_corpus makes: Excel writes a BOM when a user saves as CSV UTF-8, columns have other names, and nobody checked the size. The commands also print to a terminal, so errors must be one clear line that says what to do next.

## Decision

Module rfikit.io. read_rfis and iter_rfis (path, column map) give Rfi values, read_text(path) gives a string, read_column_map(path) reads the JSON map. One error type, InputError (a ValueError), covers every problem with a user file. A message names the file (not its folder), ends with the next step, and cuts any echoed user value (rfi_id, column name, map key) to 40 characters (textnorm.clip). The label errors in evaluate.py that echo an rfi_id use the same cut; measured.json does not change.

Reader rules, the same as the label reader in evaluate.py: symbolic links and non-regular files are refused, one bounded read, an OSError becomes "file cannot be read", UTF-8 is required, strict CSV parsing, a row with the wrong cell count is an error. The file is opened with O_NOFOLLOW where the platform has it and checked with fstat on the open descriptor, so a swap between the check and the read is refused.

Differences for user input:

- A leading UTF-8 BOM is accepted and removed. The label reader refuses it because write_corpus never writes one.
- Required columns are rfi_id, subject and question. response is optional. Extra columns are ignored. A duplicate column name is an error only for a column that is used.
- The column map is a JSON object whose keys are rfi_id, subject, question or response and whose values are column names in the file. Unknown keys, values that are not non-empty strings, mapped columns missing from the file and two fields on the same column (a mapped field landing on another field's default name too) are errors. Fields that are not in the map keep their default names.
- Blank lines and rows whose cells are all empty (",,") are skipped. An empty or repeated rfi_id is an error with the line number.

Caps, as constants: 32 MiB per CSV file (MAX_BYTES), 4 MiB per text file (MAX_TEXT_BYTES), 100,000 rows and 100,000 characters per field (MAX_FIELD) in io.py. The row cap is five times the largest corpus that generate writes (20,000 RFIs, MAX_N in cli.py). A text file has the lower cap because one text gives one citation list, so memory grows with the number of citations. A file over a cap is refused, never cut. The csv module has its own field limit of 131,072 characters; it is reported with the same message as MAX_FIELD. Columns that are not used are not checked against MAX_FIELD, only against that csv limit and MAX_BYTES.

Memory, measured with `/usr/bin/time -l rfikit extract FILE` on macOS, Python 3.13, one run each. Worst text: 4 MiB of "IEEE 1547 and " repeated (about 300,000 citations), output to stdout: peak 217,513,984 bytes, 2.0 s. A 32 MiB CSV (56,600 rows, about 1.4 million citations) with --out: peak 230,637,568 bytes, 11.2 s. Extract writes in batches, so output size does not add to the peak; the input text and the citation list of one text do.

Output files. extract --out and evaluate --json write to a temporary file in the target folder (mkstemp, which uses O_EXCL) and then os.replace it onto the target, so a failure never leaves a half file and an existing file is replaced. A target that is a symbolic link or not a regular file is refused. For extract, a target that is the same file as the input (samefile, so a hard link counts) is refused. A symbolic link as the parent folder is accepted, as in the label reader: the caller picks the folder. On stdout, extract writes UTF-8 bytes with \n line ends to sys.stdout.buffer, and a closed pipe (for example `| head`) ends quietly with exit 1. An error in the middle of a CSV can come after some rows were printed to stdout; with --out nothing is left.

generate --out. A folder that exists and is not empty is refused unless it already holds an rfikit corpus: its manifest.json parses as a JSON object with "synthetic": true and a "generator" entry (written by write_corpus; the heldout folder has no "generator" entry, so it is never overwritten). A failure in the middle of write_corpus can leave some files; running again overwrites them. n is 1 to 20,000 and the seed must not be negative.

Formula escape. A cell is written with a leading single quote when it starts with a tab, carriage return or line feed, or when, after leading white space and one U+FEFF are skipped, it starts with =, +, - or @ or with the fullwidth forms U+FF1D, U+FF0B, U+FF0D or U+FF20. The function is report.escape_cell and report.csv_chunk applies it to every cell, the header and the user's rfi_id included. The rule is applied to every column, so a new column cannot skip it. tests/test_io.py (test_escape_cell) checks every escape character.

Sharing with evaluate. evaluate._read_rows stays as it is. It raises LabelError, refuses a BOM, and requires a fixed header, and its output feeds measured.json. Sharing the byte reading would tie the two error types and the BOM rules together, so a change for user files could move a published number. The duplication is small and each reader has its own tests.

Command line. argparse with one subcommand per command: extract, generate, evaluate and analyze (still a stub that exits 1). evaluate runs evaluate(DATA, written, EvalPlan()) without baselines and prints the numbers from measured.summarize, so the terminal and measured.json agree. Both folders must exist. The table prints n/a for an undefined value, and for a level a method lacks (baselines have strict and overlap only, see ADR 8); that second case is only visible through the API, since the CLI runs no baselines. A set with no scorable RFIs prints one line instead of a table. The last line says "Measured on synthetic data." only when every folder scored has a manifest.json with "synthetic": true (write_corpus and heldout both write one); otherwise it says "Scored on the labeled folders given."

Exit codes: 0 ok, 1 input error (one line on stderr starting with "rfikit:", no traceback), 2 usage error (argparse). A file whose name does not end in .csv (any case) is read as plain text and scanned as column "text" with an empty rfi_id. Error messages for output folders name the folder only.

## Options considered

- Reject a BOM like the label reader. Excel writes one when a user saves as CSV UTF-8, so users would hit it often.
- Use the csv module's field size limit instead of a constant. It is global state and gives a less clear message.
- Escape only the text cell. A user rfi_id can start with =, so every cell is escaped.
- One shared reader. See "Sharing with evaluate".
- Refuse a symbolic link as a parent folder. Not done; the caller picks the folder.

## Consequences

An escaped cell is changed, so a program that reads the extract output back sees the leading quote on a cell that began with one of the listed characters. The output is for people and spreadsheets. The caps may need a flag later if a user has a larger export. Peak memory of a large text is about 200 MB; a streaming scanner would lower it and is not planned.
