import time

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from rfikit.cite import extract

FILLER = (
    "the transformer pump please advise conduit panel yard cable plan shows "
    "approved vendor field note drawing check load unit bay review ground "
    "then also but because each every which will would"
).split()
DASHES = ["-"] + [
    chr(code) for code in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2212)
]
GAPS = [" ", "  ", "\n", "\r\n  ", chr(0xA0), chr(0x202F)]
BREAKS = ["\n", "\r\n", "\n  "]
FRAGMENTS = [
    "IEEE",
    "IEEE Std",
    "ANSI/IEEE",
    "IEC",
    "IEC TS",
    "ANSI",
    "ASTM",
    "NEMA",
    "NESC",
    "2017",
    "C2",
    "C57.12.00",
    "80",
    "1547.1",
    "60076-1",
    "A123/A123M",
    "TC 2",
    "-2015",
    ":2011",
    "-17",
    "Rule 232B1",
    "Table 232-1",
    "Section 5.3",
    "of the",
    "in",
    "and",
    ",",
    ".",
    "-",
    "\n",
    " ",
    "kVA",
    chr(0x2013),
    chr(0x1D400),
    "x",
]


@st.composite
def fragment_text(draw: st.DrawFn) -> str:
    parts = draw(st.lists(st.sampled_from(FRAGMENTS), max_size=30))
    seps = draw(
        st.lists(st.sampled_from(["", " ", "  ", "\n"]), min_size=30, max_size=30)
    )
    return "".join(p + s for p, s in zip(parts, seps, strict=False))


def clean_filler(words: list[str]) -> str:
    return " ".join(words)


filler = st.lists(st.sampled_from(FILLER), max_size=8).map(clean_filler)


@given(fragment_text())
def test_text_matches_span_and_clause_offsets_lie_inside(text: str) -> None:
    for cite in extract(text):
        assert text[cite.start : cite.end] == cite.text
        assert 0 <= cite.start < cite.end <= len(text)
        if cite.clause_start is not None and cite.clause_end is not None:
            assert 0 <= cite.clause_start < cite.clause_end <= len(text)


@given(st.text(max_size=200))
def test_any_text_keeps_offsets_inside(text: str) -> None:
    for cite in extract(text):
        assert text[cite.start : cite.end] == cite.text


@given(fragment_text())
def test_spans_are_sorted_and_never_overlap(text: str) -> None:
    cites = extract(text)
    for first, second in zip(cites, cites[1:], strict=False):
        assert first.end <= second.start


def _ieee(draw: st.DrawFn) -> tuple[str, str]:
    year = draw(st.sampled_from(["", "-2015", "-1999", "-2021"]))
    if draw(st.booleans()):
        head = draw(st.integers(2, 99))
        tail = draw(st.lists(st.integers(1, 99), max_size=2))
        number = "C" + str(head) + "".join("." + str(t) for t in tail)
        if head == 2 and not tail:
            number = "C3"
    else:
        number = str(draw(st.integers(10, 4999)))
        amd = draw(st.sampled_from(["", "", "a"]))
        number += amd
    token = draw(st.sampled_from(["IEEE", "IEEE Std", "ANSI/IEEE", "IEEE/IEC"]))
    return token + " " + number + year, "IEEE " + number + year


def _iec(draw: st.DrawFn) -> tuple[str, str]:
    number = str(draw(st.integers(60000, 63999)))
    parts = draw(st.lists(st.integers(1, 99), max_size=3))
    part = "-".join(str(p) for p in parts)
    year = draw(st.sampled_from(["", ":2011", ":1999"]))
    kind = draw(st.sampled_from(["", "", "TS ", "TR "]))
    token = "IEC/IEEE" if not kind and draw(st.booleans()) else "IEC"
    body = number + ("-" + part if part else "")
    return token + " " + kind + body + year, "IEC " + kind + body + year


def _ansi(draw: st.DrawFn) -> tuple[str, str]:
    letter = draw(st.sampled_from(["A", "C", "H", "O", "S", "Z"]))
    number = (
        letter + str(draw(st.integers(10, 999))) + "." + str(draw(st.integers(1, 9)))
    )
    year = draw(st.sampled_from(["", "-2016", "-2020"]))
    return "ANSI " + number + year, "ANSI " + number + year


def _astm(draw: st.DrawFn) -> tuple[str, str]:
    letter = draw(st.sampled_from("ABCDEFG"))
    number = letter + str(draw(st.integers(10, 9999)))
    if draw(st.booleans()):
        number += "/" + number + "M"
    year = draw(st.sampled_from(["", "-17", "-09", "-16a", "-12e1", "-14(2021)"]))
    return "ASTM " + number + year, "ASTM " + number + year


