import csv
import hashlib
import json
from pathlib import Path

import build_heldout as bh
import pytest

from rfikit.evaluate import (
    ISSUE_TYPES,
    NEGATIVE_KINDS,
    GoldCitation,
    GoldNegative,
    RfiLabel,
    read_citations,
    read_negatives,
    read_rfi_labels,
)
from rfikit.types import BODIES

ROOT = Path(__file__).resolve().parent.parent
HELDOUT = ROOT / "heldout"
OUT_BODIES = ("NFPA", "UL", "ASME", "ISA", "TIA", "CSA", "EN")
DASHES = {chr(0x2010), chr(0x2011), chr(0x2012), chr(0x2212)}
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)


def read_inputs() -> dict[str, dict[str, str]]:
    with (HELDOUT / "input" / "rfis.csv").open(encoding="utf-8", newline="") as f:
        return {row["rfi_id"]: row for row in csv.DictReader(f)}


@pytest.fixture(scope="module")
def inputs() -> dict[str, dict[str, str]]:
    return read_inputs()


@pytest.fixture(scope="module")
def citations() -> list[GoldCitation]:
    return read_citations(HELDOUT / "labels" / "citations.csv")


@pytest.fixture(scope="module")
def negatives() -> list[GoldNegative]:
    return read_negatives(HELDOUT / "labels" / "negatives.csv")


@pytest.fixture(scope="module")
def labels() -> list[RfiLabel]:
    return read_rfi_labels(HELDOUT / "labels" / "rfis.csv")


def column_text(inputs: dict[str, dict[str, str]], rfi_id: str, column: str) -> str:
    return inputs[rfi_id][column]


