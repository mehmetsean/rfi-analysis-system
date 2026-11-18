# 9. Input reader and command line

Status: Accepted

## Context

The extract command reads a user's RFI export or a text file. A user's file is less tidy than the files that write_corpus makes: Excel writes a BOM when a user saves as CSV UTF-8 (save any sheet that way and check that the first three bytes are EF BB BF), columns have other names, and nobody checked the size. The commands also print to a terminal, so errors must be one clear line that says what to do next.

## Decision

Module rfikit.io. read_rfis and iter_rfis (path, column map) give Rfi values, read_text(path) gives a string, read_column_map(path) reads the JSON map. One error type, InputError (a ValueError), covers every problem with a user file. A message names the file (not its folder; label errors reached through evaluate get the folder name and one hint from the CLI), ends with the next step (for a label error, that hint), and shows any echoed user value (rfi_id, column name, map key) as its first 40 characters in Python repr form (quotes, and escapes such as \n), with "..." added inside the closing quote when the value was longer (textnorm.clip), so a value with a line break cannot split an error into two lines. The label errors in evaluate.py that echo an rfi_id use the same cut; measured.json does not change.

Reader rules, the same as the label reader in evaluate.py: symbolic links and non-regular files are refused, one bounded read, an OSError becomes "file cannot be read", UTF-8 is required, strict CSV parsing, a row with the wrong cell count is an error. The file is opened with O_NOFOLLOW and O_NONBLOCK where the platform has them and checked with fstat on the open descriptor. What this guarantees: the file actually opened is a regular file and not a symbolic link (a FIFO swapped in after the first check does not block). A swap to another regular file between the check and the open reads that file. A test spies on os.open to check the two flags.

Differences for user input:

