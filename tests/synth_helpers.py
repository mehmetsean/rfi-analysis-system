import re

from rfikit.evaluate import GoldCitation
from rfikit.synth.model import CitationLabel, GeneratedRfi

DASHES = {chr(code) for code in (0x2010, 0x2011, 0x2012, 0x2212)}
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
NBSP = chr(0xA0)
NNBSP = chr(0x202F)
BOM = chr(0xFEFF)
BODY_WORDS = ("IEEE", "IEC", "ANSI", "ASTM", "NEMA", "NESC")


def column_text(item: GeneratedRfi, column: str) -> str:
    return {
        "subject": item.rfi.subject,
        "question": item.rfi.question,
        "response": item.rfi.response,
    }[column]


def to_gold(rfi_id: str, c: CitationLabel) -> GoldCitation:
    return GoldCitation(
        rfi_id,
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


def cites_nesc(item: GeneratedRfi) -> bool:
    return any(
        c.key.split(" ")[0] == "NESC" and c.scope == "in" for c in item.citations
    )


def explicit_nesc(item: GeneratedRfi) -> bool:
    return any(
        c.key.split(" ")[0] == "NESC"
        and not c.inferred
        and c.noise_class != "misspelled"
        for c in item.citations
    )


def has_break(text: str) -> bool:
    return re.search(r"[\r\n]", text) is not None
