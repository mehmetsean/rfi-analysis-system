import math
import random
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

Z95 = 1.959963984540054
TAIL = 0.025

Span = tuple[str, int, int]
Tally = Mapping[str, int]
Ratios = Mapping[str, float | None]


@dataclass(frozen=True)
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def __add__(self, other: "Counts") -> "Counts":
        return Counts(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)


def ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def harmonic(p: float | None, r: float | None) -> float | None:
    if p is None or r is None:
        return None
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def precision(c: Counts) -> float | None:
    return ratio(c.tp, c.tp + c.fp)


def recall(c: Counts) -> float | None:
    return ratio(c.tp, c.tp + c.fn)


def f1(c: Counts) -> float | None:
    return harmonic(precision(c), recall(c))


@dataclass(frozen=True)
class Macro:
    value: float | None
    used: int
    skipped: int


def macro(values: Sequence[float | None]) -> Macro:
    found = [v for v in values if v is not None]
    skipped = len(values) - len(found)
    if not found:
        return Macro(None, 0, skipped)
    return Macro(sum(found) / len(found), len(found), skipped)


def strict_pairs(gold: Sequence[Span], pred: Sequence[Span]) -> list[tuple[int, int]]:
    free: dict[Span, list[int]] = {}
    for j, span in enumerate(pred):
        free.setdefault(span, []).append(j)
    pairs: list[tuple[int, int]] = []
    for i, span in enumerate(gold):
        if free.get(span):
            pairs.append((i, free[span].pop(0)))
    return pairs


def sweep(
    gold: Sequence[tuple[int, int]], pred: Sequence[tuple[int, int]]
) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    i = j = 0
    while i < len(gold) and j < len(pred):
        if gold[i][1] <= pred[j][0]:
            i += 1
        elif pred[j][1] <= gold[i][0]:
            j += 1
        else:
            pairs.append((i, j))
            i += 1
            j += 1
    return pairs


def _by_column(spans: Sequence[Span]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for index, (column, _, _) in enumerate(spans):
        found.setdefault(column, []).append(index)
    for indexes in found.values():
        indexes.sort(key=lambda k: spans[k][1])
    return found


def overlap_pairs(gold: Sequence[Span], pred: Sequence[Span]) -> list[tuple[int, int]]:
    g_cols = _by_column(gold)
    p_cols = _by_column(pred)
    pairs: list[tuple[int, int]] = []
    for column, g_idx in g_cols.items():
        p_idx = p_cols.get(column, [])
        g_spans = [(gold[k][1], gold[k][2]) for k in g_idx]
        p_spans = [(pred[k][1], pred[k][2]) for k in p_idx]
        for a, b in sweep(g_spans, p_spans):
            pairs.append((g_idx[a], p_idx[b]))
    return pairs


def multiset_matches(gold: Sequence[str], pred: Sequence[str]) -> int:
    have = Counter(gold)
    want = Counter(pred)
    return sum(min(count, want[key]) for key, count in have.items())


def wilson(k: int, n: int) -> tuple[float, float] | None:
    if k < 0 or k > n:
        raise ValueError("k must be between 0 and n")
    if n == 0:
        return None
    p = k / n
    z2 = Z95 * Z95
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    lo = 0.0 if k == 0 else centre - half
    hi = 1.0 if k == n else centre + half
    return lo, hi


def bootstrap_draws(
    items: Sequence[Tally],
    draws: int,
    seed: int,
    ratios: Callable[[Tally], Ratios],
) -> list[dict[str, float | None]]:
    if not items:
        return []
    rng = random.Random(seed)
    size = len(items)
    found: list[dict[str, float | None]] = []
    for _ in range(draws):
        total: Counter[str] = Counter()
        for _ in range(size):
            for key, value in items[int(rng.random() * size)].items():
                total[key] += value
        found.append(dict(ratios(total)))
    return found


def interval(values: Sequence[float | None]) -> tuple[float, float] | None:
    if not values:
        return None
    defined = [v for v in values if v is not None]
    if len(defined) != len(values):
        return None
    defined.sort()
    k = int(len(defined) * TAIL)
    return defined[k], defined[len(defined) - 1 - k]


def intervals(
    per_draw: Sequence[Ratios],
) -> dict[str, tuple[float, float] | None]:
    if not per_draw:
        return {}
    return {name: interval([d[name] for d in per_draw]) for name in per_draw[0]}


def gap_intervals(
    a: Sequence[Ratios], b: Sequence[Ratios]
) -> dict[str, tuple[float, float] | None]:
    if len(a) != len(b):
        raise ValueError("both sides need the same draws")
    found: dict[str, tuple[float, float] | None] = {}
    for name in a[0] if a else {}:
        diffs: list[float | None] = []
        for left, right in zip(a, b, strict=True):
            x, y = left[name], right.get(name)
            diffs.append(None if x is None or y is None else x - y)
        found[name] = interval(diffs)
    return found
