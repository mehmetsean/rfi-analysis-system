import subprocess
import sys

import pytest
from hypothesis import given
from hypothesis import strategies as st

from rfikit.analyze import MOST, AnalysisResult, analyze
from rfikit.types import Citation, Rfi


def rfi(rfi_id: str, subject: str = "", question: str = "", response: str = "") -> Rfi:
    return Rfi(rfi_id, subject, question, response)


def test_empty_input() -> None:
    result = analyze([])
    assert result == AnalysisResult(0, 0, (), (), (), (), False)


def test_rfis_without_citations() -> None:
    result = analyze([rfi("A", "hello"), rfi("B", "world")])
    assert result.rfis_read == 2
    assert result.citation_total == 0
    assert result.key_counts == ()
    assert result.body_counts == ()
    assert result.per_rfi == ((0, 2),)
    assert result.most == ()


def test_scans_all_three_columns() -> None:
    seen: list[tuple[str, Citation]] = []
    result = analyze(
        [rfi("A", "IEEE 80", "ASTM A123", "NEMA TC 2")],
        sink=lambda i, c: seen.append((i, c)),
    )
    columns = [c.column for _, c in seen]
    assert columns == ["subject", "question", "response"]
    assert result.per_rfi == ((3, 1),)


def test_counts_and_order() -> None:
    rows = [
        rfi("A", "IEEE 80 and IEEE 80-2013", "ASTM A123"),
        rfi("B", "IEEE 1547", "ASTM A123"),
    ]
    result = analyze(rows)
    assert result.key_counts == (
        ("ASTM A123", 2),
        ("IEEE 80", 2),
        ("IEEE 1547", 1),
    )
    assert result.body_counts == (("IEEE", 3), ("ASTM", 2))
    assert result.per_rfi == ((2, 1), (3, 1))
    assert result.most == (("A", 3), ("B", 2))


def test_ties_break_by_name() -> None:
    result = analyze([rfi("B", "IEC 60076-1"), rfi("A", "IEEE 80")])
    assert result.key_counts == (("IEC 60076-1", 1), ("IEEE 80", 1))
    assert result.body_counts == (("IEC", 1), ("IEEE", 1))
    assert result.most == (("A", 1), ("B", 1))


def test_most_is_capped_and_skips_zero() -> None:
    rows = [rfi(f"R{i:02d}", "IEEE 80") for i in range(MOST + 5)]
    rows.append(rfi("Z", "nothing"))
    result = analyze(rows)
    assert len(result.most) == MOST
    assert result.most[0] == ("R00", 1)
    assert all(rfi_id != "Z" for rfi_id, _ in result.most)


def test_synthetic_flag() -> None:
    assert analyze([], synthetic=True).synthetic is True


def test_citations_carry_rfi_id() -> None:
    seen: list[str] = []
    analyze([rfi("X-1", "IEEE 80")], sink=lambda i, c: seen.append(i))
    assert seen == ["X-1"]


PIECES = ["IEEE 80", "ASTM A123", "NESC Rule 232", "see", " ", "x", "\n"]
TEXTS = st.lists(st.sampled_from(PIECES), max_size=12).map("".join)


@given(st.lists(TEXTS, max_size=8))
def test_totals_agree(texts: list[str]) -> None:
    rows = [rfi(f"R{i}", t, t) for i, t in enumerate(texts)]
    seen: list[str] = []
    result = analyze(rows, sink=lambda i, c: seen.append(i))
    total = len(seen)
    assert result.citation_total == total
    assert sum(n for _, n in result.body_counts) == total
    assert sum(n for _, n in result.key_counts) == total
    assert sum(n * m for n, m in result.per_rfi) == total
    assert sum(m for _, m in result.per_rfi) == len(rows)


def test_analyze_does_not_import_synth_or_evaluate() -> None:
    code = (
        "import sys, rfikit.analyze\n"
        "bad = [m for m in sys.modules if m.startswith(('rfikit.synth',"
        " 'rfikit.evaluate'))]\n"
        "sys.exit(1 if bad else 0)\n"
    )
    done = subprocess.run([sys.executable, "-c", code], check=False)
    assert done.returncode == 0


def test_repeated_rfi_id_is_refused() -> None:
    with pytest.raises(ValueError, match="'A' repeats"):
        analyze([rfi("A"), rfi("B"), rfi("A")])
