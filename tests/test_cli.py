import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from prototype_baseline import naive_spans, prototype_spans

from rfikit import __version__, cli
from rfikit.cli import EXTRACT_HEADER, MAX_N, main, render_summary
from rfikit.evaluate import EvalPlan, evaluate_seeds
from rfikit.measured import summarize
from rfikit.synth import generate, render_files

ROOT = Path(__file__).resolve().parent.parent
HELDOUT = ROOT / "heldout"


def test_no_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "analyze is not built yet" in out


def test_analyze_stub(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["analyze", "x"]) == 1
    captured = capsys.readouterr()
    assert captured.err == (
        "rfikit: the command analyze is not built yet, "
        "use extract, generate or evaluate\n"
    )
    assert captured.out == ""


def test_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["nope"]) == 2
    assert "invalid choice" in capsys.readouterr().err


def test_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["generate", "--seed", "x", "--n", "1", "--out", "o"]) == 2
    assert "usage" in capsys.readouterr().err


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == __version__ + "\n"


def test_extract_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("See IEEE Std 1584-2018 for this.", encoding="utf-8")
    assert main(["extract", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == ",".join(EXTRACT_HEADER)
    assert lines[1].startswith(",text,4,")
    assert "IEEE 1584-2018" in lines[1]
    assert len(lines) == 2


def test_extract_csv_and_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "rfis.csv"
    path.write_text(
        "rfi_id,subject,question\n=R1,IEEE 1584,Please see IEC 60076-2:2011\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.csv"
    assert main(["extract", str(path), "--out", str(out)]) == 0
    assert capsys.readouterr().out == ""
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[1].startswith("'=R1,subject,")
    assert lines[2].startswith("'=R1,question,")


def test_extract_column_map(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "rfis.csv"
    path.write_text("No,Title,Body\n7,x,See ASTM A36\n", encoding="utf-8")
    names = {"rfi_id": "No", "subject": "Title", "question": "Body"}
    mapping = tmp_path / "m.json"
    mapping.write_text(json.dumps(names), encoding="utf-8")
    assert main(["extract", str(path), "--column-map", str(mapping)]) == 0
    assert "7,question," in capsys.readouterr().out
    assert main(["extract", str(path)]) == 1
    assert "missing column 'rfi_id'" in capsys.readouterr().err


def test_extract_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["extract", str(tmp_path / "none.txt")]) == 1
    captured = capsys.readouterr()
    assert captured.err == (
        "rfikit: none.txt: file is missing or is not a regular file, check the path\n"
    )
    assert "Traceback" not in captured.err
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    link = tmp_path / "link.csv"
    link.symlink_to(tmp_path / "target.csv")
    assert main(["extract", str(path), "--out", str(link)]) == 1
    assert "symbolic link" in capsys.readouterr().err
    gone = tmp_path / "no_folder" / "o.csv"
    assert main(["extract", str(path), "--out", str(gone)]) == 1
    assert "file cannot be written" in capsys.readouterr().err


def test_generate_matches_write_corpus(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "cli"
    assert main(["generate", "--seed", "42", "--n", "20", "--out", str(out)]) == 0
    line = capsys.readouterr().out
    assert line == "Wrote 20 synthetic RFIs (seed 42) to cli\n"
    expected = render_files(generate(42, 20))
    for name, data in expected.items():
        assert (out / name).read_bytes() == data


@pytest.mark.parametrize("n", ["0", "-1", str(MAX_N + 1)])
def test_generate_bad_n(
    n: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["generate", "--seed", "1", "--n", n, "--out", str(tmp_path / "o")]) == 1
    )
    assert "--n must be between" in capsys.readouterr().err
    assert not (tmp_path / "o").exists()


def test_generate_unsafe_and_unwritable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    link = tmp_path / "link"
    link.symlink_to(tmp_path)
    assert main(["generate", "--seed", "1", "--n", "2", "--out", str(link)]) == 1
    assert "symbolic link" in capsys.readouterr().err
    plain = tmp_path / "plain"
    plain.write_text("x", encoding="utf-8")
    assert main(["generate", "--seed", "1", "--n", "2", "--out", str(plain)]) == 1
    assert "cannot be written" in capsys.readouterr().err


def test_evaluate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = tmp_path / "data"
    assert main(["generate", "--seed", "5", "--n", "20", "--out", str(data)]) == 0
    capsys.readouterr()
    result = tmp_path / "s.json"
    argv = ["evaluate", str(data), "--written", str(HELDOUT), "--json", str(result)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    for word in ("Set A", "Set B", "Set written", "Leak check:", "synthetic data"):
        assert word in out
    for level in ("strict", "overlap", "full", "base", "clause"):
        assert level in out
    summary = json.loads(result.read_text(encoding="utf-8"))
    assert set(summary["sets"]) == {"A", "B", "written"}


def test_evaluate_without_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    main(["generate", "--seed", "5", "--n", "10", "--out", str(data)])
    capsys.readouterr()
    assert main(["evaluate", str(data)]) == 0
    assert "Set written" not in capsys.readouterr().out


def test_evaluate_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["evaluate", str(tmp_path / "none")]) == 1
    assert capsys.readouterr().err.startswith("rfikit: ")


def test_render_with_baselines() -> None:
    plan = EvalPlan(report_seeds=(101, 102), n=30, train_seeds=(1,), draws=20)
    methods = {"prototype": prototype_spans, "naive": naive_spans}
    summary = summarize(evaluate_seeds(plan, HELDOUT, methods))
    text = render_summary(summary)
    rows = [line.split() for line in text.splitlines()]
    base = {(r[0], r[1]): r[2:] for r in rows if len(r) == 5 and r[0] != "method"}
    assert base[("prototype", "strict")][0] != "n/a"
    assert base[("prototype", "full")] == ["n/a", "n/a", "n/a"]
    assert base[("naive", "clause")] == ["n/a", "n/a", "n/a"]
    assert base[("rfikit", "full")][0] != "n/a"


def test_render_undefined_value() -> None:
    summary = {
        "leak": {"pool_size": 0},
        "sets": {
            "A": {
                "methods": {
                    "rfikit": {
                        "rfis": 3,
                        "levels": {"strict": {"precision": None, "recall": 0.5}},
                    }
                }
            }
        },
    }
    text = render_summary(summary)
    row = next(line for line in text.splitlines() if " strict " in line).split()
    assert row[2:] == ["n/a", "0.500", "n/a"]
    assert "Leak check: pool 0" in text


def parse(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text, newline="")))


def test_extract_clause_and_inferred(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "n.txt"
    path.write_text("IEEE C57.12.00, C57.12.90 clause 5.3", encoding="utf-8")
    assert main(["extract", str(path)]) == 0
    rows = parse(capsys.readouterr().out)
    assert rows[0] == list(EXTRACT_HEADER)
    assert rows[1:] == [
        ["", "text", "0", "14", "IEEE C57.12.00", "IEEE C57.12.00"]
        + ["IEEE C57.12.00", "IEEE", "", "", "0"],
        ["", "text", "16", "25", "C57.12.90", "IEEE C57.12.90 Clause 5.3"]
        + ["IEEE C57.12.90", "IEEE", "26", "36", "1"],
    ]


def test_upper_case_csv_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "rfis.CSV"
    path.write_text("rfi_id,subject,question\nR1,S,See ASTM A36\n", encoding="utf-8")
    assert main(["extract", str(path)]) == 0
    assert "R1,question," in capsys.readouterr().out


def test_other_suffix_is_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "rfis.tsv"
    path.write_text("See ASTM A36", encoding="utf-8")
    assert main(["extract", str(path)]) == 0
    assert ",text," in capsys.readouterr().out


def test_offsets_are_code_points_csv(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    subject = "\U0001f600\U0001f600 IEEE 1547-2018"
    path = tmp_path / "rfis.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rfi_id", "subject", "question"])
        writer.writerow(["R1", subject, "none"])
    assert main(["extract", str(path)]) == 0
    rows = parse(capsys.readouterr().out)[1:]
    assert len(rows) == 1
    start, end = int(rows[0][2]), int(rows[0][3])
    assert rows[0][1] == "subject"
    assert (start, end) == (3, len(subject))
    assert subject[start:end] == rows[0][4]


def test_offsets_are_code_points_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "\U0001f600\U0001f600 IEEE 1547-2018"
    path = tmp_path / "n.txt"
    path.write_text(text, encoding="utf-8")
    assert main(["extract", str(path)]) == 0
    rows = parse(capsys.readouterr().out)[1:]
    assert len(rows) == 1
    start, end = int(rows[0][2]), int(rows[0][3])
    assert text[start:end] == rows[0][4]
    assert start == 3


def test_extract_out_replaces_and_refuses_same_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "n.csv"
    path.write_text("rfi_id,subject,question\nR1,S,See ASTM A36\n", encoding="utf-8")
    original = path.read_text(encoding="utf-8")
    assert main(["extract", str(path), "--out", str(path)]) == 1
    assert "same file as n.csv" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == original
    out = tmp_path / "o.csv"
    out.write_text("old", encoding="utf-8")
    assert main(["extract", str(path), "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("rfi_id,column,")


def test_extract_failure_leaves_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "n.csv"
    path.write_text(
        "rfi_id,subject,question\nR1,S,See ASTM A36\nR1,S,Q\n", encoding="utf-8"
    )
    out = tmp_path / "o.csv"
    assert main(["extract", str(path), "--out", str(out)]) == 1
    assert "repeats" in capsys.readouterr().err
    assert not out.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["n.csv"]


def test_extract_stdout_is_utf8_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "n.txt"
    path.write_text("\U0001f600 IEEE 1547", encoding="utf-8")
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="ascii"))
    assert main(["extract", str(path)]) == 0
    data = raw.getvalue()
    assert data.startswith(b"rfi_id,column,")
    assert b"\r" not in data
    assert data.endswith(b"\n")


def test_extract_broken_pipe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "n.txt"
    path.write_text("IEEE 1547", encoding="utf-8")

    class Broken:
        class buffer:  # noqa: N801
            @staticmethod
            def write(data: bytes) -> int:
                raise BrokenPipeError

    monkeypatch.setattr(sys, "stdout", Broken)
    assert main(["extract", str(path)]) == 1
    assert capsys.readouterr().err == ""


def test_generate_negative_seed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["generate", "--seed", "-1", "--n", "5", "--out", str(tmp_path / "o")])
        == 1
    )
    captured = capsys.readouterr()
    assert captured.err == (
        "rfikit: --seed must not be negative, pass 0 or a larger whole number\n"
    )


