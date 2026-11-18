import ast
import csv
from pathlib import Path

import pytest

from rfikit.evaluate import (
    CITATION_HEADER,
    NEGATIVE_HEADER,
    RFI_HEADER,
    GoldCitation,
    GoldNegative,
    LabelError,
    RfiLabel,
    read_citations,
    read_negatives,
    read_rfi_labels,
)

SRC = Path(__file__).resolve().parent.parent / "src" / "rfikit"


def write_csv(path: Path, header: tuple[str, ...], rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return path


def citation_row(**changes: str) -> list[str]:
    values = {
        "rfi_id": "W001",
        "column": "question",
        "start": "10",
        "end": "25",
        "clause_start": "",
        "clause_end": "",
        "key": "IEEE C57.12.00-2015",
        "base_key": "IEEE C57.12.00",
        "scope": "in",
        "inferred": "0",
        "catalog": "real",
        "noise_class": "",
    }
    values.update(changes)
    return [values[name] for name in CITATION_HEADER]


def test_read_citation(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "c.csv",
        CITATION_HEADER,
        [
            citation_row(),
            citation_row(clause_start="30", clause_end="40", inferred="1"),
        ],
    )
    first, second = read_citations(path)
    assert first == GoldCitation(
        "W001",
        "question",
        10,
        25,
        None,
        None,
        "IEEE C57.12.00-2015",
        "IEEE C57.12.00",
        "in",
        False,
        "real",
        "",
    )
    assert second.clause_start == 30
    assert second.clause_end == 40
    assert second.inferred is True


def test_read_negative(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "n.csv", NEGATIVE_HEADER, [["W002", "subject", "0", "8", "date"]]
    )
    assert read_negatives(path) == [GoldNegative("W002", "subject", 0, 8, "date")]


def test_read_rfi_labels(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "r.csv",
        RFI_HEADER,
        [["W003", "field_condition", "G01", "", "written"]],
    )
    assert read_rfi_labels(path) == [
        RfiLabel("W003", "field_condition", "G01", "", "written")
    ]


def test_extra_columns_and_order_are_fine(tmp_path: Path) -> None:
    path = tmp_path / "n.csv"
    path.write_text("kind,end,start,column,rfi_id,note\ndate,8,0,subject,W1,x\n")
    assert read_negatives(path) == [GoldNegative("W1", "subject", 0, 8, "date")]


def test_missing_column(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "n.csv", ("rfi_id", "column", "start", "end"), [])
    with pytest.raises(LabelError, match="missing column 'kind'"):
        read_negatives(path)


def test_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "n.csv"
    path.write_text("")
    with pytest.raises(LabelError, match="empty"):
        read_negatives(path)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"start": "x"}, "not an integer"),
        ({"start": "-1"}, "negative"),
        ({"end": "10"}, "not after start"),
        ({"clause_start": "5"}, "go together"),
        ({"clause_start": "9", "clause_end": "9"}, "clause end"),
        ({"clause_start": "a", "clause_end": "9"}, "not an integer"),
        ({"scope": "maybe"}, "unknown value 'maybe'"),
        ({"column": "body"}, "unknown value 'body'"),
        ({"inferred": "yes"}, "unknown value 'yes'"),
        ({"catalog": ""}, "unknown value"),
        ({"noise_class": "loud"}, "unknown value 'loud'"),
        ({"key": ""}, "value is empty"),
    ],
)
def test_bad_citation(tmp_path: Path, change: dict[str, str], message: str) -> None:
    path = write_csv(tmp_path / "c.csv", CITATION_HEADER, [citation_row(**change)])
    with pytest.raises(LabelError, match=message) as info:
        read_citations(path)
    assert "line 2" in str(info.value)


def test_bad_kind(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "n.csv", NEGATIVE_HEADER, [["W1", "subject", "0", "4", "fruit"]]
    )
    with pytest.raises(LabelError, match="unknown value 'fruit'"):
        read_negatives(path)


def test_bad_issue_type(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "r.csv", RFI_HEADER, [["W1", "chat", "G01", "", "written"]]
    )
    with pytest.raises(LabelError, match="unknown value 'chat'"):
        read_rfi_labels(path)


def test_short_row(tmp_path: Path) -> None:
    path = tmp_path / "n.csv"
    path.write_text("rfi_id,column,start,end,kind\nW1,subject,0\n")
    with pytest.raises(LabelError, match="expected 5 cells"):
        read_negatives(path)


def test_duplicate_header(tmp_path: Path) -> None:
    path = tmp_path / "n.csv"
    path.write_text("rfi_id,column,start,end,kind,kind\nW1,subject,0,4,date,date\n")
    with pytest.raises(LabelError, match="duplicate column 'kind'"):
        read_negatives(path)


def test_bom_file(tmp_path: Path) -> None:
    path = tmp_path / "n.csv"
    path.write_bytes(b"\xef\xbb\xbfrfi_id,column,start,end,kind\n")
    with pytest.raises(LabelError, match="BOM"):
        read_negatives(path)


def test_bad_utf8(tmp_path: Path) -> None:
    path = tmp_path / "n.csv"
    path.write_bytes(b"rfi_id,column,start,end,kind\n\xff\xfe\n")
    with pytest.raises(LabelError, match="not valid UTF-8"):
        read_negatives(path)


def test_bad_csv_syntax(tmp_path: Path) -> None:
    path = tmp_path / "n.csv"
    path.write_text('rfi_id,column,start,end,kind\nW1,"sub"x,0,4,date\n')
    with pytest.raises(LabelError, match="bad CSV"):
        read_negatives(path)


BLOCKED = {"rfikit.evaluate", "rfikit.synth"}


def imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = "rfikit" + ("." + base if base else "")
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else ""
            if isinstance(func, ast.Name):
                called = func.id
            if called in ("import_module", "__import__") and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    names.add(arg.value)
    return names


def blocked_imports(path: Path) -> set[str]:
    found: set[str] = set()
    for name in imported_modules(path):
        for blocked in BLOCKED:
            if name == blocked or name.startswith(blocked + "."):
                found.add(name)
        if name in ("evaluate", "synth"):
            found.add(name)
    return found


@pytest.mark.parametrize(
    "line",
    [
        "import rfikit.evaluate",
        "from rfikit import evaluate",
        "from rfikit.evaluate import read_citations",
        "from . import evaluate",
        "from .evaluate import read_citations",
        "from . import synth",
        "import importlib\nimportlib.import_module('rfikit.evaluate')",
        "from importlib import import_module\nimport_module('rfikit.synth')",
        "__import__('rfikit.evaluate')",
    ],
)
def test_boundary_check_catches_every_form(tmp_path: Path, line: str) -> None:
    path = tmp_path / "bad.py"
    path.write_text(line + "\n")
    assert blocked_imports(path)


def test_boundary_check_allows_other_imports(tmp_path: Path) -> None:
    path = tmp_path / "good.py"
    path.write_text("from . import types\nimport re\nfrom .types import Rfi\n")
    assert blocked_imports(path) == set()


def test_only_allowed_modules_import_evaluate_or_synth() -> None:
    for name in ("types", "textnorm", "cite", "classify", "group", "io"):
        path = SRC / f"{name}.py"
        if path.exists():
            assert blocked_imports(path) == set(), name


def test_evaluate_imports_only_the_standard_library() -> None:
    for name in imported_modules(SRC / "evaluate.py"):
        assert not name.startswith("rfikit"), name
