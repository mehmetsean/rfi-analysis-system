import ast
import re
import sys
from pathlib import Path

import pytest

from keychecks import check_key_matches_slice, expected_base, key_clause, norm
from rfikit.evaluate import NEGATIVE_KINDS, NOISE_CLASSES
from rfikit.synth import Corpus, GenParams, generate
from rfikit.synth.library import TEMPLATES
from rfikit.synth.templates import Template
from rfikit.types import BODIES
from synth_helpers import (
    BODY_WORDS,
    DASHES,
    EM_DASH,
    EN_DASH,
    NBSP,
    NNBSP,
    cites_nesc,
    column_text,
    explicit_nesc,
    has_break,
    to_gold,
)

SYNTH = Path(__file__).resolve().parent.parent / "src" / "rfikit" / "synth"
CLAUSE_START = ("RULE", "TABLE", "SECTION", "SEC.", "CLAUSE", "PARA", "FIGURE", "ANNEX")


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return generate(42, 600)


def test_same_call_same_corpus() -> None:
    assert generate(5, 30) == generate(5, 30)
    assert generate(5, 30) != generate(6, 30)


def test_size_and_ids(corpus: Corpus) -> None:
    assert corpus.n == 600 == len(corpus.rfis)
    assert [g.rfi.rfi_id for g in corpus.rfis[:2]] == ["R0001", "R0002"]
    assert generate(1, 0).rfis == ()
    assert generate(1, 12000).rfis[-1].rfi.rfi_id == "R12000"


def test_bad_arguments() -> None:
    with pytest.raises(ValueError):
        generate(1, -1)
    with pytest.raises(ValueError):
        generate(1, True)
    with pytest.raises(TypeError):
        generate(1.5, 3)  # type: ignore[arg-type]
    for bad in (
        {"noise_rate": 1.5},
        {"invented_rate": -0.1},
        {"families": ()},
        {"families": ("C",)},
        {"families": ("A", "A")},
    ):
        with pytest.raises(ValueError):
            GenParams(**bad)


def test_labels_match_the_text(corpus: Corpus) -> None:
    for g in corpus.rfis:
        for c in g.citations:
            text = column_text(g, c.column)
            assert 0 <= c.start < c.end <= len(text)
            assert text[c.start : c.end] == c.text
            assert c.text == c.text.strip()
        for n in g.negatives:
            text = column_text(g, n.column)
            assert 0 <= n.start < n.end <= len(text)
            assert text[n.start : n.end] == n.text


def test_clause_offsets(corpus: Corpus) -> None:
    for g in corpus.rfis:
        for c in g.citations:
            if c.clause_start is None or c.clause_end is None:
                assert c.clause_start is None and c.clause_end is None
                assert c.scope == "out" or key_clause(c.key) == "" or c.inferred
                continue
            text = column_text(g, c.column)
            assert 0 <= c.clause_start < c.clause_end <= len(text)
            piece = norm(text[c.clause_start : c.clause_end])
            assert piece.startswith(CLAUSE_START)
            if c.inferred:
                assert (c.start, c.end) == (c.clause_start, c.clause_end)
            else:
                assert c.clause_end <= c.start or c.clause_start >= c.end


def test_clause_words_map_to_key_words(corpus: Corpus) -> None:
    seen = set()
    for g in corpus.rfis:
        for c in g.citations:
            if c.clause_start is None or c.clause_end is None:
                continue
            text = column_text(g, c.column)[c.clause_start : c.clause_end]
            word, number = text.split(" ", 1)
            key_word, key_number = key_clause(c.key).split(" ", 1)
            assert number == key_number
            if c.key.startswith("NESC"):
                assert key_word == {"Sec.": "Section"}.get(word, word.capitalize())
            elif word.lower() in ("section", "sec.", "para", "clause"):
                assert key_word == "Clause"
            else:
                assert key_word == word.capitalize()
            seen.add(word)
    assert {"Section", "Sec.", "para", "Table", "Annex", "Rule", "Figure"} <= seen


def test_no_overlaps(corpus: Corpus) -> None:
    for g in corpus.rfis:
        for column in ("subject", "question", "response"):
            spans = [
                (c.start, c.end, "c") for c in g.citations if c.column == column
            ] + [(n.start, n.end, "n") for n in g.negatives if n.column == column]
            spans.sort()
            for left, right in zip(spans, spans[1:], strict=False):
                assert left[1] <= right[0], (g.rfi.rfi_id, left, right)


