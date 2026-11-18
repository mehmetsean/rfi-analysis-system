import argparse
import json
import os
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any

from rfikit import __version__
from rfikit.cite import extract, extract_rfi
from rfikit.evaluate import EvalPlan, LabelError, evaluate
from rfikit.io import (
    WRITE_HINT,
    InputError,
    atomic_text,
    check_output,
    check_outside,
    iter_rfis,
    read_column_map,
    read_text,
    shown,
)
from rfikit.measured import HEAD_LEVELS, summarize
from rfikit.report import (
    CITATION_HEADER,
    analyze_to,
    citation_row,
    csv_batches,
    csv_chunk,
)
from rfikit.synth import GenParams, generate, write_corpus
from rfikit.synth.files import UnsafeOutput
from rfikit.types import Rfi

MAX_N = 20_000
SYNTHETIC_LINE = "Measured on synthetic data."
OTHER_LINE = "Scored on the labeled folders given."

Json = dict[str, Any]


def extract_chunks(path: Path, column_map: Path | None) -> Iterator[str]:
    if path.suffix.lower() != ".csv" and column_map is not None:
        raise InputError(
            "--column-map works only with a .csv file, drop it or pass a .csv file"
        )
    if path.suffix.lower() == ".csv":
        names = read_column_map(column_map) if column_map else None
        rfis = iter_rfis(path, names)
        return _chunks(_csv_rows(rfis))
    text = read_text(path)
    return _chunks(citation_row("", c) for c in extract(text, "text"))


def _csv_rows(rfis: Iterable[Rfi]) -> Iterator[list[str]]:
    for rfi in rfis:
        for c in extract_rfi(rfi):
            yield citation_row(rfi.rfi_id, c)


def _chunks(rows: Iterable[list[str]]) -> Iterator[str]:
    yield csv_chunk([list(CITATION_HEADER)])
    yield from csv_batches(rows)


def _quiet_stdout() -> None:
    try:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    except (OSError, ValueError, AttributeError):
        pass


def stream_stdout(chunks: Iterable[str]) -> int:
    try:
        out = sys.stdout.buffer
        for chunk in chunks:
            out.write(chunk.encode("utf-8"))
        out.flush()
    except BrokenPipeError:
        _quiet_stdout()
        return 1
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    path = Path(args.file)
    protected = [path] if args.column_map is None else [path, args.column_map]
    if args.out is not None:
        check_output(args.out, protected)
    chunks = extract_chunks(path, args.column_map)
    if args.out is None:
        return stream_stdout(chunks)
    with atomic_text(args.out, protected) as handle:
        for chunk in chunks:
            handle.write(chunk)
    return 0