def test_manifest_checksums() -> None:
    manifest = json.loads((HELDOUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    for name, digest in manifest["files"].items():
        data = (ROOT / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, name
    source = (ROOT / manifest["source"]["path"]).read_bytes()
    assert hashlib.sha256(source).hexdigest() == manifest["source"]["sha256"]
    assert "heldout/input/rfis.csv" in manifest["files"]
    assert "heldout/labels/citations.csv" in manifest["files"]


def test_manifest_counts_match_files(citations: list[GoldCitation]) -> None:
    manifest = json.loads((HELDOUT / "manifest.json").read_text(encoding="utf-8"))
    counts = manifest["counts"]
    in_scope = [c for c in citations if c.scope == "in"]
    assert counts["citations_in_scope"] == len(in_scope)
    assert counts["citations_out_of_scope"] == len(citations) - len(in_scope)


def test_build_check_passes() -> None:
    assert bh.check(ROOT) == []


def test_readme_and_changes_exist() -> None:
    readme = (HELDOUT / "README.txt").read_text(encoding="utf-8")
    assert "synthetic" in readme.lower()
    assert "All rights reserved." in readme
    assert "Decision support only" in readme
    changes = (HELDOUT / "CHANGES.md").read_text(encoding="utf-8")
    assert "No changes yet." in changes


def test_no_forbidden_dashes() -> None:
    for path in HELDOUT.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert EN_DASH not in text, path
            assert EM_DASH not in text, path


def test_dash_noise_uses_allowed_characters(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    dashed = [c for c in citations if c.noise_class == "unicode_dash"]
    assert len(dashed) >= 4
    seen: set[str] = set()
    for c in dashed:
        text = column_text(inputs, c.rfi_id, c.column)[c.start : c.end]
        found = {ch for ch in text if ord(ch) > 127}
        assert found
        assert found <= DASHES
        seen |= found
    assert len(seen) >= 3


def test_citation_slices(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    for c in citations:
        text = column_text(inputs, c.rfi_id, c.column)
        piece = text[c.start : c.end]
        assert piece != ""
        assert piece == piece.strip()
        assert c.end <= len(text)


def test_slices_equal_marked_text(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    source = (ROOT / bh.SOURCE_PATH).read_text(encoding="utf-8")
    marks: dict[tuple[str, str], list[bh.CitationMark]] = {}
    for rfi in bh.parse_source(source):
        for name, parsed in rfi.columns.items():
            assert parsed.text == inputs[rfi.rfi_id][name]
            marks[(rfi.rfi_id, name)] = sorted(parsed.citations, key=lambda m: m.start)
    for key, expected in marks.items():
        found = [c for c in citations if (c.rfi_id, c.column) == key]
        assert [(c.start, c.end, c.key) for c in found] == [
            (m.start, m.end, m.key) for m in expected
        ]


def test_clause_offsets(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    for c in citations:
        if c.clause_start is None or c.clause_end is None:
            assert not c.inferred or c.key.split(" ")[0] != "NESC"
            continue
        text = column_text(inputs, c.rfi_id, c.column)
        assert 0 <= c.clause_start < c.clause_end <= len(text)
        assert text[c.clause_start : c.clause_end].strip() != ""
        if c.inferred and c.start == c.clause_start:
            assert c.end == c.clause_end
        else:
            assert c.clause_end <= c.start or c.clause_start >= c.end


def test_inferred_bare_nesc_has_clause_span(citations: list[GoldCitation]) -> None:
    bare = [c for c in citations if c.key.startswith("NESC ") and c.inferred]
    assert len(bare) >= 5
    for c in bare:
        assert (c.start, c.end) == (c.clause_start, c.clause_end)
        assert c.noise_class == ""


def test_spans_do_not_overlap(citations: list[GoldCitation]) -> None:
    by_column: dict[tuple[str, str], list[GoldCitation]] = {}
    for c in citations:
        by_column.setdefault((c.rfi_id, c.column), []).append(c)
    for items in by_column.values():
        items.sort(key=lambda c: c.start)
        for left, right in zip(items, items[1:], strict=False):
            assert left.end <= right.start, (left, right)


def test_negatives_do_not_overlap_citations(
    inputs: dict[str, dict[str, str]],
    citations: list[GoldCitation],
    negatives: list[GoldNegative],
) -> None:
    for n in negatives:
        text = column_text(inputs, n.rfi_id, n.column)
        assert 0 <= n.start < n.end <= len(text)
        for c in citations:
            if (c.rfi_id, c.column) == (n.rfi_id, n.column):
                assert n.end <= c.start or n.start >= c.end, (n, c)
    by_column: dict[tuple[str, str], list[GoldNegative]] = {}
    for n in negatives:
        by_column.setdefault((n.rfi_id, n.column), []).append(n)
    for items in by_column.values():
        items.sort(key=lambda n: n.start)
        for left, right in zip(items, items[1:], strict=False):
            assert left.end <= right.start


def test_keys_start_with_body(citations: list[GoldCitation]) -> None:
    for c in citations:
        body = c.key.split(" ")[0]
        assert c.base_key.split(" ")[0] == body
        if c.scope == "in":
            assert body in BODIES, c
            if body != "NESC":
                assert c.key.startswith(c.base_key), c
        else:
            assert body in OUT_BODIES, c
            assert c.key == c.base_key
            assert not c.inferred
            assert c.clause_start is None


def test_minimum_counts(
    inputs: dict[str, dict[str, str]],
    citations: list[GoldCitation],
    negatives: list[GoldNegative],
) -> None:
    assert 78 <= len(inputs) <= 85
    in_scope = [c for c in citations if c.scope == "in"]
    assert len(in_scope) >= 150
    for body in BODIES:
        assert len([c for c in in_scope if c.key.split(" ")[0] == body]) >= 15, body
    assert len(citations) > len(in_scope)
    assert len(negatives) >= 40
    assert {n.kind for n in negatives} == set(NEGATIVE_KINDS)
    noise = {c.noise_class for c in in_scope}
    assert noise >= {
        "misspelled",
        "list_continuation",
        "line_break",
        "unicode_dash",
        "spacing",
        "case",
    }
    assert any(c.inferred for c in in_scope)
    assert {c.catalog for c in in_scope} == {"real", "invented"}


def test_labels_cover_every_rfi(
    inputs: dict[str, dict[str, str]],
    citations: list[GoldCitation],
    negatives: list[GoldNegative],
    labels: list[RfiLabel],
) -> None:
    assert [label.rfi_id for label in labels] == list(inputs)
    ids = set(inputs)
    assert {c.rfi_id for c in citations} <= ids
    assert {n.rfi_id for n in negatives} <= ids
    for row in inputs.values():
        assert row["subject"].strip()
        assert row["question"].strip()
        assert EN_DASH not in "".join(row.values())
        assert EM_DASH not in "".join(row.values())
    assert sum(1 for row in inputs.values() if row["response"]) >= len(inputs) // 2


def test_issue_types_and_groups(labels: list[RfiLabel]) -> None:
    assert {label.issue_type for label in labels} == set(ISSUE_TYPES)
    groups: dict[str, list[RfiLabel]] = {}
    for label in labels:
        groups.setdefault(label.group_id, []).append(label)
        assert label.template_id == ""
        assert label.family == "written"
    recurring = {name: items for name, items in groups.items() if len(items) > 1}
    assert len(recurring) == 12
    for items in recurring.values():
        assert 2 <= len(items) <= 4
        assert len({item.issue_type for item in items}) == 1
    for name, items in groups.items():
        if name not in recurring:
            assert name == "single-" + items[0].rfi_id
