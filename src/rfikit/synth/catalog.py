from dataclasses import dataclass

from rfikit.synth.rng import Rng


@dataclass(frozen=True)
class Edition:
    year: str
    suffix: str = ""


@dataclass(frozen=True)
class Entry:
    body: str
    number: str
    editions: tuple[Edition, ...]
    part: str = ""
    doc_type: str = ""
    joint: str = ""
    real: bool = True


@dataclass(frozen=True)
class OutOfScope:
    body: str
    number: str
    joint: bool = False


def _e(*years: str) -> tuple[Edition, ...]:
    return tuple(Edition(y) for y in years)


def _a(*items: tuple[str, str]) -> tuple[Edition, ...]:
    return tuple(Edition(y, s) for y, s in items)


IEEE = (
    Entry("IEEE", "C57.12.00", _e("2010", "2015", "2021"), joint="ANSI/IEEE"),
    Entry("IEEE", "C57.12.90", _e("2010", "2015", "2021"), joint="ANSI/IEEE"),
    Entry("IEEE", "C57.91", _e("2011"), joint="ANSI/IEEE"),
    Entry("IEEE", "C57.13", _e("2016"), joint="ANSI/IEEE"),
    Entry("IEEE", "C37.2", _e("2008"), joint="ANSI/IEEE"),
    Entry("IEEE", "C37.04", _e("2018"), joint="ANSI/IEEE"),
    Entry("IEEE", "C37.20.2", _e("1999")),
    Entry("IEEE", "C37.90", _e("2005"), joint="ANSI/IEEE"),
    Entry("IEEE", "C62.11", _e("2020")),
    Entry("IEEE", "80", _e("2000", "2013")),
    Entry("IEEE", "81", _e("2012")),
    Entry("IEEE", "142", _e("2007")),
    Entry("IEEE", "242", _e("2001")),
    Entry("IEEE", "485", _e("2010")),
    Entry("IEEE", "519", _e("2014", "2022")),
    Entry("IEEE", "693", _e("2018")),
    Entry("IEEE", "738", _e("2012")),
    Entry("IEEE", "979", _e("2012")),
    Entry("IEEE", "1100", _e("2005")),
    Entry("IEEE", "1547", _e("2003", "2018")),
    Entry("IEEE", "1547.1", _e("2020")),
    Entry("IEEE", "1547a", _e("2020")),
    Entry("IEEE", "1584", _e("2018")),
    Entry("IEEE", "1588", _e("2019"), joint="IEEE/IEC"),
)

IEC = (
    Entry("IEC", "60076", _e("2011"), part="1"),
    Entry("IEC", "60076", _e("2011"), part="2"),
    Entry("IEC", "60076", _e("2018"), part="3"),
    Entry("IEC", "60076", _e("2006"), part="5"),
    Entry("IEC", "60076", _e("2018"), part="11"),
    Entry("IEC", "60255", _e("2018"), part="118-1", joint="IEC/IEEE"),
    Entry("IEC", "60364", _e("2011"), part="5-54"),
    Entry("IEC", "60529", _e("1989")),
    Entry("IEC", "60909", _e("2016"), part="0"),
    Entry("IEC", "60947", _e("2016"), part="2"),
    Entry("IEC", "61000", _e("2015"), part="4-30"),
    Entry("IEC", "61439", _e("2020"), part="1"),
    Entry("IEC", "61850", _e(), part=""),
    Entry("IEC", "61850", _e("2009", "2014"), part="6"),
    Entry("IEC", "61850", _e("2010"), part="7-4"),
    Entry("IEC", "61850", _a(("2011", ""), ("2011", "+AMD1:2020")), part="8-1"),
    Entry("IEC", "61850", _e("2011"), part="9-2"),
    Entry("IEC", "61850", _e("2013"), part="1", doc_type="TR"),
    Entry("IEC", "61850", _e("2016"), part="80-1", doc_type="TS"),
    Entry("IEC", "62351", _e("2014"), part="3", doc_type="TS"),
    Entry("IEC", "62271", _e("2017"), part="1"),
    Entry("IEC", "62271", _e("2021"), part="100"),
    Entry("IEC", "62271", _e("2021"), part="200"),
    Entry("IEC", "61869", _e("2012"), part="2"),
)

