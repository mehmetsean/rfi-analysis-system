import random
from collections.abc import Mapping

import pytest
from hypothesis import given
from hypothesis import strategies as st

from rfikit.metrics import (
    Counts,
    bootstrap_draws,
    f1,
    gap_intervals,
    harmonic,
    interval,
    intervals,
    macro,
    multiset_matches,
    overlap_pairs,
    precision,
    ratio,
    recall,
    strict_pairs,
    sweep,
    wilson,
)


def test_ratio_zero_over_zero_is_none() -> None:
    assert ratio(0, 0) is None
    assert ratio(0, 5) == 0.0
    assert ratio(5, 5) == 1.0
    assert ratio(1, 4) == 0.25


def test_counts_hand_computed() -> None:
    c = Counts(tp=6, fp=2, fn=4)
    assert precision(c) == 0.75
    assert recall(c) == 0.6
    assert f1(c) == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6))


def test_counts_add() -> None:
    assert Counts(1, 2, 3) + Counts(4, 5, 6) == Counts(5, 7, 9)


def test_empty_counts_are_none() -> None:
    c = Counts()
    assert precision(c) is None
    assert recall(c) is None
    assert f1(c) is None


def test_no_predictions_gives_no_precision_but_zero_recall() -> None:
    c = Counts(tp=0, fp=0, fn=3)
    assert precision(c) is None
    assert recall(c) == 0.0
    assert f1(c) is None


def test_no_gold_gives_no_recall() -> None:
    c = Counts(tp=0, fp=3, fn=0)
    assert precision(c) == 0.0
    assert recall(c) is None
    assert f1(c) is None


def test_zero_precision_and_recall_gives_zero_f1() -> None:
    assert f1(Counts(tp=0, fp=2, fn=2)) == 0.0


def test_perfect_counts_score_one() -> None:
    c = Counts(tp=7, fp=0, fn=0)
    assert (precision(c), recall(c), f1(c)) == (1.0, 1.0, 1.0)


def test_harmonic() -> None:
    assert harmonic(None, 0.5) is None
    assert harmonic(0.5, None) is None
    assert harmonic(0.0, 0.0) == 0.0
    assert harmonic(0.5, 1.0) == pytest.approx(2 / 3)


def test_macro_skips_none_and_counts_them() -> None:
    result = macro([0.5, None, 1.0, None, 0.0])
    assert result.value == 0.5
    assert result.used == 3
    assert result.skipped == 2


def test_macro_of_nothing_is_none() -> None:
    result = macro([None, None])
    assert result.value is None
    assert (result.used, result.skipped) == (0, 2)
    assert macro([]).value is None


def test_strict_pairs_same_column_start_end() -> None:
    gold = [("question", 0, 5), ("question", 10, 15), ("subject", 0, 5)]
    pred = [("subject", 0, 5), ("question", 10, 14), ("question", 0, 5)]
    pairs = strict_pairs(gold, pred)
    assert sorted(pairs) == [(0, 2), (2, 0)]


def test_strict_pairs_are_one_to_one() -> None:
    gold = [("question", 0, 5)]
    pred = [("question", 0, 5), ("question", 0, 5)]
    assert strict_pairs(gold, pred) == [(0, 0)]


def test_sweep_hand_cases() -> None:
    assert sweep([(0, 5), (10, 15)], [(3, 8), (12, 20)]) == [(0, 0), (1, 1)]
    assert sweep([(0, 5)], [(5, 8)]) == []
    assert sweep([(0, 10)], [(0, 4), (5, 9)]) == [(0, 0)]
    assert sweep([(0, 4), (5, 9)], [(0, 10)]) == [(0, 0)]
    assert sweep([], [(0, 1)]) == []
    assert sweep([(0, 1)], []) == []


def test_overlap_pairs_by_column_with_original_indices() -> None:
    gold = [("question", 20, 30), ("subject", 0, 5), ("question", 0, 10)]
    pred = [("question", 5, 12), ("subject", 4, 9), ("question", 25, 26)]
    pairs = overlap_pairs(gold, pred)
    assert sorted(pairs) == [(0, 2), (1, 1), (2, 0)]


def test_overlap_pairs_other_column_never_matches() -> None:
    assert overlap_pairs([("subject", 0, 5)], [("question", 0, 5)]) == []


