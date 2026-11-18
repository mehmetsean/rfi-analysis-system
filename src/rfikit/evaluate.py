import csv
import io
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from rfikit.cite import extract_rfi
from rfikit.metrics import (
    multiset_matches,
    overlap_pairs,
    strict_pairs,
)
from rfikit.synth import GenParams, generate
from rfikit.synth.model import Corpus
from rfikit.textnorm import clean
from rfikit.types import Rfi

COLUMNS = ("subject", "question", "response")
SCOPES = ("in", "out")
CATALOG_VALUES = ("real", "invented")
NOISE_CLASSES = (
    "",
    "misspelled",
    "list_continuation",
    "line_break",
    "unicode_dash",
    "spacing",
    "case",
)
ISSUE_TYPES = (
    "design_clarification",
    "missing_information",
    "document_conflict",
    "substitution_request",
    "field_condition",
    "standard_applicability",
)
NEGATIVE_KINDS = (
    "ieee_transactions",
    "rfi_number",
    "kva_rating",
    "bare_rule",
    "bare_nesc_no_context",
    "room_number",
    "sheet_number",
    "ip_rating",
    "drawing_number",
    "ansi_color",
    "ansi_class",
    "ansi_sheet",
    "astm_grade",
    "part_number",
    "nema_enclosure",
    "nema_plug",
    "nema_size",
    "nema_premium",
    "date",
    "spec_section",
)

CITATION_HEADER = (
    "rfi_id",
    "column",
    "start",
    "end",
    "clause_start",
    "clause_end",
    "key",
    "base_key",
    "scope",
    "inferred",
    "catalog",
    "noise_class",
)
NEGATIVE_HEADER = ("rfi_id", "column", "start", "end", "kind")
RFI_HEADER = ("rfi_id", "issue_type", "group_id", "template_id", "family")
RFI_REQUIRED = ("rfi_id", "template_id", "family")
INPUT_HEADER = ("rfi_id", "subject", "question", "response")
RFIKIT = "rfikit"
FAMILIES = ("A", "B")


class LabelError(ValueError):
    pass


@dataclass(frozen=True)
class GoldCitation:
    rfi_id: str
    column: str
    start: int
    end: int
    clause_start: int | None
    clause_end: int | None
    key: str
    base_key: str
    scope: str
    inferred: bool
    catalog: str
    noise_class: str


@dataclass(frozen=True)
class GoldNegative:
    rfi_id: str
    column: str
    start: int
    end: int
    kind: str


@dataclass(frozen=True)
class RfiLabel:
    rfi_id: str
    issue_type: str
    group_id: str
    template_id: str
    family: str


class _Row:
    def __init__(self, path: Path, line: int, values: dict[str, str]) -> None:
        self.path = path
        self.line = line
        self.values = values

    def fail(self, name: str, message: str) -> LabelError:
        return LabelError(
            f"{self.path.name} line {self.line}, column {name}: {message}"
        )

    def has(self, name: str) -> bool:
        return name in self.values

    def text(self, name: str) -> str:
        return self.values[name]

    def required(self, name: str) -> str:
        value = self.values[name]
        if value == "":
            raise self.fail(name, "value is empty")
        return value

    def integer(self, name: str) -> int:
        value = self.values[name]
        try:
            number = int(value)
        except ValueError:
            raise self.fail(name, f"not an integer: {value!r}") from None
        if number < 0:
            raise self.fail(name, f"negative offset: {number}")
        return number

    def optional_integer(self, name: str) -> int | None:
        if self.values[name] == "":
            return None
        return self.integer(name)

    def choice(self, name: str, allowed: tuple[str, ...]) -> str:
        value = self.values[name]
        if value not in allowed:
            raise self.fail(name, f"unknown value {value!r}, allowed: {list(allowed)}")
        return value

    def span(self) -> tuple[int, int]:
        start = self.integer("start")
        end = self.integer("end")
        if end <= start:
            raise self.fail("end", f"end {end} is not after start {start}")
        return start, end


def _read_rows(path: Path, header: tuple[str, ...]) -> list[_Row]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
    except UnicodeDecodeError:
        raise LabelError(f"{path.name}: file is not valid UTF-8") from None
    if text.startswith("\ufeff"):
        raise LabelError(f"{path.name}: file starts with a BOM, save it without one")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        first = next(reader, None)
        if first is None:
            raise LabelError(f"{path.name}: file is empty")
        for name in first:
            if first.count(name) > 1:
                raise LabelError(f"{path.name}: duplicate column {name!r}")
        for name in header:
            if name not in first:
                raise LabelError(f"{path.name}: missing column {name!r}")
        rows: list[_Row] = []
        for cells in reader:
            line = reader.line_num
            if len(cells) != len(first):
                raise LabelError(
                    f"{path.name} line {line}: expected {len(first)} cells, "
                    f"got {len(cells)}"
                )
            rows.append(_Row(path, line, dict(zip(first, cells, strict=True))))
    except csv.Error as error:
        raise LabelError(f"{path.name}: bad CSV: {error}") from None
    return rows


