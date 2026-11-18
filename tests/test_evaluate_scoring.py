from collections import Counter
from pathlib import Path

import pytest

from eval_helpers import W1_Q, W2_Q, at, cite, make_folder, write_rows
from rfikit.evaluate import (
    CITATION_HEADER,
    MAX_BYTES,
    RFI_HEADER,
    EvalPlan,
    GoldCitation,
    GoldNegative,
    Item,
    LabelError,
    Pred,
    drop_leaks,
    drop_overlaps,
    evaluate,
    evaluate_seeds,
    items_from_corpus,
    items_from_folder,
    leak_key,
    leak_pool,
    method_preds,
    read_inputs,
    rfikit_preds,
    score_groups,
    score_item,
)
from rfikit.synth import GenParams, generate
from rfikit.types import Rfi

SMALL = EvalPlan(report_seeds=(101, 102), n=30, train_seeds=(1,), draws=20)


def label_row(rfi_id: str) -> list[str]:
    return [rfi_id, "design_clarification", "single-" + rfi_id, "", "A"]


TEXT = "Use IEEE 80-2013 and Rule 12 and NFPA 70E."


def gold(
    start: int,
    end: int,
    key: str = "IEEE 80-2013",
    scope: str = "in",
    clause: tuple[int, int] | None = None,
    inferred: bool = False,
    noise: str = "",
    catalog: str = "real",
) -> GoldCitation:
    c = clause or (None, None)
    return GoldCitation(
        "R1",
        "question",
        start,
        end,
        c[0],
        c[1],
        key,
        key,
        scope,
        inferred,
        catalog,
        noise,
    )


def item(golds: list[GoldCitation], negs: list[GoldNegative] | None = None) -> Item:
    return Item(Rfi("R1", "", TEXT, ""), "A", tuple(golds), tuple(negs or []))


def pred(start: int, end: int, key: str = "IEEE 80-2013", body: str = "IEEE") -> Pred:
    return Pred("question", start, end, body, key, key)


def test_perfect_prediction() -> None:
    s, e = at(TEXT, "IEEE 80-2013")
    tally = score_item(item([gold(s, e)]), [pred(s, e)], True)
    for level in ("strict", "overlap", "full", "base"):
        assert (tally[level + ".tp"], tally[level + ".fp"], tally[level + ".fn"]) == (
            1,
            0,
            0,
        )
    assert tally["g.body.IEEE.key.gold_hit"] == 1
    assert tally["g.body.IEEE.key.pred_hit"] == 1


def test_longer_prediction_is_overlap_only() -> None:
    s, e = at(TEXT, "IEEE 80-2013")
    tally = score_item(item([gold(s, e)]), [pred(s, e + 4)], True)
    assert (tally["strict.tp"], tally["strict.fp"], tally["strict.fn"]) == (0, 1, 1)
    assert (tally["overlap.tp"], tally["overlap.fp"], tally["overlap.fn"]) == (1, 0, 0)
    assert tally["full.tp"] == 1


def test_wrong_key_counts_in_span_but_not_key() -> None:
    s, e = at(TEXT, "IEEE 80-2013")
    tally = score_item(item([gold(s, e)]), [pred(s, e, key="IEEE 80-2000")], True)
    assert tally["overlap.tp"] == 1
    assert tally["full.tp"] == 0
    assert tally["full.fp"] == 1
    assert tally["g.body.IEEE.overlap.gold_hit"] == 1
    assert tally["g.body.IEEE.key.gold_hit"] == 0
    assert tally["g.body.IEEE.key.pred_hit"] == 0


def test_out_of_scope_is_never_a_miss_but_a_hit_is_a_false_positive() -> None:
    s, e = at(TEXT, "NFPA 70E")
    out = gold(s, e, key="NFPA 70E", scope="out")
    quiet = score_item(item([out]), [], True)
    assert quiet["strict.fn"] == 0
    assert quiet["oos.total"] == 1
    assert quiet["oos.hit"] == 0
    loud = score_item(item([out]), [pred(s, e, key="NFPA 70E", body="IEEE")], True)
    assert loud["strict.fp"] == 1
    assert loud["overlap.fp"] == 1
    assert loud["oos.hit"] == 1


def test_negative_hit_per_kind() -> None:
    s, e = at(TEXT, "Rule 12")
    neg = GoldNegative("R1", "question", s, e, "bare_rule")
    miss = GoldNegative("R1", "question", 0, 3, "date")
    tally = score_item(item([], [neg, miss]), [pred(s, e)], True)
    assert tally["neg.bare_rule.total"] == 1
    assert tally["neg.bare_rule.hit"] == 1
    assert tally["neg.date.total"] == 1
    assert tally["neg.date.hit"] == 0
    assert tally["strict.fp"] == 1


