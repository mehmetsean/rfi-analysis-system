import json
from pathlib import Path

import pytest
from prototype_baseline import naive_spans, prototype_spans

from rfikit import __version__
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
    assert "not built yet" in captured.err
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
    assert captured.err == "rfikit: none.txt: missing or not a regular file\n"
    assert "Traceback" not in captured.err
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    link = tmp_path / "link.csv"
    link.symlink_to(tmp_path / "target.csv")
    assert main(["extract", str(path), "--out", str(link)]) == 1
    assert "symbolic link" in capsys.readouterr().err
    gone = tmp_path / "no_folder" / "o.csv"
    assert main(["extract", str(path), "--out", str(gone)]) == 1
    assert "cannot be written" in capsys.readouterr().err


def test_generate_matches_write_corpus(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "cli"
    assert main(["generate", "--seed", "42", "--n", "20", "--out", str(out)]) == 0
    line = capsys.readouterr().out
    assert "20" in line
    assert str(out) in line
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
                    "rfikit": {"levels": {"strict": {"precision": None, "recall": 0.5}}}
                }
            }
        },
    }
    text = render_summary(summary)
    row = next(line for line in text.splitlines() if " strict " in line).split()
    assert row[2:] == ["n/a", "0.500", "n/a"]
    assert "Leak check: pool 0" in text
