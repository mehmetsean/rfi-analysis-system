import json
from pathlib import Path
from typing import Any

import make_measured
import pytest

Json = dict[str, Any]


def write_doc(path: Path, ci: Json) -> None:
    path.write_text(json.dumps({"ci": ci}, sort_keys=True, indent=1) + "\n")


def test_check_passes_when_equal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "measured.json"
    write_doc(target, {"a": 1, "b": [1, 2]})
    assert make_measured.check(target, lambda: {"b": [1, 2], "a": 1}) == 0
    assert "current" in capsys.readouterr().out


def test_check_fails_with_a_short_diff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "measured.json"
    write_doc(target, {"a": 1, "b": 2})
    assert make_measured.check(target, lambda: {"a": 1, "b": 3}) == 1
    out = capsys.readouterr().out
    assert "differs" in out
    assert '- "b": 2' in out
    assert '+ "b": 3' in out


def test_check_cuts_a_long_diff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "measured.json"
    write_doc(target, {str(i): i for i in range(100)})
    assert make_measured.check(target, lambda: {str(i): i + 1 for i in range(100)}) == 1
    out = capsys.readouterr().out
    assert "more diff lines" in out
    assert len(out.splitlines()) < 50


def test_rebuild_writes_sorted_json(tmp_path: Path) -> None:
    target = tmp_path / "measured.json"
    assert make_measured.rebuild(target, lambda: {"b": 1, "a": 2}) == 0
    text = target.read_text()
    assert text == '{\n "a": 2,\n "b": 1\n}\n'


def test_main_check_and_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "measured.json"
    monkeypatch.setattr(make_measured, "TARGET", target)
    monkeypatch.setattr(make_measured, "compute_doc", lambda: {"ci": {"x": 1}})
    monkeypatch.setattr(make_measured, "compute_ci", lambda: {"x": 1})
    assert make_measured.main([]) == 0
    assert make_measured.main(["--check"]) == 0
    monkeypatch.setattr(make_measured, "compute_ci", lambda: {"x": 2})
    assert make_measured.main(["--check"]) == 1


def test_baselines_are_the_two_prototype_functions() -> None:
    found = make_measured.baselines()
    assert set(found) == {"prototype", "naive"}
    assert found["naive"]("see IEEE 80") == [("IEEE", 4, 11)]


@pytest.mark.parametrize("content", [None, "not json", "{}", "[]"])
def test_check_reports_a_missing_or_bad_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str | None
) -> None:
    target = tmp_path / "measured.json"
    if content is not None:
        target.write_text(content)
    assert make_measured.check(target, lambda: {}) == 1
    assert "missing or unreadable" in capsys.readouterr().out
