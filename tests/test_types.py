import pytest
from hypothesis import given
from hypothesis import strategies as st

from rfikit.types import Citation, Designation, Rfi


def test_ieee() -> None:
    d = Designation("IEEE", "C57.12.00", year="2015")
    assert d.key() == "IEEE C57.12.00-2015"
    assert d.base_key() == "IEEE C57.12.00"


def test_nesc_example() -> None:
    d = Designation("NESC", "C2", year="2017", clause="Rule 232B1")
    assert d.key() == "NESC 2017 Rule 232B1"
    assert d.base_key() == "NESC Rule 232B1"


def test_nesc_without_clause() -> None:
    d = Designation("NESC", "C2", year="2017")
    assert d.key() == "NESC 2017"
    assert d.base_key() == "NESC"


def test_iec() -> None:
    d = Designation("IEC", "60076", part="1", year="2011")
    assert d.key() == "IEC 60076-1:2011"
    assert d.base_key() == "IEC 60076-1"


def test_iec_suffix_and_type() -> None:
    d = Designation(
        "IEC", "61850", doc_type="TS", part="7-4", year="2010", suffix="+AMD1:2020"
    )
    assert d.key() == "IEC TS 61850-7-4:2010+AMD1:2020"
    assert d.base_key() == "IEC TS 61850-7-4"


def test_ansi() -> None:
    d = Designation("ANSI", "C84.1", year="2020")
    assert d.key() == "ANSI C84.1-2020"
    assert d.base_key() == "ANSI C84.1"


def test_astm() -> None:
    d = Designation("ASTM", "A123/A123M", year="17")
    assert d.key() == "ASTM A123/A123M-17"
    assert d.base_key() == "ASTM A123/A123M"


def test_astm_suffix() -> None:
    d = Designation("ASTM", "A123/A123M", year="17", suffix="e1")
    assert d.key() == "ASTM A123/A123M-17e1"
    assert d.base_key() == "ASTM A123/A123M"


def test_nema() -> None:
    d = Designation("NEMA", "TC 2", year="2020")
    assert d.key() == "NEMA TC 2-2020"
    assert d.base_key() == "NEMA TC 2"


def test_no_year() -> None:
    assert Designation("IEEE", "80").key() == "IEEE 80"


def test_clause_in_key_not_in_base_key() -> None:
    d = Designation("IEEE", "80", year="2013", clause="Table 5")
    assert d.key() == "IEEE 80-2013 Table 5"
    assert d.base_key() == "IEEE 80"


def test_co_bodies_never_in_keys() -> None:
    a = Designation("IEEE", "C37.2", co_bodies=("ANSI",), year="2008")
    b = Designation("IEEE", "C37.2", year="2008")
    assert a.key() == b.key() == "IEEE C37.2-2008"
    assert a.base_key() == b.base_key()


def test_frozen() -> None:
    d = Designation("IEEE", "80")
    with pytest.raises(AttributeError):
        d.number = "81"  # type: ignore[misc]


def test_rfi_and_citation() -> None:
    assert Rfi("R1", "s", "q").response == ""
    d = Designation("IEEE", "80")
    c = Citation("text", 0, 7, None, None, "IEEE 80", d)
    assert c.inferred is False


number = st.from_regex(r"[A-Z]?[0-9]{1,5}(\.[0-9]{1,2}){0,2}", fullmatch=True)
year = st.one_of(st.just(""), st.from_regex(r"[0-9]{2,4}", fullmatch=True))
suffix = st.one_of(st.just(""), st.just("e1"), st.just("+AMD1:2020"))
body = st.sampled_from(["IEEE", "IEC", "ANSI", "ASTM", "NEMA"])


@given(body, number, year, suffix)
def test_key_stable_and_base_ignores_year_and_suffix(
    b: str, n: str, y: str, s: str
) -> None:
    d = Designation(b, n, year=y, suffix=s)
    same = Designation(b, n, year=y, suffix=s)
    plain = Designation(b, n)
    assert d.key() == same.key()
    assert d.base_key() == plain.base_key()
    assert d.key().startswith(d.base_key())


@given(year, year, suffix)
def test_nesc_base_ignores_year(y1: str, y2: str, s: str) -> None:
    a = Designation("NESC", "C2", year=y1, suffix=s, clause="Rule 232B1")
    b = Designation("NESC", "C2", year=y2, clause="Rule 232B1")
    assert a.base_key() == b.base_key() == "NESC Rule 232B1"