def brute_force_size(gold: list[tuple[int, int]], pred: list[tuple[int, int]]) -> int:
    edges = [
        [j for j, p in enumerate(pred) if g[0] < p[1] and p[0] < g[1]] for g in gold
    ]
    owner: dict[int, int] = {}

    def try_gold(i: int, seen: set[int]) -> bool:
        for j in edges[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in owner or try_gold(owner[j], seen):
                owner[j] = i
                return True
        return False

    return sum(1 for i in range(len(gold)) if try_gold(i, set()))


def disjoint_spans(cuts: list[int], keep: list[bool]) -> list[tuple[int, int]]:
    points = sorted(set(cuts))
    spans = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    return [s for s, k in zip(spans, keep, strict=False) if k]


span_lists = st.builds(
    disjoint_spans,
    st.lists(st.integers(0, 60), min_size=2, max_size=14),
    st.lists(st.booleans(), min_size=14, max_size=14),
)


@given(span_lists, span_lists)
def test_sweep_matches_brute_force(
    gold: list[tuple[int, int]], pred: list[tuple[int, int]]
) -> None:
    pairs = sweep(gold, pred)
    assert len(pairs) == brute_force_size(gold, pred)
    assert len({g for g, _ in pairs}) == len(pairs)
    assert len({p for _, p in pairs}) == len(pairs)
    for g, p in pairs:
        assert gold[g][0] < pred[p][1] and pred[p][0] < gold[g][1]


def test_multiset_matches() -> None:
    assert multiset_matches(["a", "a", "b"], ["a", "b", "b", "c"]) == 2
    assert multiset_matches([], ["a"]) == 0
    assert multiset_matches(["a"], []) == 0
    assert multiset_matches(["a", "a"], ["a", "a"]) == 2


def test_wilson_known_values() -> None:
    lo, hi = wilson(81, 263) or (0.0, 0.0)
    assert (round(lo, 4), round(hi, 4)) == (0.2553, 0.3662)
    lo, hi = wilson(15, 148) or (0.0, 0.0)
    assert (round(lo, 4), round(hi, 4)) == (0.0624, 0.1605)
    lo, hi = wilson(0, 20) or (1.0, 1.0)
    assert (lo, round(hi, 4)) == (0.0, 0.1611)
    lo, hi = wilson(20, 20) or (0.0, 0.0)
    assert (round(lo, 4), hi) == (0.8389, 1.0)


def test_wilson_empty_is_none() -> None:
    assert wilson(0, 0) is None


def test_wilson_rejects_bad_counts() -> None:
    with pytest.raises(ValueError):
        wilson(3, 2)
    with pytest.raises(ValueError):
        wilson(-1, 2)


@given(st.integers(1, 500).flatmap(lambda n: st.tuples(st.integers(0, n), st.just(n))))
def test_wilson_contains_the_proportion(pair: tuple[int, int]) -> None:
    k, n = pair
    found = wilson(k, n)
    assert found is not None
    lo, hi = found
    assert 0.0 <= lo <= k / n <= hi <= 1.0


def total_ratios(tally: Mapping[str, int]) -> dict[str, float | None]:
    return {"hit": ratio(tally["hit"], tally["all"])}


def test_draws_are_fixed_by_seed() -> None:
    items = [{"hit": 1, "all": 2}, {"hit": 2, "all": 2}, {"hit": 0, "all": 2}]
    first = bootstrap_draws(items, 50, 7, total_ratios)
    again = bootstrap_draws(items, 50, 7, total_ratios)
    other = bootstrap_draws(items, 50, 8, total_ratios)
    assert first == again
    assert first != other
    assert len(first) == 50


def test_draws_use_one_index_stream() -> None:
    rng = random.Random(7)
    items = [{"hit": 1, "all": 1}, {"hit": 0, "all": 1}]
    first = bootstrap_draws(items, 1, 7, total_ratios)[0]["hit"]
    picks = [int(rng.random() * 2) for _ in range(2)]
    assert first == sum(1 - p for p in picks) / 2


def test_draws_of_one_item_are_constant() -> None:
    items = [{"hit": 3, "all": 4}]
    found = bootstrap_draws(items, 20, 1, total_ratios)
    assert all(d["hit"] == 0.75 for d in found)
    assert intervals(found) == {"hit": (0.75, 0.75)}


def test_draws_of_no_items() -> None:
    assert bootstrap_draws([], 5, 1, total_ratios) == []
    assert intervals([]) == {}
    assert gap_intervals([], []) == {}


def test_interval_percentile_rule() -> None:
    values: list[float | None] = [float(i) for i in range(2000)]
    assert interval(values) == (50.0, 1949.0)
    shuffled = list(reversed(values))
    assert interval(shuffled) == (50.0, 1949.0)


def test_interval_none_when_any_draw_is_undefined() -> None:
    assert interval([0.1, None, 0.3]) is None
    assert interval([]) is None


def test_intervals_by_name() -> None:
    draws: list[dict[str, float | None]] = [
        {"a": float(i), "b": None} for i in range(40)
    ]
    found = intervals(draws)
    assert found["a"] == (1.0, 38.0)
    assert found["b"] is None


def test_gap_uses_the_same_draws() -> None:
    items_a = [{"hit": 2, "all": 2}, {"hit": 1, "all": 2}]
    items_b = [{"hit": 1, "all": 2}, {"hit": 0, "all": 2}]
    a = bootstrap_draws(items_a, 100, 3, total_ratios)
    b = bootstrap_draws(items_b, 100, 3, total_ratios)
    found = gap_intervals(a, b)
    expected = sorted(
        (x["hit"] or 0.0) - (y["hit"] or 0.0) for x, y in zip(a, b, strict=True)
    )
    assert found["hit"] == (expected[2], expected[97])


def test_gap_none_when_a_side_is_undefined() -> None:
    a: list[dict[str, float | None]] = [{"x": 0.5}] * 10
    b: list[dict[str, float | None]] = [{"x": None}] * 10
    assert gap_intervals(a, b) == {"x": None}
    with pytest.raises(ValueError):
        gap_intervals(a, [{"x": 0.5}] * 9)
