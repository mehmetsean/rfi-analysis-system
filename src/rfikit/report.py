import csv
import io
from collections.abc import Iterable, Sequence

LEADING = ("=", "+", "-", "@", "＝", "＋", "－", "＠")
CONTROL = ("\t", "\r", "\n")


def escape_cell(value: str) -> str:
    probe = value.lstrip().removeprefix("﻿").lstrip()
    if value.startswith(CONTROL) or probe.startswith(LEADING):
        return "'" + value
    return value


def csv_chunk(rows: Iterable[Sequence[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for row in rows:
        writer.writerow([escape_cell(cell) for cell in row])
    return buffer.getvalue()


def csv_text(header: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    return csv_chunk([header]) + csv_chunk(rows)
