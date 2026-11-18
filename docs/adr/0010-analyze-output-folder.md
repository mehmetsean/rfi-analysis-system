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

A rerun needs a new folder or an emptied one. A failure in the middle of the four writes can leave some of the files, as with generate. When the folder did not exist before the run and the export fails to read (for example a bad row in the middle of the file), the empty folder is removed again with a plain rmdir.

Memory. analyze runs one pass over the RFIs. analyze(rfis, synthetic, sink) calls the optional sink with each (rfi_id, citation) as it is found and keeps only counters: base key counts, body counts, a histogram of citations per RFI, the 10 RFIs with the most citations, the totals and the set of rfi_ids (a repeated id raises ValueError, the same rule as the reader). AnalysisResult holds those counters and no citations. report.analyze_to(out, rfis, synthetic, protected) passes a sink that writes the rows of citations.csv in batches through the same atomic temp file, then calls write_analysis for the three report files, so the counts have one source, the analyze loop. A first version kept every citation and measured 1.53 GB peak for 2.7 million citations and 2.37 GB for 4.14 million (about 570 bytes per citation).

Measured on this Mac (macOS 27.2.1 arm64, Python 3.13.13, one run each, /usr/bin/time -l, peak is the maximum resident set size), on two crafted CSV files with the columns rfi_id, subject, question and response:

- 100,000 rows, each text cell "IEC 61439-1 " repeated 8 times (30 MB, 2,400,000 citations): peak 242,532,352 bytes, 32 s.
- 110 rows, each text cell "IEEE 80 " repeated 12,499 times (33 MB, 4,124,670 citations): peak 270,925,824 bytes, 55 s.

The input text itself (up to 32 MiB) and the rfi_ids are in memory, so the peak does not go to zero. It no longer grows with the number of citations. Timings vary by machine and by run.

The top keys table is capped at 20 rows and the RFIs with the most citations table at 10. The body table has one row per body, and the citations per RFI table has one row per distinct count, so neither grows with the number of RFIs.

Echoed input (rfi_id) in the Markdown and HTML tables is cut to 40 characters, with "..." added when cut, and control, format and line separator characters (Unicode categories Cc, Cf, Zl and Zp, which include the bidi controls) become a space (report.short_cell). No repr form is used there, so an id shows as the user wrote it; terminal error lines keep textnorm.clip. Markdown cells escape backslash, pipe, backtick, angle brackets, square brackets, asterisk, underscore, ampersand, exclamation mark and tilde, line breaks become spaces, and the scheme colon of http, https and ftp and the dot of a www. prefix get a backslash so extended autolinks do not form. The HTML escapes every cell with html.escape (quote=True), has no script, no external resource and no event handler, and carries a meta Content-Security-Policy with default-src 'none' and style-src 'unsafe-inline' for its one style element.

A base key of NESC with no rule, table or section (an edition alone, as in "2002 NESC") is shown in the tables as "NESC (no rule given)" with a note, because it counts mentions and not one rule. citations.csv keeps the key as it is.

CSV cells. Every cell of citations.csv and of extract output goes through report.plain_cell before the formula escape: C0 controls other than tab, carriage return and line feed, DEL and C1 controls are written as a backslash, x and two hex digits, so cat of the file cannot send an escape sequence to a terminal. Bidi control characters are left as they are in the CSV files, because they can be part of real text; the tables replace them with a space.
