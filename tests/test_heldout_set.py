import csv
import hashlib
import json
import re
from pathlib import Path

import build_heldout as bh
import pytest

from keychecks import (
    CLAUSE_WORDS,
    check_key_matches_slice,
    expected_base,
    is_bare,
    key_clause,
    norm,
)
from rfikit.evaluate import (
    ISSUE_TYPES,
    NEGATIVE_KINDS,
    RFI_HEADER,
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
    assert changes.startswith("# Changes to the written held-out set")


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


def test_label_header_is_the_full_one() -> None:
    path = HELDOUT / "labels" / "rfis.csv"
    first = path.read_text(encoding="utf-8").split("\n", 1)[0]
    assert first == ",".join(RFI_HEADER)


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


def slice_of(inputs: dict[str, dict[str, str]], c: GoldCitation) -> str:
    return inputs[c.rfi_id][c.column][c.start : c.end]


def in_scope_rows(citations: list[GoldCitation]) -> list[GoldCitation]:
    return [c for c in citations if c.scope == "in"]


def test_key_matches_slice(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    checked = 0
    for c in in_scope_rows(citations):
        if check_key_matches_slice(c, slice_of(inputs, c)):
            checked += 1
    assert checked > 100


def test_base_key_rule(citations: list[GoldCitation]) -> None:
    for c in citations:
        if c.scope == "in":
            assert c.base_key == expected_base(c.key), c
    for c in in_scope_rows(citations):
        if c.key.split(" ")[0] != "NESC" and c.clause_start is not None:
            assert key_clause(c.key) != "", c
        if c.key.split(" ")[0] != "NESC" and key_clause(c.key):
            assert c.clause_start is not None, c


def test_clause_matches_key(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    seen: set[str] = set()
    for c in in_scope_rows(citations):
        if c.clause_start is None or c.clause_end is None:
            assert key_clause(c.key) == "", c
            continue
        text = inputs[c.rfi_id][c.column][c.clause_start : c.clause_end]
        word = re.match(CLAUSE_WORDS, norm(text))
        assert word, (c, text)
        spoken = word.group(0)
        seen.add(spoken)
        number = norm(text)[len(spoken) :]
        wanted = key_clause(c.key)
        key_word = wanted.split(" ")[0].upper()
        assert norm(wanted)[len(key_word) :] == number, (c, text)
        if c.key.startswith("NESC"):
            assert key_word == ("SECTION" if spoken == "SEC." else spoken), c
        elif spoken in ("SECTION", "SEC.", "PARA", "CLAUSE"):
            assert key_word == "CLAUSE", c
        else:
            assert key_word == spoken, c
    assert {"SECTION", "SEC.", "PARA", "CLAUSE", "TABLE", "FIGURE", "ANNEX"} <= seen
    assert "RULE" in seen


def test_noise_is_backed_by_the_slice(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    for c in in_scope_rows(citations):
        piece = slice_of(inputs, c)
        noise = c.noise_class
        has_break = "\n" in piece or "\r" in piece
        has_dash = any(ch in DASHES for ch in piece)
        bodies = re.search(r"(?i)ieee|iec|ansi|nema|astm|nesc", piece)
        word = re.match(r"[A-Za-z]+", piece)
        first = word.group(0).upper() if word else ""
        if noise == "line_break":
            assert has_break, c
        else:
            assert not has_break, c
        if noise == "unicode_dash":
            assert has_dash, c
        else:
            assert not has_dash, c
        if noise == "spacing":
            assert (
                chr(0xA0) in piece
                or chr(0x202F) in piece
                or "  " in piece
                or re.search(r"(?i)(ieee|iec|ansi|nema|astm|nesc)\d", piece)
                or re.search(r"\b[A-Z] \d", piece)
                or re.search(r"\b(TC|MG|WD|ICS|VE|FB)\d", piece)
            ), c
        elif noise == "":
            assert chr(0xA0) not in piece and chr(0x202F) not in piece, c
            assert "  " not in piece, c
        if noise == "case":
            assert bodies is not None
            assert bodies.group(0) != bodies.group(0).upper(), c
        elif bodies is not None and noise != "list_continuation":
            assert bodies.group(0) == bodies.group(0).upper(), c
        unknown_body = first not in BODIES and first not in ("STD", "")
        if unknown_body and not is_bare(c) and noise != "list_continuation":
            assert noise == "misspelled", c
        if noise == "misspelled":
            assert unknown_body or re.search(r"\dO|O\d", piece), c
        if noise == "list_continuation":
            assert bodies is None, c
        if noise == "":
            assert all(ord(ch) < 128 for ch in piece), c


def test_inferred_matches_its_causes(citations: list[GoldCitation]) -> None:
    for c in in_scope_rows(citations):
        causes = c.noise_class == "list_continuation" or is_bare(c)
        assert c.inferred == causes, c


def test_independent_nema_items(
    labels: list[RfiLabel], citations: list[GoldCitation]
) -> None:
    group_of = {label.rfi_id: label.group_id for label in labels}
    per_rfi: dict[str, int] = {}
    for c in in_scope_rows(citations):
        if c.key.startswith("NEMA "):
            per_rfi[c.rfi_id] = per_rfi.get(c.rfi_id, 0) + 1
    per_group: dict[str, int] = {}
    for rfi_id, count in per_rfi.items():
        name = group_of[rfi_id]
        per_group[name] = max(per_group.get(name, 0), count)
    assert sum(per_group.values()) >= 15
    keys = {c.key for c in in_scope_rows(citations) if c.key.startswith("NEMA ")}
    assert "NEMA TC 2-2020" in keys
    assert any(key_clause(k) for k in keys)
    assert len([k for k in keys if re.search(r"-\d{4}", k)]) >= 4


def test_invented_and_noise_spread(citations: list[GoldCitation]) -> None:
    rows = in_scope_rows(citations)
    for body in BODIES:
        invented = [
            c for c in rows if c.key.startswith(body) and c.catalog == "invented"
        ]
        assert len(invented) >= 1, body
    for body in ("IEC", "ANSI", "NEMA"):
        invented = [
            c for c in rows if c.key.startswith(body) and c.catalog == "invented"
        ]
        assert len(invented) >= 2, body
    for noise in ("case", "line_break", "list_continuation", "misspelled"):
        assert len([c for c in rows if c.noise_class == noise]) >= 6, noise
    for noise in ("spacing", "unicode_dash"):
        assert len([c for c in rows if c.noise_class == noise]) >= 6, noise
    for body in ("NESC", "ANSI", "NEMA"):
        classes = {c.noise_class for c in rows if c.key.startswith(body)}
        assert len(classes - {""}) >= 3, body
    subjects = [c for c in rows if c.column == "subject"]
    assert len(subjects) >= 10


def test_windows_breaks_and_astral_characters(
    inputs: dict[str, dict[str, str]], citations: list[GoldCitation]
) -> None:
    crlf = [c for c in citations if "\r\n" in slice_of(inputs, c)]
    assert crlf
    assert all(c.noise_class == "line_break" for c in crlf)
    found = False
    for c in citations:
        before = inputs[c.rfi_id][c.column][: c.start]
        if any(ord(ch) > 0xFFFF for ch in before):
            found = True
            assert c.start > len(before.encode("utf-16-le")) // 2 - len(before)
    assert found
