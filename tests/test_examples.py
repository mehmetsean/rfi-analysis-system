import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest
from make_examples import COUNT, TARGET, build, check, files, write

from rfikit.notice import DISCLAIMER, LICENSE_LINE

ROOT = Path(__file__).resolve().parent.parent


def test_examples_match_the_generator() -> None:
    assert check(TARGET) == 0


def test_examples_content() -> None:
    with (TARGET / "rfis.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.reader(handle))) == COUNT + 1
    for name in ("README.txt", "results/README.txt"):
        text = (TARGET / name).read_text(encoding="utf-8")
        assert text.startswith("Synthetic data.")
        assert LICENSE_LINE in text
        assert DISCLAIMER in text
    md = (TARGET / "results" / "analysis.md").read_text(encoding="utf-8")
    assert "| RFIs read | 200 |" in md
    assert "measured on synthetic data" in md


def test_check_reports_a_difference(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "examples"
    write(copy)
    assert check(copy) == 0
    (copy / "results" / "analysis.md").write_text("changed", encoding="utf-8")
    (copy / "extra.txt").write_text("x", encoding="utf-8")
    assert check(copy) == 1
    out = capsys.readouterr().out
    assert "examples/results/analysis.md differs" in out
    assert "examples/extra.txt differs" in out
    assert check(tmp_path / "missing") == 1


def test_build_is_deterministic(tmp_path: Path) -> None:
    build(tmp_path / "a")
    build(tmp_path / "b")
    assert files(tmp_path / "a") == files(tmp_path / "b")


def test_check_passes_under_another_hash_seed() -> None:
    env = {**os.environ, "PYTHONHASHSEED": "12345"}
    script = ROOT / "scripts" / "make_examples.py"
    done = subprocess.run(
        [sys.executable, str(script), "--check"], env=env, check=False
    )
    assert done.returncode == 0
