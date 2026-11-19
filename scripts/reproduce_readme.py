"""Check the numbers in README.md against files and a fresh run.

python scripts/reproduce_readme.py          rewrites the numbers block
python scripts/reproduce_readme.py --check  exits 1 if the README is out of date
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
MEASURED = ROOT / "src" / "rfikit" / "measured.json"
CLI = ROOT / "docs" / "cli.md"
BENCH = ROOT / "docs" / "benchmark.md"
ADR10 = ROOT / "docs" / "adr" / "0010-analyze-output-folder.md"
START = "<!-- numbers:start -->"
END = "<!-- numbers:end -->"
SETS = [("A", "Set A"), ("B", "Set B"), ("written", "Written set")]
LEVELS = [("strict", "Strict"), ("overlap", "Overlap")]

CODE = "import sys; from rfikit.cli import main; sys.exit(main())"

Json = dict[str, Any]


def level_rates(doc: Json, set_name: str, level: str) -> tuple[float, float]:
    found = doc["full"]["sets"][set_name]["methods"]["rfikit"]["levels"][level]
    return float(found["precision"]), float(found["recall"])


def build_block(doc: Json) -> str:
    lines = [
        START,
        "| Level | Set | Precision | Recall |",
        "|---|---|---|---|",
    ]
    for level, level_label in LEVELS:
        for set_name, set_label in SETS:
            p, r = level_rates(doc, set_name, level)
            lines.append(f"| {level_label} | {set_label} | {p:.3f} | {r:.3f} |")
    lines.append(END)
    return "\n".join(lines)


def replace_block(text: str, block: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit("README.md has no numbers block")
    return pattern.sub(lambda _m: block, text)


def check_limits(text: str) -> list[str]:
    from rfikit import io

    wanted = {
        "32 MiB": io.MAX_BYTES == 32 * io.MIB,
        "4 MiB": io.MAX_TEXT_BYTES == 4 * io.MIB,
        "100,000 rows": io.MAX_ROWS == 100_000,
        "100,000 characters": io.MAX_FIELD == 100_000,
    }
    problems = []
    for phrase, ok in wanted.items():
        if phrase not in text:
            problems.append(f"README does not state {phrase}")
        elif not ok:
            problems.append(f"README says {phrase} but src/rfikit/io.py differs")
    return problems


def check_memory(text: str) -> list[str]:
    adr = ADR10.read_text(encoding="utf-8")
    problems = []
    for number in re.findall(r"\b\d{3},\d{3},\d{3}\b", text):
        if number not in adr:
            problems.append(f"{number} is not in {ADR10.name}")
    return problems


def check_benchmark(doc: Json) -> list[str]:
    problems = []
    for set_name, label in (("A", "seed corpus A"), ("written", "written set")):
        p, r = level_rates(doc, set_name, "strict")
        want = f"| rfikit | {label}"
        rows = [x for x in BENCH.read_text(encoding="utf-8").splitlines()]
        row = [x for x in rows if x.startswith(want)]
        if not row:
            problems.append(f"no rfikit row for {label} in docs/benchmark.md")
        elif f"| {p:.3f} | {r:.3f} |" not in row[0]:
            problems.append(f"strict P and R for {label} differ from benchmark.md")
    return problems


def check_leak(text: str, doc: Json) -> list[str]:
    pool = doc["full"]["leak"]["pool_size"]
    match = re.search(r"Leak check: pool (\d+), A dropped", text)
    if match is None:
        return ["README has no leak check line"]
    problems = []
    if int(match.group(1)) != pool:
        problems.append("pool size in README differs from measured.json")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "data"
        cli = [sys.executable, "-c", CODE]
        subprocess.run(
            [*cli, "generate", "--seed", "42", "--n", "600", "--out", str(out)],
            check=True,
            capture_output=True,
        )
        run = subprocess.run(
            [*cli, "evaluate", str(out)], check=True, capture_output=True, text=True
        )
    line = [x for x in run.stdout.splitlines() if x.startswith("Leak check")]
    if not line or line[0] not in text:
        problems.append("leak check line in README differs from a fresh run")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    doc: Json = json.loads(MEASURED.read_text(encoding="utf-8"))
    text = README.read_text(encoding="utf-8")
    fresh = replace_block(text, build_block(doc))
    if not args.check:
        README.write_text(fresh, encoding="utf-8")
        text = fresh
    problems = []
    if fresh != text:
        problems.append("numbers block in README.md is out of date")
    both = text + "\n" + CLI.read_text(encoding="utf-8")
    problems += check_limits(both)
    problems += check_memory(both)
    problems += check_benchmark(doc)
    problems += check_leak(both, doc)
    for problem in problems:
        print(f"reproduce_readme: {problem}")
    if problems:
        return 1
    print("README numbers match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
