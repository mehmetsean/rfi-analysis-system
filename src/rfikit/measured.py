import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from rfikit import __version__
from rfikit.evaluate import (
    EvalPlan,
    EvalReport,
    SetResult,
    SpanMethod,
    evaluate_seeds,
)
from rfikit.metrics import (
    bootstrap_draws,
    gap_intervals,
    harmonic,
    intervals,
    macro,
    ratio,
    wilson,
)
from rfikit.notice import LICENSE_LINE

Json = dict[str, Any]
Interval = tuple[float, float] | None

PLACES = 6
CI_PLAN = EvalPlan(report_seeds=(101, 102, 103))
FULL_PLAN = EvalPlan()
HEAD_LEVELS = ("strict", "overlap", "full", "base", "clause")
NO_PRECISION = ("noise", "catalog")
DATA_NOTE = (
    "Measured on synthetic data: generated sets A and B from rfikit.synth and the "
    "written set in heldout/."
)


def r6(value: float | None) -> float | None:
    return None if value is None else round(value, PLACES)


def r6s(pair: Interval) -> list[float] | None:
    if pair is None:
        return None
    return [round(pair[0], PLACES), round(pair[1], PLACES)]


def total(tallies: Sequence[Mapping[str, int]]) -> dict[str, int]:
    found: dict[str, int] = {}
    for tally in tallies:
        for key, value in tally.items():
            found[key] = found.get(key, 0) + value
    return found


def group_prefixes(keys: set[str]) -> list[str]:
    found = {k.rsplit(".", 1)[0] for k in keys if k.startswith("g.")}
    return sorted(found)


def _group_parts(prefix: str) -> tuple[str, str, str]:
    _, dim, rest = prefix.split(".", 2)
    value, level = rest.rsplit(".", 1)
    return dim, value, level


def make_ratios(
    keys: set[str],
) -> Callable[[Mapping[str, int]], dict[str, float | None]]:
    levels = [lv for lv in HEAD_LEVELS if lv + ".tp" in keys]
    groups = group_prefixes(keys)
    kinds = sorted(
        k.split(".")[1] for k in keys if k.startswith("neg.") and k.endswith(".total")
    )

    def ratios(t: Mapping[str, int]) -> dict[str, float | None]:
        found: dict[str, float | None] = {}
        for level in levels:
            tp, fp, fn = (t.get(f"{level}.{x}", 0) for x in ("tp", "fp", "fn"))
            p = ratio(tp, tp + fp)
            r = ratio(tp, tp + fn)
            found[f"{level}.precision"] = p
            found[f"{level}.recall"] = r
            found[f"{level}.f1"] = harmonic(p, r)
        for prefix in groups:
            found[prefix + ".recall"] = ratio(
                t.get(prefix + ".gold_hit", 0), t.get(prefix + ".gold", 0)
            )
            if prefix + ".pred" in keys:
                found[prefix + ".precision"] = ratio(
                    t.get(prefix + ".pred_hit", 0), t.get(prefix + ".pred", 0)
                )
        for kind in kinds:
            found[f"neg.{kind}.rate"] = ratio(
                t.get(f"neg.{kind}.hit", 0), t.get(f"neg.{kind}.total", 0)
            )
        if kinds:
            hit = sum(t.get(f"neg.{k}.hit", 0) for k in kinds)
            count = sum(t.get(f"neg.{k}.total", 0) for k in kinds)
            found["neg.all.rate"] = ratio(hit, count)
            found["oos.rate"] = ratio(t.get("oos.hit", 0), t.get("oos.total", 0))
        return found

    return ratios


