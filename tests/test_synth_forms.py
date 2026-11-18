import re
from dataclasses import replace

import pytest

from rfikit.synth import cites, noise
from rfikit.synth.forms import Rendered, render_entry, render_nesc
from rfikit.synth.params import GenParams
from rfikit.synth.rng import Rng
from synth_helpers import EM_DASH, EN_DASH


def sample(
    body: str, seed: int = 1, year_mode: str = "yes", clause_mode: str = "none"
) -> cites.CiteSpec:
    params = GenParams(noise_rate=0.0)
    return cites.make_cite(Rng(seed), params, body, year_mode, clause_mode)


def test_render_entry_key_and_spans() -> None:
    item = render_entry("IEEE", "C57.12.00", "", "", "2015", "", "IEEE Std", "real")
    assert item.text == "IEEE Std C57.12.00-2015"
    assert item.designation.key() == "IEEE C57.12.00-2015"
    assert item.designation.base_key() == "IEEE C57.12.00"
    assert item.text[item.number_at :] == "C57.12.00-2015"
    assert item.text[slice(*item.word)] == "IEEE"


def test_render_joint_and_type_forms() -> None:
    joint = render_entry("IEC", "60255", "118-1", "", "2018", "", "IEC/IEEE", "real")
    assert joint.text == "IEC/IEEE 60255-118-1:2018"
    assert joint.designation.co_bodies == ("IEEE",)
    assert joint.designation.key() == "IEC 60255-118-1:2018"
    typed = render_entry(
        "IEC", "61850", "7-4", "TS", "2010", "+AMD1:2020", "IEC", "real"
    )
    assert typed.text == "IEC TS 61850-7-4:2010+AMD1:2020"
    assert typed.designation.key() == "IEC TS 61850-7-4:2010+AMD1:2020"
    assert typed.designation.base_key() == "IEC TS 61850-7-4"
    reversed_joint = render_entry(
        "IEEE", "1588", "", "", "2019", "", "IEEE/IEC", "real"
    )
    assert reversed_joint.designation.co_bodies == ("IEC",)
    assert reversed_joint.designation.key() == "IEEE 1588-2019"
    ansi = render_entry("IEEE", "C37.2", "", "", "2008", "", "ANSI/IEEE", "real")
    assert ansi.designation.key() == "IEEE C37.2-2008"
    assert ansi.word == (5, 9)


def test_render_nesc_forms() -> None:
    first = render_nesc("{y} NESC", "2017", "real")
    assert first.text == "2017 NESC"
    assert first.designation.key() == "NESC 2017"
    assert first.text[slice(*first.word)] == "NESC"
    alias = render_nesc("ANSI/IEEE C2-{y}", "2007", "real")
    assert alias.designation.key() == "NESC 2007"
    assert alias.text[slice(*alias.word)] == "IEEE"
    plain = render_nesc("NESC", "", "real")
    assert plain.designation.key() == "NESC"


def test_clause_keys_follow_the_guide() -> None:
    seen: dict[str, set[str]] = {"NESC": set(), "other": set()}
    for seed in range(300):
        for body in ("NESC", "IEEE", "ASTM"):
            clause, _ = cites.choose_clause(Rng(seed), body)
            word = clause.text.split(" ")[0]
            key_word = clause.key.split(" ")[0]
            assert clause.text.split(" ")[1] == clause.key.split(" ")[1]
            seen["NESC" if body == "NESC" else "other"].add(f"{word}>{key_word}")
    assert "Sec.>Section" in seen["NESC"]
    assert "Rule>Rule" in seen["NESC"]
    assert {"Section>Clause", "Sec.>Clause", "para>Clause", "Annex>Annex"} <= seen[
        "other"
    ]
    assert not any(pair.endswith(">Rule") for pair in seen["other"])


@pytest.mark.parametrize("body", ["IEEE", "NESC", "IEC", "ANSI", "ASTM", "NEMA"])
def test_make_cite_without_noise_is_clean(body: str) -> None:
    for seed in range(40):
        spec = sample(body, seed, "any", "any")
        assert spec.noise_class == ""
        assert spec.rendered.text.isascii()
        assert spec.rendered.designation.body == body
        assert (spec.clause is None) == (spec.connector == "")