def _nema(draw: st.DrawFn) -> tuple[str, str]:
    if draw(st.booleans()):
        number = str(draw(st.integers(200, 999)))
    else:
        number = draw(st.sampled_from(["TC", "MG", "WD", "ICS", "FB", "VE"]))
        number += " " + str(draw(st.integers(1, 99)))
    year = draw(st.sampled_from(["", "-2020", "-1993"]))
    token = draw(st.sampled_from(["NEMA", "ANSI/NEMA"]))
    return token + " " + number + year, "NEMA " + number + year


def _nesc(draw: st.DrawFn) -> tuple[str, str]:
    year = draw(st.sampled_from(["2002", "2012", "2017", "2023"]))
    form = draw(st.sampled_from(["{y} NESC", "NESC-{y}", "NESC {y}", "IEEE C2-{y}"]))
    return form.replace("{y}", year), "NESC " + year


@st.composite
def designation(draw: st.DrawFn) -> tuple[str, str]:
    maker = draw(st.sampled_from([_ieee, _iec, _ansi, _astm, _nema, _nesc]))
    return maker(draw)


def render(text: str, gap: str, dash: str, case: str, brk: str) -> str:
    at = text.index(" ") if " " in text else len(text)
    head, tail = text[:at], text[at:]
    if tail and "-" in tail and dash != "-":
        tail = tail.replace("-", dash)
    if tail and gap != " ":
        glue_ok = tail[1:2].isdigit()
        if gap == "" and not glue_ok:
            gap = " "
        tail = gap + tail[1:]
    if brk and tail:
        marks = [
            i for i, ch in enumerate(tail) if ch in ".-" + dash and i < len(tail) - 1
        ]
        if marks:
            i = marks[0]
            tail = tail[: i + 1] + brk + tail[i + 1 :]
    out = head + tail
    if case == "lower":
        out = out.lower()
    elif case == "title":
        out = head.title() + tail
    return out


@given(
    designation(),
    filler,
    filler,
    st.sampled_from(GAPS + [""]),
    st.sampled_from(DASHES),
    st.sampled_from(["", "lower", "title"]),
    st.sampled_from([""] + BREAKS),
)
@example(("IEEE C2.1", "IEEE C2.1"), "x", "y", " ", "-", "", "\n")
@example(("IEEE C2.1", "IEEE C2.1"), "x", "y", " ", "-", "", "\r\n  ")
@settings(max_examples=400)
def test_rendered_designation_gives_the_same_key(
    item: tuple[str, str],
    before: str,
    after: str,
    gap: str,
    dash: str,
    case: str,
    brk: str,
) -> None:
    canonical, key = item
    if key.startswith("NESC") and gap in ("", "\n", "\r\n  "):
        gap = " "
    if key.startswith("NESC"):
        brk = ""
    text = before + " " + render(canonical, gap, dash, case, brk) + " " + after
    found = extract(text)
    assert [c.designation.key() for c in found] == [key]


@given(fragment_text(), filler, filler)
@settings(max_examples=300)
def test_unrelated_text_shifts_offsets_exactly(
    core: str, before: str, after: str
) -> None:
    prefix = before + " "
    suffix = " " + after
    base = extract(core)
    moved = extract(prefix + core + suffix)
    shift = len(prefix)

    def shape(c_start: int | None, offset: int) -> int | None:
        return None if c_start is None else c_start + offset

    assert [
        (
            c.start + shift,
            c.end + shift,
            c.designation,
            shape(c.clause_start, shift),
            shape(c.clause_end, shift),
            c.inferred,
        )
        for c in base
    ] == [
        (c.start, c.end, c.designation, c.clause_start, c.clause_end, c.inferred)
        for c in moved
    ]


PATTERNS = [
    "IEEE 1.1.1.1.1.1.1.1. ",
    "IEC 60076-1-1-1-1-1-1 ",
    "00000000000000000000 ",
    "ASTM A1/A1M-1a(2021) ",
    "ANSI/IEEE/IEC/NEMA/NESC/ ",
    "Rule 1.1.1-1.1-1 Table 1-1-1 ",
    "NESC 2017 2017 NESC 2017 ",
    "IEEE 80, 81, 82, C37.2, C37.3, ",
]


def _seconds(text: str) -> float:
    began = time.process_time()
    extract(text)
    return time.process_time() - began


def _ratio(pattern: str) -> float:
    small = (pattern * (1_000_000 // len(pattern) + 1))[:1_000_000]
    large = (pattern * (2_000_000 // len(pattern) + 1))[:2_000_000]
    return _seconds(large) / _seconds(small)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_hostile_input_runs_in_linear_time(pattern: str) -> None:
    best = _ratio(pattern)
    for _ in range(3):
        if best < 3:
            break
        best = min(best, _ratio(pattern))
    assert best < 3
