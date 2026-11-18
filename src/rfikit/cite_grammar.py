import re
from dataclasses import dataclass
from re import Match, Pattern

from rfikit.textnorm import word_at
from rfikit.types import Designation

WINDOW = 96
SIX = ("IEEE", "NESC", "IEC", "ANSI", "ASTM", "NEMA")
OUT = ("NFPA", "UL", "ASME", "ISA", "TIA", "CSA", "EN")

FLAGS = re.IGNORECASE | re.ASCII
GAP = r"[ \t\r\n]{0,6}"
BRK = r"(?:\r?\n[ \t]{0,4})?"
YEAR = r"(?:19|20)\d\d"
LEVELS = rf"(?:\.{BRK}\d{{1,3}})"
COMMON = frozenset(
    "a i an as at be by do go if in is it me my no of on or so to up us we and are "
    "for not per the was you can but has had".split()
)
UNITS = frozenset(
    "kva kv mva mw kw hz ft mm cm amp amps ohm ohms kvar mvar psi awg kcmil mcm".split()
)
SHORT_UNIT = re.compile(r"[ \t]*[AV](?![A-Za-z])")


def _rx(pattern: str) -> Pattern[str]:
    return re.compile(pattern, FLAGS)


_ELEM = "(?:" + "|".join(SIX + OUT) + ")(?![A-Za-z])"
_SIXALT = "(?:" + "|".join(SIX) + ")(?![A-Za-z])"
ANCHOR = _rx(rf"(?<![A-Za-z0-9])(?:{_ELEM}/){{0,3}}{_SIXALT}(?:/{_ELEM}){{0,3}}")
STD = _rx(r"[ \t\r\n]{1,6}Std(?![A-Za-z])\.?")
C2 = _rx(rf"{GAP}C2(?!\d)(?!\.\d)(?:-{BRK}(?P<y>{YEAR})(?!\d))?(?![A-Za-z0-9])")
NESC_YEAR = _rx(rf"(?:-{BRK}|[ \t]{{1,3}})(?P<y>{YEAR})(?!\d)")
YEAR_BEFORE = _rx(rf"(?<![A-Za-z0-9.\-:/])(?P<y>{YEAR})[ \t]{{1,3}}\Z")
SEP = _rx(
    r"(?:[ \t]{0,2}[,;][ \t]{0,3}(?:(?:and|or)[ \t]{1,3})?"
    r"|[ \t]{1,3}(?:and|or)[ \t]{1,3})"
)


def _grammar(prefix: str) -> dict[str, Pattern[str]]:
    tail = rf"(?:-{BRK}(?P<y>{YEAR})(?!\d))?(?![A-Za-z0-9])"
    return {
        "IEEE": _rx(
            prefix
            + rf"(?:(?P<let>c)(?P<sp>[ \t]{{0,2}})(?P<num>\d{{1,3}}{LEVELS}{{0,3}})"
            + rf"|(?P<plain>\d{{2,4}}{LEVELS}{{0,3}}))(?P<amd>[a-z])?"
            + tail
        ),
        "IEC": _rx(
            prefix
            + r"(?:(?P<dt>TS|TR)(?![A-Za-z])"
            + GAP
            + r")?(?P<num>\d{5})"
            + rf"(?:-{BRK}(?P<part>\d{{1,3}}(?:-{BRK}\d{{1,3}}){{0,3}}))?"
            + rf"(?::(?P<y>{YEAR})(?!\d)(?P<amd>\+AMD\d{{1,2}}:{YEAR})?)?"
            + r"(?![A-Za-z0-9])"
        ),
        "ANSI": _rx(
            prefix
            + rf"(?P<let>[a-z])(?P<sp>[ \t]{{0,2}})(?P<num>\d{{1,3}}{LEVELS}{{0,2}})"
            + tail
        ),
        "ASTM": _rx(
            prefix
            + r"(?P<let>[a-g])(?P<sp>[ \t]{0,2})(?P<d>\d{1,4})"
            + r"(?:/(?P<tl>[a-g])?(?P<td>\d{1,4})(?P<tm>m)?)?"
            + rf"(?:-{BRK}(?P<y>{YEAR}|\d\d)(?!\d)(?P<rev>[a-df-z])?"
            + rf"(?P<eps>e\d)?(?P<rap>\({YEAR}\))?)?(?![A-Za-z0-9])"
        ),
        "NEMA": _rx(
            prefix
            + r"(?:(?P<let>[a-z]{1,3})(?P<sp>[ \t]{0,2})(?P<d>\d{1,3})|(?P<d3>\d{3}))"
            + tail
        ),
    }


HEAD = _grammar(GAP)
ITEM = _grammar("")


@dataclass(frozen=True)
class Read:
    start: int
    end: int
    designation: Designation


def _strip(text: str) -> str:
    return re.sub(r"[ \t\r\n]", "", text)


