from hypothesis import given
from hypothesis import strategies as st

from rfikit.textnorm import clean, word_at

DASHES = [
    chr(code) for code in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212)
]
SPACES = [chr(code) for code in (0xA0, 0x2007, 0x202F, 0x2009, 0x3000)]


def test_dashes_become_hyphen() -> None:
    for dash in DASHES:
        assert clean("C57" + dash + "2015") == "C57-2015"


def test_spaces_become_space() -> None:
    for space in SPACES:
        assert clean("IEEE" + space + "80") == "IEEE 80"


def test_plain_text_is_unchanged() -> None:
    text = "IEEE C57.12.00-2015, Rule 232B1\r\n"
    assert clean(text) == text


@given(st.text())
def test_length_is_kept(text: str) -> None:
    assert len(clean(text)) == len(text)


@given(st.text())
def test_clean_is_idempotent(text: str) -> None:
    assert clean(clean(text)) == clean(text)


def test_word_at() -> None:
    assert word_at("a  kVA unit", 1) == "kva"
    assert word_at("a  ", 1) == ""
    assert word_at("abc", 3) == ""
    assert word_at("C57\r\nkVA", 3) == "kva"
    assert word_at("C2\nNESC", 2) == "nesc"
