from pathlib import Path

import build_heldout as bh
import pytest


def test_unescape() -> None:
    assert bh.unescape("a\\nb") == "a\nb"
    assert bh.unescape("a\\\\b") == "a\\b"
    assert bh.unescape("IEEE\\u00a0X\\u2011") == "IEEE" + chr(0xA0) + "X" + chr(0x2011)
    assert bh.unescape("plain") == "plain"


def test_bad_escape() -> None:
    with pytest.raises(bh.BuildError, match="bad escape"):
        bh.unescape("a\\qb")


def test_plain_column() -> None:
    column = bh.parse_column("Nothing to see")
    assert column.text == "Nothing to see"
    assert column.citations == []
    assert column.negatives == []


def test_simple_citation() -> None:
    column = bh.parse_column("Is [[c IEEE 80 | IEEE 80 | real | IEEE 80]] ok?")
    assert column.text == "Is IEEE 80 ok?"
    (cite,) = column.citations
    assert (cite.start, cite.end) == (3, 10)
    assert cite.clause_start is None
    assert cite.key == "IEEE 80"
    assert cite.base_key == "IEEE 80"
    assert cite.scope == "in"
    assert cite.catalog == "real"
    assert not cite.inferred


def test_clause_after_span() -> None:
    raw = (
        "[[c NESC 2017 Rule 232B1 | NESC Rule 232B1 | real | "
        "<s>2017 NESC</s> <k>Rule 232B1</k>]]"
    )
    column = bh.parse_column(raw)
    assert column.text == "2017 NESC Rule 232B1"
    (cite,) = column.citations
    assert column.text[cite.start : cite.end] == "2017 NESC"
    assert cite.clause_start is not None
    assert cite.clause_end is not None
    assert column.text[cite.clause_start : cite.clause_end] == "Rule 232B1"


def test_clause_before_span() -> None:
    raw = (
        "Q: [[c IEEE 80 Clause 5.3 | IEEE 80 | real | "
        "<k>Section 5.3</k> of <s>IEEE 80</s>]]"
    )
    column = bh.parse_column(raw)
    (cite,) = column.citations
    assert column.text[cite.start : cite.end] == "IEEE 80"
    assert cite.clause_start == 3


def test_inferred_clause_only() -> None:
    raw = (
        "See [[c NESC Rule 234B | NESC Rule 234B | real inferred | <k>Rule 234B</k>]]."
    )
    (cite,) = bh.parse_column(raw).citations
    assert cite.inferred
    assert (cite.start, cite.end) == (cite.clause_start, cite.clause_end)


def test_clause_only_needs_inferred() -> None:
    with pytest.raises(bh.BuildError, match="inferred"):
        bh.parse_column("[[c K | B | real | <k>Rule 1</k>]]")


def test_flags_and_noise() -> None:
    raw = "[[c NFPA 70 | NFPA 70 | invented out noise=case | nfpa 70]]"
    (cite,) = bh.parse_column(raw).citations
    assert cite.scope == "out"
    assert cite.catalog == "invented"
    assert cite.noise_class == "case"


@pytest.mark.parametrize(
    "flags", ["", "weird real", "real invented", "inferred", "real noise=a noise=b"]
)
def test_bad_flags(flags: str) -> None:
    with pytest.raises(bh.BuildError):
        bh.parse_column(f"[[c K | B | {flags} | text]]")


def test_escapes_and_offsets() -> None:
    raw = "a\\nb [[c IEEE 80 | IEEE 80 | real | IEEE\\n80]] z"
    column = bh.parse_column(raw)
    (cite,) = column.citations
    assert column.text == "a\nb IEEE\n80 z"
    assert column.text[cite.start : cite.end] == "IEEE\n80"


def test_negative() -> None:
    column = bh.parse_column("Hi [[n date | 2017-06-01]] there")
    (neg,) = column.negatives
    assert column.text[neg.start : neg.end] == "2017-06-01"
    assert neg.kind == "date"


def test_negative_with_tags_fails() -> None:
    with pytest.raises(bh.BuildError, match="takes no"):
        bh.parse_column("[[n date | <s>x</s>]]")


@pytest.mark.parametrize(
    "raw",
    [
        "[[c K | B | real | text",
        "text]]",
        "[[c K | B | real | [[n date | x]]]]",
        "[[x K | B | real | text]]",
        "[[c K | B | real]]",
        "[[c K | B | real |text]]",
        "[[c K | B | real | <s>a<s>b</s></s>]]",
        "[[c K | B | real | <s>a]]",
        "[[c K | B | real | a</s>]]",
        "[[c K | B | real | <s>a</s><s>b</s>]]",
        "[[c K | B | real | <s>a</k>]]",
        "[[c K | B | real |  text]]",
        "[[c K | B | real | text ]]",
        "[[c K | B | real | <s> a</s>]]",
        "[[n | x]]",
        "[[c | B | real | x]]",
        "[[c K |  | real | x]]",
        "[[n date | ]]",
        "[[n date x]]",
    ],
)
def test_malformed_marks(raw: str) -> None:
    with pytest.raises(bh.BuildError):
        bh.parse_column(raw)


def test_banned_dashes() -> None:
    with pytest.raises(bh.BuildError, match="banned"):
        bh.parse_column("a\\u2013b")
    with pytest.raises(bh.BuildError, match="banned"):
        bh.parse_column("a" + chr(0x2014) + "b")


SMALL = """# comment
=== W001 | field_condition | G01
subject: Edition of [[c IEEE 80 | IEEE 80 | real | IEEE 80]]
question: Is [[n date | 2017-06-01]] fine?
response: Yes.

=== W002 | field_condition | G01
subject: Again
question: Same thing.

=== W003 | document_conflict | -
subject: Other
question: Another one.
"""