def test_keys_agree_with_the_text(corpus: Corpus) -> None:
    checked = 0
    for g in corpus.rfis:
        for c in g.citations:
            if c.scope != "in":
                continue
            gold = to_gold(g.rfi.rfi_id, c)
            piece = column_text(g, c.column)[c.start : c.end]
            if check_key_matches_slice(gold, piece):
                checked += 1
            assert c.base_key == expected_base(c.key), c
            if c.key.startswith("NESC"):
                assert (key_clause(c.key) != "") == (c.clause_start is not None)
            else:
                assert (key_clause(c.key) != "") == (c.clause_start is not None)
            assert c.key.isascii()
    assert checked > 500


def test_noise_labels_are_backed_by_the_text(corpus: Corpus) -> None:
    for g in corpus.rfis:
        for c in g.citations:
            assert c.noise_class in NOISE_CLASSES
            if c.scope == "out":
                assert c.noise_class == "" and not c.inferred
                assert c.text.isascii()
                continue
            piece = c.text
            assert has_break(piece) == (c.noise_class == "line_break")
            assert any(ch in DASHES for ch in piece) == (
                c.noise_class == "unicode_dash"
            )
            if c.noise_class == "":
                assert piece.isascii() and "  " not in piece
            if c.noise_class == "list_continuation":
                assert c.inferred
                assert not any(w in piece.upper() for w in BODY_WORDS)
            words = re.findall(r"(?i)ieee|iec|ansi|nema|astm|nesc", piece)
            if c.noise_class == "case":
                assert any(w != w.upper() for w in words)
            else:
                assert all(w == w.upper() for w in words)
            if c.noise_class == "spacing":
                assert (
                    NBSP in piece
                    or NNBSP in piece
                    or "  " in piece
                    or re.search(r"[A-Za-z]\d", piece)
                    or re.search(r"\b[A-Z] \d", piece)
                ), piece
            assert c.inferred == (
                c.noise_class == "list_continuation" or c.start == c.clause_start
            )


def test_bare_nesc_needs_context_elsewhere(corpus: Corpus) -> None:
    bare_seen = 0
    for g in corpus.rfis:
        for c in g.citations:
            if c.inferred and c.noise_class == "":
                bare_seen += 1
                assert explicit_nesc(g), g.rfi.rfi_id
                assert c.key.startswith("NESC ") and not any(
                    ch.isdigit() and part.isdigit() and len(part) == 4
                    for part in c.key.split(" ")[:2]
                    for ch in part
                )
        for n in g.negatives:
            if n.kind in ("bare_nesc_no_context", "bare_rule"):
                assert not cites_nesc(g), g.rfi.rfi_id
    assert bare_seen >= 20


def test_clause_word_negatives_have_no_citation_before(corpus: Corpus) -> None:
    for g in corpus.rfis:
        for n in g.negatives:
            if n.kind not in ("bare_rule", "bare_nesc_no_context", "spec_section"):
                continue
            for c in g.citations:
                if c.column == n.column and c.end <= n.start:
                    assert n.start - c.end > 45, (g.rfi.rfi_id, n, c)
            after = column_text(g, n.column)[n.end : n.end + 4]
            if n.kind != "bare_rule":
                assert not after.startswith((" of ", " in "))


def test_a_clause_after_the_designation_is_not_followed_by_of_or_in(
    corpus: Corpus,
) -> None:
    for g in corpus.rfis:
        for c in g.citations:
            if c.clause_end is not None and c.clause_start is not None:
                if c.clause_start >= c.end:
                    after = column_text(g, c.column)[c.clause_end : c.clause_end + 4]
                    assert not after.startswith((" of ", " in ")), after


def test_the_corpus_covers_every_class(corpus: Corpus) -> None:
    cites = [c for g in corpus.rfis for c in g.citations]
    in_scope = [c for c in cites if c.scope == "in"]
    for body in BODIES:
        assert len([c for c in in_scope if c.key.split(" ")[0] == body]) >= 15, body
    out_bodies = {c.key.split(" ")[0] for c in cites if c.scope == "out"}
    assert out_bodies == {"NFPA", "UL", "ASME", "ISA", "TIA", "CSA", "EN"}
    assert {c.noise_class for c in in_scope} == set(NOISE_CLASSES)
    assert {c.catalog for c in in_scope} == {"real", "invented"}
    kinds = {n.kind for g in corpus.rfis for n in g.negatives}
    assert kinds == set(NEGATIVE_KINDS)
    starts = [c.text for c in in_scope]
    for form in (
        "ANSI/IEEE",
        "IEC/IEEE",
        "IEEE/IEC",
        "ANSI/NEMA",
        "IEEE C2",
        "ANSI C2",
    ):
        assert any(t.startswith(form) for t in starts), form
    assert any(
        c.clause_start is not None and c.clause_start < c.start for c in in_scope
    )
    assert any(
        c.clause_start is not None and c.clause_start > c.start for c in in_scope
    )
    assert len([c for c in in_scope if c.inferred]) >= 50
    with_clause = [c for c in in_scope if c.clause_start is not None]
    assert len(with_clause) >= 50


