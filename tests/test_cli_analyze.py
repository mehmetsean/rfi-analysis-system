import json
from pathlib import Path

import pytest

from rfikit.cli import main

CSV = (
    "rfi_id,subject,question,response\n"
    "R1,IEEE 80 and IEEE 80-2013,Check ASTM A123,\n"
    "R2,Nothing here,See NEMA TC 2,\n"
)
FILES = ["README.txt", "analysis.html", "analysis.md", "citations.csv"]


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def names(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


def test_analyze_writes_four_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out)]) == 0
    assert capsys.readouterr().out == (
        "Analyzed 2 RFIs, 4 citations, wrote 4 files to results\n"
    )
    assert names(out) == FILES
    assert "| RFIs read | 2 |" in (out / "analysis.md").read_text(encoding="utf-8")
    assert "synthetic" not in (out / "README.txt").read_text(encoding="utf-8").lower()


def test_analyze_citations_match_extract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "results"
    assert main(["extract", str(source)]) == 0
    extracted = capsys.readouterr().out
    assert main(["analyze", str(source), "--out", str(out)]) == 0
    assert (out / "citations.csv").read_text(encoding="utf-8") == extracted


def test_analyze_column_map_and_bom(tmp_path: Path) -> None:
    text = "No,Title,Body\nR1,IEEE 80,x\n"
    source = tmp_path / "rfis.csv"
    source.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    names_map = {"rfi_id": "No", "subject": "Title", "question": "Body"}
    mapping = write(tmp_path / "map.json", json.dumps(names_map))
    out = tmp_path / "results"
    argv = ["analyze", str(source), "--out", str(out), "--column-map", str(mapping)]
    assert main(argv) == 0
    assert "| IEEE 80 | 1 |" in (out / "analysis.md").read_text(encoding="utf-8")


def test_analyze_synthetic_flag(tmp_path: Path) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out), "--synthetic"]) == 0
    assert (
        (out / "README.txt").read_text(encoding="utf-8").startswith("Synthetic data.")
    )


def test_analyze_zero_rfis(tmp_path: Path) -> None:
    source = write(tmp_path / "rfis.csv", "rfi_id,subject,question\n")
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out)]) == 0
    assert "No citations found." in (out / "analysis.md").read_text(encoding="utf-8")
    assert (out / "citations.csv").read_text(encoding="utf-8").count("\n") == 1


def test_analyze_creates_nested_and_uses_empty_folder(tmp_path: Path) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    nested = tmp_path / "a" / "b"
    assert main(["analyze", str(source), "--out", str(nested)]) == 0
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["analyze", str(source), "--out", str(empty)]) == 0
    assert names(empty) == FILES


def test_analyze_refuses_nonempty_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out)]) == 0
    capsys.readouterr()
    assert main(["analyze", str(source), "--out", str(out)]) == 1
    assert capsys.readouterr().err == (
        "rfikit: results: folder is not empty, pick an empty or new folder\n"
    )
    assert names(out) == FILES


def test_analyze_never_touches_input_in_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "results"
    out.mkdir()
    source = write(out / "citations.csv", CSV)
    assert main(["analyze", str(source), "--out", str(out)]) == 1
    assert "not empty" in capsys.readouterr().err
    assert source.read_text(encoding="utf-8") == CSV


def test_analyze_refuses_symlink_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    assert main(["analyze", str(source), "--out", str(link)]) == 1
    assert capsys.readouterr().err == (
        "rfikit: link: output is a symbolic link, pick a plain folder\n"
    )
    assert names(real) == []


def test_analyze_refuses_file_as_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    other = write(tmp_path / "out", "keep")
    assert main(["analyze", str(source), "--out", str(other)]) == 1
    assert capsys.readouterr().err == (
        "rfikit: out: output is not a folder, pick a new folder\n"
    )
    assert other.read_text(encoding="utf-8") == "keep"


def test_analyze_unwritable_parent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    blocker = write(tmp_path / "blocker", "x")
    assert main(["analyze", str(source), "--out", str(blocker / "sub")]) == 1
    assert "sub: folder cannot be written" in capsys.readouterr().err


def test_analyze_refuses_text_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "notes.txt", "IEEE 80")
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out)]) == 1
    assert capsys.readouterr().err == (
        "rfikit: notes.txt: analyze reads a .csv file, "
        "save the RFI export as CSV and pass that file\n"
    )
    assert not out.exists()


def test_analyze_bad_input_leaves_no_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", "rfi_id,subject\nR1,x\n")
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out)]) == 1
    assert capsys.readouterr().err.startswith("rfikit: rfis.csv")
    assert not out.exists()


def test_analyze_missing_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "results"
    assert main(["analyze", str(tmp_path / "no.csv"), "--out", str(out)]) == 1
    assert "no.csv: file is missing" in capsys.readouterr().err
    assert not out.exists()


def test_analyze_bad_column_map(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    mapping = write(tmp_path / "map.json", "[]")
    out = tmp_path / "results"
    assert (
        main(["analyze", str(source), "--out", str(out), "--column-map", str(mapping)])
        == 1
    )
    assert capsys.readouterr().err.startswith("rfikit: map.json")
    assert not out.exists()


def test_analyze_needs_out(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["analyze", "x.csv"]) == 2
    assert "usage" in capsys.readouterr().err


def test_analyze_escapes_formula_ids(tmp_path: Path) -> None:
    source = write(tmp_path / "rfis.csv", "rfi_id,subject,question\n=A1,IEEE 80,\n")
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out)]) == 0
    text = (out / "citations.csv").read_text(encoding="utf-8")
    assert text.splitlines()[1].startswith("'=A1,")
