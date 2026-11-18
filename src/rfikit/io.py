import csv
import io
import json
import os
import stat
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

from rfikit.textnorm import clip
from rfikit.types import Rfi

MIB = 1024 * 1024
MAX_BYTES = 32 * MIB
MAX_TEXT_BYTES = 4 * MIB
MAX_ROWS = 100_000
MAX_FIELD = 100_000
REQUIRED = ("rfi_id", "subject", "question")
OPTIONAL = ("response",)
FIELDS = REQUIRED + OPTIONAL
WRITE_HINT = "check that the folder exists and that you can write to it"


class InputError(ValueError):
    pass


def shown(path: Path) -> str:
    name = path.name or str(path)
    return "".join(
        c if c.isprintable() else c.encode("unicode_escape").decode() for c in name
    )


def _mib(cap: int) -> str:
    return f"{cap / MIB:g}"


def _read_file(path: Path, cap: int) -> str:
    name = shown(path)
    if path.is_symlink():
        raise InputError(
            f"{name}: symbolic links are not read, pass the real file instead"
        )
    if not path.is_file():
        raise InputError(
            f"{name}: file is missing or is not a regular file, check the path"
        )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise InputError(
            f"{name}: file cannot be read, check the file permissions"
        ) from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise InputError(
                f"{name}: file is missing or is not a regular file, check the path"
            )
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(cap + 1)
    except OSError:
        raise InputError(
            f"{name}: file cannot be read, check the file permissions"
        ) from None
    finally:
        os.close(fd)
    if len(raw) > cap:
        raise InputError(
            f"{name}: file is over {_mib(cap)} MiB, split it into smaller files"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(f"{name}: file is not valid UTF-8, save it as UTF-8") from None
    return text.removeprefix("﻿")


def read_text(path: Path) -> str:
    return _read_file(path, MAX_TEXT_BYTES)


def read_column_map(path: Path) -> dict[str, str]:
    name = shown(path)
    text = _read_file(path, MAX_TEXT_BYTES)
    try:
        data = json.loads(text)
    except ValueError:
        raise InputError(f"{name}: not valid JSON, check the syntax") from None
    if not isinstance(data, dict):
        raise InputError(
            f"{name}: the column map must be a JSON object, see the README"
        )
    found: dict[str, str] = {}
    for key, value in data.items():
        if key not in FIELDS:
            raise InputError(
                f"{name}: unknown key {clip(str(key))}, "
                f"remove it or use only these keys: {', '.join(FIELDS)}"
            )
        if not isinstance(value, str) or value == "":
            raise InputError(
                f"{name}: the value of {key!r} must be a column name, "
                "use a non-empty string"
            )
        found[key] = value
    return found


def _bad_csv(name: str, error: csv.Error) -> InputError:
    if "field larger than field limit" in str(error):
        return InputError(f"{name}: a value is over {MAX_FIELD} characters, shorten it")
    return InputError(f"{name}: bad CSV: {error}, check the quotes in the file")


def _header_index(
    name: str, header: list[str], column_map: dict[str, str]
) -> dict[str, int]:
    index: dict[str, int] = {}
    for field in FIELDS:
        column = column_map.get(field, field)
        if header.count(column) > 1:
            raise InputError(
                f"{name}: duplicate column {clip(column)}, "
                "rename one of them in the file"
            )
        if column in header:
            index[field] = header.index(column)
        elif field in REQUIRED or field in column_map:
            raise InputError(
                f"{name}: missing column {clip(column)} for {field}, "
                "add it to the file or fix the column map"
            )
    for field, position in index.items():
        for other, spot in index.items():
            if field < other and position == spot:
                raise InputError(
                    f"{name}: column {clip(header[position])} is used for both "
                    f"{field} and {other}, fix the column map"
                )
    return index


def iter_rfis(path: Path, column_map: dict[str, str] | None = None) -> Iterator[Rfi]:
    name = shown(path)
    text = _read_file(path, MAX_BYTES)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, None)
    except csv.Error as error:
        raise _bad_csv(name, error) from None
    if header is None:
        raise InputError(f"{name}: file is empty, add a header row")
    index = _header_index(name, header, column_map or {})
    return _rows(name, reader, header, index)


def _rows(
    name: str, reader: Any, header: list[str], index: dict[str, int]
) -> Iterator[Rfi]:
    seen: set[str] = set()
    try:
        for cells in reader:
            line = reader.line_num
            if not any(cells):
                continue
            if len(cells) != len(header):
                raise InputError(
                    f"{name} line {line}: expected {len(header)} cells, "
                    f"got {len(cells)}, check for an unquoted comma in the line"
                )
            if len(seen) >= MAX_ROWS:
                raise InputError(f"{name}: more than {MAX_ROWS} rows, split the file")
            values = {f: cells[i] for f, i in index.items()}
            for field, value in values.items():
                if len(value) > MAX_FIELD:
                    raise InputError(
                        f"{name} line {line}, column "
                        f"{clip(header[index[field]])}: value is over "
                        f"{MAX_FIELD} characters, shorten it"
                    )
            rfi_id = values["rfi_id"]
            if rfi_id == "":
                raise InputError(
                    f"{name} line {line}: rfi_id is empty, "
                    "give every row a unique rfi_id"
                )
            if rfi_id in seen:
                raise InputError(
                    f"{name} line {line}: rfi_id {clip(rfi_id)} repeats, "
                    "give each row a unique rfi_id"
                )
            seen.add(rfi_id)
            yield Rfi(
                rfi_id,
                values["subject"],
                values["question"],
                values.get("response", ""),
            )
    except csv.Error as error:
        raise _bad_csv(name, error) from None


def read_rfis(path: Path, column_map: dict[str, str] | None = None) -> list[Rfi]:
    return list(iter_rfis(path, column_map))


def _remove(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _umask() -> int:
    old = os.umask(0)
    os.umask(old)
    return old


def check_output(path: Path, protected: Sequence[Path] = ()) -> None:
    name = shown(path)
    if path.is_symlink():
        raise InputError(f"{name}: output is a symbolic link, pick another file")
    if path.exists():
        if not path.is_file():
            raise InputError(f"{name}: output is not a regular file, pick another file")
        for other in protected:
            if other.exists() and os.path.samefile(path, other):
                raise InputError(
                    f"{name}: output is the same file as {shown(other)}, "
                    "pick another file"
                )


def check_outside(path: Path, folders: Sequence[Path]) -> None:
    for start in (Path(os.path.abspath(path)), Path(os.path.realpath(path))):
        for item in [start, *start.parents]:
            if not item.exists():
                continue
            for folder in folders:
                if os.path.samefile(item, folder):
                    raise InputError(
                        f"{shown(path)}: output is inside the input folder "
                        f"{shown(folder)}, pick a path outside it"
                    )


@contextmanager
def atomic_text(path: Path, protected: Sequence[Path] = ()) -> Iterator[TextIO]:
    check_output(path, protected)
    failed = f"{shown(path)}: file cannot be written, {WRITE_HINT}"
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o666 & ~_umask()
    try:
        fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".rfikit-", suffix=".tmp")
    except OSError:
        raise InputError(failed) from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            yield handle
        os.chmod(temp, mode)
        os.replace(temp, path)
    except OSError:
        _remove(temp)
        raise InputError(failed) from None
    except BaseException:
        _remove(temp)
        raise