def read_citations(path: Path) -> list[GoldCitation]:
    result: list[GoldCitation] = []
    for row in _read_rows(path, CITATION_HEADER):
        start, end = row.span()
        clause_start = row.optional_integer("clause_start")
        clause_end = row.optional_integer("clause_end")
        if (clause_start is None) != (clause_end is None):
            raise row.fail("clause_end", "clause_start and clause_end go together")
        if clause_start is not None and clause_end is not None:
            if clause_end <= clause_start:
                raise row.fail("clause_end", "clause end is not after clause start")
        result.append(
            GoldCitation(
                rfi_id=row.required("rfi_id"),
                column=row.choice("column", COLUMNS),
                start=start,
                end=end,
                clause_start=clause_start,
                clause_end=clause_end,
                key=row.required("key"),
                base_key=row.required("base_key"),
                scope=row.choice("scope", SCOPES),
                inferred=row.choice("inferred", ("0", "1")) == "1",
                catalog=row.choice("catalog", CATALOG_VALUES),
                noise_class=row.choice("noise_class", NOISE_CLASSES),
            )
        )
    return result


def read_negatives(path: Path) -> list[GoldNegative]:
    result: list[GoldNegative] = []
    for row in _read_rows(path, NEGATIVE_HEADER):
        start, end = row.span()
        result.append(
            GoldNegative(
                rfi_id=row.required("rfi_id"),
                column=row.choice("column", COLUMNS),
                start=start,
                end=end,
                kind=row.choice("kind", NEGATIVE_KINDS),
            )
        )
    return result


def read_rfi_labels(path: Path) -> list[RfiLabel]:
    result: list[RfiLabel] = []
    for row in _read_rows(path, RFI_REQUIRED):
        issue_type = ""
        if row.has("issue_type"):
            issue_type = row.choice("issue_type", ISSUE_TYPES)
        group_id = row.required("group_id") if row.has("group_id") else ""
        result.append(
            RfiLabel(
                rfi_id=row.required("rfi_id"),
                issue_type=issue_type,
                group_id=group_id,
                template_id=row.text("template_id"),
                family=row.required("family"),
            )
        )
    return result


def read_inputs(path: Path) -> list[Rfi]:
    return [
        Rfi(
            row.required("rfi_id"),
            row.text("subject"),
            row.text("question"),
            row.text("response"),
        )
        for row in _read_rows(path, INPUT_HEADER)
    ]


@dataclass(frozen=True)
class EvalPlan:
    report_seeds: tuple[int, ...] = tuple(range(101, 131))
    n: int = 600
    train_seeds: tuple[int, ...] = tuple(range(1, 11))
    draws: int = 2000
    bootstrap_seed: int = 4242


@dataclass(frozen=True)
class Item:
    rfi: Rfi
    family: str
    gold: tuple[GoldCitation, ...]
    negatives: tuple[GoldNegative, ...]


@dataclass(frozen=True)
class Pred:
    column: str
    start: int
    end: int
    body: str
    key: str = ""
    base_key: str = ""
    inferred: bool = False
    clause: tuple[int, int] | None = None


@dataclass(frozen=True)
class SetResult:
    seeds: tuple[int, ...]
    methods: dict[str, list[dict[str, int]]]


@dataclass(frozen=True)
class EvalReport:
    plan: EvalPlan
    pool: int
    leak: dict[str, dict[str, int]]
    sets: dict[str, SetResult]


SpanMethod = Callable[[str], Sequence[tuple[str, int, int]]]
COLUMNS = ("subject", "question", "response")
KEYED_DIMS = ("body", "noise", "inferred", "catalog")
KEYED_LEVELS = ("strict", "overlap", "key")
PLAIN_LEVELS = ("strict", "overlap")


def items_from_corpus(corpus: Corpus) -> list[Item]:
    items: list[Item] = []
    for made in corpus.rfis:
        rid = made.rfi.rfi_id
        gold = tuple(
            GoldCitation(
                rid,
                c.column,
                c.start,
                c.end,
                c.clause_start,
                c.clause_end,
                c.key,
                c.base_key,
                c.scope,
                c.inferred,
                c.catalog,
                c.noise_class,
            )
            for c in made.citations
        )
        negatives = tuple(
            GoldNegative(rid, n.column, n.start, n.end, n.kind) for n in made.negatives
        )
        items.append(Item(made.rfi, made.family, gold, negatives))
    return items