def _level_block(
    t: Mapping[str, int],
    level: str,
    ci: Mapping[str, Interval] | None,
    exact: bool,
) -> Json:
    tp, fp, fn = (t.get(f"{level}.{x}", 0) for x in ("tp", "fp", "fn"))
    p = ratio(tp, tp + fp)
    r = ratio(tp, tp + fn)
    block: Json = {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": r6(p),
        "recall": r6(r),
        "f1": r6(harmonic(p, r)),
    }
    if ci is not None:
        block["ci"] = {
            name: r6s(ci.get(f"{level}.{name}"))
            for name in ("precision", "recall", "f1")
        }
    if exact:
        block["wilson"] = {
            "precision": r6s(wilson(tp, tp + fp)),
            "recall": r6s(wilson(tp, tp + fn)),
        }
    return block


def _group_block(
    t: Mapping[str, int], prefix: str, dim: str, ci: Mapping[str, Interval] | None
) -> Json:
    gold = t.get(prefix + ".gold", 0)
    gold_hit = t.get(prefix + ".gold_hit", 0)
    block: Json = {
        "gold": gold,
        "gold_hit": gold_hit,
        "recall": r6(ratio(gold_hit, gold)),
        "precision": None,
    }
    if dim not in NO_PRECISION:
        pred = t.get(prefix + ".pred", 0)
        pred_hit = t.get(prefix + ".pred_hit", 0)
        block["pred"] = pred
        block["pred_hit"] = pred_hit
        block["precision"] = r6(ratio(pred_hit, pred))
    if ci is not None:
        block["ci"] = {
            "precision": r6s(ci.get(prefix + ".precision")),
            "recall": r6s(ci.get(prefix + ".recall")),
        }
    return block


def _macro_block(groups: Json) -> Json:
    found: Json = {}
    for dim, values in groups.items():
        found[dim] = {}
        for level in next(iter(values.values())):
            rows = [values[v][level] for v in sorted(values)]
            precisions = [row["precision"] for row in rows]
            recalls = [row["recall"] for row in rows]
            entry: Json = {"recall": _macro_entry(recalls)}
            if dim not in NO_PRECISION:
                entry["precision"] = _macro_entry(precisions)
                f1s = [harmonic(p, r) for p, r in zip(precisions, recalls, strict=True)]
                entry["f1"] = _macro_entry(f1s)
            found[dim][level] = entry
    return found


def _macro_entry(values: Sequence[float | None]) -> Json:
    result = macro(values)
    return {
        "value": r6(result.value),
        "used": result.used,
        "skipped": result.skipped,
    }


def _groups_block(
    t: Mapping[str, int], keys: set[str], ci: Mapping[str, Interval] | None
) -> Json:
    groups: Json = {}
    prefixes = group_prefixes(keys)
    for prefix in prefixes:
        dim, value, level = _group_parts(prefix)
        groups.setdefault(dim, {}).setdefault(value, {})[level] = _group_block(
            t, prefix, dim, ci
        )
    return groups


def _negatives_block(
    t: Mapping[str, int], keys: set[str], ci: Mapping[str, Interval] | None, exact: bool
) -> Json:
    kinds = sorted(
        k.split(".")[1] for k in keys if k.startswith("neg.") and k.endswith(".total")
    )
    block: Json = {"kinds": {}}
    for kind in kinds:
        hit = t.get(f"neg.{kind}.hit", 0)
        count = t.get(f"neg.{kind}.total", 0)
        block["kinds"][kind] = {
            "total": count,
            "hit": hit,
            "rate": r6(ratio(hit, count)),
        }
    hit = sum(v["hit"] for v in block["kinds"].values())
    count = sum(v["total"] for v in block["kinds"].values())
    block["pooled"] = {"total": count, "hit": hit, "rate": r6(ratio(hit, count))}
    if ci is not None:
        block["pooled"]["ci"] = r6s(ci.get("neg.all.rate"))
    if exact:
        block["pooled"]["wilson"] = r6s(wilson(hit, count))
    out_hit = t.get("oos.hit", 0)
    out_total = t.get("oos.total", 0)
    block["out_of_scope"] = {
        "total": out_total,
        "hit": out_hit,
        "rate": r6(ratio(out_hit, out_total)),
    }
    return block


