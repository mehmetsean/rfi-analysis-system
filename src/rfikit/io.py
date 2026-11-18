import csv
import io
import json
from pathlib import Path

from rfikit.types import Rfi

MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100_000
MAX_FIELD = 100_000
REQUIRED = ("rfi_id", "subject", "question")
OPTIONAL = ("response",)
FIELDS = REQUIRED + OPTIONAL


class InputError(ValueError):
    pass


def _read_file(path: Path) -> str:
    name = path.name
    if path.is_symlink():
        raise InputError(f"{name}: symbolic links are not read")
    if not path.is_file():
        raise InputError(f"{name}: missing or not a regular file")
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError:
        raise InputError(f"{name}: file cannot be read") from None
    if len(raw) > MAX_BYTES:
        raise InputError(f"{name}: file is over the limit of {MAX_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(f"{name}: file is not valid UTF-8, save it as UTF-8") from None
    return text.removeprefix("﻿")


def read_text(path: Path) -> str:
    return _read_file(path)


def read_column_map(path: Path) -> dict[str, str]:
    name = path.name
    text = _read_file(path)
    try:
        data = json.loads(text)
    except ValueError:
        raise InputError(f"{name}: not valid JSON") from None
    if not isinstance(data, dict):
        raise InputError(f"{name}: the column map must be a JSON object")
    found: dict[str, str] = {}
    for key, value in data.items():
        if key not in FIELDS:
            raise InputError(f"{name}: unknown key {key!r}, allowed: {list(FIELDS)}")
        if not isinstance(value, str) or value == "":
            raise InputError(f"{name}: the value of {key!r} must be a column name")
        found[key] = value
    return found


def _header_index(
    name: str, header: list[str], column_map: dict[str, str]
) -> dict[str, int]:
    for column in header:
        if header.count(column) > 1:
            raise InputError(f"{name}: duplicate column {column!r}")
    index: dict[str, int] = {}
    for field in FIELDS:
        column = column_map.get(field, field)
        if column in header:
            index[field] = header.index(column)
        elif field in REQUIRED or field in column_map:
            raise InputError(f"{name}: missing column {column!r} for {field}")
    return index


def read_rfis(path: Path, column_map: dict[str, str] | None = None) -> list[Rfi]:
    name = path.name
    text = _read_file(path)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rfis: list[Rfi] = []
    seen: set[str] = set()
    try:
        header = next(reader, None)
        if header is None:
            raise InputError(f"{name}: file is empty")
        index = _header_index(name, header, column_map or {})
        for cells in reader:
            line = reader.line_num
            if not cells:
                continue
            if len(cells) != len(header):
                raise InputError(
                    f"{name} line {line}: expected {len(header)} cells, "
                    f"got {len(cells)}"
                )
            if len(rfis) >= MAX_ROWS:
                raise InputError(f"{name}: more than {MAX_ROWS} rows")
            values = {f: cells[i] for f, i in index.items()}
            for field, value in values.items():
                if len(value) > MAX_FIELD:
                    raise InputError(
                        f"{name} line {line}, column {field}: "
                        f"value is over {MAX_FIELD} characters"
                    )
            rfi_id = values["rfi_id"]
            if rfi_id == "":
                raise InputError(f"{name} line {line}: rfi_id is empty")
            if rfi_id in seen:
                raise InputError(f"{name} line {line}: rfi_id {rfi_id!r} repeats")
            seen.add(rfi_id)
            rfis.append(
                Rfi(
                    rfi_id,
                    values["subject"],
                    values["question"],
                    values.get("response", ""),
                )
            )
    except csv.Error as error:
        raise InputError(f"{name}: bad CSV: {error}") from None
    return rfis