def items_from_folder(folder: Path) -> list[Item]:
    rfis = read_inputs(folder / "input" / "rfis.csv")
    labels = read_rfi_labels(folder / "labels" / "rfis.csv")
    cites = read_citations(folder / "labels" / "citations.csv")
    negatives = read_negatives(folder / "labels" / "negatives.csv")
    families = {label.rfi_id: label.family for label in labels}
    known = {rfi.rfi_id for rfi in rfis}
    by_cite: dict[str, list[GoldCitation]] = {}
    by_neg: dict[str, list[GoldNegative]] = {}
    for c in cites:
        by_cite.setdefault(c.rfi_id, []).append(c)
    for n in negatives:
        by_neg.setdefault(n.rfi_id, []).append(n)
    for rfi_id in [*families, *by_cite, *by_neg]:
        if rfi_id not in known:
            raise LabelError(f"{folder.name}: label for unknown rfi_id {rfi_id!r}")
    items: list[Item] = []
    for rfi in rfis:
        if rfi.rfi_id not in families:
            raise LabelError(f"{folder.name}: no family label for {rfi.rfi_id!r}")
        items.append(
            Item(
                rfi,
                families[rfi.rfi_id],
                tuple(by_cite.get(rfi.rfi_id, ())),
                tuple(by_neg.get(rfi.rfi_id, ())),
            )
        )
    return items


def drop_overlaps(
    spans: Sequence[tuple[str, int, int]],
) -> list[tuple[str, int, int]]:
    kept: list[tuple[str, int, int]] = []
    last = 0
    for span in sorted(spans, key=lambda s: (s[1], -s[2])):
        if span[1] >= last:
            kept.append(span)
            last = span[2]
    return kept


def rfikit_preds(rfi: Rfi) -> list[Pred]:
    found: list[Pred] = []
    for c in extract_rfi(rfi):
        d = c.designation
        clause = None
        if c.clause_start is not None and c.clause_end is not None:
            clause = (c.clause_start, c.clause_end)
        found.append(
            Pred(
                c.column,
                c.start,
                c.end,
                d.body,
                d.key(),
                d.base_key(),
                c.inferred,
                clause,
            )
        )
    return found


def method_preds(rfi: Rfi, method: SpanMethod) -> list[Pred]:
    texts = (rfi.subject, rfi.question, rfi.response)
    found: list[Pred] = []
    for column, text in zip(COLUMNS, texts, strict=True):
        for body, start, end in drop_overlaps(method(text)):
            found.append(Pred(column, start, end, body))
    return found


def _level(tally: Counter[str], level: str, gold: int, pred: int, tp: int) -> None:
    tally[level + ".tp"] += tp
    tally[level + ".fp"] += pred - tp
    tally[level + ".fn"] += gold - tp


def _gold_groups(g: GoldCitation) -> dict[str, str]:
    return {
        "body": g.key.split(" ")[0],
        "noise": g.noise_class or "none",
        "inferred": "inferred" if g.inferred else "explicit",
        "catalog": g.catalog,
    }


def _pred_groups(p: Pred) -> dict[str, str]:
    return {"body": p.body, "inferred": "inferred" if p.inferred else "explicit"}


def _touches(column: str, start: int, end: int, p: Pred) -> bool:
    return p.column == column and p.start < end and start < p.end


def score_item(item: Item, preds: Sequence[Pred], keyed: bool) -> Counter[str]:
    tally: Counter[str] = Counter()
    tally["rfis"] += 1
    gold = [g for g in item.gold if g.scope == "in"]
    g_spans = [(g.column, g.start, g.end) for g in gold]
    p_spans = [(p.column, p.start, p.end) for p in preds]
    strict = strict_pairs(g_spans, p_spans)
    over = overlap_pairs(g_spans, p_spans)
    _level(tally, "strict", len(gold), len(preds), len(strict))
    _level(tally, "overlap", len(gold), len(preds), len(over))
    hits = {"strict": strict, "overlap": over}
    dims: tuple[str, ...] = ("body",)
    levels: tuple[str, ...] = PLAIN_LEVELS
    if keyed:
        hits["key"] = [(i, j) for i, j in over if preds[j].key == gold[i].key]
        dims = KEYED_DIMS
        levels = KEYED_LEVELS
    for level in levels:
        gold_hit = {i for i, _ in hits[level]}
        pred_hit = {j for _, j in hits[level]}
        for i, g in enumerate(gold):
            for dim, value in _gold_groups(g).items():
                if dim in dims:
                    prefix = f"g.{dim}.{value}.{level}."
                    tally[prefix + "gold"] += 1
                    tally[prefix + "gold_hit"] += int(i in gold_hit)
        for j, p in enumerate(preds):
            for dim, value in _pred_groups(p).items():
                if dim in dims:
                    prefix = f"g.{dim}.{value}.{level}."
                    tally[prefix + "pred"] += 1
                    tally[prefix + "pred_hit"] += int(j in pred_hit)
    if keyed:
        _keyed_levels(tally, item, gold, preds)
    return tally


