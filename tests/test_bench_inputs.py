from pathlib import Path

from make_bench_inputs import write_csv, write_text

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