def test_generate_n_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "MAX_N", 5)
    assert (
        main(["generate", "--seed", "1", "--n", "5", "--out", str(tmp_path / "a")]) == 0
    )
    assert (
        main(["generate", "--seed", "1", "--n", "6", "--out", str(tmp_path / "b")]) == 1
    )
    assert "between 1 and 5" in capsys.readouterr().err


def test_generate_folder_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "data"
    assert main(["generate", "--seed", "1", "--n", "3", "--out", str(out)]) == 0
    assert main(["generate", "--seed", "2", "--n", "3", "--out", str(out)]) == 0
    other = tmp_path / "other"
    other.mkdir()
    (other / "keep.txt").write_text("x", encoding="utf-8")
    capsys.readouterr()
    assert main(["generate", "--seed", "1", "--n", "3", "--out", str(other)]) == 1
    assert "not empty" in capsys.readouterr().err
    assert (other / "keep.txt").exists()
    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / "manifest.json").write_text('{"synthetic": true}', encoding="utf-8")
    assert main(["generate", "--seed", "1", "--n", "3", "--out", str(fake)]) == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["generate", "--seed", "1", "--n", "3", "--out", str(empty)]) == 0
    held = tmp_path / "held"
    held.mkdir()
    (held / "manifest.json").write_text("not json", encoding="utf-8")
    assert main(["generate", "--seed", "1", "--n", "3", "--out", str(held)]) == 1