def test_other_column_does_not_touch() -> None:
    s, e = at(TEXT, "Rule 12")
    neg = GoldNegative("R1", "subject", s, e, "bare_rule")
    tally = score_item(item([], [neg]), [pred(s, e)], True)
    assert tally["neg.bare_rule.hit"] == 0


def test_clause_line_uses_offsets_only() -> None:
    s, e = at(TEXT, "IEEE 80-2013")
    c = at(TEXT, "Rule 12")
    inferred = gold(c[0], c[1], key="NESC Rule 12", clause=c, inferred=True)
    right = Pred(
        "question", c[0], c[1], "NESC", "NESC Rule 12", "NESC Rule 12", True, c
    )
    wrong = Pred("question", s, e, "IEEE", "IEEE 80-2013", "IEEE 80", False, (0, 3))
    tally = score_item(item([inferred]), [right, wrong], True)
    assert (tally["clause.tp"], tally["clause.fp"], tally["clause.fn"]) == (1, 1, 0)


def test_groups_split_by_attribute() -> None:
    s, e = at(TEXT, "IEEE 80-2013")
    c = at(TEXT, "Rule 12")
    golds = [
        gold(s, e, noise="spacing", catalog="invented"),
        gold(c[0], c[1], key="NESC Rule 12", inferred=True),
    ]
    tally = score_item(item(golds), [pred(s, e)], True)
    assert tally["g.noise.spacing.strict.gold"] == 1
    assert tally["g.noise.spacing.strict.gold_hit"] == 1
    assert tally["g.noise.none.strict.gold_hit"] == 0
    assert tally["g.catalog.invented.overlap.gold"] == 1
    assert tally["g.inferred.inferred.strict.gold"] == 1
    assert tally["g.inferred.explicit.strict.pred"] == 1
    assert tally["g.inferred.explicit.strict.pred_hit"] == 1
    assert tally["g.body.NESC.strict.gold_hit"] == 0
    assert "g.noise.spacing.strict.pred" not in tally
    assert "g.catalog.invented.strict.pred" not in tally


def test_plain_method_scores_only_spans_and_body() -> None:
    s, e = at(TEXT, "IEEE 80-2013")
    tally = score_item(item([gold(s, e)]), [Pred("question", s, e, "IEEE")], False)
    assert tally["strict.tp"] == 1
    assert tally["g.body.IEEE.strict.pred_hit"] == 1
    assert "full.tp" not in tally
    assert "g.noise.none.strict.gold" not in tally
    assert "g.body.IEEE.key.gold" not in tally
    assert "oos.total" not in tally


def test_drop_overlaps_keeps_longest_first() -> None:
    spans = [("q", 5, 9), ("q", 0, 4), ("q", 0, 10), ("q", 12, 14), ("q", 13, 15)]
    assert drop_overlaps(spans) == [("q", 0, 10), ("q", 12, 14)]


def test_method_preds_runs_per_column() -> None:
    def method(text: str) -> list[tuple[str, int, int]]:
        return [("IEEE", 0, 4)] if "IEEE" in text else []

    rfi = Rfi("R1", "IEEE x", "none", "IEEE y")
    found = method_preds(rfi, method)
    assert [(p.column, p.start, p.end, p.body) for p in found] == [
        ("subject", 0, 4, "IEEE"),
        ("response", 0, 4, "IEEE"),
    ]


def test_rfikit_preds_carry_keys_and_clauses() -> None:
    found = rfikit_preds(Rfi("R1", "", W1_Q, ""))
    assert [p.key for p in found] == [
        "IEEE C57.12.00-2015 Clause 5.3",
        "ASTM A123/A123M-17",
    ]
    assert found[0].clause == at(W1_Q, "Section 5.3")
    assert found[1].clause is None


def test_leak_key_cleans_text() -> None:
    a = Rfi("R1", "Hello  World", "IEEE 80\u2010 2013\r\nx", "")
    b = Rfi("R2", "hello world", "ieee 80- 2013 x", "other response")
    assert leak_key(a) == leak_key(b)
    assert leak_key(a) != leak_key(Rfi("R3", "hello world", "ieee 80", ""))


def test_drop_leaks_counts() -> None:
    items = [item([]), Item(Rfi("R2", "s", "q", ""), "A", (), ())]
    pool = {leak_key(items[1].rfi)}
    kept, dropped = drop_leaks(items, pool)
    assert kept == [items[0]]
    assert dropped == 1


