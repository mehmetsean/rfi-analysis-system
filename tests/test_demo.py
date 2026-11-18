import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from rfikit import demo
from rfikit.cite import extract

ASTRAL = "\U0001f600"


def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def test_offsets_without_astral_characters_equal_code_points() -> None:
    assert demo.utf16_offsets("abc") == [0, 1, 2, 3]


def test_an_astral_character_counts_two_units() -> None:
    assert demo.utf16_offsets(f"a{ASTRAL}b") == [0, 1, 3, 4]


def test_empty_text_has_one_offset() -> None:
    assert demo.utf16_offsets("") == [0]


@given(st.text(max_size=60))
def test_offsets_match_the_utf16_length_of_every_prefix(text: str) -> None:
    got = demo.utf16_offsets(text)
    assert len(got) == len(text) + 1
    for i in range(len(text) + 1):
        assert got[i] == utf16_length(text[:i])


def test_find_returns_utf16_offsets_after_an_astral_character() -> None:
    text = f"Note {ASTRAL} see IEEE 1547-2018 please"
    found = demo.find_citations(text)
    assert len(found) == 1
    c = found[0]
    assert c["text"] == "IEEE 1547-2018"
    assert c["start"] == 5 + 2 + 5
    assert c["end"] == c["start"] + 14
    units = text.encode("utf-16-le")
    assert units[c["start"] * 2 : c["end"] * 2].decode("utf-16-le") == c["text"]


def test_find_fields() -> None:
    text = "See IEEE 1547-2018 clause 4.2 here."
    (c,) = demo.find_citations(text)
    assert c["key"] == "IEEE 1547-2018 Clause 4.2"
    assert c["base_key"] == "IEEE 1547"
    assert c["body"] == "IEEE"
    assert c["clause"] == "clause 4.2"
    assert c["inferred"] is False


def test_find_agrees_with_extract() -> None:
    text = "IEEE 1547-2018, then ASTM A36 and Rule 250B of NESC C2-2017."
    ours = demo.find_citations(text)
    theirs = extract(text)
    assert [c["text"] for c in ours] == [c.text for c in theirs]
    assert [c["key"] for c in ours] == [c.designation.key() for c in theirs]


def test_find_result_is_json_safe() -> None:
    found = demo.find_citations(f"{ASTRAL} IEEE 1547-2018")
    assert json.loads(json.dumps(found)) == found


def test_find_on_text_without_citations() -> None:
    assert demo.find_citations("Nothing here.") == []


def test_find_refuses_too_long_text() -> None:
    with pytest.raises(ValueError, match="characters"):
        demo.find_citations("a" * (demo.MAX_CHARS + 1))


def test_sample_is_repeatable_and_differs_by_seed() -> None:
    assert demo.sample_text(42) == demo.sample_text(42)
    assert demo.sample_text(42) != demo.sample_text(43)


def test_sample_has_citations() -> None:
    assert len(demo.find_citations(demo.sample_text(42))) > 0


def test_sample_refuses_bad_seeds() -> None:
    with pytest.raises(ValueError):
        demo.sample_text(-1)
    with pytest.raises(TypeError):
        demo.sample_text(True)


@given(st.integers(min_value=0, max_value=500))
def test_sample_stays_under_the_text_limit(seed: int) -> None:
    assert len(demo.sample_text(seed)) <= demo.MAX_CHARS