def test_evaluate_not_a_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["evaluate", str(tmp_path / "typed")]) == 1
    assert capsys.readouterr().err == "rfikit: typed: not a folder, check the path\n"
    data = tmp_path / "data"
    main(["generate", "--seed", "5", "--n", "5", "--out", str(data)])
    capsys.readouterr()
    assert main(["evaluate", str(data), "--written", str(tmp_path / "w")]) == 1
    assert "w: not a folder" in capsys.readouterr().err


def test_evaluate_exact_lines_and_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    main(["generate", "--seed", "5", "--n", "20", "--out", str(data)])
    capsys.readouterr()
    result = tmp_path / "s.json"
    assert main(["evaluate", str(data), "--json", str(result)]) == 0
    out = capsys.readouterr().out
    assert "Leak check: pool 12000, A dropped 2 of 16, B dropped 0 of 4\n" in out
    assert out.endswith("Measured on synthetic data.\n")
    summary = json.loads(result.read_text(encoding="utf-8"))
    expected = json.dumps(summary, sort_keys=True, indent=1) + "\n"
    assert result.read_text(encoding="utf-8") == expected


def test_evaluate_table_matches_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    main(["generate", "--seed", "5", "--n", "20", "--out", str(data)])
    capsys.readouterr()
    result = tmp_path / "s.json"
    argv = ["evaluate", str(data), "--written", str(HELDOUT), "--json", str(result)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    summary = json.loads(result.read_text(encoding="utf-8"))
    levels = summary["sets"]["written"]["methods"]["rfikit"]["levels"]
    lines = out.split("Set written")[1].splitlines()
    for level, got in levels.items():
        row = next(
            x.split() for x in lines if x.startswith("rfikit") and f" {level} " in x
        )
        assert row[2:] == [f"{got[k]:.3f}" for k in ("precision", "recall", "f1")]


def test_evaluate_empty_set(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = tmp_path / "data"
    main(["generate", "--seed", "5", "--n", "1", "--out", str(data)])
    capsys.readouterr()
    assert main(["evaluate", str(data)]) == 0
    out = capsys.readouterr().out
    assert "Set A: no RFIs to score" in out
    assert "Set B: no RFIs to score" in out
    assert "precision" not in out


def test_other_marker_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = tmp_path / "data"
    main(["generate", "--seed", "5", "--n", "20", "--out", str(data)])
    manifest = data / "manifest.json"
    parsed = json.loads(manifest.read_text(encoding="utf-8"))
    parsed["synthetic"] = False
    manifest.write_text(json.dumps(parsed), encoding="utf-8")
    capsys.readouterr()
    assert main(["evaluate", str(data)]) == 0
    out = capsys.readouterr().out
    assert out.endswith("Scored on the labeled folders given.\n")
    manifest.unlink()
    assert main(["evaluate", str(data)]) == 0
    assert "Scored on the labeled folders given." in capsys.readouterr().out
    good = tmp_path / "good"
    main(["generate", "--seed", "6", "--n", "20", "--out", str(good)])
    capsys.readouterr()
    assert main(["evaluate", str(good), "--written", str(data)]) == 0
    assert "Scored on the labeled folders given." in capsys.readouterr().out


def test_evaluate_label_error_clips_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    main(["generate", "--seed", "5", "--n", "5", "--out", str(data)])
    capsys.readouterr()
    long = "R" * 100
    rows = ["rfi_id,subject,question,response", f"{long},S,Q,", f"{long},S,Q,"]
    (data / "input" / "rfis.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    assert main(["evaluate", str(data)]) == 1
    err = capsys.readouterr().err
    assert "repeats rfi_id" in err
    assert long not in err


def make_corpus(folder: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    assert main(["generate", "--seed", "3", "--n", "5", "--out", str(folder)]) == 0
    capsys.readouterr()
    return folder


def edit_manifest(folder: Path, changes: dict[str, object]) -> None:
    path = folder / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.update(changes)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def refused(folder: Path, capsys: pytest.CaptureFixture[str]) -> bool:
    argv = ["generate", "--seed", "4", "--n", "5", "--out", str(folder)]
    code = main(argv)
    err = capsys.readouterr().err
    if code == 1:
        assert "not empty" in err
    return code == 1


def test_generate_accepts_a_real_corpus(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = make_corpus(tmp_path / "c", capsys)
    assert not refused(folder, capsys)


@pytest.mark.parametrize(
    "changes",
    [
        {"generator": 1},
        {"generator": {"seed": "3", "n": 5}},
        {"generator": {"seed": True, "n": 5}},
        {"generator": {"seed": 3}},
        {"synthetic": "yes"},
        {"synthetic": 1},
        {"files": {}},
        {"files": {"../x.txt": "0"}},
        {"files": {"input/missing.csv": "0"}},
        {"files": []},
    ],
)
def test_generate_refuses_crafted_manifest(
    changes: dict[str, object],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder = make_corpus(tmp_path / "c", capsys)
    edit_manifest(folder, changes)
    assert refused(folder, capsys)


def test_generate_refuses_edited_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = make_corpus(tmp_path / "c", capsys)
    with (folder / "input" / "rfis.csv").open("a", encoding="utf-8") as handle:
        handle.write("extra\n")
    assert refused(folder, capsys)


def test_synthetic_must_be_exactly_true(tmp_path: Path) -> None:
    folder = tmp_path / "f"
    folder.mkdir()
    for value in ("yes", 1, None):
        (folder / "manifest.json").write_text(
            json.dumps({"synthetic": value}), encoding="utf-8"
        )
        assert not cli.is_synthetic(folder)
    (folder / "manifest.json").write_text('{"synthetic": true}', encoding="utf-8")
    assert cli.is_synthetic(folder)


def test_write_corpus_does_not_write_through_links(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    outside = tmp_path / "outside.csv"
    outside.write_text("keep", encoding="utf-8")
    out = tmp_path / "c"
    (out / "input").mkdir(parents=True)
    os.link(outside, out / "input" / "rfis.csv")
    assert main(["generate", "--seed", "1", "--n", "3", "--out", str(out)]) == 1
    assert outside.read_text(encoding="utf-8") == "keep"
    capsys.readouterr()
    empty = tmp_path / "e"
    (empty / "input").mkdir(parents=True)
    os.link(outside, empty / "input" / "rfis.csv")
    from rfikit.synth import generate, write_corpus

    write_corpus(generate(1, 3), empty)
    assert outside.read_text(encoding="utf-8") == "keep"
    assert (empty / "input" / "rfis.csv").read_text(encoding="utf-8") != "keep"


def test_missing_seed_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["generate", "--n", "3", "--out", "o"]) == 2
    assert "--seed" in capsys.readouterr().err


def test_column_map_needs_csv(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "n.txt"
    path.write_text("ASTM A36", encoding="utf-8")
    mapping = tmp_path / "m.json"
    mapping.write_text("{}", encoding="utf-8")
    assert main(["extract", str(path), "--column-map", str(mapping)]) == 1
    err = capsys.readouterr().err
    assert err == (
        "rfikit: --column-map works only with a .csv file, "
        "drop it or pass a .csv file\n"
    )


def test_extract_out_cannot_replace_column_map(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "n.csv"
    path.write_text("No,Title,Body\n1,S,ASTM A36\n", encoding="utf-8")
    mapping = tmp_path / "m.json"
    names = {"rfi_id": "No", "subject": "Title", "question": "Body"}
    mapping.write_text(json.dumps(names), encoding="utf-8")
    before = mapping.read_text(encoding="utf-8")
    argv = ["extract", str(path), "--column-map", str(mapping), "--out", str(mapping)]
    assert main(argv) == 1
    assert "same file as m.json" in capsys.readouterr().err
    assert mapping.read_text(encoding="utf-8") == before


def test_json_cannot_land_in_input_folders(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = make_corpus(tmp_path / "data", capsys)
    written = make_corpus(tmp_path / "written", capsys)
    target = data / "input" / "rfis.csv"
    before = target.read_bytes()
    assert main(["evaluate", str(data), "--json", str(target)]) == 1
    assert "inside the input folder data" in capsys.readouterr().err
    assert target.read_bytes() == before
    argv = ["evaluate", str(data), "--written", str(written)]
    assert main([*argv, "--json", str(written / "new.json")]) == 1
    assert "inside the input folder written" in capsys.readouterr().err
    assert not (written / "new.json").exists()


def test_label_error_names_folder_and_next_step(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = make_corpus(tmp_path / "data", capsys)
    (data / "input" / "rfis.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    assert main(["evaluate", str(data)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("rfikit: data: rfis.csv: missing column 'rfi_id', check")
    assert "docs/annotation_guide.md" in err
    assert (ROOT / "docs" / "annotation_guide.md").exists()


def test_newline_id_in_labels_is_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = make_corpus(tmp_path / "data", capsys)
    rows = 'rfi_id,subject,question,response\n"a\nb",S,Q,\n"a\nb",S,Q,\n'
    (data / "input" / "rfis.csv").write_text(rows, encoding="utf-8")
    assert main(["evaluate", str(data)]) == 1
    assert len(capsys.readouterr().err.splitlines()) == 1


def test_real_cli_into_head(tmp_path: Path) -> None:
    script = Path(sys.executable).parent / "rfikit"
    if not script.exists():
        pytest.skip("console script not installed")
    path = tmp_path / "big.txt"
    path.write_text("IEEE 1547 and " * 40_000, encoding="utf-8")
    run = subprocess.Popen(
        [sys.executable, "-I", str(script), "extract", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert run.stdout is not None
    assert run.stderr is not None
    first = run.stdout.readline()
    run.stdout.close()
    err = run.stderr.read()
    run.wait()
    run.stderr.close()
    assert first.startswith(b"rfi_id,column,")
    assert err == b""