def test_leak_pool_has_both_families_of_every_train_seed() -> None:
    plan = EvalPlan(train_seeds=(1, 2), n=20)
    pool = leak_pool(plan)
    for seed in (1, 2):
        for family in ("A", "B"):
            corpus = generate(seed, 20, GenParams(families=(family,)))
            assert all(leak_key(g.rfi) in pool for g in corpus.rfis)


def test_report_seed_equal_to_train_seed_is_dropped_whole() -> None:
    plan = EvalPlan(report_seeds=(1,), n=25, train_seeds=(1,), draws=5)
    report = evaluate_seeds(plan)
    assert report.leak["A"] == {"rfis": 25, "dropped": 25}
    assert report.leak["B"] == {"rfis": 25, "dropped": 25}
    assert report.sets["A"].methods["rfikit"][0] == {}


def test_items_from_corpus_match_labels() -> None:
    corpus = generate(5, 20, GenParams(families=("B",)))
    items = items_from_corpus(corpus)
    assert len(items) == 20
    assert all(i.family == "B" for i in items)
    first = corpus.rfis[0]
    assert len(items[0].gold) == len(first.citations)
    assert len(items[0].negatives) == len(first.negatives)


def test_evaluate_tiny_folder_end_to_end(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    written = make_folder(tmp_path / "written", second_family="written")
    report = evaluate(folder, written, SMALL)
    a = Counter(report.sets["A"].methods["rfikit"][0])
    b = Counter(report.sets["B"].methods["rfikit"][0])
    w = Counter(report.sets["written"].methods["rfikit"][0])
    assert report.sets["A"].seeds == (0,)
    assert report.sets["written"].seeds == ()
    assert (a["strict.tp"], a["strict.fp"], a["strict.fn"]) == (2, 0, 0)
    assert (a["full.tp"], a["base.tp"]) == (2, 2)
    assert (a["clause.tp"], a["clause.fp"], a["clause.fn"]) == (1, 0, 0)
    assert (b["strict.tp"], b["strict.fp"], b["strict.fn"]) == (1, 2, 1)
    assert (b["full.tp"], b["full.fp"], b["full.fn"]) == (1, 2, 1)
    assert (b["oos.total"], b["oos.hit"]) == (2, 1)
    assert (b["neg.nema_enclosure.total"], b["neg.nema_enclosure.hit"]) == (1, 0)
    assert b["g.noise.misspelled.strict.gold"] == 1
    assert b["g.noise.misspelled.strict.gold_hit"] == 0
    assert b["g.body.ASTM.strict.pred"] == 1
    assert b["g.body.ASTM.strict.pred_hit"] == 0
    assert (w["strict.tp"], w["strict.fp"], w["strict.fn"]) == (3, 2, 1)
    assert report.leak["A"] == {"rfis": 1, "dropped": 0}
    assert report.pool == len(leak_pool(SMALL))


def test_evaluate_without_written(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    report = evaluate(folder, None, SMALL)
    assert set(report.sets) == {"A", "B"}


def test_extra_methods_are_scored_at_span_level(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")

    def first_word(text: str) -> list[tuple[str, int, int]]:
        return [("IEEE", 4, 8)] if text.startswith("Use ") else []

    report = evaluate(folder, None, SMALL, {"first": first_word})
    first = Counter(report.sets["A"].methods["first"][0])
    assert report.sets["A"].methods["first"][0]["strict.fn"] == 2
    assert first["overlap.tp"] == 1
    assert first["strict.fp"] == 1
    assert "full.tp" not in first


def test_method_name_rfikit_is_taken(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    with pytest.raises(ValueError):
        evaluate(folder, None, SMALL, {"rfikit": lambda text: []})


def test_evaluate_seeds_makes_one_tally_per_seed() -> None:
    report = evaluate_seeds(SMALL)
    assert report.sets["A"].seeds == (101, 102)
    assert len(report.sets["A"].methods["rfikit"]) == 2
    assert "written" not in report.sets


def test_score_groups_adds_up_items() -> None:
    s, e = at(TEXT, "IEEE 80-2013")
    one = Item(Rfi("R1", "", TEXT, ""), "A", (gold(s, e),), ())
    found = score_groups([[one, one], []], {})
    assert found["rfikit"][0]["rfis"] == 2
    assert found["rfikit"][0]["strict.tp"] == 2
    assert found["rfikit"][1] == {}


def test_read_inputs(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    rfis = read_inputs(folder / "input" / "rfis.csv")
    assert [r.rfi_id for r in rfis] == ["W1", "W2"]
    assert rfis[0].question == W1_Q


def test_folder_label_for_unknown_rfi(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    write_rows(
        folder / "labels" / "rfis.csv",
        RFI_HEADER,
        [label_row("W1"), label_row("W2"), label_row("W3")],
    )
    with pytest.raises(LabelError, match="unknown rfi_id"):
        items_from_folder(folder)


def test_folder_rfi_without_family(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    write_rows(folder / "labels" / "rfis.csv", RFI_HEADER, [label_row("W1")])
    with pytest.raises(LabelError, match="no family label"):
        items_from_folder(folder)


def test_folder_citation_for_unknown_rfi(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    row = [
        "W9",
        "question",
        "0",
        "4",
        "",
        "",
        "IEEE 1",
        "IEEE 1",
        "in",
        "0",
        "real",
        "",
    ]
    write_rows(folder / "labels" / "citations.csv", CITATION_HEADER, [row])
    with pytest.raises(LabelError, match="unknown rfi_id"):
        items_from_folder(folder)


def test_text_constant_has_second_rfi_parts() -> None:
    assert "ANSI/TIA-568" in W2_Q


def test_touching_ends_are_not_hits() -> None:
    s, e = at(TEXT, "Rule 12")
    neg = GoldNegative("R1", "question", e, e + 3, "date")
    out = gold(e + 4, e + 8, key="NFPA 1", scope="out")
    p = Pred("question", s, e, "NESC")
    tally = score_item(item([out], [neg]), [p], True)
    assert tally["neg.date.hit"] == 0
    assert tally["oos.hit"] == 0
    before = GoldNegative("R1", "question", s - 3, s, "date")
    assert score_item(item([], [before]), [p], True)["neg.date.hit"] == 0
    out_before = gold(s - 3, s, key="NFPA 1", scope="out")
    assert score_item(item([out_before]), [p], True)["oos.hit"] == 0


def test_overlapping_gold_in_one_column_is_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    rows = [
        cite("W1", W1_Q, "IEEE C57.12.00-2015", "IEEE C57", "IEEE C57"),
        cite("W1", W1_Q, "C57.12.00-2015", "IEEE C57", "IEEE C57"),
    ]
    write_rows(folder / "labels" / "citations.csv", CITATION_HEADER, rows)
    with pytest.raises(LabelError, match="overlap"):
        items_from_folder(folder)


def test_unknown_family_in_data_is_an_error(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data", second_family="C")
    with pytest.raises(LabelError, match="family 'C'"):
        evaluate(folder, None, SMALL)


@pytest.mark.parametrize(
    "changes",
    [
        {"draws": 0},
        {"draws": 100_001},
        {"report_seeds": ()},
        {"report_seeds": tuple(range(1001))},
        {"n": 0},
        {"bootstrap_seed": "x"},
        {"bootstrap_seed": True},
    ],
)
def test_plan_limits(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        EvalPlan(**changes)  # type: ignore[arg-type]


def test_plan_limits_allow_the_edges() -> None:
    EvalPlan(draws=1, n=1, report_seeds=(1,))
    EvalPlan(draws=100_000, report_seeds=tuple(range(1000)))


def test_big_label_file_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = make_folder(tmp_path / "data")
    monkeypatch.setattr("rfikit.evaluate.MAX_BYTES", 10)
    with pytest.raises(LabelError, match="over the limit of 10 bytes"):
        items_from_folder(folder)
    assert MAX_BYTES == 64 * 1024 * 1024


def test_symlinked_label_file_is_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    real = folder / "labels" / "negatives.csv"
    moved = tmp_path / "elsewhere.csv"
    real.rename(moved)
    real.symlink_to(moved)
    with pytest.raises(LabelError, match="symbolic link"):
        items_from_folder(folder)


def test_missing_label_file_names_the_file(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    (folder / "labels" / "negatives.csv").unlink()
    with pytest.raises(LabelError, match="negatives.csv: missing or not a regular"):
        items_from_folder(folder)


def test_label_folder_in_place_of_a_file_is_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    path = folder / "labels" / "negatives.csv"
    path.unlink()
    path.mkdir()
    with pytest.raises(LabelError, match="not a regular file"):
        items_from_folder(folder)


def test_unreadable_label_file_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = make_folder(tmp_path / "data")

    def refuse(self: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "open", refuse)
    with pytest.raises(LabelError, match="file cannot be read"):
        items_from_folder(folder)


def _repeat_last_row(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(lines) + lines[-1], encoding="utf-8")


def test_repeated_input_rfi_id_is_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    _repeat_last_row(folder / "input" / "rfis.csv")
    with pytest.raises(LabelError, match="input/rfis.csv repeats rfi_id"):
        items_from_folder(folder)


def test_repeated_label_rfi_id_is_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "data")
    _repeat_last_row(folder / "labels" / "rfis.csv")
    with pytest.raises(LabelError, match="labels/rfis.csv repeats rfi_id"):
        items_from_folder(folder)