def patch_templates(monkeypatch: pytest.MonkeyPatch, question: str) -> None:
    module = sys.modules["rfikit.synth.generate"]
    template = Template("dc-A9", "A", "design_clarification", "Subject", question, "")
    monkeypatch.setattr(module, "TEMPLATES", (template,))
    monkeypatch.setattr(module, "ISSUE_TYPES", ("design_clarification",))


def test_a_pool_that_is_too_small_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_templates(monkeypatch, "{d1}")
    with pytest.raises(RuntimeError, match="unused"):
        generate(1, 10)


def test_a_small_pool_gives_unique_values_under_the_pool_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_templates(monkeypatch, "{a1}")
    for seed in range(5):
        corpus = generate(seed, 5)
        assert len({g.rfi.question for g in corpus.rfis}) == 5


def test_noise_variants_do_not_count_as_new_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_templates(monkeypatch, "{y1} {d1}")
    seen = set()
    for g in generate(4, 60, GenParams(noise_rate=1.0)).rfis:
        key = (tuple(c.key for c in g.citations), g.rfi.question.split(" ")[-1])
        assert key not in seen
        seen.add(key)


def test_two_plain_citations_name_different_documents(corpus: Corpus) -> None:
    checked = 0
    for g in corpus.rfis:
        if g.template_id in ("cf-A3", "sr-A1", "dc-A1", "dc-B1"):
            found = [c for c in g.citations if c.column == "question"]
            assert len(found) == 2
            assert found[0].base_key != found[1].base_key
            checked += 1
    assert checked > 20


def test_the_texts_are_never_repeated(corpus: Corpus) -> None:
    seen = set()
    for g in corpus.rfis:
        item = (g.template_id, g.rfi.subject, g.rfi.question, g.rfi.response)
        assert item not in seen
        seen.add(item)
    big = generate(3, 4000)
    keys = {
        (g.template_id, g.rfi.subject, g.rfi.question, g.rfi.response) for g in big.rfis
    }
    assert len(keys) == 4000


def test_no_en_or_em_dash(corpus: Corpus) -> None:
    for g in corpus.rfis:
        text = g.rfi.subject + g.rfi.question + g.rfi.response
        assert EN_DASH not in text and EM_DASH not in text
    for path in SYNTH.glob("*.py"):
        raw = path.read_text(encoding="utf-8")
        assert EN_DASH not in raw and EM_DASH not in raw


def test_families_follow_the_template_list(corpus: Corpus) -> None:
    family_of = {t.template_id: t.family for t in TEMPLATES}
    for g in corpus.rfis:
        assert g.family == family_of[g.template_id]
    only_a = generate(9, 200, GenParams(families=("A",)))
    assert {g.family for g in only_a.rfis} == {"A"}
    assert all(not g.template_id.split("-")[1].startswith("B") for g in only_a.rfis)


def test_params_change_the_output() -> None:
    quiet = generate(2, 100, GenParams(noise_rate=0.0, invented_rate=0.0))
    cites = [c for g in quiet.rfis for c in g.citations if c.scope == "in"]
    assert all(c.noise_class in ("", "list_continuation") for c in cites)
    assert all(c.catalog == "real" or c.key.startswith("NESC") for c in cites)
    always = generate(2, 100, GenParams(response_rate=1.0, greeting_rate=1.0))
    assert all(
        g.rfi.question.split(". ")[0] in ("Hello team", "Good morning", "Hi all")
        for g in always.rfis
    )


def test_generator_does_not_import_evaluate() -> None:
    for path in sorted(SYNTH.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                names = [base] + [f"{base}.{a.name}" for a in node.names]
            else:
                continue
            for name in names:
                assert "evaluate" not in name.split("."), (path, name)


def test_norm_helper_still_strips_noise() -> None:
    assert norm("IEEE\r\nC57.12.\n00" + chr(0x2011) + " 2015") == "IEEEC57.12.00-2015"


def test_family_b_rows_are_about_a_quarter(corpus: Corpus) -> None:
    share = len([g for g in corpus.rfis if g.family == "B"]) / len(corpus.rfis)
    assert 0.15 < share < 0.35
    for g in corpus.rfis:
        assert ("-A" in g.template_id) == (g.family == "A")


def test_a_citation_pool_of_one_document_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rfikit.synth import cites
    from rfikit.synth.rng import Rng

    module = sys.modules["rfikit.synth.generate"]
    params = GenParams()
    only = cites.make_cite(Rng(3), params, "IEEE")
    monkeypatch.setattr(cites, "make_cite", lambda rng, p, body: only)
    with pytest.raises(RuntimeError, match="differs from the others"):
        module._another_cite(Rng(1), params, {"c1": only})
