# 10. The analyze output folder

Status: Accepted

## Context

analyze writes four files: citations.csv, analysis.md, analysis.html and README.txt. A user can point it at a folder that already holds an earlier run, or by mistake at the folder that holds the export. ADR 9 sets the output rules for the other commands: never overwrite an input file, refuse symbolic links and non-regular targets, write each file with mkstemp and os.replace.

## Options

- Replace only the four file names in any folder. A rerun then works in place, but the folder can hold the input export, and the checks must cover every case (hard links, a folder that is also the input folder, a name that is a directory).
- Refuse any folder that is not empty, as generate does. A rerun needs a new folder or an emptied one. The input file can never be in the folder, so it cannot be overwritten, and one check replaces many.

## Decision

The second option. analyze writes only into a new or empty folder, using the same check_folder as generate (the same message: "folder is not empty, pick an empty or new folder"). A missing folder is created, parents included. A symbolic link as the output folder and an output path that is a file are refused, each with one next step. The checks run before the export is read, and the folder is created only after the export was read and analyzed, so a bad export leaves nothing behind.

Each file is still written by mkstemp and os.replace through io.atomic_text, so write_analysis stays safe when it is called from Python on a folder that is not empty: a symbolic link or a directory under one of the four names is refused, and an optional list of protected files (the CLI passes the export and the column map) is refused when a target is the same file, hard links included. citations.csv uses the same row builder, header and formula escape as extract.

The command accepts only a .csv file, because analyze counts RFIs; a text file has no RFIs. Use extract for text.

## Consequences

A rerun needs a new folder or an emptied one. A failure in the middle of the four writes can leave some of the files, as with generate. The result keeps every citation in memory (extract streams), so the worst case in ADR 9 (about 1.4 million citations) needs more memory with analyze than with extract; it was not measured. The tables are built from counts, so their size does not grow with the export, except the list of RFIs with the most citations, which is capped at 10 rows, and the top keys, capped at 20.

Echoed input (rfi_id) in the Markdown and HTML tables is cut and shown in Python repr form (textnorm.clip), the same as in terminal errors. Markdown cells escape backslash, pipe, backtick, angle brackets, square brackets, asterisk, underscore, ampersand, exclamation mark and tilde, and line breaks become spaces. The HTML escapes every cell with html.escape (quote=True), has no script, no external resource and no event handler, and carries a meta Content-Security-Policy with default-src 'none' and style-src 'unsafe-inline' for its one style element.
