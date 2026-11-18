"""Rebuild or check src/rfikit/measured.json.

python scripts/make_measured.py          rebuild the full and ci blocks
python scripts/make_measured.py --check  recompute the ci block only, exit 1 on a diff
"""

import argparse
import difflib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "src" / "rfikit" / "measured.json"
WRITTEN = ROOT / "heldout"
MAX_DIFF = 30

Json = dict[str, Any]


def baselines() -> Json:
    sys.path.insert(0, str(ROOT / "benchmarks"))
    from prototype_baseline import naive_spans, prototype_spans

    return {"prototype": prototype_spans, "naive": naive_spans}


def compute_ci() -> Json:
    from rfikit.measured import CI_PLAN, build_block

    block: Json = build_block(CI_PLAN, WRITTEN, baselines())
    return block


def compute_doc() -> Json:
    from rfikit.measured import build_doc

    doc: Json = build_doc(WRITTEN, baselines())
    return doc


def lines(block: Json) -> list[str]:
    return json.dumps(block, sort_keys=True, indent=1).splitlines()


def check(target: Path, compute: Callable[[], Json]) -> int:
    stored: Json = json.loads(target.read_text(encoding="utf-8"))["ci"]
    fresh = compute()
    if lines(stored) == lines(fresh):
        print("measured.json ci block is current")
        return 0
    diff = difflib.unified_diff(
        lines(stored), lines(fresh), "stored", "recomputed", lineterm="", n=0
    )
    shown = list(diff)
    print("measured.json ci block differs, run: python scripts/make_measured.py")
    for line in shown[:MAX_DIFF]:
        print(line)
    if len(shown) > MAX_DIFF:
        print(f"... {len(shown) - MAX_DIFF} more diff lines")
    return 1


def rebuild(target: Path, compute: Callable[[], Json]) -> int:
    from rfikit.measured import render

    target.write_text(render(compute()), encoding="utf-8", newline="\n")
    print(f"wrote {target.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        return check(TARGET, compute_ci)
    return rebuild(TARGET, compute_doc)


if __name__ == "__main__":
    sys.exit(main())
