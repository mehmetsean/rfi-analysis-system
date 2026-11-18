import pytest

from rfikit.evaluate import NEGATIVE_KINDS
from rfikit.synth import negatives
from rfikit.synth.rng import Rng


def test_kinds_match_the_label_reader() -> None:
    found = set(negatives.GENERAL_KINDS) | set(negatives.CLAUSE_KINDS)
    assert found == set(NEGATIVE_KINDS)
    assert len(found) == len(negatives.GENERAL_KINDS) + len(negatives.CLAUSE_KINDS)


@pytest.mark.parametrize("kind", NEGATIVE_KINDS)
def test_every_kind_builds_text(kind: str) -> None:
    for seed in range(40):
        spec = negatives.make_negative(Rng(seed), kind)
        assert spec.kind == kind
        assert spec.text == spec.text.strip()
        assert spec.text.isascii()
        assert not spec.prefix.endswith("  ")


def test_spans_follow_the_guide() -> None:
    rng = Rng(3)
    assert negatives.make_negative(rng, "bare_rule").text.startswith("Rule ")
    assert negatives.make_negative(rng, "spec_section").text.startswith("Section ")
    assert negatives.make_negative(rng, "sheet_number").text.startswith("E-")
    assert negatives.make_negative(rng, "ansi_sheet").text.endswith("size sheets")
    assert negatives.make_negative(rng, "rfi_number").text.startswith("RFI-")
    assert negatives.make_negative(rng, "kva_rating").text.endswith(" kVA")
    assert negatives.make_negative(rng, "ieee_transactions").text == "IEEE Transactions"


def test_dates_come_in_three_shapes() -> None:
    shapes = set()
    for seed in range(60):
        text = negatives.make_negative(Rng(seed), "date").text
        shapes.add("iso" if text[4] == "-" else "slash" if "/" in text else "words")
    assert shapes == {"iso", "slash", "words"}


def test_unknown_kind() -> None:
    with pytest.raises(ValueError):
        negatives.make_negative(Rng(1), "other")