ANSI = (
    Entry("ANSI", "C84.1", _e("2016", "2020")),
    Entry("ANSI", "C12.1", _e("2014")),
    Entry("ANSI", "C12.20", _e("2015")),
    Entry("ANSI", "C63.4", _e("2014")),
    Entry("ANSI", "C80.1", _e("2020")),
    Entry("ANSI", "C119.4", _e("2016")),
    Entry("ANSI", "Z535.4", _e("2011")),
    Entry("ANSI", "Z87.1", _e("2020")),
    Entry("ANSI", "O5.1", _e("2017")),
    Entry("ANSI", "A14.3", _e("2008")),
)

ASTM = (
    Entry("ASTM", "A123/A123M", _e("12", "17", "22")),
    Entry("ASTM", "A153/A153M", _a(("16", ""), ("16", "a"), ("23", ""))),
    Entry("ASTM", "A36/A36M", _e("14", "19")),
    Entry("ASTM", "A572/A572M", _e("21")),
    Entry("ASTM", "A786/A786M", _e("09")),
    Entry("ASTM", "B117", _e("19")),
    Entry("ASTM", "B187/B187M", _e("22")),
    Entry("ASTM", "C33/C33M", _e("18")),
    Entry("ASTM", "C94/C94M", _e("22")),
    Entry("ASTM", "C150/C150M", _e("22")),
    Entry("ASTM", "D149", _e("20")),
    Entry("ASTM", "D257", _a(("14", "(2021)"))),
    Entry("ASTM", "D698", _a(("12", "(2021)"))),
    Entry("ASTM", "D1248", _e("16")),
    Entry("ASTM", "D1557", _a(("12", "e1"), ("12", "(2021)"))),
    Entry("ASTM", "D2240", _a(("15", "(2021)"))),
    Entry("ASTM", "D2487", _a(("17", "e1"))),
    Entry("ASTM", "D4318", _a(("17", "e1"))),
    Entry("ASTM", "E8/E8M", _e("21")),
    Entry("ASTM", "F436/F436M", _e("19")),
    Entry("ASTM", "F1554", _e("20")),
    Entry("ASTM", "G154", _e("16")),
)

NEMA = (
    Entry("NEMA", "TC 2", _e("2013", "2020")),
    Entry("NEMA", "TC 3", _e("2021")),
    Entry("NEMA", "MG 1", _e("2016", "2021"), joint="ANSI/NEMA"),
    Entry("NEMA", "WD 6", _e("2016", "2021"), joint="ANSI/NEMA"),
    Entry("NEMA", "250", _e("2018", "2020"), joint="ANSI/NEMA"),
    Entry("NEMA", "ICS 1", _e("2022")),
    Entry("NEMA", "ICS 2", _e("2000")),
    Entry("NEMA", "ICS 6", _e("1993"), joint="ANSI/NEMA"),
    Entry("NEMA", "FB 1", _e("2014")),
    Entry("NEMA", "VE 1", _e("2017")),
    Entry("NEMA", "PB 1", _e("2011")),
    Entry("NEMA", "KS 1", _e("2013")),
    Entry("NEMA", "WC 70", _e("2009")),
)

REAL = {"IEEE": IEEE, "IEC": IEC, "ANSI": ANSI, "ASTM": ASTM, "NEMA": NEMA}

NESC_EDITIONS = ("2002", "2007", "2012", "2017", "2023")
NESC_RULES = (
    "232",
    "232B1",
    "232B2",
    "234B",
    "234C",
    "235C",
    "238",
    "239",
    "250B",
    "250C",
    "410A",
    "420",
)
NESC_TABLES = ("232-1", "234-1", "235-1", "235-5", "250-1", "253-1")
NESC_SECTIONS = ("2", "9", "23")

OUT_OF_SCOPE = (
    OutOfScope("NFPA", "70", True),
    OutOfScope("NFPA", "70E", True),
    OutOfScope("NFPA", "72"),
    OutOfScope("UL", "1741", True),
    OutOfScope("UL", "489"),
    OutOfScope("UL", "891"),
    OutOfScope("ASME", "B31.1", True),
    OutOfScope("ASME", "B16.5", True),
    OutOfScope("ASME", "B18.2.6"),
    OutOfScope("ISA", "84.00.01", True),
    OutOfScope("ISA", "12.12.01", True),
    OutOfScope("TIA", "568-D", True),
    OutOfScope("CSA", "C22.2 No. 94"),
    OutOfScope("CSA", "Z462"),
    OutOfScope("EN", "50160"),
    OutOfScope("EN", "61850-8-1"),
)

