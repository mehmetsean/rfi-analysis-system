import re
from collections import Counter

from rfikit.synth.library import TEMPLATES
from rfikit.synth.templates import (
    ISSUE_TYPES,
    SLOT_KINDS,
    slot_names,
    split_slots,
)

BANNED_WORDS = (
    "IEEE",
    "IEC",
    "ANSI",
    "ASTM",
    "NEMA",
    "NESC",
    "RULE",
    "TABLE",
    "SECTION",
    "SEC.",
    "CLAUSE",
    "PARA ",
    "FIGURE",
    "ANNEX",
    "REQUIRE",
    "SHALL",
    "MUST",
    "MANDAT",
)


def statics(text: str) -> str:
    return "".join(value for kind, value in split_slots(text) if kind == "text")


def test_ids_are_unique_and_match_family() -> None:
    ids = [t.template_id for t in TEMPLATES]
    assert len(ids) == len(set(ids))
    for t in TEMPLATES:
        assert t.family in ("A", "B")
        assert re.fullmatch(r"[a-z]{2}-" + t.family + r"\d", t.template_id)
        assert t.issue_type in ISSUE_TYPES


def test_every_issue_type_has_templates() -> None:
    counts = Counter(t.issue_type for t in TEMPLATES)
    assert set(counts) == set(ISSUE_TYPES)
    assert min(counts.values()) >= 3


def test_slots_are_known_and_cites_are_not_reused() -> None:
    for t in TEMPLATES:
        names = slot_names(t.subject) + slot_names(t.question) + slot_names(t.response)
        assert names, t.template_id
        for name in names:
            assert name[0] in SLOT_KINDS, (t.template_id, name)
        for name in set(names):
            if name[0] in "cwynlboe" or name[0] in "xk":
                assert names.count(name) == 1, (t.template_id, name)
        assert any(name[0] == "p" for name in names), t.template_id
        if any(n[0] == "b" for n in names):
            assert any(n[0] == "n" for n in names), t.template_id
        if "e2" in names:
            assert "e1" in names and names.index("e1") < names.index("e2")


def test_clause_word_slots_come_before_any_citation_in_their_column() -> None:
    for t in TEMPLATES:
        for text in (t.subject, t.question, t.response):
            names = slot_names(text)
            for i, name in enumerate(names):
                if name[0] == "k":
                    assert not any(n[0] in "cwynlboe" for n in names[:i]), t.template_id


def test_fixed_text_names_no_body_and_states_no_requirement() -> None:
    for t in TEMPLATES:
        for text in (t.subject, t.question, t.response):
            fixed = statics(text).upper()
            for word in BANNED_WORDS:
                assert word not in fixed, (t.template_id, word)


def test_text_is_plain() -> None:
    for t in TEMPLATES:
        for text in (t.subject, t.question, t.response):
            assert text.isascii()
            assert "  " not in text
