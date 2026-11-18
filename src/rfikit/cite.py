import re
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, replace

from rfikit.cite_grammar import ANCHOR, read_head, read_items
from rfikit.textnorm import clean
from rfikit.types import Citation, Designation, Rfi

REACH = 40
COLUMNS = ("subject", "question", "response")

_CLAUSE = re.compile(
    r"(?<![A-Za-z0-9])(?P<word>section|sec\.?|clause|paragraph|para|table|figure"
    r"|annex|rule)(?![A-Za-z])[ \t]{0,2}"
    r"(?:(?P<num>\d{1,3}(?:[.\-]\d{1,3}){0,3}(?:[A-Za-z]\d?[a-z]?)?)"
    r"|(?P<let>(?-i:[A-Z])(?:\.\d{1,3}){0,2}))"
    r"(?![A-Za-z0-9])(?![.\-]\d)(?![ \t]\d{2}[ \t]\d{2}(?!\d))",
    re.IGNORECASE | re.ASCII,
)
_CONNECTOR = re.compile(
    r"[ \t\r\n]{1,4}(?:of|in)[ \t\r\n]{1,4}(?:the[ \t\r\n]{1,4})?",
    re.IGNORECASE | re.ASCII,
)
_JOINER = re.compile(r"\b(?:and|or)\b", re.IGNORECASE | re.ASCII)
_NESC_RULE = re.compile(r"\d{3}(?:[A-Za-z]\d?[a-z]?)?\Z")
_NESC_TABLE = re.compile(r"\d{3}-\d{1,2}\Z")
_WORDS = {
    "section": "Clause",
    "sec": "Clause",
    "para": "Clause",
    "paragraph": "Clause",
    "clause": "Clause",
    "table": "Table",
    "figure": "Figure",
    "annex": "Annex",
    "rule": "Rule",
}


@dataclass(frozen=True)
class CiteContext:
    nesc: bool = False


@dataclass(frozen=True)
class _Hit:
    start: int
    end: int
    designation: Designation
    inferred: bool


@dataclass(frozen=True)
class _Clause:
    start: int
    end: int
    word: str
    ident: str


def _scan(norm: str) -> list[_Hit]:
    hits: list[_Hit] = []
    pos = 0
    floor = 0
    while True:
        m = ANCHOR.search(norm, pos)
        if m is None:
            return hits
        read = read_head(norm, m.start(), m.end(), m.group(0), floor)
        if read is None:
            pos = m.end()
            continue
        hits.append(_Hit(read.start, read.end, read.designation, False))
        end = read.end
        if read.designation.body != "NESC":
            body = read.designation.body
            for item in read_items(norm, end, body, m.group(0).islower()):
                hits.append(_Hit(item.start, item.end, item.designation, True))
                end = item.end
        pos = floor = end


def _clauses(norm: str, hits: list[_Hit]) -> list[_Clause]:
    ends = [h.end for h in hits]
    found: list[_Clause] = []
    for m in _CLAUSE.finditer(norm):
        i = bisect_left(ends, m.start() + 1)
        if i < len(hits) and hits[i].start < m.end():
            continue
        word = m.group("word").lower().rstrip(".")
        ident = m.group("num") or m.group("let")
        found.append(_Clause(m.start(), m.end(), word, ident))
    return found


def _clause_key(body: str, clause: _Clause) -> str:
    word = _WORDS[clause.word]
    if body == "NESC" and clause.word in ("section", "sec"):
        word = "Section"
    return word + " " + clause.ident


def _bind(
    norm: str, hits: list[_Hit], clauses: list[_Clause], forward: set[int]
) -> dict[int, int]:
    starts = [h.start for h in hits]
    ends = [h.end for h in hits]
    bound: dict[int, int] = {}
    for ci, clause in enumerate(clauses):
        link = _CONNECTOR.match(norm, clause.end)
        if link:
            forward.add(ci)
            j = bisect_left(starts, link.end())
            if j < len(hits) and starts[j] == link.end() and j not in bound:
                bound[j] = ci
            continue
        k = bisect_right(ends, clause.start) - 1
        if k < 0 or k in bound or clause.start - ends[k] > REACH:
            continue
        if _JOINER.search(norm, ends[k], clause.start) is None:
            bound[k] = ci
    return bound


def _is_nesc_clause(clause: _Clause) -> bool:
    if clause.word == "rule":
        return _NESC_RULE.match(clause.ident) is not None
    if clause.word == "table":
        return _NESC_TABLE.match(clause.ident) is not None
    return False


def _finish(
    text: str, norm: str, column: str, hits: list[_Hit], nesc: bool
) -> list[Citation]:
    clauses = _clauses(norm, hits)
    forward: set[int] = set()
    bound = _bind(norm, hits, clauses, forward)
    taken = set(bound.values()) | forward
    found: list[Citation] = []
    for i, hit in enumerate(hits):
        design = hit.designation
        c_start = c_end = None
        if i in bound:
            clause = clauses[bound[i]]
            design = replace(design, clause=_clause_key(design.body, clause))
            c_start, c_end = clause.start, clause.end
        text_slice = text[hit.start : hit.end]
        found.append(
            Citation(
                column,
                hit.start,
                hit.end,
                text_slice,
                design,
                c_start,
                c_end,
                hit.inferred,
            )
        )
    if nesc:
        for ci, clause in enumerate(clauses):
            if ci in taken or not _is_nesc_clause(clause):
                continue
            design = Designation("NESC", "C2", clause=_clause_key("NESC", clause))
            piece = text[clause.start : clause.end]
            found.append(
                Citation(
                    column,
                    clause.start,
                    clause.end,
                    piece,
                    design,
                    clause.start,
                    clause.end,
                    True,
                )
            )
    found.sort(key=lambda c: c.start)
    return found


def _has_nesc(hits: list[_Hit]) -> bool:
    return any(h.designation.body == "NESC" for h in hits)


def extract(
    text: str, column: str = "text", context: CiteContext | None = None
) -> list[Citation]:
    norm = clean(text)
    hits = _scan(norm)
    nesc = _has_nesc(hits) or (context is not None and context.nesc)
    return _finish(text, norm, column, hits, nesc)


def extract_rfi(rfi: Rfi) -> list[Citation]:
    texts = (rfi.subject, rfi.question, rfi.response)
    norms = [clean(t) for t in texts]
    scans = [_scan(n) for n in norms]
    nesc = any(_has_nesc(h) for h in scans)
    found: list[Citation] = []
    for column, text, norm, hits in zip(COLUMNS, texts, norms, scans, strict=True):
        found.extend(_finish(text, norm, column, hits, nesc))
    return found


def parse_designation(raw: str) -> Designation | None:
    found = extract(raw)
    if len(found) != 1:
        return None
    cite = found[0]
    norm = clean(raw)
    low = len(norm) - len(norm.lstrip())
    high = len(norm.rstrip())
    last = max(cite.end, cite.clause_end or 0)
    if cite.inferred or cite.start != low or last != high:
        return None
    return cite.designation
