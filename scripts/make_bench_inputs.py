"""Write the two worst-case input files used for the extract memory numbers in ADR 9.

python scripts/make_bench_inputs.py OUTDIR [--text-bytes N] [--csv-bytes N]
"""

import argparse
import csv
import sys
from pathlib import Path

MIB = 1024 * 1024
UNIT = "IEEE 1547 and "
QUESTION = "See IEEE 1547 and NESC 2017 rule 250.B please " * 12


def write_text(path: Path, size: int) -> None:
    count = size // len(UNIT)
    path.write_text(UNIT * count, encoding="utf-8", newline="")


def write_csv(path: Path, size: int) -> int:
    rows = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["rfi_id", "subject", "question", "response"])
        while handle.tell() < size - 2000:
            rows += 1
            subject = "Subject about IEEE 1547-2018"
            writer.writerow([f"R{rows}", subject, QUESTION, "ok"])
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--text-bytes", type=int, default=4 * MIB)
    parser.add_argument("--csv-bytes", type=int, default=32 * MIB)
    args = parser.parse_args(argv)
    for name in ("worst.txt", "dense.csv"):
        if (args.outdir / name).exists():
            print(
                f"{name} already exists in {args.outdir.name}, pick a new folder",
                file=sys.stderr,
            )
            return 1
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_text(args.outdir / "worst.txt", args.text_bytes)
    rows = write_csv(args.outdir / "dense.csv", args.csv_bytes)
    print(f"Wrote worst.txt and dense.csv ({rows} rows) to {args.outdir.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