def _letters_ok(letters: str, space: str, lower_body: bool) -> bool:
    if letters.isupper() or space == "":
        return True
    return lower_body and letters.lower() not in COMMON


def _group(m: Match[str], name: str) -> str:
    return m.group(name) or ""


def _build(
    body: str, m: Match[str], co: tuple[str, ...], lower: bool
) -> Designation | None:
    year = _group(m, "y")
    if body == "IEEE":
        return _ieee(m, co, lower, year)
    if body == "IEC":
        part = _strip(_group(m, "part"))
        suffix = _group(m, "amd").upper()
        number = m.group("num")
        doc = _group(m, "dt").upper()
        return Designation("IEC", number, co, doc, part, year, suffix)
    letters = _group(m, "let")
    if body != "NEMA" or letters:
        if not _letters_ok(letters, _group(m, "sp"), lower):
            return None
    if body == "ANSI":
        number = letters.upper() + _strip(m.group("num"))
        return Designation("ANSI", number, co, year=year)
    if body == "ASTM":
        return _astm(m, co, year)
    number = _group(m, "d3")
    if letters:
        number = letters.upper() + " " + m.group("d")
    return Designation("NEMA", number, co, year=year)


def _ieee(
    m: Match[str], co: tuple[str, ...], lower: bool, year: str
) -> Designation | None:
    letters = _group(m, "let")
    if letters and not _letters_ok(letters, _group(m, "sp"), lower):
        return None
    digits = m.group("num") or m.group("plain")
    number = letters.upper() + _strip(digits) + _group(m, "amd").lower()
    return Designation("IEEE", number, co, year=year)


def _astm(m: Match[str], co: tuple[str, ...], year: str) -> Designation:
    number = m.group("let").upper() + m.group("d")
    if m.group("td"):
        twin = (m.group("tl") or m.group("let")).upper() + m.group("td")
        number += "/" + twin + _group(m, "tm").upper()
    suffix = _group(m, "rev").lower() + _group(m, "eps").lower() + _group(m, "rap")
    return Designation("ASTM", number, co, year=year, suffix=suffix)


def _fits(body: str, m: Match[str]) -> bool:
    if body == "IEEE":
        return bool(m.group("let")) or "." in m.group("plain")
    if body in ("ANSI", "ASTM"):
        return _group(m, "sp") == ""
    if body == "NEMA":
        letters = _group(m, "let")
        return bool(letters) and letters.upper() not in OUT
    return True


def read_head(text: str, start: int, end: int, chain: str, floor: int) -> Read | None:
    elems = tuple(chain.upper().split("/"))
    if any(e in OUT for e in elems):
        return None
    limit = min(len(text), end + WINDOW)
    lower = chain.islower()
    pos = end
    std = STD.match(text, pos, limit)
    if std:
        pos = std.end()
    if all(e in ("IEEE", "ANSI") for e in elems):
        c2 = C2.match(text, pos, limit)
        if c2:
            nesc = Designation("NESC", "C2", elems, year=_group(c2, "y"))
            return Read(start, c2.end(), nesc)
    others = [e for e in elems if e != "ANSI"]
    body = others[0] if others else "ANSI"
    co = list(elems)
    co.remove(body)
    if body == "NESC":
        return _nesc(text, start, end, elems, floor)
    m = HEAD[body].match(text, pos, limit)
    if m is None:
        return None
    design = _build(body, m, tuple(co), lower)
    if design is None:
        return None
    return Read(start, m.end(), design)


def _nesc(text: str, start: int, end: int, elems: tuple[str, ...], floor: int) -> Read:
    co = tuple(e for e in elems if e != "NESC")
    after = NESC_YEAR.match(text, end, min(len(text), end + WINDOW))
    if after:
        return Read(
            start, after.end(), Designation("NESC", "C2", co, year=after.group("y"))
        )
    lo = max(floor, start - 8)
    before = YEAR_BEFORE.search(text, lo, start)
    if before and not co:
        design = Designation("NESC", "C2", co, year=before.group("y"))
        return Read(before.start("y"), end, design)
    return Read(start, end, Designation("NESC", "C2", co))


def read_items(text: str, pos: int, body: str, lower: bool) -> list[Read]:
    found: list[Read] = []
    n = len(text)
    while True:
        sep = SEP.match(text, pos, min(n, pos + WINDOW))
        if sep is None:
            return found
        m = ITEM[body].match(text, sep.end(), min(n, sep.end() + WINDOW))
        if m is None or not _fits(body, m):
            return found
        after = word_at(text, m.end())
        if after in UNITS or after == "nesc" or SHORT_UNIT.match(text, m.end()):
            return found
        design = _build(body, m, (), lower)
        if design is None:
            return found
        found.append(Read(m.start(), m.end(), design))
        pos = m.end()
