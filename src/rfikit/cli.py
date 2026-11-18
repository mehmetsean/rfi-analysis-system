import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rfikit import __version__
from rfikit.cite import extract, extract_rfi
from rfikit.evaluate import EvalPlan, LabelError, evaluate
from rfikit.io import InputError, read_column_map, read_rfis, read_text
from rfikit.measured import HEAD_LEVELS, summarize
from rfikit.report import csv_text
from rfikit.synth import GenParams, generate, write_corpus
from rfikit.synth.files import UnsafeOutput
from rfikit.types import Citation

EXTRACT_HEADER = (
    "rfi_id",
    "column",
    "start",
    "end",
    "text",
    "key",
    "base_key",
    "body",
    "clause_start",
    "clause_end",
    "inferred",
)
MAX_N = 20_000
SYNTHETIC_LINE = "Measured on synthetic data."

Json = dict[str, Any]


def _number(value: int | None) -> str:
    return "" if value is None else str(value)


def _row(rfi_id: str, c: Citation) -> list[str]:
    d = c.designation
    return [
        rfi_id,
        c.column,
        str(c.start),
        str(c.end),
        c.text,
        d.key(),
        d.base_key(),
        d.body,
        _number(c.clause_start),
        _number(c.clause_end),
        "1" if c.inferred else "0",
    ]


def extract_rows(path: Path, column_map: Path | None) -> list[list[str]]:
    rows: list[list[str]] = []
    if path.suffix.lower() == ".csv":
        names = read_column_map(column_map) if column_map else None
        for rfi in read_rfis(path, names):
            rows.extend(_row(rfi.rfi_id, c) for c in extract_rfi(rfi))
    else:
        rows.extend(_row("", c) for c in extract(read_text(path), "text"))
    return rows


def write_output(path: Path, text: str) -> None:
    if path.is_symlink():
        raise InputError(f"{path.name}: output is a symbolic link, pick another file")
    try:
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    except OSError:
        raise InputError(f"{path.name}: file cannot be written") from None


def cmd_extract(args: argparse.Namespace) -> int:
    rows = extract_rows(Path(args.file), args.column_map)
    text = csv_text(EXTRACT_HEADER, rows)
    if args.out is None:
        sys.stdout.write(text)
    else:
        write_output(args.out, text)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    if not 1 <= args.n <= MAX_N:
        raise InputError(f"--n must be between 1 and {MAX_N}")
    corpus = generate(args.seed, args.n, GenParams())
    try:
        write_corpus(corpus, args.out)
    except OSError:
        raise InputError(f"{args.out.name}: folder cannot be written") from None
    print(f"Wrote {len(corpus.rfis)} synthetic RFIs (seed {args.seed}) to {args.out}")
    return 0


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def render_summary(summary: Json) -> str:
    lines: list[str] = []
    leak = summary["leak"]
    for set_name, block in summary["sets"].items():
        lines.append(f"Set {set_name}")
        lines.append(
            f"{'method':<12}{'level':<9}{'precision':>10}{'recall':>8}{'F1':>8}"
        )
        for method, found in block["methods"].items():
            for level in HEAD_LEVELS:
                got = found["levels"].get(level, {})
                cells = [_fmt(got.get(k)) for k in ("precision", "recall", "f1")]
                lines.append(
                    f"{method:<12}{level:<9}{cells[0]:>10}{cells[1]:>8}{cells[2]:>8}"
                )
        lines.append("")
    parts = [f"pool {leak['pool_size']}"]
    for name in ("A", "B"):
        if name in leak:
            parts.append(
                f"{name} dropped {leak[name]['dropped']} of {leak[name]['rfis']}"
            )
    lines.append("Leak check: " + ", ".join(parts))
    lines.append(SYNTHETIC_LINE)
    return "\n".join(lines) + "\n"


def cmd_evaluate(args: argparse.Namespace) -> int:
    report = evaluate(args.data, args.written, EvalPlan())
    summary = summarize(report)
    sys.stdout.write(render_summary(summary))
    if args.json is not None:
        write_output(args.json, json.dumps(summary, sort_keys=True, indent=1) + "\n")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    print("The command analyze is not built yet.", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rfikit")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("extract", help="list the standard citations in a file")
    p.add_argument("file", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--column-map", type=Path)
    p.set_defaults(run=cmd_extract)
    p = sub.add_parser("generate", help="write a synthetic corpus")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(run=cmd_generate)
    p = sub.add_parser("evaluate", help="score the extractor on labeled data")
    p.add_argument("data", type=Path)
    p.add_argument("--written", type=Path)
    p.add_argument("--json", type=Path)
    p.set_defaults(run=cmd_evaluate)
    p = sub.add_parser("analyze", help="not built yet")
    p.add_argument("rest", nargs="*")
    p.set_defaults(run=cmd_analyze)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return stop.code if isinstance(stop.code, int) else 2
    if args.version:
        print(__version__)
        return 0
    if args.command is None:
        print(f"rfikit {__version__}")
        print("Commands: extract, generate, evaluate.")
        print("The command analyze is not built yet.")
        return 0
    try:
        code: int = args.run(args)
    except (InputError, LabelError, UnsafeOutput) as error:
        print(f"rfikit: {error}", file=sys.stderr)
        return 1
    return code