- A leading UTF-8 BOM is accepted and removed. The label reader refuses it because write_corpus never writes one.
- Required columns are rfi_id, subject and question. response is optional. Extra columns are ignored. A duplicate column name is an error only for a column that is used.
- The column map is a JSON object whose keys are rfi_id, subject, question or response and whose values are column names in the file. Unknown keys, values that are not non-empty strings, mapped columns missing from the file and two fields on the same column (a mapped field landing on another field's default name too) are errors. Fields that are not in the map keep their default names.
- Blank lines and rows whose cells are all empty (",,") are skipped. An empty or repeated rfi_id is an error with the line number.

Caps, as constants: 32 MiB per CSV file (MAX_BYTES), 4 MiB per text file (MAX_TEXT_BYTES), 100,000 rows and 100,000 characters per field (MAX_FIELD) in io.py. The row cap is five times the largest corpus that generate writes (20,000 RFIs, MAX_N in cli.py). A text file has the lower cap because one text gives one citation list, so memory grows with the number of citations. A file over a cap is refused, never cut. The csv module has its own field limit of 131,072 characters; it is reported with the same message as MAX_FIELD. Columns that are not used are not checked against MAX_FIELD, only against that csv limit and MAX_BYTES.

Memory. scripts/make_bench_inputs.py writes the two worst cases (deterministic, standard library only): worst.txt, 4 MiB of "IEEE 1547 and " repeated (about 300,000 citations), and dense.csv, a CSV of about 32 MiB with 56,696 rows and about 1.4 million citations. Commands:

```
python scripts/make_bench_inputs.py bench/
/usr/bin/time -l rfikit extract bench/worst.txt > /dev/null
/usr/bin/time -l rfikit extract bench/dense.csv --out bench/out.csv
```

Measured on macOS 27.2.1, arm64, Python 3.13.13, one run each: worst.txt peak 213,008,384 bytes (maximum resident set size), 2.3 s; dense.csv peak 225,460,224 bytes, 13.8 s. Timings vary by machine and by run: earlier runs of the CSV case took 11.2 s and 15.1 s. Extract writes in batches, so output size does not add to the peak; the input text and the citation list of one text do.

Output files. extract --out and evaluate --json write to a temporary file in the target folder (mkstemp, which uses O_EXCL) and then os.replace it onto the target, so a failure never leaves a half file and an existing file is replaced. A target that is a symbolic link or not a regular file is refused. A new file gets mode 0666 minus the umask, and an existing target keeps its mode. For extract, a target that is the same file as the input or the column map (samefile, so a hard link counts) is refused. For evaluate, a --json path is refused when it, or any folder above it, is the DATA or --written folder (compared with samefile, so a path with different letter case on a case-insensitive filesystem is caught too). These checks run before any work starts, also before extract reads its input. A --json path is checked through both its path as typed and its resolved path, so a link inside DATA that points elsewhere and a link elsewhere that points into a subfolder of DATA are both refused. A symbolic link as the parent folder is accepted, as in the label reader: the caller picks the folder. On stdout, extract writes UTF-8 bytes with \n line ends to sys.stdout.buffer, and a closed pipe (for example `| head`) ends quietly with exit 1. An error in the middle of a CSV can come after some rows were printed to stdout; with --out nothing is left.

generate --out. generate writes only into a new or empty folder; any existing folder that is not empty is refused, with no exception for an earlier corpus. The check never reads manifest.json, so a crafted manifest cannot change it. write_corpus writes each file to a temporary file and replaces the target, so it never writes through a hard link. A failure in the middle of write_corpus can leave some files, so empty the folder or pick a new one before running again. n is 1 to 20,000 and the seed must not be negative.

Formula escape. A cell is written with a leading single quote when it starts with a tab, carriage return or line feed, or when, after leading white space and invisible characters (Unicode categories Cc and Cf) are skipped, it starts with =, +, - or @ or with the fullwidth forms U+FF1D, U+FF0B, U+FF0D or U+FF20. The function is report.escape_cell and report.csv_chunk applies it to every cell, the header and the user's rfi_id included. The rule is applied to every column, so a new column cannot skip it. tests/test_io.py (test_escape_cell) checks every escape character.

Sharing with evaluate. evaluate._read_rows stays as it is. It raises LabelError, refuses a BOM, and requires a fixed header, and its output feeds measured.json. Sharing the byte reading would tie the two error types and the BOM rules together, so a change for user files could move a published number. The duplication is small and each reader has its own tests.

Command line. argparse with one subcommand per command: extract, generate, evaluate and analyze (analyze is in ADR 10). evaluate runs evaluate(data, written, EvalPlan()) without baselines and prints the numbers from measured.summarize, so the terminal and measured.json agree. Both folders must exist. The table prints n/a for an undefined value, and for a level a method lacks (baselines have strict and overlap only, see ADR 8); that second case is only visible through the API, since the CLI runs no baselines. A set with no scorable RFIs prints one line instead of a table. The last line says "Measured on synthetic data." only when every folder scored has a manifest.json with "synthetic": true (write_corpus and heldout both write one); otherwise it says "Scored on the labeled folders given."

Exit codes: 0 ok, 1 input error (one line on stderr starting with "rfikit:", no traceback), 2 usage error (argparse). A file whose name does not end in .csv (any case) is read as plain text, in column "text" with an empty rfi_id. Passing --column-map with such a file is refused. Error messages for output folders name the folder only. An error that evaluate reaches in a label file is shown with each folder's last name and one hint to check the label format (docs/annotation_guide.md).

## Options considered

- Reject a BOM like the label reader. Excel writes one when a user saves as CSV UTF-8 (check: the first three bytes are EF BB BF), so users would hit it often.
- Use the csv module's field size limit instead of a constant. It is global state and gives a less clear message.
- Escape only the text cell. A user rfi_id can start with =, so every cell is escaped.
- One shared reader. See "Sharing with evaluate".
- Refuse a symbolic link as a parent folder. Not done; the caller picks the folder.

## Consequences

An escaped cell is changed, so a program that reads the extract output back sees the leading quote on a cell that began with one of the listed characters. The output is for people and spreadsheets. The caps may need a flag later if a user has a larger export. Peak memory of a large text is about 213 MB (213,008,384 bytes on the machine in the Memory section); a streaming scanner would lower it and is not planned.