def test_parse_source() -> None:
    rfis = bh.parse_source(SMALL)
    assert [r.rfi_id for r in rfis] == ["W001", "W002", "W003"]
    assert rfis[0].columns["response"].text == "Yes."
    assert rfis[1].columns["response"].text == ""
    assert rfis[2].group_id == "single-W003"


@pytest.mark.parametrize(
    "source",
    [
        "subject: no header\n",
        "=== W1 | a\nsubject: x\nquestion: y\n",
        "=== W1 | a | b\nsubject: x\n",
        "=== W1 | a | b\nquestion: x\n",
        "=== W1 | a | b\nsubject: x\nsubject: y\nquestion: z\n",
        "=== W1 | a | b\nsubject: x\nquestion: y\nnotes: z\n",
        "=== W1 | a | b\nsubject: x\nquestion: y\n"
        "=== W1 | a | b\nsubject: x\nquestion: y\n",
    ],
)
def test_bad_source(source: str) -> None:
    with pytest.raises(bh.BuildError):
        bh.parse_source(source)


def test_build_files() -> None:
    files = bh.build(SMALL)
    assert set(files) == {
        "heldout/input/rfis.csv",
        "heldout/labels/citations.csv",
        "heldout/labels/negatives.csv",
        "heldout/labels/rfis.csv",
        "heldout/README.txt",
        "heldout/input/README.txt",
        "heldout/labels/README.txt",
        "heldout/manifest.json",
    }
    assert files["heldout/labels/citations.csv"].decode().splitlines()[1] == (
        "W001,subject,11,18,,,IEEE 80,IEEE 80,in,0,real,"
    )
    assert b"single-W003" in files["heldout/labels/rfis.csv"]
    assert bh.build(SMALL) == files


def test_manifest_counts() -> None:
    import json

    manifest = json.loads(bh.build(SMALL)["heldout/manifest.json"])
    assert manifest["synthetic"] is True
    assert manifest["counts"]["rfis"] == 3
    assert manifest["counts"]["citations_per_body"] == {"IEEE": 1}
    assert manifest["counts"]["negatives_per_kind"] == {"date": 1}
    assert manifest["recurring_groups"] == {"G01": ["W001", "W002"]}
    assert manifest["source"]["sha256"] == bh.sha256(SMALL.encode())


def test_write_then_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "heldout").mkdir()
    (tmp_path / bh.SOURCE_PATH).write_text(SMALL, encoding="utf-8")
    assert bh.check(tmp_path) != []
    bh.write(tmp_path)
    assert bh.check(tmp_path) == []
    (tmp_path / "heldout/labels/rfis.csv").write_text("changed")
    assert bh.check(tmp_path) == ["differs: heldout/labels/rfis.csv"]


def test_main_modes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "heldout").mkdir()
    (tmp_path / bh.SOURCE_PATH).write_text(SMALL, encoding="utf-8")
    monkeypatch.setattr(bh, "ROOT", tmp_path)
    assert bh.main(["--check"]) == 1
    assert bh.main([]) == 0
    assert bh.main(["--check"]) == 0
    assert bh.main(["--bogus"]) == 2
    (tmp_path / bh.SOURCE_PATH).write_text("=== bad\n", encoding="utf-8")
    assert bh.main([]) == 1
    assert "error" in capsys.readouterr().out


BS = chr(92)


def test_cr_and_astral_escapes() -> None:
    assert bh.unescape("a" + BS + "r" + BS + "nb") == "a\r\nb"
    assert bh.unescape(BS + "U0001d400") == chr(0x1D400)


def test_astral_character_offsets() -> None:
    raw = BS + "U0001d400 [[c IEEE 80 | IEEE 80 | real | IEEE 80]]"
    column = bh.parse_column(raw)
    (cite,) = column.citations
    assert column.text[cite.start : cite.end] == "IEEE 80"
    assert cite.start == 2


@pytest.mark.parametrize(
    "escape", [BS + "ud800", BS + "udfff", BS + "U0000d900", BS + "U00110000"]
)
def test_bad_code_points(escape: str) -> None:
    with pytest.raises(bh.BuildError, match="not a valid character"):
        bh.unescape(escape)


def test_error_names_rfi_column_and_line() -> None:
    source = "=== W1 | a | b\nsubject: fine\nquestion: bad [[c K | B | real | x\n"
    with pytest.raises(bh.BuildError) as info:
        bh.parse_source(source)
    message = str(info.value)
    assert "W1" in message
    assert "question" in message
    assert "line 3" in message


def prepare(tmp_path: Path, data: bytes) -> None:
    (tmp_path / "heldout").mkdir()
    (tmp_path / bh.SOURCE_PATH).write_bytes(data)


def test_crlf_source_fails_check(tmp_path: Path) -> None:
    prepare(tmp_path, SMALL.encode("utf-8"))
    bh.write(tmp_path)
    assert bh.check(tmp_path) == []
    crlf = SMALL.replace("\n", "\r\n").encode("utf-8")
    (tmp_path / bh.SOURCE_PATH).write_bytes(crlf)
    assert "differs: heldout/manifest.json" in bh.check(tmp_path)


def test_main_missing_and_bad_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(bh, "ROOT", tmp_path)
    (tmp_path / "heldout").mkdir()
    assert bh.main(["--check"]) == 1
    assert "cannot find" in capsys.readouterr().out
    prepare_bytes = b"=== W1 | a | b\nsubject: \xff\xfe\n"
    (tmp_path / bh.SOURCE_PATH).write_bytes(prepare_bytes)
    assert bh.main([]) == 1
    assert "not valid UTF-8" in capsys.readouterr().out