def test_year_modes() -> None:
    for seed in range(60):
        assert sample("IEEE", seed, "none").rendered.designation.year == ""
        assert sample("IEEE", seed, "yes").rendered.designation.year != ""
        assert sample("NESC", seed, "yes").rendered.designation.year != ""
        assert sample("NESC", seed, "none").rendered.designation.year == ""


def test_pairs_name_one_document_with_two_editions() -> None:
    params = GenParams(noise_rate=0.0)
    for seed in range(100):
        first, second = cites.make_pair(Rng(seed), params)
        a = first.rendered.designation
        b = second.rendered.designation
        assert a.base_key() == b.base_key()
        assert a.key() != b.key()


def test_lists_inherit_the_body() -> None:
    params = GenParams()
    for seed in range(100):
        spec = cites.make_list(Rng(seed), params)
        head, *rest = spec.items
        assert len(spec.separators) == len(rest)
        assert head.noise_class != "misspelled"
        assert head.clause is None
        numbers = [head.rendered.designation.base_key()]
        for item in rest:
            assert item.noise_class == "list_continuation"
            assert item.rendered.inferred
            assert item.rendered.designation.body == head.rendered.designation.body
            assert item.rendered.text[0].isalnum()
            numbers.append(item.rendered.designation.base_key())
        assert len(set(numbers)) == len(numbers)


def test_bare_and_out_of_scope() -> None:
    for seed in range(60):
        bare = cites.make_bare(Rng(seed))
        assert bare.rendered.inferred
        assert bare.rendered.designation.year == ""
        assert bare.rendered.designation.key().startswith("NESC ")
        out = cites.make_out(Rng(seed))
        assert out.rendered.scope == "out"
        assert out.rendered.designation.key() == out.rendered.designation.base_key()


def make_rendered(text: str, number_at: int, word: tuple[int, int]) -> Rendered:
    base = render_entry("IEEE", "80", "", "", "", "", "IEEE", "real")
    return replace(base, text=text, number_at=number_at, word=word)


def test_noise_classes_change_the_text_as_named() -> None:
    items = [
        render_entry("IEEE", "C57.12.00", "", "", "2015", "", "IEEE Std", "real"),
        render_entry("IEC", "60076", "1", "", "2011", "", "IEC", "real"),
        render_entry("ASTM", "A123/A123M", "", "", "17", "", "ASTM", "real"),
        render_entry("NEMA", "TC 2", "", "", "2020", "", "NEMA", "real"),
        render_entry("ANSI", "C84.1", "", "", "2020", "", "ANSI", "real"),
        render_nesc("{y} NESC", "2017", "real"),
        render_nesc("NESC-{y}", "2017", "real"),
    ]
    for item in items:
        for name in noise.eligible(item):
            for seed in range(30):
                out = noise.apply_noise(Rng(seed), item, name)
                assert out != item.text, (item.text, name)
                assert out == out.strip()
                assert EN_DASH not in out and EM_DASH not in out
                if name == "unicode_dash":
                    assert "-" not in out
                    assert set(out) - set(item.text) <= set(noise.DASHES)
                if name == "line_break":
                    assert "\n" in out
                    assert re.sub(r"\r?\n *", "", out).replace(
                        " ", ""
                    ) == item.text.replace(" ", "")
                if name == "case":
                    assert out.upper() == item.text.upper()
                if name == "misspelled":
                    assert out.upper() != item.text


def test_every_class_is_reachable_for_a_typical_designation() -> None:
    item = render_entry("ASTM", "A123/A123M", "", "", "17", "", "ASTM", "real")
    assert set(noise.eligible(item)) == set(noise.NOISE_ORDER)


def test_nesc_without_a_number_has_no_line_break() -> None:
    item = render_nesc("NESC-{y}", "2017", "real")
    assert "line_break" not in noise.eligible(item)
    assert "spacing" not in noise.eligible(item)


def test_bare_items_get_no_noise() -> None:
    bare = cites.make_bare(Rng(1)).rendered
    assert noise.eligible(bare) == []


def test_unknown_noise_class() -> None:
    item = render_entry("IEEE", "80", "", "", "", "", "IEEE", "real")
    with pytest.raises(ValueError):
        noise.apply_noise(Rng(1), item, "other")


def test_noise_rate_one_noises_every_eligible_citation() -> None:
    params = GenParams(noise_rate=1.0)
    for seed in range(50):
        spec = cites.make_cite(Rng(seed), params, "IEEE", "yes", "none")
        assert spec.noise_class in noise.NOISE_ORDER
