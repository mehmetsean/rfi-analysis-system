import csv
import json
import os
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from rfikit import io as rio
from rfikit.cite import extract_rfi
from rfikit.io import (
    InputError,
    atomic_text,
    check_outside,
    read_column_map,
    read_rfis,
    read_text,
)
from rfikit.report import csv_text, escape_cell
from rfikit.textnorm import clip
from rfikit.types import Rfi


def write(path: Path, text: str, bom: bool = False) -> Path:
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)
    return path


def test_read_basic(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nR1,S,Q\n")
    assert read_rfis(path) == [Rfi("R1", "S", "Q", "")]


def test_read_response_and_extra_columns(tmp_path: Path) -> None:
    text = "extra,response,question,subject,rfi_id\nx,A,Q,S,R1\n"
    path = write(tmp_path / "a.csv", text)
    assert read_rfis(path) == [Rfi("R1", "S", "Q", "A")]


def test_bom_accepted(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nR1,S,Q\n", bom=True)
    assert read_rfis(path)[0].rfi_id == "R1"


def test_bom_text(tmp_path: Path) -> None:
    path = write(tmp_path / "a.txt", "hello", bom=True)
    assert read_text(path) == "hello"


def test_blank_line_skipped(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nR1,S,Q\n\n")
    assert len(read_rfis(path)) == 1


def test_symlink(tmp_path: Path) -> None:
    real = write(tmp_path / "real.csv", "rfi_id,subject,question\n")
    link = tmp_path / "link.csv"
    link.symlink_to(real)
    with pytest.raises(InputError, match="link.csv: symbolic links"):
        read_rfis(link)
    with pytest.raises(InputError, match="symbolic links"):
        read_text(link)


def test_missing_and_not_regular(tmp_path: Path) -> None:
    with pytest.raises(
        InputError, match="nope.csv: file is missing or is not a regular file"
    ):
        read_rfis(tmp_path / "nope.csv")
    with pytest.raises(InputError, match="not a regular"):
        read_text(tmp_path)


def test_unreadable(tmp_path: Path) -> None:
    path = write(tmp_path / "a.txt", "x")
    path.chmod(0)
    try:
        with pytest.raises(InputError, match="a.txt: file cannot be read"):
            read_text(path)
    finally:
        path.chmod(0o600)


def test_over_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rio, "MAX_TEXT_BYTES", 10)
    path = write(tmp_path / "a.txt", "x" * 11)
    with pytest.raises(InputError, match="file is over .* MiB, split it"):
        read_text(path)
    assert read_text(write(tmp_path / "b.txt", "x" * 10)) == "x" * 10


def test_csv_cap_is_separate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rio, "MAX_BYTES", 30)
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nR1,S,Q\n")
    with pytest.raises(InputError, match="over .* MiB"):
        read_rfis(path)
    assert rio.MAX_TEXT_BYTES == 4 * rio.MIB
    assert rio.MAX_BYTES != rio.MAX_TEXT_BYTES


def test_fifo_is_refused(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(InputError, match="not a regular file"):
        read_text(fifo)


def test_descriptor_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write(tmp_path / "a.txt", "x")
    monkeypatch.setattr("rfikit.io.os.fstat", lambda fd: os.stat(tmp_path))
    with pytest.raises(InputError, match="not a regular file"):
        read_text(path)


def test_not_utf8(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_bytes(b"rfi_id,subject,question\nR1,\xff,Q\n")
    with pytest.raises(InputError, match="not valid UTF-8"):
        read_rfis(path)


def test_empty_file(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="file is empty"):
        read_rfis(write(tmp_path / "a.csv", ""))


def test_malformed_csv(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", 'rfi_id,subject,question\nR1,"S"x,Q\n')
    with pytest.raises(InputError, match="a.csv: bad CSV"):
        read_rfis(path)


def test_wrong_cell_count(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nR1,S\n")
    with pytest.raises(InputError, match="line 2: expected 3 cells, got 2"):
        read_rfis(path)


@pytest.mark.parametrize("missing", ["rfi_id", "subject", "question"])
def test_missing_column(tmp_path: Path, missing: str) -> None:
    names = [n for n in ("rfi_id", "subject", "question") if n != missing]
    path = write(tmp_path / "a.csv", ",".join(names) + "\n")
    with pytest.raises(InputError, match=f"missing column '{missing}'"):
        read_rfis(path)


def test_duplicate_column(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question,subject\n")
    with pytest.raises(InputError, match="duplicate column 'subject'"):
        read_rfis(path)


def test_empty_and_repeated_id(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nR1,S,Q\n,S,Q\n")
    with pytest.raises(InputError, match="line 3: rfi_id is empty"):
        read_rfis(path)
    path = write(tmp_path / "b.csv", "rfi_id,subject,question\nR1,S,Q\nR1,S,Q\n")
    with pytest.raises(InputError, match="line 3: rfi_id 'R1' repeats"):
        read_rfis(path)


def test_row_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rio, "MAX_ROWS", 2)
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nA,S,Q\nB,S,Q\nC,S,Q\n")
    with pytest.raises(InputError, match="more than 2 rows"):
        read_rfis(path)
    path = write(tmp_path / "b.csv", "rfi_id,subject,question\nA,S,Q\nB,S,Q\n")
    assert len(read_rfis(path)) == 2


def test_field_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rio, "MAX_FIELD", 5)
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nA,S,123456\n")
    with pytest.raises(InputError, match="line 2, column 'question': value is over 5"):
        read_rfis(path)
    path = write(tmp_path / "b.csv", "rfi_id,subject,question\nA,S,12345\n")
    assert read_rfis(path)[0].question == "12345"


def test_column_map(tmp_path: Path) -> None:
    csv_path = write(tmp_path / "a.csv", "RFI No,Title,Body,Reply\n1,S,Q,A\n")
    names = {"rfi_id": "RFI No", "subject": "Title", "question": "Body"}
    names["response"] = "Reply"
    map_path = write(tmp_path / "m.json", json.dumps(names))
    assert read_rfis(csv_path, read_column_map(map_path)) == [Rfi("1", "S", "Q", "A")]


def test_column_map_partial(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "RFI No,subject,question\n1,S,Q\n")
    assert read_rfis(path, {"rfi_id": "RFI No"})[0].rfi_id == "1"


def test_column_map_missing_column(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\n1,S,Q\n")
    message = "missing column 'Reply' for the response field"
    with pytest.raises(InputError, match=message):
        read_rfis(path, {"response": "Reply"})


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("{", "not valid JSON"),
        ("[1]", "must be a JSON object"),
        ('{"nope": "x"}', "unknown key 'nope'"),
        ('{"subject": 3}', "value of 'subject' must be a column name"),
        ('{"subject": ""}', "value of 'subject' must be a column name"),
    ],
)
def test_column_map_errors(tmp_path: Path, body: str, message: str) -> None:
    with pytest.raises(InputError, match=message):
        read_column_map(write(tmp_path / "m.json", body))


ESCAPED = [
    "=1",
    "+1",
    "-1",
    "@a",
    "\t1",
    "\r1",
    "\n1",
    " =1",
    "\n=1",
    "\ufeff=1",
    " \ufeff =1",
    "\uff1d1",
    "\uff0b1",
    "\uff0d1",
    "\uff20a",
]


@pytest.mark.parametrize("value", ESCAPED)
def test_escape_cell(value: str) -> None:
    assert escape_cell(value) == "'" + value


@pytest.mark.parametrize("value", ["plain", "", "a=b", "1-2", " x", "\ufeffx"])
def test_escape_cell_leaves_plain(value: str) -> None:
    assert escape_cell(value) == value


def test_csv_text_escapes_header_and_rows() -> None:
    assert csv_text(["=a"], [["=1+1"]]) == "'=a\n'=1+1\n"


def test_unused_duplicate_column_is_fine(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,x,subject,question,x\nR1,1,S,Q,2\n")
    assert read_rfis(path) == [Rfi("R1", "S", "Q", "")]


def test_all_empty_rows_skipped(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question\nR1,S,Q\n,,\n,,\n")
    assert len(read_rfis(path)) == 1


def test_two_fields_one_column(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,Body\nR1,Q\n")
    names = {"subject": "Body", "question": "Body"}
    with pytest.raises(InputError, match="column 'Body' is used for both"):
        read_rfis(path, names)


def test_mapped_field_lands_on_default_name(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", "rfi_id,subject,question,response\nR1,S,Q,A\n")
    with pytest.raises(InputError, match="used for both"):
        read_rfis(path, {"subject": "response"})


def test_long_values_are_clipped(tmp_path: Path) -> None:
    long = "R" * 100
    path = write(
        tmp_path / "a.csv", f"rfi_id,subject,question\n{long},S,Q\n{long},S,Q\n"
    )
    with pytest.raises(InputError) as caught:
        read_rfis(path)
    assert long not in str(caught.value)
    assert "R" * 40 + "..." in str(caught.value)
    with pytest.raises(InputError) as caught:
        read_column_map(write(tmp_path / "m.json", json.dumps({long: "x"})))
    assert long not in str(caught.value)


def test_csv_field_limit_message(tmp_path: Path) -> None:
    big = "x" * 140_000
    path = write(tmp_path / "a.csv", f"rfi_id,subject,question,other\nR1,S,Q,{big}\n")
    with pytest.raises(InputError, match="a value is over 100000 characters"):
        read_rfis(path)


def test_field_cap_names_the_column(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rio, "MAX_FIELD", 3)
    path = write(tmp_path / "a.csv", "No,Title,Body\n1,S,12345\n")
    names = {"rfi_id": "No", "subject": "Title", "question": "Body"}
    with pytest.raises(InputError, match="column 'Body': value is over 3 characters"):
        read_rfis(path, names)


def test_atomic_text_writes_and_replaces(tmp_path: Path) -> None:
    target = tmp_path / "out.csv"
    target.write_text("old", encoding="utf-8")
    with atomic_text(target) as handle:
        handle.write("new\n")
    assert target.read_text(encoding="utf-8") == "new\n"
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]


def test_atomic_text_failure_keeps_old_file(tmp_path: Path) -> None:
    target = tmp_path / "out.csv"
    target.write_text("old", encoding="utf-8")
    with pytest.raises(InputError, match="boom"), atomic_text(target) as handle:
        handle.write("half")
        raise InputError("boom")
    assert target.read_text(encoding="utf-8") == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]


def test_atomic_text_refusals(tmp_path: Path) -> None:
    real = write(tmp_path / "real.txt", "x")
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    with pytest.raises(InputError, match="symbolic link"), atomic_text(link):
        pass
    with pytest.raises(InputError, match="not a regular file"), atomic_text(tmp_path):
        pass
    with (
        pytest.raises(InputError, match="same file as"),
        atomic_text(real, [real]),
    ):
        pass
    hard = tmp_path / "hard.txt"
    os.link(real, hard)
    with (
        pytest.raises(InputError, match="same file as"),
        atomic_text(hard, [real]),
    ):
        pass
    assert real.read_text(encoding="utf-8") == "x"


def test_atomic_text_missing_folder(tmp_path: Path) -> None:
    with (
        pytest.raises(InputError, match="file cannot be written, check that"),
        atomic_text(tmp_path / "none" / "o.csv"),
    ):
        pass


def test_atomic_text_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "o.csv"

    def fail(src: str, dst: Path) -> None:
        raise OSError("disk")

    monkeypatch.setattr("rfikit.io.os.replace", fail)
    with pytest.raises(InputError, match="file cannot be written"):
        with atomic_text(target) as handle:
            handle.write("x")
    assert list(tmp_path.iterdir()) == []


PIECES = st.one_of(
    st.characters(codec="utf-8", exclude_characters="\x00\ufeff"),
    st.sampled_from(['"', ",", "\n", "\r\n", "\U0001f600", "IEEE 1584", " NESC "]),
)
TEXT = st.lists(PIECES, max_size=15).map("".join)


@settings(max_examples=100, deadline=None)
@given(st.lists(st.tuples(TEXT, TEXT, TEXT), max_size=6))
def test_csv_roundtrip_and_extract(
    tmp_path_factory: pytest.TempPathFactory, rows: list[tuple[str, str, str]]
) -> None:
    folder = tmp_path_factory.mktemp("prop")
    rfis = [Rfi(f"R{i}", s, q, a) for i, (s, q, a) in enumerate(rows)]
    path = folder / "a.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rfi_id", "subject", "question", "response"])
        for r in rfis:
            writer.writerow([r.rfi_id, r.subject, r.question, r.response])
    back = read_rfis(path)
    assert back == rfis
    for original, loaded in zip(rfis, back, strict=True):
        assert extract_rfi(loaded) == extract_rfi(original)


def test_cite_does_not_import_io() -> None:
    source = (Path(rio.__file__).parent / "cite.py").read_text(encoding="utf-8")
    for name in ("rfikit.io", "rfikit.synth", "rfikit.evaluate"):
        assert name not in source


def test_clip_boundaries() -> None:
    assert clip("a" * 40) == repr("a" * 40)
    assert clip("a" * 41) == "'" + "a" * 40 + "...'"
    assert clip("a\nb") == "'a\\nb'"


def test_newline_id_gives_one_line(tmp_path: Path) -> None:
    rows = 'rfi_id,subject,question\n"a\nb",S,Q\n"a\nb",S,Q\n'
    path = write(tmp_path / "a.csv", rows)
    with pytest.raises(InputError) as caught:
        read_rfis(path)
    assert "\n" not in str(caught.value)
    assert "'a\\nb'" in str(caught.value)


@pytest.mark.parametrize(
    "value",
    ["​=1", "⁠=1", "﻿﻿=1", "\x00=1", "​ ﻿\x00+1"],
)
def test_escape_cell_skips_invisible_characters(value: str) -> None:
    assert escape_cell(value) == "'" + value


def test_new_file_follows_umask(tmp_path: Path) -> None:
    old = os.umask(0o077)
    try:
        target = tmp_path / "new.csv"
        with atomic_text(target) as handle:
            handle.write("x")
    finally:
        os.umask(old)
    assert target.stat().st_mode & 0o777 == 0o600


def test_existing_mode_is_kept(tmp_path: Path) -> None:
    target = tmp_path / "old.csv"
    target.write_text("old", encoding="utf-8")
    target.chmod(0o600)
    old = os.umask(0o022)
    try:
        with atomic_text(target) as handle:
            handle.write("x")
    finally:
        os.umask(old)
    assert target.stat().st_mode & 0o777 == 0o600


def test_new_file_default_mode(tmp_path: Path) -> None:
    old = os.umask(0o022)
    try:
        target = tmp_path / "new.csv"
        with atomic_text(target) as handle:
            handle.write("x")
    finally:
        os.umask(old)
    assert target.stat().st_mode & 0o777 == 0o644


def test_protected_list(tmp_path: Path) -> None:
    first = write(tmp_path / "a.txt", "x")
    second = write(tmp_path / "b.txt", "y")
    with (
        pytest.raises(InputError, match="same file as b.txt"),
        atomic_text(second, [first, second]),
    ):
        pass


def test_check_outside(tmp_path: Path) -> None:
    folder = tmp_path / "data"
    folder.mkdir()
    with pytest.raises(InputError, match="inside the input folder data"):
        check_outside(folder / "x" / ".." / "out.json", [folder])
    check_outside(tmp_path / "out.json", [folder])
    link = tmp_path / "link"
    link.symlink_to(folder)
    with pytest.raises(InputError, match="inside the input folder"):
        check_outside(link / "out.json", [folder])


def test_check_outside_link_into_subfolder(tmp_path: Path) -> None:
    folder = tmp_path / "data"
    (folder / "labels").mkdir(parents=True)
    link = tmp_path / "to_labels"
    link.symlink_to(folder / "labels")
    with pytest.raises(InputError, match="inside the input folder data"):
        check_outside(link / "out.json", [folder])


def test_check_outside_link_inside_folder(tmp_path: Path) -> None:
    folder = tmp_path / "data"
    folder.mkdir()
    away = tmp_path / "away"
    away.mkdir()
    (folder / "to_away").symlink_to(away)
    with pytest.raises(InputError, match="inside the input folder data"):
        check_outside(folder / "to_away" / "out.json", [folder])


def test_open_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []
    real_open = os.open

    def spy(path: Path, flags: int, *rest: int) -> int:
        seen.append(flags)
        return real_open(path, flags, *rest)

    path = write(tmp_path / "a.txt", "x")
    monkeypatch.setattr("rfikit.io.os.open", spy)
    assert read_text(path) == "x"
    assert seen[0] & os.O_NOFOLLOW
    assert seen[0] & os.O_NONBLOCK
