from dataclasses import dataclass, replace

from rfikit.synth import catalog
from rfikit.synth.catalog import Entry
from rfikit.synth.forms import (
    NESC_FORMS,
    Clause,
    Rendered,
    render_bare_nesc,
    render_entry,
    render_list_item,
    render_nesc,
    render_out_of_scope,
    with_clause,
)
from rfikit.synth.noise import apply_noise, eligible
from rfikit.synth.params import GenParams
from rfikit.synth.rng import Rng

BODY_WEIGHTS = (
    ("IEEE", 28),
    ("ASTM", 18),
    ("IEC", 14),
    ("NEMA", 14),
    ("ANSI", 12),
    ("NESC", 14),
)
LIST_BODIES = ("IEEE", "IEC", "ANSI", "ASTM", "NEMA")
NON_NESC_WORDS = (
    ("Clause", "Clause"),
    ("clause", "Clause"),
    ("Section", "Clause"),
    ("section", "Clause"),
    ("Sec.", "Clause"),
    ("Para", "Clause"),
    ("para", "Clause"),
    ("Table", "Table"),
    ("table", "Table"),
    ("Figure", "Figure"),
    ("Annex", "Annex"),
)
NESC_WORDS = {
    "rule": (("Rule", "Rule"), ("rule", "Rule")),
    "table": (("Table", "Table"), ("table", "Table")),
    "section": (("Section", "Section"), ("Sec.", "Section"), ("section", "Section")),
}


@dataclass(frozen=True)
class CiteSpec:
    rendered: Rendered
    noise_class: str = ""
    clause: Clause | None = None
    clause_first: bool = False
    connector: str = ""
    clause_real: bool = True


@dataclass(frozen=True)
class ListSpec:
    items: tuple[CiteSpec, ...]
    separators: tuple[str, ...]


def pick_body(rng: Rng) -> str:
    names = [name for name, _ in BODY_WEIGHTS]
    return rng.weighted(names, [weight for _, weight in BODY_WEIGHTS])


def _clause_id(rng: Rng, word_key: str) -> str:
    if word_key == "Annex":
        return rng.pick(("A", "B", "C", "D", "E", "F"))
    if word_key in ("Table", "Figure"):
        if rng.chance(0.4):
            return f"{rng.between(1, 9)}-{rng.between(1, 9)}"
        return str(rng.between(1, 24))
    text = f"{rng.between(1, 14)}.{rng.between(1, 9)}"
    if rng.chance(0.3):
        text += f".{rng.between(1, 9)}"
    return text


def choose_clause(rng: Rng, body: str) -> tuple[Clause, bool]:
    if body == "NESC":
        kind = rng.weighted(("rule", "table", "section"), (60, 25, 15))
        real = rng.chance(0.75)
        number = catalog.nesc_clause(rng, kind, real)
        word, key_word = rng.pick(NESC_WORDS[kind])
        return Clause(f"{word} {number}", f"{key_word} {number}"), real
    word, key_word = rng.pick(NON_NESC_WORDS)
    number = _clause_id(rng, key_word)
    return Clause(f"{word} {number}", f"{key_word} {number}"), True


def _joint_token(rng: Rng, entry: Entry) -> str:
    body = entry.body
    allowed = {
        "IEEE": ("ANSI/IEEE", "IEEE/IEC"),
        "IEC": ("IEC/IEEE",),
        "NEMA": ("ANSI/NEMA",),
    }.get(body, ())
    token = body
    joint = entry.joint
    if not entry.real and allowed and rng.chance(0.2):
        joint = rng.pick(allowed)
    if joint and not entry.doc_type and rng.chance(0.5):
        token = joint
    if body == "IEEE" and rng.chance(0.35):
        token += " Std"
    return token


def _pick_entry(rng: Rng, params: GenParams, body: str, need_year: bool) -> Entry:
    while True:
        if rng.chance(params.invented_rate):
            entry = catalog.invent(rng, body)
        else:
            entry = rng.pick(catalog.REAL[body])
        if entry.editions or not need_year:
            return entry


def _noised(
    rng: Rng, params: GenParams, item: Rendered, misspell: bool
) -> tuple[Rendered, str]:
    if not rng.chance(params.noise_rate):
        return item, ""
    options = [name for name in eligible(item) if misspell or name != "misspelled"]
    if not options:
        return item, ""
    name = rng.pick(options)
    return replace(item, text=apply_noise(rng, item, name)), name


def _explicit(rng: Rng, params: GenParams, body: str, year_mode: str) -> Rendered:
    if body == "NESC":
        forms = [
            f for f in NESC_FORMS if year_mode == "any" or f[1] == (year_mode == "yes")
        ]
        form = rng.weighted([f[0] for f in forms], [f[2] for f in forms])
        year = rng.pick(catalog.NESC_EDITIONS) if "{y}" in form else ""
        return render_nesc(form, year, "real")
    entry = _pick_entry(rng, params, body, year_mode == "yes")
    year = ""
    suffix = ""
    if entry.editions and (
        year_mode == "yes" or (year_mode == "any" and rng.chance(0.6))
    ):
        edition = rng.pick(entry.editions)
        year, suffix = edition.year, edition.suffix
    token = _joint_token(rng, entry)
    return render_entry(
        body,
        entry.number,
        entry.part,
        entry.doc_type,
        year,
        suffix,
        token,
        "real" if entry.real else "invented",
    )


