from rfikit.synth import cites, negatives
from rfikit.synth.build import Builder
from rfikit.synth.cites import CiteSpec, ListSpec
from rfikit.synth.library import TEMPLATES
from rfikit.synth.model import Corpus, GeneratedRfi
from rfikit.synth.negatives import NegSpec
from rfikit.synth.params import GenParams
from rfikit.synth.rng import Rng
from rfikit.synth.templates import ISSUE_TYPES, Template, split_slots
from rfikit.types import Rfi

COLUMNS = ("subject", "question", "response")
DISCIPLINES = ("substation", "distribution line", "solar plant", "commercial building")
ITEMS = (
    "main transformer",
    "feeder breaker",
    "inverter skid",
    "switchgear lineup",
    "grounding grid",
    "cable tray",
    "pole structure",
    "panelboard",
    "pad mount unit",
    "conduit run",
)
ROLES = (
    "CONTRACTOR_PM",
    "OWNER_REP",
    "EOR",
    "CONTRACTOR_SUPER",
    "ELECTRICAL_LEAD",
    "VENDOR_REP",
)
AREAS = ("Area 3", "Bay 2", "Zone B", "Yard C", "Level 2", "Block 5")
GREETINGS = ("Hello team. ", "Good morning. ", "Hi all. ")
MAX_TRIES = 500

Spec = CiteSpec | ListSpec | NegSpec | str
Done = tuple[Rfi, tuple[Builder, ...], tuple[str, ...]]


def _draw_cites(
    rng: Rng, params: GenParams, names: list[str]
) -> dict[str, CiteSpec | ListSpec]:
    found: dict[str, CiteSpec | ListSpec] = {}
    for name in names:
        kind = name[0]
        if name in found:
            continue
        if kind == "c":
            found[name] = _another_cite(rng, params, found)
        elif kind == "w":
            found[name] = cites.make_cite(
                rng, params, cites.pick_body(rng), clause_mode="yes"
            )
        elif kind == "y":
            found[name] = cites.make_cite(
                rng, params, cites.pick_body(rng), "none", "none"
            )
        elif kind == "e":
            first, second = cites.make_pair(rng, params)
            found["e1"], found["e2"] = first, second
        elif kind == "n":
            found[name] = cites.make_cite(rng, params, "NESC", misspell=False)
        elif kind == "l":
            found[name] = cites.make_list(rng, params)
        elif kind == "b":
            found[name] = cites.make_bare(rng)
        elif kind == "o":
            found[name] = cites.make_out(rng)
    return found


def _another_cite(
    rng: Rng, params: GenParams, found: dict[str, CiteSpec | ListSpec]
) -> CiteSpec:
    used = [
        spec.rendered.designation.base_key()
        for name, spec in found.items()
        if name[0] == "c" and isinstance(spec, CiteSpec)
    ]
    for _ in range(MAX_TRIES):
        spec = cites.make_cite(rng, params, cites.pick_body(rng))
        if spec.rendered.designation.base_key() not in used:
            return spec
    raise RuntimeError(
        "could not draw a citation that differs from the others in the template;"
        " widen the catalog or the invented number pool, then run again"
    )


def _text_value(rng: Rng, params: GenParams, kind: str) -> str:
    if kind == "p":
        return f"P-{rng.between(1, 9999):04d}"
    if kind == "d":
        return rng.pick(DISCIPLINES)
    if kind == "i":
        return rng.pick(ITEMS)
    if kind == "r":
        return rng.pick(ROLES)
    if kind == "a":
        return rng.pick(AREAS)
    if rng.chance(params.greeting_rate):
        return rng.pick(GREETINGS)
    return ""


