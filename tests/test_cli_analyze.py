import json
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, TextIO

import pytest

from rfikit import io as rio
from rfikit.cli import clean_up, main, make_folders
from rfikit.io import InputError
from rfikit.types import Rfi

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


def test_analyze_bad_row_midway_leaves_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "rfi_id,subject,question\nR1,IEEE 80,\nR2,x\n"
    source = write(tmp_path / "rfis.csv", text)
    fresh = tmp_path / "fresh"
    assert main(["analyze", str(source), "--out", str(fresh)]) == 1
    assert "line 3" in capsys.readouterr().err
    assert not fresh.exists()
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["analyze", str(source), "--out", str(empty)]) == 1
    assert names(empty) == []


def test_analyze_streams_in_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("rfikit.report.BATCH", 2)
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "results"
    assert main(["analyze", str(source), "--out", str(out)]) == 0
    lines = (out / "citations.csv").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5


def test_failure_removes_only_what_this_run_made(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "fresh"

    def fail(
        folder: Path, rfis: object, synthetic: bool, protected: object, written: object
    ) -> None:
        (folder / "other.txt").write_text("not ours", encoding="utf-8")
        raise InputError("boom, try again")

    monkeypatch.setattr("rfikit.cli.analyze_to", fail)
    assert main(["analyze", str(source), "--out", str(out)]) == 1
    assert "boom" in capsys.readouterr().err
    assert names(out) == ["other.txt"]


def test_interrupt_removes_the_fresh_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "fresh"

    def interrupted(path: Path, names: object) -> Iterator[Rfi]:
        yield Rfi("R1", "IEEE 80", "", "")
        raise KeyboardInterrupt

    monkeypatch.setattr("rfikit.cli.iter_rfis", interrupted)
    with pytest.raises(KeyboardInterrupt):
        main(["analyze", str(source), "--out", str(out)])
    assert not out.exists()


def test_bad_row_removes_every_folder_made(tmp_path: Path) -> None:
    text = "rfi_id,subject,question\nR1,IEEE 80,\nR2,x\n"
    source = write(tmp_path / "rfis.csv", text)
    assert main(["analyze", str(source), "--out", str(tmp_path / "a/b/c/d")]) == 1
    assert not (tmp_path / "a").exists()


def test_existing_parents_are_kept(tmp_path: Path) -> None:
    text = "rfi_id,subject,question\nR1,IEEE 80,\nR2,x\n"
    source = write(tmp_path / "rfis.csv", text)
    (tmp_path / "a").mkdir()
    assert main(["analyze", str(source), "--out", str(tmp_path / "a/b/c")]) == 1
    assert (tmp_path / "a").is_dir()
    assert not (tmp_path / "a" / "b").exists()


def test_late_failure_removes_written_files_from_empty_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "empty"
    out.mkdir()

    def fail(*args: object, **kwargs: object) -> None:
        raise InputError("late failure, try again")

    monkeypatch.setattr("rfikit.report.write_analysis", fail)
    assert main(["analyze", str(source), "--out", str(out)]) == 1
    assert names(out) == []


def test_failure_in_the_last_file_removes_all_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    out = tmp_path / "fresh"
    monkeypatch.setattr("rfikit.report.render_readme", lambda result: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        main(["analyze", str(source), "--out", str(out)])
    assert not out.exists()


def test_folder_made_by_another_process_is_not_ours(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "a" / "b"
    real = Path.mkdir

    def racing(self: Path, *args: Any, **kwargs: Any) -> None:
        if self == out:
            real(self, *args, **kwargs)
        real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", racing)
    created = make_folders(out)
    assert created == [tmp_path / "a"]
    assert out.is_dir()
    clean_up([], created)
    assert out.exists()


def test_make_folders_refuses_a_file_made_in_between(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "a" / "b"
    real = Path.mkdir

    def racing(self: Path, *args: Any, **kwargs: Any) -> None:
        if self == out:
            out.write_text("x", encoding="utf-8")
        real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", racing)
    with pytest.raises(InputError, match="not a folder"):
        make_folders(out)
    assert out.is_file()


def test_make_folders_unwritable(tmp_path: Path) -> None:
    blocker = write(tmp_path / "blocker", "x")
    with pytest.raises(InputError, match="cannot be written"):
        make_folders(blocker / "sub" / "deep")


def test_clean_up_ignores_missing_paths(tmp_path: Path) -> None:
    clean_up([tmp_path / "gone.txt"], [tmp_path / "gone"])


def test_make_folders_refuses_a_folder_filled_in_between(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "a" / "b"
    real = Path.mkdir

    def racing(self: Path, *args: Any, **kwargs: Any) -> None:
        real(self, *args, **kwargs)
        if self == out:
            (out / "x.txt").write_text("x", encoding="utf-8")

    monkeypatch.setattr(Path, "mkdir", racing)
    with pytest.raises(InputError, match="not empty"):
        make_folders(out)
    assert (out / "x.txt").exists()


def test_make_folders_removes_its_folders_when_the_final_check_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(folder: Path) -> None:
        raise InputError("refused, try again")

    monkeypatch.setattr("rfikit.cli.check_analysis_folder", refuse)
    with pytest.raises(InputError, match="refused"):
        make_folders(tmp_path / "a" / "b")
    assert not (tmp_path / "a").exists()


@pytest.mark.parametrize("fail_at", [2, 3, 4])
@pytest.mark.parametrize("existing", [False, True])
def test_late_failures_remove_every_written_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_at: int, existing: bool
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    real = rio.atomic_text
    calls = {"n": 0}

    def counting(
        path: Path, protected: Sequence[Path] = ()
    ) -> AbstractContextManager[TextIO]:
        calls["n"] += 1
        if calls["n"] == fail_at:
            raise InputError("write failed, try again")
        return real(path, protected)

    monkeypatch.setattr("rfikit.report.atomic_text", counting)
    out = tmp_path / "out"
    if existing:
        out.mkdir()
    assert main(["analyze", str(source), "--out", str(out)]) == 1
    assert out.is_dir() if existing else not out.exists()
    if existing:
        assert names(out) == []


def test_dangling_symlink_out_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write(tmp_path / "rfis.csv", CSV)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "nowhere")
    assert main(["analyze", str(source), "--out", str(link)]) == 1
    assert "symbolic link" in capsys.readouterr().err
    assert link.is_symlink()
    assert not (tmp_path / "nowhere").exists()
