import ast
import subprocess
import sys
from pathlib import Path

import pytest

from rfikit.cite import extract_rfi
from rfikit.evaluate import NEGATIVE_KINDS
from rfikit.synth import GenParams, generate
from rfikit.synth.model import GeneratedRfi

SEEDS = range(1, 11)
SRC = Path(__file__).resolve().parent.parent / "src" / "rfikit"
PARAMS = GenParams(families=("A",))


@pytest.fixture(scope="module")
def rows() -> list[GeneratedRfi]:
    found: list[GeneratedRfi] = []
    for seed in SEEDS:
        found.extend(generate(seed, 600, PARAMS).rfis)
    return found


def test_every_labeled_citation_is_found(rows: list[GeneratedRfi]) -> None:
    missed = []
    wrong = 0
    total = 0
    for row in rows:
        found = extract_rfi(row.rfi)
        spoiled = any(c.noise_class == "misspelled" for c in row.citations)
        for label in row.citations:
            if label.scope != "in" or label.noise_class == "misspelled":
                continue
            total += 1
            same = [
                c
                for c in found
                if c.column == label.column
                and (c.start, c.end) == (label.start, label.end)
            ]
            if not same:
                missed.append((row.rfi.rfi_id, label.text, label.noise_class))
            elif same[0].designation.key() != label.key and not spoiled:
                wrong += 1
    assert total > 1000
    assert missed == []
    assert wrong == 0


def test_inferred_flag_and_clause_offsets_agree(rows: list[GeneratedRfi]) -> None:
    for row in rows:
        found = extract_rfi(row.rfi)
        if any(c.noise_class == "misspelled" for c in row.citations):
            continue
        for label in row.citations:
            if label.scope != "in":
                continue
            same = [
                c
                for c in found
                if c.column == label.column
                and (c.start, c.end) == (label.start, label.end)
            ]
            assert same[0].inferred == label.inferred
            assert (same[0].clause_start, same[0].clause_end) == (
                label.clause_start,
                label.clause_end,
            )


def test_no_prediction_touches_a_hard_negative(rows: list[GeneratedRfi]) -> None:
    kinds = {n.kind for row in rows for n in row.negatives}
    assert set(NEGATIVE_KINDS) <= kinds
    for row in rows:
        found = extract_rfi(row.rfi)
        marks = list(row.negatives) + [c for c in row.citations if c.scope == "out"]
        for cite in found:
            for mark in marks:
                if mark.column != cite.column:
                    continue
                assert not (cite.start < mark.end and mark.start < cite.end), (
                    row.rfi.rfi_id,
                    cite.text,
                    mark.text,
                )


def test_cite_does_not_import_synth_or_evaluate() -> None:
    code = (
        "import sys, rfikit.cite, rfikit.cite_grammar, rfikit.textnorm\n"
        "bad = [m for m in sys.modules if m.startswith(('rfikit.synth',"
        " 'rfikit.evaluate'))]\n"
        "sys.exit(1 if bad else 0)\n"
    )
    done = subprocess.run([sys.executable, "-c", code], check=False)
    assert done.returncode == 0


def test_cite_files_import_only_types_and_textnorm() -> None:
    allowed = {"rfikit.types", "rfikit.textnorm", "rfikit.cite_grammar"}
    for name in ("cite.py", "cite_grammar.py", "textnorm.py"):
        tree = ast.parse((SRC / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("rfikit"):
                    assert node.module in allowed, (name, node.module)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("rfikit"), (name, alias.name)