def read_manifest(folder: Path) -> Json | None:
    try:
        data = json.loads(read_text(folder / "manifest.json"))
    except (InputError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def is_synthetic(folder: Path) -> bool:
    manifest = read_manifest(folder)
    return manifest is not None and manifest.get("synthetic") is True


def check_folder(out: Path) -> None:
    if out.is_symlink() or not out.is_dir():
        return
    try:
        filled = any(out.iterdir())
    except OSError:
        raise InputError(
            f"{shown(out)}: folder cannot be written, {WRITE_HINT}"
        ) from None
    if filled:
        raise InputError(
            f"{shown(out)}: folder is not empty, pick an empty or new folder"
        )


def cmd_generate(args: argparse.Namespace) -> int:
    if args.seed < 0:
        raise InputError("--seed must not be negative, pass 0 or a larger whole number")
    if not 1 <= args.n <= MAX_N:
        raise InputError(
            f"--n must be between 1 and {MAX_N}, pass a number in that range"
        )
    check_folder(args.out)
    corpus = generate(args.seed, args.n, GenParams())
    try:
        write_corpus(corpus, args.out)
    except OSError:
        raise InputError(
            f"{shown(args.out)}: folder cannot be written, {WRITE_HINT}"
        ) from None
    print(
        f"Wrote {len(corpus.rfis)} synthetic RFIs (seed {args.seed}) "
        f"to {shown(args.out)}"
    )
    return 0


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def render_summary(summary: Json, synthetic: bool = True) -> str:
    lines: list[str] = []
    leak = summary["leak"]
    for set_name, block in summary["sets"].items():
        if block["methods"]["rfikit"]["rfis"] == 0:
            lines.append(
                f"Set {set_name}: no RFIs to score "
                "(none left after the leak check, or the folder has none)"
            )
            lines.append("")
            continue
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
    lines.append(SYNTHETIC_LINE if synthetic else OTHER_LINE)
    return "\n".join(lines) + "\n"


def need_folder(path: Path) -> None:
    if not path.is_dir():
        raise InputError(f"{shown(path)}: not a folder, check the path")


LABEL_HINT = (
    "check that the folder was written by rfikit generate or follows the "
    "label format in docs/annotation_guide.md"
)
LINK_HINT = "replace the link with a real file"


def label_hint(message: str) -> str:
    return LINK_HINT if message.endswith("symbolic links are not read") else LABEL_HINT


def run_evaluate(folders: list[Path], written: Path | None) -> Json:
    try:
        return summarize(evaluate(folders[0], written, EvalPlan()))
    except LabelError as error:
        names = " and ".join(shown(folder) for folder in folders)
        raise InputError(f"{names}: {error}, {label_hint(str(error))}") from None


def cmd_evaluate(args: argparse.Namespace) -> int:
    folders = [args.data]
    if args.written is not None:
        folders.append(args.written)
    for folder in folders:
        need_folder(folder)
    if args.json is not None:
        check_output(args.json)
        check_outside(args.json, folders)
    summary = run_evaluate(folders, args.written)
    synthetic = all(is_synthetic(folder) for folder in folders)
    sys.stdout.write(render_summary(summary, synthetic))
    if args.json is not None:
        with atomic_text(args.json) as handle:
            handle.write(json.dumps(summary, sort_keys=True, indent=1) + "\n")
    return 0


def check_analysis_folder(out: Path) -> None:
    if out.is_symlink():
        raise InputError(
            f"{shown(out)}: output is a symbolic link, pick a plain folder"
        )
    if out.exists() and not out.is_dir():
        raise InputError(f"{shown(out)}: output is not a folder, pick a new folder")
    check_folder(out)


def cmd_analyze(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if path.suffix.lower() != ".csv":
        raise InputError(
            f"{shown(path)}: analyze reads a .csv file, "
            "save the RFI export as CSV and pass that file"
        )
    check_analysis_folder(args.out)
    names = read_column_map(args.column_map) if args.column_map else None
    created = make_folders(args.out)
    protected = [path] if args.column_map is None else [path, args.column_map]
    written: list[Path] = []
    try:
        result = analyze_to(
            args.out, iter_rfis(path, names), args.synthetic, protected, written
        )
    except BaseException:
        clean_up(written, created)
        raise
    print(
        f"Analyzed {result.rfis_read} RFIs, {result.citation_total} citations, "
        f"wrote 4 files to {shown(args.out)}"
    )
    return 0


def clean_up(written: list[Path], created: list[Path]) -> None:
    for path in written:
        try:
            os.unlink(path)
        except OSError:
            pass
    for folder in reversed(created):
        try:
            folder.rmdir()
        except OSError:
            pass


def make_folders(out: Path) -> list[Path]:
    missing: list[Path] = []
    here = out
    while not os.path.lexists(here) and here.parent != here:
        missing.append(here)
        here = here.parent
    created: list[Path] = []
    for folder in reversed(missing):
        try:
            folder.mkdir()
            created.append(folder)
        except FileExistsError:
            if folder.is_symlink() or not folder.is_dir():
                clean_up([], created)
                raise InputError(
                    f"{shown(folder)}: output is not a folder, pick a new folder"
                ) from None
        except OSError:
            clean_up([], created)
            raise InputError(
                f"{shown(out)}: folder cannot be written, {WRITE_HINT}"
            ) from None
    try:
        check_analysis_folder(out)
    except InputError:
        clean_up([], created)
        raise
    return created


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
    p = sub.add_parser("analyze", help="write citations and an analysis of an export")
    p.add_argument("file", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--column-map", type=Path)
    p.add_argument("--synthetic", action="store_true")
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
        print("Commands: extract, generate, evaluate, analyze.")
        return 0
    try:
        code: int = args.run(args)
    except (InputError, LabelError, UnsafeOutput) as error:
        print(f"rfikit: {error}", file=sys.stderr)
        return 1
    return code
