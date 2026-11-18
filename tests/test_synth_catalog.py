import re

from rfikit.synth import catalog
from rfikit.synth.rng import Rng

SHAPES = {
    "IEEE": re.compile(r"(?:C\d{1,3}(?:\.\d{1,3}){1,2}|\d{2,4}(?:\.\d{1,2})?[a-z]?)"),
    "IEC": re.compile(r"\d{5}"),
    "ANSI": re.compile(r"[A-Z]\d{1,3}(?:\.\d{1,2})?"),
    "ASTM": re.compile(r"[A-G]\d{1,4}(?:/[A-G]\d{1,4}M)?"),
    "NEMA": re.compile(r"(?:[A-Z]{2,3} \d{1,2}|\d{3})"),
}


def test_real_entries_are_unique() -> None:
    seen = set()
    for body, items in catalog.REAL.items():
        for entry in items:
            ident = (body, entry.doc_type, entry.number, entry.part)
            assert ident not in seen, ident
            seen.add(ident)
            assert entry.real
            assert entry.body == body


def test_real_entries_fit_their_grammar() -> None:
    for body, items in catalog.REAL.items():
        for entry in items:
            assert SHAPES[body].fullmatch(entry.number), entry
            for edition in entry.editions:
                if body == "ASTM":
                    assert re.fullmatch(r"\d{2}", edition.year), entry
                    assert re.fullmatch(r"|[a-b]|e1|\(\d{4}\)", edition.suffix)
                elif body == "IEC":
                    assert re.fullmatch(r"\d{4}", edition.year), entry
                    assert re.fullmatch(r"|\+AMD1:\d{4}", edition.suffix)
                else:
                    assert re.fullmatch(r"\d{4}", edition.year), entry
                    assert edition.suffix == ""


def test_every_body_has_enough_real_entries() -> None:
    for items in catalog.REAL.values():
        assert len(items) >= 9


def test_invented_entries_fit_and_are_not_real() -> None:
    rng = Rng(11)
    real = {
        (e.body, e.doc_type, e.number, e.part)
        for items in catalog.REAL.values()
        for e in items
    }
    for body in catalog.REAL:
        for _ in range(300):
            entry = catalog.invent(rng, body)
            assert not entry.real
            assert (entry.body, entry.doc_type, entry.number, entry.part) not in real
            assert SHAPES[body].fullmatch(entry.number), entry
            assert len(entry.editions) == 1


def test_invented_nesc_clauses_are_not_in_the_real_lists() -> None:
    rng = Rng(5)
    for _ in range(200):
        assert catalog.nesc_clause(rng, "rule", False) not in catalog.NESC_RULES
        assert catalog.nesc_clause(rng, "table", False) not in catalog.NESC_TABLES
        assert catalog.nesc_clause(rng, "section", False) not in catalog.NESC_SECTIONS
        assert catalog.nesc_clause(rng, "rule", True) in catalog.NESC_RULES
        assert catalog.nesc_clause(rng, "table", True) in catalog.NESC_TABLES
        assert catalog.nesc_clause(rng, "section", True) in catalog.NESC_SECTIONS


def test_out_of_scope_bodies() -> None:
    bodies = {item.body for item in catalog.OUT_OF_SCOPE}
    assert bodies == {"NFPA", "UL", "ASME", "ISA", "TIA", "CSA", "EN"}
