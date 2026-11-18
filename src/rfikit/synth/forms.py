from dataclasses import dataclass, replace

from rfikit.synth.catalog import OutOfScope
from rfikit.types import Designation


@dataclass(frozen=True)
class Rendered:
    text: str
    designation: Designation
    number_at: int
    word: tuple[int, int]
    catalog: str
    scope: str = "in"
    inferred: bool = False


@dataclass(frozen=True)
class Clause:
    text: str
    key: str


NESC_FORMS = (
    ("NESC", False, 4),
    ("IEEE C2", False, 1),
    ("ANSI C2", False, 1),
    ("{y} NESC", True, 3),
    ("NESC-{y}", True, 2),
    ("NESC {y}", True, 2),
    ("IEEE C2-{y}", True, 2),
    ("ANSI C2-{y}", True, 1),
    ("ANSI/IEEE C2-{y}", True, 1),
)


def with_clause(rendered: Rendered, clause: Clause | None) -> Rendered:
    if clause is None:
        return rendered
    designation = replace(rendered.designation, clause=clause.key)
    return replace(rendered, designation=designation)


def _year_text(body: str, year: str, suffix: str) -> str:
    if not year:
        return ""
    sep = ":" if body == "IEC" else "-"
    return sep + year + suffix


def render_entry(
    body: str,
    number: str,
    part: str,
    doc_type: str,
    year: str,
    suffix: str,
    token: str,
    catalog: str,
) -> Rendered:
    word_at = token.index(body)
    head = token + (" " + doc_type if doc_type else "")
    number_text = number + ("-" + part if part else "")
    co_bodies = tuple(p for p in token.replace(" Std", "").split("/") if p != body)
    designation = Designation(
        body=body,
        number=number,
        co_bodies=co_bodies,
        doc_type=doc_type,
        part=part,
        year=year,
        suffix=suffix,
    )
    return Rendered(
        text=head + " " + number_text + _year_text(body, year, suffix),
        designation=designation,
        number_at=len(head) + 1,
        word=(word_at, word_at + len(body)),
        catalog=catalog,
    )


def render_nesc(form: str, year: str, catalog: str) -> Rendered:
    text = form.replace("{y}", year)
    primary = "NESC"
    for name in ("NESC", "IEEE", "ANSI"):
        if name in text:
            primary = name
            break
    at = text.index(primary)
    co_bodies: tuple[str, ...] = ()
    if "C2" in text:
        co_bodies = tuple(text.split(" ")[0].split("/"))
    return Rendered(
        text=text,
        designation=Designation(
            body="NESC", number="C2", co_bodies=co_bodies, year=year
        ),
        number_at=-1,
        word=(at, at + len(primary)),
        catalog=catalog,
    )


def render_bare_nesc(clause: Clause, catalog: str) -> Rendered:
    return Rendered(
        text=clause.text,
        designation=Designation(body="NESC", number="C2", clause=clause.key),
        number_at=-1,
        word=(-1, -1),
        catalog=catalog,
        inferred=True,
    )


def render_out_of_scope(item: OutOfScope, dash_sep: bool) -> Rendered:
    token = ("ANSI/" if item.joint else "") + item.body
    sep = "-" if dash_sep else " "
    return Rendered(
        text=token + sep + item.number,
        designation=Designation(body=item.body, number=item.number),
        number_at=len(token) + 1,
        word=(-1, -1),
        catalog="real",
        scope="out",
    )


def render_list_item(
    body: str, number: str, part: str, year: str, suffix: str
) -> Rendered:
    number_text = number + ("-" + part if part else "")
    designation = Designation(
        body=body, number=number, part=part, year=year, suffix=suffix
    )
    return Rendered(
        text=number_text + _year_text(body, year, suffix),
        designation=designation,
        number_at=0,
        word=(-1, -1),
        catalog="real",
        inferred=True,
    )