def make_cite(
    rng: Rng,
    params: GenParams,
    body: str,
    year_mode: str = "any",
    clause_mode: str = "any",
    misspell: bool = True,
) -> CiteSpec:
    rendered = _explicit(rng, params, body, year_mode)
    has_clause = clause_mode == "yes" or (clause_mode == "any" and rng.chance(0.3))
    clause = None
    clause_first = False
    connector = ""
    clause_real = True
    if has_clause:
        clause, clause_real = choose_clause(rng, body)
        clause_first = rng.chance(0.4)
        if clause_first:
            options = (
                (" of the ", " in the ", " of ") if body == "NESC" else (" of ", " in ")
            )
            connector = rng.pick(options)
        else:
            connector = rng.pick((", ", " ", ", "))
        if not clause_real:
            rendered = replace(rendered, catalog="invented")
    rendered = with_clause(rendered, clause)
    rendered, noise = _noised(rng, params, rendered, misspell)
    return CiteSpec(rendered, noise, clause, clause_first, connector, clause_real)


def make_pair(rng: Rng, params: GenParams) -> tuple[CiteSpec, CiteSpec]:
    while True:
        body = pick_body(rng)
        if body == "NESC":
            years = list(catalog.NESC_EDITIONS)
            rng.mix(years)
            forms = [f for f in NESC_FORMS if f[1]]
            picks = []
            for year in years[:2]:
                form = rng.weighted([f[0] for f in forms], [f[2] for f in forms])
                picks.append(render_nesc(form, year, "real"))
        else:
            entry = _pick_entry(rng, params, body, True)
            if len({(e.year, e.suffix) for e in entry.editions}) < 2:
                continue
            editions = list(entry.editions)
            rng.mix(editions)
            token = _joint_token(rng, entry)
            catalog_value = "real" if entry.real else "invented"
            picks = [
                render_entry(
                    body,
                    entry.number,
                    entry.part,
                    entry.doc_type,
                    e.year,
                    e.suffix,
                    token,
                    catalog_value,
                )
                for e in editions[:2]
            ]
        if picks[0].designation.key() == picks[1].designation.key():
            continue
        specs = []
        for item in picks:
            noised, name = _noised(rng, params, item, True)
            specs.append(CiteSpec(noised, name))
        return specs[0], specs[1]


def _fits(body: str, entry: Entry) -> bool:
    if entry.doc_type:
        return False
    if body == "IEEE":
        return entry.number.startswith("C") or "." in entry.number
    if body == "NEMA":
        return entry.number[0].isalpha()
    return True


def make_list(rng: Rng, params: GenParams) -> ListSpec:
    body = rng.pick(LIST_BODIES)
    while True:
        head = make_cite(rng, params, body, "any", "none", misspell=False)
        if not head.rendered.designation.doc_type:
            break
    used = [(head.rendered.designation.number, head.rendered.designation.part)]
    items: list[CiteSpec] = [head]
    for _ in range(rng.between(1, 3)):
        while True:
            entry = _pick_entry(rng, params, body, False)
            if _fits(body, entry) and (entry.number, entry.part) not in used:
                break
        used.append((entry.number, entry.part))
        year = ""
        suffix = ""
        if entry.editions and rng.chance(0.3):
            edition = rng.pick(entry.editions)
            year, suffix = edition.year, edition.suffix
        item = render_list_item(body, entry.number, entry.part, year, suffix)
        item = replace(item, catalog="real" if entry.real else "invented")
        items.append(CiteSpec(item, "list_continuation"))
    separators = []
    for index in range(1, len(items)):
        if index == len(items) - 1:
            separators.append(rng.pick((" and ", ", and ", ", ")))
        else:
            separators.append(", ")
    return ListSpec(tuple(items), tuple(separators))


def make_bare(rng: Rng) -> CiteSpec:
    kind = rng.weighted(("rule", "table"), (60, 40))
    real = rng.chance(0.8)
    number = catalog.nesc_clause(rng, kind, real)
    word, key_word = rng.pick(NESC_WORDS[kind])
    clause = Clause(f"{word} {number}", f"{key_word} {number}")
    rendered = render_bare_nesc(clause, "real" if real else "invented")
    return CiteSpec(rendered, "", clause, False, "", real)


def make_out(rng: Rng) -> CiteSpec:
    item = rng.pick(catalog.OUT_OF_SCOPE)
    dash = item.body == "TIA" and rng.chance(0.5)
    return CiteSpec(render_out_of_scope(item, dash))
