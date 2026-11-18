import csv
import json
from pathlib import Path

import pytest

from keychecks import check_key_matches_slice, expected_base
from rfikit.evaluate import (
    CITATION_HEADER,
    NEGATIVE_HEADER,
    RFI_HEADER,
    read_citations,
    read_negatives,
    read_rfi_labels,
)
from rfikit.synth import Corpus, GenParams, generate, render_files, write_corpus
from rfikit.synth.files import CITATION_HEADER as OUT_CITATION_HEADER
from rfikit.synth.files import NEGATIVE_HEADER as OUT_NEGATIVE_HEADER
from rfikit.synth.files import RFI_HEADER as OUT_RFI_HEADER
from rfikit.synth.files import sha256
from synth_helpers import column_text, to_gold

NAMES = [
    "README.txt",
    "input/README.txt",
    "input/rfis.csv",
    "labels/README.txt",
    "labels/citations.csv",
    "labels/negatives.csv",
    "labels/rfis.csv",
    "manifest.json",
]


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return generate(42, 200)


@pytest.fixture(scope="module")
def folder(corpus: Corpus, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("synth") / "data"
    write_corpus(corpus, out)
    return out


def test_the_file_set(folder: Path) -> None:
    found = sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file())
    assert found == sorted(NAMES)
    assert sorted(p.name for p in (folder / "input").iterdir()) == [
        "README.txt",
        "rfis.csv",
    ]


def test_manifest_checksums_verify(folder: Path) -> None:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert sorted(manifest["files"]) == sorted(n for n in NAMES if n != "manifest.json")
    for name, digest in manifest["files"].items():
        assert sha256((folder / name).read_bytes()) == digest, name
    assert manifest["generator"]["seed"] == 42
    assert manifest["generator"]["n"] == 200
    assert manifest["counts"]["rfis"] == 200
    assert manifest["counts"]["negatives"] > 0


def test_manifest_counts_match_the_labels(folder: Path) -> None:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    cites = read_citations(folder / "labels" / "citations.csv")
    negatives = read_negatives(folder / "labels" / "negatives.csv")
    counts = manifest["counts"]
    assert counts["citations_in_scope"] == len([c for c in cites if c.scope == "in"])
    assert counts["citations_out_of_scope"] == len(
        [c for c in cites if c.scope == "out"]
    )
    assert counts["negatives"] == len(negatives)
    assert sum(counts["families"].values()) == 200


def test_every_folder_has_the_notices(folder: Path) -> None:
    for name in ("README.txt", "input/README.txt", "labels/README.txt"):
        text = (folder / name).read_text(encoding="utf-8")
        assert "Synthetic data" in text or "synthetic" in text
        assert "All rights reserved." in text
        assert "https://www.linkedin.com/in/mstuzunkan" in text
    root = (folder / "README.txt").read_text(encoding="utf-8")
    assert "Decision support only" in root
    assert "No guarantee of compliance" in root
    assert "no affiliation with or endorsement" in root.replace("\n", " ")


def test_headers_match_the_label_readers() -> None:
    assert OUT_CITATION_HEADER == CITATION_HEADER
    assert OUT_NEGATIVE_HEADER == NEGATIVE_HEADER
    assert set(OUT_RFI_HEADER) < set(RFI_HEADER)


def test_files_are_accepted_by_the_readers(folder: Path, corpus: Corpus) -> None:
    cites = read_citations(folder / "labels" / "citations.csv")
    negatives = read_negatives(folder / "labels" / "negatives.csv")
    labels = read_rfi_labels(folder / "labels" / "rfis.csv")
    assert len(cites) == sum(len(g.citations) for g in corpus.rfis)
    assert len(negatives) == sum(len(g.negatives) for g in corpus.rfis)
    assert [(x.rfi_id, x.template_id, x.family) for x in labels] == [
        (g.rfi.rfi_id, g.template_id, g.family) for g in corpus.rfis
    ]
    assert all(x.issue_type == "" and x.group_id == "" for x in labels)


def read_inputs(folder: Path) -> dict[str, dict[str, str]]:
    with (folder / "input" / "rfis.csv").open(encoding="utf-8", newline="") as f:
        return {row["rfi_id"]: row for row in csv.DictReader(f)}


def test_labels_read_back_match_the_stored_text(folder: Path) -> None:
    inputs = read_inputs(folder)
    cites = read_citations(folder / "labels" / "citations.csv")
    negatives = read_negatives(folder / "labels" / "negatives.csv")
    checked = 0
    for c in cites:
        text = inputs[c.rfi_id][c.column]
        piece = text[c.start : c.end]
        assert piece and piece == piece.strip()
        if c.clause_start is not None and c.clause_end is not None:
            assert 0 <= c.clause_start < c.clause_end <= len(text)
        if c.scope == "in":
            if check_key_matches_slice(c, piece):
                checked += 1
            assert c.base_key == expected_base(c.key)
    assert checked > 100
    for n in negatives:
        text = inputs[n.rfi_id][n.column]
        assert 0 <= n.start < n.end <= len(text)
        for c in cites:
            if (c.rfi_id, c.column) == (n.rfi_id, n.column):
                assert n.end <= c.start or n.start >= c.end


def test_stored_text_equals_the_corpus(folder: Path, corpus: Corpus) -> None:
    inputs = read_inputs(folder)
    for g in corpus.rfis:
        row = inputs[g.rfi.rfi_id]
        for column in ("subject", "question", "response"):
            assert row[column] == column_text(g, column)
        for c in g.citations:
            assert to_gold(g.rfi.rfi_id, c).start == c.start


def test_crlf_and_non_ascii_survive_the_round_trip(
    folder: Path, corpus: Corpus
) -> None:
    raw = (folder / "input" / "rfis.csv").read_bytes()
    text = raw.decode("utf-8")
    assert not text.startswith("﻿")
    assert "\u2013" not in text and "\u2014" not in text
    stored = read_inputs(folder)
    assert any("\r\n" in row["question"] for row in stored.values())
    assert any(" " in row["subject"] + row["question"] for row in stored.values())


def test_writing_twice_gives_the_same_bytes(corpus: Corpus, tmp_path: Path) -> None:
    write_corpus(corpus, tmp_path / "a")
    write_corpus(corpus, tmp_path / "a")
    write_corpus(corpus, tmp_path / "b")
    for name in NAMES:
        assert (tmp_path / "a" / name).read_bytes() == (
            tmp_path / "b" / name
        ).read_bytes()
    assert render_files(corpus) == render_files(corpus)


def test_an_empty_corpus_still_writes_valid_files(tmp_path: Path) -> None:
    write_corpus(generate(1, 0), tmp_path)
    assert read_citations(tmp_path / "labels" / "citations.csv") == []
    assert read_rfi_labels(tmp_path / "labels" / "rfis.csv") == []


def test_manifest_records_the_parameters(tmp_path: Path) -> None:
    params = GenParams(noise_rate=0.5, families=("A",))
    write_corpus(generate(3, 20, params), tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generator"]["params"]["noise_rate"] == 0.5
    assert manifest["generator"]["params"]["families"] == ["A"]
    assert list(manifest["counts"]["families"]) == ["A"]
