import argparse
import csv
import sys
from pathlib import Path

HEADER = ["rfi_id", "subject", "question", "response"]
MANY = ("rfis_100k.csv", "IEC 61439-1 " * 8, 100_000)
WIDE = ("rfis_110.csv", "IEEE 80 " * 12_499, 110)


def write_file(path: Path, cell: str, rows: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        for number in range(1, rows + 1):
            writer.writerow([f"R{number:06d}", cell, cell, cell])


def build(out: Path, many_rows: int = MANY[2], wide_rows: int = WIDE[2]) -> None:
    if out.is_symlink() or (out.exists() and not out.is_dir()):
        raise SystemExit(f"{out.name}: output is not a plain folder, pick a new folder")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(
            f"{out.name}: folder is not empty, pick an empty or new folder"
        )
    out.mkdir(parents=True, exist_ok=True)
    write_file(out / MANY[0], MANY[1], many_rows)
    write_file(out / WIDE[0], WIDE[1], wide_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the two CSV files for the analyze memory numbers (ADR 10)."
    )
    parser.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    build(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