def _keyed_levels(
    tally: Counter[str], item: Item, gold: list[GoldCitation], preds: Sequence[Pred]
) -> None:
    full = multiset_matches([g.key for g in gold], [p.key for p in preds])
    _level(tally, "full", len(gold), len(preds), full)
    base = multiset_matches([g.base_key for g in gold], [p.base_key for p in preds])
    _level(tally, "base", len(gold), len(preds), base)
    g_clauses = [
        (g.column, g.clause_start, g.clause_end)
        for g in gold
        if g.clause_start is not None and g.clause_end is not None
    ]
    p_clauses = [(p.column, p.clause[0], p.clause[1]) for p in preds if p.clause]
    _level(
        tally,
        "clause",
        len(g_clauses),
        len(p_clauses),
        len(strict_pairs(g_clauses, p_clauses)),
    )
    for n in item.negatives:
        tally[f"neg.{n.kind}.total"] += 1
        hit = any(_touches(n.column, n.start, n.end, p) for p in preds)
        tally[f"neg.{n.kind}.hit"] += int(hit)
    for o in item.gold:
        if o.scope == "out":
            tally["oos.total"] += 1
            hit = any(_touches(o.column, o.start, o.end, p) for p in preds)
            tally["oos.hit"] += int(hit)


def _norm(text: str) -> str:
    return " ".join(clean(text).casefold().split())


def leak_key(rfi: Rfi) -> tuple[str, str]:
    return _norm(rfi.subject), _norm(rfi.question)


def leak_pool(plan: EvalPlan) -> set[tuple[str, str]]:
    pool: set[tuple[str, str]] = set()
    for seed in plan.train_seeds:
        for family in FAMILIES:
            corpus = generate(seed, plan.n, GenParams(families=(family,)))
            pool.update(leak_key(made.rfi) for made in corpus.rfis)
    return pool


def drop_leaks(
    items: Sequence[Item], pool: set[tuple[str, str]]
) -> tuple[list[Item], int]:
    kept = [i for i in items if leak_key(i.rfi) not in pool]
    return kept, len(items) - len(kept)


def score_groups(
    groups: Sequence[Sequence[Item]], methods: Mapping[str, SpanMethod]
) -> dict[str, list[dict[str, int]]]:
    found: dict[str, list[dict[str, int]]] = {RFIKIT: []}
    found.update({name: [] for name in methods})
    for items in groups:
        totals: dict[str, Counter[str]] = {name: Counter() for name in found}
        for item in items:
            totals[RFIKIT].update(score_item(item, rfikit_preds(item.rfi), True))
            for name, method in methods.items():
                preds = method_preds(item.rfi, method)
                totals[name].update(score_item(item, preds, False))
        for name, total in totals.items():
            found[name].append(dict(total))
    return found


def _build(
    plan: EvalPlan,
    pool: set[tuple[str, str]],
    generated: Mapping[str, Sequence[Sequence[Item]]],
    seeds: tuple[int, ...],
    written: Sequence[Item] | None,
    methods: Mapping[str, SpanMethod],
) -> EvalReport:
    if RFIKIT in methods:
        raise ValueError(f"the method name {RFIKIT!r} is taken")
    leak: dict[str, dict[str, int]] = {}
    sets: dict[str, SetResult] = {}
    for name, groups in generated.items():
        kept: list[list[Item]] = []
        dropped = 0
        total = 0
        for items in groups:
            left, gone = drop_leaks(items, pool)
            kept.append(left)
            dropped += gone
            total += len(items)
        leak[name] = {"rfis": total, "dropped": dropped}
        sets[name] = SetResult(seeds, score_groups(kept, methods))
    if written is not None:
        sets["written"] = SetResult((), score_groups([written], methods))
    return EvalReport(plan, len(pool), leak, sets)


def evaluate_seeds(
    plan: EvalPlan,
    written: Path | None = None,
    methods: Mapping[str, SpanMethod] | None = None,
) -> EvalReport:
    generated: dict[str, list[list[Item]]] = {}
    for family in FAMILIES:
        params = GenParams(families=(family,))
        generated[family] = [
            items_from_corpus(generate(seed, plan.n, params))
            for seed in plan.report_seeds
        ]
    items = items_from_folder(written) if written is not None else None
    return _build(
        plan,
        leak_pool(plan),
        generated,
        plan.report_seeds,
        items,
        methods or {},
    )


def evaluate(
    data: Path,
    written: Path | None,
    plan: EvalPlan,
    methods: Mapping[str, SpanMethod] | None = None,
) -> EvalReport:
    items = items_from_folder(data)
    generated = {
        family: [[i for i in items if i.family == family]] for family in FAMILIES
    }
    extra = items_from_folder(written) if written is not None else None
    return _build(plan, leak_pool(plan), generated, (0,), extra, methods or {})