_REAL_IDS = {
    (e.body, e.doc_type, e.number, e.part) for group in REAL.values() for e in group
}
_NEMA_LETTERS = ("TC", "MG", "WD", "ICS", "FB", "VE", "PB", "KS", "AB", "LD")
_ANSI_LETTERS = ("A", "C", "H", "O", "S", "Z")
_ASTM_LETTERS = ("A", "B", "C", "D", "E", "F", "G")


def _invent_ieee(rng: Rng) -> Entry:
    shape = rng.below(3)
    if shape == 0:
        number = str(rng.between(100, 4999))
    elif shape == 1:
        number = f"{rng.between(100, 3999)}.{rng.between(1, 9)}"
    else:
        number = f"C{rng.between(2, 99)}.{rng.between(1, 99)}"
        if rng.chance(0.5):
            number += f".{rng.between(0, 99):02d}"
    edition = Edition(str(rng.between(1990, 2023)))
    return Entry("IEEE", number, (edition,), real=False)


def _invent_iec(rng: Rng) -> Entry:
    number = str(rng.between(60000, 63999))
    part = ""
    if rng.chance(0.7):
        part = str(rng.between(1, 99))
        if rng.chance(0.4):
            part += f"-{rng.between(1, 9)}"
    doc_type = rng.pick(("", "", "", "TS", "TR"))
    edition = Edition(str(rng.between(1995, 2023)))
    return Entry("IEC", number, (edition,), part=part, doc_type=doc_type, real=False)


def _invent_ansi(rng: Rng) -> Entry:
    number = f"{rng.pick(_ANSI_LETTERS)}{rng.between(10, 999)}.{rng.between(1, 9)}"
    edition = Edition(str(rng.between(1990, 2023)))
    return Entry("ANSI", number, (edition,), real=False)


def _invent_astm(rng: Rng) -> Entry:
    letter = rng.pick(_ASTM_LETTERS)
    number = f"{letter}{rng.between(10, 9999)}"
    if letter in ("A", "B", "C", "E", "F") and rng.chance(0.4):
        number += f"/{number}M"
    suffix = rng.pick(("", "", "", "a", "b", "e1", "(2021)"))
    edition = Edition(f"{rng.between(0, 23):02d}", suffix)
    return Entry("ASTM", number, (edition,), real=False)


def _invent_nema(rng: Rng) -> Entry:
    if rng.chance(0.25):
        number = str(rng.between(200, 999))
    else:
        number = f"{rng.pick(_NEMA_LETTERS)} {rng.between(1, 99)}"
    edition = Edition(str(rng.between(1990, 2023)))
    return Entry("NEMA", number, (edition,), real=False)


_INVENTORS = {
    "IEEE": _invent_ieee,
    "IEC": _invent_iec,
    "ANSI": _invent_ansi,
    "ASTM": _invent_astm,
    "NEMA": _invent_nema,
}


def invent(rng: Rng, body: str) -> Entry:
    while True:
        entry = _INVENTORS[body](rng)
        if (entry.body, entry.doc_type, entry.number, entry.part) not in _REAL_IDS:
            return entry


def nesc_clause(rng: Rng, kind: str, real: bool) -> str:
    if real:
        if kind == "rule":
            return rng.pick(NESC_RULES)
        if kind == "table":
            return rng.pick(NESC_TABLES)
        return rng.pick(NESC_SECTIONS)
    while True:
        if kind == "rule":
            letter = rng.pick(("A", "B", "C", "D", "E"))
            tail = rng.pick(("", "", str(rng.between(1, 4)), "1a"))
            value = f"{rng.between(100, 999)}{letter}{tail}"
            if value not in NESC_RULES:
                return value
        elif kind == "table":
            value = f"{rng.between(100, 999)}-{rng.between(1, 9)}"
            if value not in NESC_TABLES:
                return value
        else:
            value = str(rng.between(30, 99))
            return value