def _draw_rest(
    rng: Rng,
    params: GenParams,
    names: list[str],
    has_nesc: bool,
) -> dict[str, NegSpec | str]:
    found: dict[str, NegSpec | str] = {}
    for name in names:
        kind = name[0]
        if name in found or kind not in ("x", "k", "p", "d", "i", "r", "a", "g"):
            continue
        if kind == "x":
            found[name] = negatives.make_negative(
                rng, rng.pick(negatives.GENERAL_KINDS)
            )
        elif kind == "k":
            pool = ("spec_section",) if has_nesc else negatives.CLAUSE_KINDS
            found[name] = negatives.make_negative(rng, rng.pick(pool))
        else:
            found[name] = _text_value(rng, params, kind)
    return found


def _value_key(
    drawn: dict[str, CiteSpec | ListSpec], rest: dict[str, NegSpec | str], name: str
) -> str:
    if name in drawn:
        spec = drawn[name]
        if isinstance(spec, ListSpec):
            return "|".join(i.rendered.designation.key() for i in spec.items)
        return spec.rendered.designation.key()
    other = rest[name]
    return other.text if isinstance(other, NegSpec) else other


def _has_nesc(drawn: dict[str, CiteSpec | ListSpec]) -> bool:
    for spec in drawn.values():
        if isinstance(spec, CiteSpec) and spec.rendered.designation.body == "NESC":
            return True
    return False


def _build(
    rng: Rng, params: GenParams, template: Template
) -> tuple[list[Builder], tuple[str, ...]]:
    """Return the built columns and the subject and question slot values.

    The values are taken before noise.
    """
    texts = [template.subject, template.question, ""]
    if template.response and rng.chance(params.response_rate):
        texts[2] = template.response
    parts = [split_slots(text) for text in texts]
    names = [name for column in parts for kind, name in column if kind == "slot"]
    drawn = _draw_cites(rng, params, names)
    rest = _draw_rest(rng, params, names, _has_nesc(drawn))
    values = tuple(
        _value_key(drawn, rest, name)
        for name in dict.fromkeys(
            n for column in parts[:2] for k, n in column if k == "slot"
        )
    )
    builders: list[Builder] = []
    for column, pieces in zip(COLUMNS, parts, strict=True):
        builder = Builder(column)
        for kind, value in pieces:
            if kind == "text":
                builder.add_text(value)
                continue
            if value in drawn:
                spec = drawn[value]
                if isinstance(spec, ListSpec):
                    builder.add_list(spec)
                else:
                    builder.add_cite(spec)
                continue
            other = rest[value]
            if isinstance(other, NegSpec):
                builder.add_negative(other)
            else:
                builder.add_text(other)
        builders.append(builder)
    return builders, values


def _pick_template(rng: Rng, params: GenParams) -> Template:
    issue = rng.pick(ISSUE_TYPES)
    pool = [
        t for t in TEMPLATES if t.issue_type == issue and t.family in params.families
    ]
    return rng.pick(pool)


def generate(seed: int, n: int, params: GenParams | None = None) -> Corpus:
    """Write n labeled RFIs for a seed.

    No (template, slot values) pair repeats. The pair is the template id and
    the values of the slots in the subject and question before noise (the
    designation key for a citation), so a noise variant, a clause style or a
    response does not make a repeat look new. A repeat is drawn again, and
    RuntimeError is raised when 500 draws in a row repeat.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative int")
    params = params or GenParams()
    rng = Rng(seed)
    seen: set[tuple[str, tuple[str, ...]]] = set()
    width = max(4, len(str(n)))
    made: list[GeneratedRfi] = []
    for index in range(1, n + 1):
        for _ in range(MAX_TRIES):
            template = _pick_template(rng, params)
            builders, values = _build(rng, params, template)
            key = (template.template_id, values)
            if key not in seen:
                seen.add(key)
                break
        else:
            raise RuntimeError("could not find an unused template and slot pair")
        subject, question, response = (b.text for b in builders)
        made.append(
            GeneratedRfi(
                rfi=Rfi(f"R{index:0{width}d}", subject, question, response),
                template_id=template.template_id,
                family=template.family,
                citations=tuple(c for b in builders for c in b.citations),
                negatives=tuple(x for b in builders for x in b.negatives),
            )
        )
    return Corpus(seed, n, params, tuple(made))
