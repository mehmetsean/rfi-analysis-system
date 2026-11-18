import csv
from pathlib import Path

import pytest
from make_analyze_inputs import MANY, WIDE, build, main

from rfikit.analyze import analyze
from rfikit.io import read_rfis


def test_defaults_match_the_adr() -> None:
    assert MANY[2] == 100_000 and MANY[1] == "IEC 61439-1 " * 8
    assert WIDE[2] == 110 and WIDE[1] == "IEEE 80 " * 12_499
    assert len(WIDE[1]) < 100_000


def test_small_build(tmp_path: Path) -> None:
    out = tmp_path / "bench"
    build(out, 3, 2)
    with (out / "rfis_100k.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["rfi_id", "subject", "question", "response"]
    assert rows[1] == ["R000001", MANY[1], MANY[1], MANY[1]]
    assert len(rows) == 4
    wide = read_rfis(out / "rfis_110.csv")
    assert len(wide) == 2
    assert analyze(wide).citation_total == 2 * 3 * 12_499


def test_refuses_a_folder_with_files(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="not empty"):
        build(tmp_path, 1, 1)


def test_main_writes_default_row_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("make_analyze_inputs.build.__defaults__", (2, 1))
    assert main([str(tmp_path / "o")]) == 0
    assert sorted(p.name for p in (tmp_path / "o").iterdir()) == [
        "rfis_100k.csv",
        "rfis_110.csv",
    ]
