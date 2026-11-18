from pathlib import Path

import pytest
from make_bench_inputs import main, write_csv, write_text

from rfikit.io import read_rfis, read_text


def test_small_inputs_are_deterministic(tmp_path: Path) -> None:
    write_text(tmp_path / "a.txt", 140)
    write_text(tmp_path / "b.txt", 140)
    assert (tmp_path / "a.txt").read_bytes() == (tmp_path / "b.txt").read_bytes()
    assert read_text(tmp_path / "a.txt") == "IEEE 1547 and " * 10
    rows = write_csv(tmp_path / "a.csv", 5000)
    assert write_csv(tmp_path / "b.csv", 5000) == rows
    assert len(read_rfis(tmp_path / "a.csv")) == rows
    assert rows > 1


def test_refuses_existing_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sizes = ["--text-bytes", "140", "--csv-bytes", "5000"]
    assert main([str(tmp_path), *sizes]) == 0
    capsys.readouterr()
    before = (tmp_path / "worst.txt").read_bytes()
    assert main([str(tmp_path), *sizes]) == 1
    err = capsys.readouterr().err
    assert len(err.splitlines()) == 1
    assert "already exists" in err
    assert (tmp_path / "worst.txt").read_bytes() == before