def _method_block(
    tallies: Sequence[Mapping[str, int]],
    draws: Sequence[Mapping[str, float | None]] | None,
    exact: bool,
) -> Json:
    keys = {k for t in tallies for k in t}
    t = total(tallies)
    ci = intervals(draws) if draws else None
    block: Json = {"rfis": t.get("rfis", 0)}
    block["levels"] = {
        level: _level_block(t, level, ci, exact)
        for level in HEAD_LEVELS
        if level + ".tp" in keys
    }
    block["groups"] = _groups_block(t, keys, ci)
    block["macro"] = _macro_block(block["groups"])
    if any(k.startswith("neg.") for k in keys):
        block["hard_negatives"] = _negatives_block(t, keys, ci, exact)
    return block


def _draws(
    result: SetResult, plan: EvalPlan, names: Sequence[str]
) -> dict[str, list[dict[str, float | None]]]:
    found: dict[str, list[dict[str, float | None]]] = {}
    if len(result.seeds) < 2:
        return found
    for name in names:
        tallies = result.methods[name]
        keys = {k for t in tallies for k in t}
        found[name] = bootstrap_draws(
            tallies, plan.draws, plan.bootstrap_seed, make_ratios(keys)
        )
    return found


def summarize(report: EvalReport) -> Json:
    plan = report.plan
    names = list(next(iter(report.sets.values())).methods)
    draws = {s: _draws(r, plan, names) for s, r in report.sets.items()}
    sets: Json = {}
    for set_name, result in report.sets.items():
        exact = set_name == "written"
        methods: Json = {}
        for name in names:
            methods[name] = _method_block(
                result.methods[name], draws[set_name].get(name), exact
            )
        sets[set_name] = {"seeds": len(result.seeds), "methods": methods}
    block: Json = {
        "plan": {
            "report_seeds": list(plan.report_seeds),
            "n": plan.n,
            "train_seeds": list(plan.train_seeds),
            "draws": plan.draws,
            "bootstrap_seed": plan.bootstrap_seed,
        },
        "leak": _leak_block(report),
        "sets": sets,
        "no_precision_dims": list(NO_PRECISION),
    }
    if draws.get("A") and draws.get("B"):
        block["gap_a_minus_b"] = {
            name: _gap_method(
                sets["A"]["methods"][name]["levels"],
                sets["B"]["methods"][name]["levels"],
                gap_intervals(draws["A"][name], draws["B"][name]),
            )
            for name in names
        }
    return block


def _gap_method(a: Json, b: Json, found: Mapping[str, Interval]) -> Json:
    block: Json = {}
    for level in a:
        block[level] = {}
        for name in ("precision", "recall", "f1"):
            x = a[level][name]
            y = b[level][name]
            value = None if x is None or y is None else round(x - y, PLACES)
            block[level][name] = {
                "value": value,
                "ci": r6s(found.get(f"{level}.{name}")),
            }
    return block


def _leak_block(report: EvalReport) -> Json:
    block: Json = {"pool_size": report.pool}
    for name, counts in report.leak.items():
        block[name] = {
            "rfis": counts["rfis"],
            "dropped": counts["dropped"],
            "fraction": r6(ratio(counts["dropped"], counts["rfis"])),
        }
    return block


def build_block(
    plan: EvalPlan, written: Path, methods: Mapping[str, SpanMethod]
) -> Json:
    return summarize(evaluate_seeds(plan, written, methods))


def build_doc(written: Path, methods: Mapping[str, SpanMethod]) -> Json:
    return {
        "rfikit_version": __version__,
        "notice": LICENSE_LINE,
        "data": DATA_NOTE,
        "full": build_block(FULL_PLAN, written, methods),
        "ci": build_block(CI_PLAN, written, methods),
    }


def render(doc: Json) -> str:
    return json.dumps(doc, sort_keys=True, indent=1) + "\n"
