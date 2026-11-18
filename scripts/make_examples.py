"""Rebuild or check examples/.

python scripts/make_examples.py          rewrite examples/
python scripts/make_examples.py --check  rebuild in a temp folder, exit 1 on a diff
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from rfikit.cli import main as rfikit
from rfikit.notice import DISCLAIMER, LICENSE_LINE

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "examples"
SEED = 42
COUNT = 200
README = "\n".join(
    [
        "Synthetic data. Example input and output of rfikit analyze.",
        "",
        f"rfis.csv is the input of rfikit generate --seed {SEED} --n {COUNT}.",
        "results/ is the output of rfikit analyze on that file:",
        "",
        "rfikit analyze examples/rfis.csv --out results/ --synthetic",
        "",
        "Rebuild or check these files with scripts/make_examples.py.",
        "",
        "License",
        LICENSE_LINE,
        "",
        "Disclaimer",
        DISCLAIMER,
        "",
    ]
)


def build(folder: Path) -> None:
    data = folder / "data"
    if rfikit(["generate", "--seed", str(SEED), "--n", str(COUNT), "--out", str(data)]):
        raise SystemExit("generate failed")
    examples = folder / "examples"
    examples.mkdir()
    shutil.copyfile(data / "input" / "rfis.csv", examples / "rfis.csv")
    (examples / "README.txt").write_bytes(README.encode("utf-8"))
    argv = [
        "analyze",
        str(examples / "rfis.csv"),
        "--out",
        str(examples / "results"),
        "--synthetic",
    ]
    if rfikit(argv):
        raise SystemExit("analyze failed")


def files(folder: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(folder)): p.read_bytes()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def check(target: Path) -> int:
    with tempfile.TemporaryDirectory() as temp:
        build(Path(temp))
        want = files(Path(temp) / "examples")
    have = files(target) if target.is_dir() else {}
    bad = sorted(n for n in want.keys() | have.keys() if want.get(n) != have.get(n))
    for name in bad:
        print(f"examples/{name} differs, run python scripts/make_examples.py")
    return 1 if bad else 0


def write(target: Path) -> int:
    with tempfile.TemporaryDirectory() as temp:
        build(Path(temp))
        for name, data in files(Path(temp) / "examples").items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return check(TARGET) if args.check else write(TARGET)


if __name__ == "__main__":
    sys.exit(main())
